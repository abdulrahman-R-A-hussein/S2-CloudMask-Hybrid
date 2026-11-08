"""Accuracy metrics for binary cloud/shadow masks, with site-level bootstrap CIs.

Positive class = "contaminated" (label 1 thick, 2 thin, 3 shadow). Label 0 = clear.
Definitions (match the 2026 CloudSEN12+ audit, so numbers are comparable):
- leak     = contaminated pixels the mask accepts as clear / all pixels the mask accepts
           = FN / (FN + TN)
- discard  = clear pixels the mask throws away / all clear pixels = FP / (FP + TN)
- recall   = TP / (TP + FN)        omission = 1 - recall
- precision= TP / (TP + FP)        commission = 1 - precision
- BOA      = (recall + specificity) / 2, specificity = TN / (TN + FP)
- F1       = 2 TP / (2 TP + FP + FN)
Per-class recall uses the label class subset (e.g. recall on thin-cloud pixels only).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

COUNT_COLS = ["tp", "fp", "fn", "tn", "thick_n", "thick_hit", "thin_n", "thin_hit", "shadow_n", "shadow_hit"]


def counts(pred: np.ndarray, label: np.ndarray, sel: np.ndarray) -> dict[str, int]:
    """Confusion counts on the selected pixels."""
    p = pred[sel]
    y = label[sel]
    pos = y > 0
    out = {
        "tp": int(np.sum(p & pos)),
        "fp": int(np.sum(p & ~pos)),
        "fn": int(np.sum(~p & pos)),
        "tn": int(np.sum(~p & ~pos)),
    }
    for name, cls in (("thick", 1), ("thin", 2), ("shadow", 3)):
        m = y == cls
        out[f"{name}_n"] = int(m.sum())
        out[f"{name}_hit"] = int(np.sum(p & m))
    return out


def _safe(a: float, b: float) -> float:
    return float(a) / float(b) if b else float("nan")


def scores(c: pd.Series | dict) -> dict[str, float]:
    tp, fp, fn, tn = (float(c[k]) for k in ("tp", "fp", "fn", "tn"))
    rec = _safe(tp, tp + fn)
    spec = _safe(tn, tn + fp)
    return {
        "leak_%": 100 * _safe(fn, fn + tn),
        "discard_%": 100 * _safe(fp, fp + tn),
        "recall_%": 100 * rec,
        "precision_%": 100 * _safe(tp, tp + fp),
        "F1_%": 100 * _safe(2 * tp, 2 * tp + fp + fn),
        "BOA_%": 100 * (rec + spec) / 2,
        "thick_recall_%": 100 * _safe(c["thick_hit"], c["thick_n"]),
        "thin_recall_%": 100 * _safe(c["thin_hit"], c["thin_n"]),
        "shadow_recall_%": 100 * _safe(c["shadow_hit"], c["shadow_n"]),
    }


def summarize(df: pd.DataFrame, group_cols: list[str], site_col: str = "roi_id",
              n_boot: int = 1000, seed: int = 0) -> pd.DataFrame:
    """Pooled (micro) scores per group, with 95 % bootstrap CIs resampling sites."""
    rng = np.random.default_rng(seed)
    rows = []
    for key, g in df.groupby(group_cols, sort=False):
        key = key if isinstance(key, tuple) else (key,)
        per_site = g.groupby(site_col)[COUNT_COLS].sum()
        point = scores(per_site.sum())
        sites = per_site.to_numpy(dtype=float)
        n = len(sites)
        idx = rng.integers(0, n, (n_boot, n))
        with np.errstate(invalid="ignore", divide="ignore"):
            boot = pd.DataFrame(scores_arr(sites[idx].sum(axis=1)))
        row = dict(zip(group_cols, key))
        row.update({"n_sites": n, "n_patches": int(g["patch"].nunique()), "n_pixels": int(per_site[["tp", "fp", "fn", "tn"]].to_numpy().sum())})
        for m, v in point.items():
            row[m] = v
            lo, hi = np.nanpercentile(boot[m], [2.5, 97.5]) if boot[m].notna().any() else (np.nan, np.nan)
            row[m.replace("_%", "_lo")] = lo
            row[m.replace("_%", "_hi")] = hi
        rows.append(row)
    return pd.DataFrame(rows)


# --- R1: vectorised bootstrap, paired method differences, stratum differences ----------
def scores_arr(s: np.ndarray) -> dict[str, np.ndarray]:
    """``scores`` for many count vectors at once; ``s`` has COUNT_COLS on the last axis."""
    c = {k: s[..., i].astype(float) for i, k in enumerate(COUNT_COLS)}
    with np.errstate(invalid="ignore", divide="ignore"):
        rec = c["tp"] / (c["tp"] + c["fn"])
        spec = c["tn"] / (c["tn"] + c["fp"])
        return {
            "leak_%": 100 * c["fn"] / (c["fn"] + c["tn"]),
            "discard_%": 100 * c["fp"] / (c["fp"] + c["tn"]),
            "recall_%": 100 * rec,
            "precision_%": 100 * c["tp"] / (c["tp"] + c["fp"]),
            "F1_%": 100 * 2 * c["tp"] / (2 * c["tp"] + c["fp"] + c["fn"]),
            "BOA_%": 100 * (rec + spec) / 2,
            "thick_recall_%": 100 * c["thick_hit"] / c["thick_n"],
            "thin_recall_%": 100 * c["thin_hit"] / c["thin_n"],
            "shadow_recall_%": 100 * c["shadow_hit"] / c["shadow_n"],
        }


def boot_index(n_sites: int, n_boot: int = 1000, seed: int = 0) -> np.ndarray:
    """One resampling matrix (n_boot x n_sites). Reusing it makes comparisons paired."""
    return np.random.default_rng(seed).integers(0, n_sites, (n_boot, n_sites))


def site_table(df: pd.DataFrame, sites: list, site_col: str = "roi_id") -> np.ndarray:
    """Per-site summed counts in a fixed site order (sites without rows count as zero)."""
    return df.groupby(site_col)[COUNT_COLS].sum().reindex(sites, fill_value=0).to_numpy(dtype=float)


def _diff_row(a: np.ndarray, b: np.ndarray, idx: np.ndarray, metric_list: list[str]) -> dict:
    pa, pb = scores_arr(a.sum(0)), scores_arr(b.sum(0))
    ba, bb = scores_arr(a[idx].sum(1)), scores_arr(b[idx].sum(1))
    row = {}
    for m in metric_list:
        d = ba[m] - bb[m]
        d = d[~np.isnan(d)]
        k = m.replace("_%", "")
        row[f"{k}_diff"] = float(pa[m] - pb[m])
        if len(d):
            row[f"{k}_lo"], row[f"{k}_hi"] = (float(x) for x in np.percentile(d, [2.5, 97.5]))
            # two-sided bootstrap p: how often the resampled difference crosses zero
            row[f"{k}_p"] = float(min(1.0, 2 * min(np.mean(d <= 0), np.mean(d >= 0))))
        else:
            row[f"{k}_lo"] = row[f"{k}_hi"] = row[f"{k}_p"] = float("nan")
    return row


DIFF_METRICS = ["BOA_%", "leak_%", "discard_%", "F1_%", "shadow_recall_%", "thin_recall_%"]


def paired_diff(df: pd.DataFrame, a: str, b: str, stratum: str, site_col: str = "roi_id",
                n_boot: int = 1000, seed: int = 0, metric_list: list[str] = DIFF_METRICS) -> dict:
    """Method a minus method b on one stratum, resampling the same sites for both (paired)."""
    sub = df[df.stratum == stratum]
    sites = sorted(set(sub.loc[sub.method == a, site_col]) & set(sub.loc[sub.method == b, site_col]))
    idx = boot_index(len(sites), n_boot, seed)
    row = {"stratum": stratum, "a": a, "b": b, "n_sites": len(sites)}
    row.update(_diff_row(site_table(sub[sub.method == a], sites, site_col),
                         site_table(sub[sub.method == b], sites, site_col), idx, metric_list))
    return row


def stratum_diff(df: pd.DataFrame, method: str, s1: str, s2: str, site_col: str = "roi_id",
                 n_boot: int = 1000, seed: int = 0, metric_list: list[str] = DIFF_METRICS) -> dict:
    """Stratum s1 minus s2 for one method (e.g. water - land, H1), resampling sites jointly."""
    sub = df[df.method == method]
    sites = sorted(set(sub[site_col]))
    idx = boot_index(len(sites), n_boot, seed)
    row = {"method": method, "s1": s1, "s2": s2, "n_sites": len(sites),
           "n_sites_s1": int(sub.loc[sub.stratum == s1, site_col].nunique())}
    row.update(_diff_row(site_table(sub[sub.stratum == s1], sites, site_col),
                         site_table(sub[sub.stratum == s2], sites, site_col), idx, metric_list))
    return row
