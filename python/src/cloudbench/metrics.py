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
        boot = []
        for _ in range(n_boot):
            idx = rng.integers(0, n, n)
            boot.append(scores(dict(zip(COUNT_COLS, sites[idx].sum(axis=0)))))
        boot = pd.DataFrame(boot)
        row = dict(zip(group_cols, key))
        row.update({"n_sites": n, "n_patches": int(g["patch"].nunique()), "n_pixels": int(per_site[["tp", "fp", "fn", "tn"]].to_numpy().sum())})
        for m, v in point.items():
            row[m] = v
            lo, hi = np.nanpercentile(boot[m], [2.5, 97.5]) if boot[m].notna().any() else (np.nan, np.nan)
            row[m.replace("_%", "_lo")] = lo
            row[m.replace("_%", "_hi")] = hi
        rows.append(row)
    return pd.DataFrame(rows)
