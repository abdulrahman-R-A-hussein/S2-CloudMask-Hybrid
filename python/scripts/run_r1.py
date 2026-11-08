"""R1 development benchmark (validation split): every method, threshold sweeps, coast stratum,
paired site-bootstrap tests, water-vs-land differences (H1) and the dataset table T1.

Runs from the local cache only (no network for pixels): CloudSEN12+ arrays, GEE detector inputs
(data.gee_inputs), the alignment gate (scripts/check_gee_alignment.py --n 0) and, when present,
deep-learning masks written by scripts/run_dl.py (dl_<model>_<tid>.npz).

Main results use only patches that pass the alignment gate (EXPERIMENT_PROTOCOL §2: failures are
listed and excluded). A sensitivity table repeats the main methods on all patches.

Usage (from python/):  .venv/Scripts/python.exe scripts/run_r1.py --run r1_2026-11-08
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from cloudbench import data, detectors, metrics, strata  # noqa: E402

WATER_RICH_MIN = 0.05
DL_MODELS = {"omnicloudmask": "OmniCloudMask (DL)"}
SWEEPS = {
    "cs": [round(t, 2) for t in np.arange(0.40, 0.801, 0.05)],
    "cs_cdf": [round(t, 2) for t in np.arange(0.40, 0.801, 0.05)],
    "s2cloudless": list(range(20, 61, 5)),
}
# Pairs tested with the paired site bootstrap (a minus b). cs<0.60 is the best GEE single mask
# in the pilot, so it is the reference for the fusion rules.
PAIRS = [
    ("v1.0.2 union (std)", "cs<0.60"),
    ("v1.0.2 union+shadow", "v1.0.2 union (std)"),
    ("v1.0.2 FINAL (smoothed)", "v1.0.2 union+shadow"),
    ("v1.0.2 FINAL (smoothed)", "cs<0.60"),
    ("family 2-of-3", "cs<0.60"),
    ("cs<0.60", "cs_cdf<0.60"),
    ("cs<0.60", "SCL"),
    ("cs<0.60", "s2cloudless>50"),
    ("UnetMobV2-v2 (DL, in-domain)", "cs<0.60"),
    ("SEnSeIv2 (DL)", "cs<0.60"),
    ("OmniCloudMask (DL)", "cs<0.60"),
    ("OmniCloudMask (DL)", "UnetMobV2-v2 (DL, in-domain)"),
]
PAIR_STRATA = ["all", "water", "land", "coast (<=200 m)"]
OPERATIONAL = ["SCL", "s2cloudless>50", "cs<0.60", "cs_cdf<0.60", "QA60", "v1.0.2 union (std)",
               "v1.0.2 union+shadow", "v1.0.2 FINAL (smoothed)"]


def git_hash() -> str:
    try:
        return subprocess.run(["git", "-c", "safe.directory=*", "rev-parse", "--short", "HEAD"],
                              cwd=ROOT, capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def load_patch(tid: str) -> dict:
    with np.load(data.CACHE / f"{tid}.npz") as z:
        cs12 = {k: z[k] for k in z.files}
    with np.load(data.CACHE / f"gee_{tid}.npz") as z:
        gee = {k: z[k] for k in z.files}
    p = data.assemble(cs12, gee)
    for key in DL_MODELS:
        f = data.CACHE / f"dl_{key}_{tid}.npz"
        if f.exists():
            with np.load(f) as z:
                p[f"dl_{key}"] = z["mask"]
    return p


def methods_for(p: dict) -> dict[str, np.ndarray]:
    m = detectors.v102_all(p)
    fam = [m["SCL"], m["s2cloudless>50"], m["cs<0.60"] | m["cs_cdf<0.60"]]
    m["family 1-of-3"] = detectors.k_of_n(fam, 1)
    # morphology ablation: buffer without the erosion that deletes small clouds (AUDIT F-05/F-12)
    m["v1.0.2 union+shadow, buffer only"] = detectors.morphology(m["v1.0.2 union+shadow"], 0, 50)
    m["QA60"] = detectors.qa60_mask(p["qa60"])
    m["UnetMobV2-v2 (DL, in-domain)"] = detectors.class_mask(p["unet_v2"])
    m["SEnSeIv2 (DL)"] = detectors.class_mask(p["sensei_v2"])
    for key, name in DL_MODELS.items():
        if f"dl_{key}" in p:
            m[name] = detectors.class_mask(p[f"dl_{key}"])
    return m


def sweep_masks(p: dict):
    for t in SWEEPS["cs"]:
        yield "cs", t, detectors.cs_mask(p["cs"], t)
    for t in SWEEPS["cs_cdf"]:
        yield "cs_cdf", t, detectors.cs_mask(p["cs_cdf"], t)
    for t in SWEEPS["s2cloudless"]:
        yield "s2cloudless", t, detectors.s2cloudless_mask(p["s2cl"], t)


def work(args) -> tuple[list, list, dict]:
    tid, meta = args
    p = load_patch(tid)
    valid = data.valid_mask(p)
    st = strata.surface_strata(p["lc10"], valid)
    water_frac = st["water"].sum() / max(valid.sum(), 1)
    rows, srows = [], []
    for name, pred in methods_for(p).items():
        for sn, sel in st.items():
            if sel.any():
                rows.append({**meta, "method": name, "stratum": sn, "water_frac": float(water_frac),
                             **metrics.counts(pred, p["label"], sel)})
    for det, t, pred in sweep_masks(p):
        for sn in ("all", "water", "land"):
            sel = st[sn]
            if sel.any():
                srows.append({**meta, "detector": det, "threshold": t, "method": f"{det} T={t}",
                              "stratum": sn, **metrics.counts(pred, p["label"], sel)})
    # calibration: treat each continuous score as P(contaminated) and bin it (10 equal bins)
    crows = []
    probs = {"cs (1 - cs)": 1 - p["cs"] / 1e4, "cs_cdf (1 - cs_cdf)": 1 - p["cs_cdf"] / 1e4,
             "s2cloudless (prob/100)": p["s2cl"] / 100.0}
    for name, pr in probs.items():
        for sn in ("all", "water", "land"):
            sel = st[sn]
            if not sel.any():
                continue
            x = np.clip(pr[sel], 0, 1)
            y = p["label"][sel] > 0
            b = np.minimum((x * 10).astype(int), 9)
            crows.append({**meta, "score": name, "stratum": sn,
                          **{f"n{k}": int(np.sum(b == k)) for k in range(10)},
                          **{f"pos{k}": int(np.sum(y & (b == k))) for k in range(10)},
                          **{f"sum{k}": float(np.sum(x[b == k])) for k in range(10)}})
    lab = p["label"][valid]
    t1 = {**meta, "valid_px": int(valid.sum()), "water_frac": float(water_frac),
          "coast_px": int(st["coast (<=200 m)"].sum()),
          **{f"{n}_px": int(np.sum(lab == c)) for c, n in enumerate(("clear", "thick", "thin", "shadow"))},
          **{f"water_{n}_px": int(np.sum(p["label"][st["water"]] == c))
             for c, n in enumerate(("clear", "thick", "thin", "shadow"))},
          "has_dl": {k: f"dl_{k}" in p for k in DL_MODELS}}
    return rows, srows, t1, crows


def ece_table(cal: pd.DataFrame) -> pd.DataFrame:
    """Expected calibration error and the reliability curve per score and stratum."""
    out = []
    for (score, sn), g in cal.groupby(["score", "stratum"], sort=False):
        n = np.array([g[f"n{k}"].sum() for k in range(10)], float)
        pos = np.array([g[f"pos{k}"].sum() for k in range(10)], float)
        s = np.array([g[f"sum{k}"].sum() for k in range(10)], float)
        with np.errstate(invalid="ignore", divide="ignore"):
            conf, freq = s / n, pos / n
        ok = n > 0
        ece = float(np.sum(n[ok] / n.sum() * np.abs(conf[ok] - freq[ok])))
        out.append({"score": score, "stratum": sn, "pixels": int(n.sum()), "ECE_%": 100 * ece,
                    **{f"bin{k}_mean_p": conf[k] for k in range(10)},
                    **{f"bin{k}_obs_freq": freq[k] for k in range(10)},
                    **{f"bin{k}_share_%": 100 * n[k] / n.sum() for k in range(10)}})
    return pd.DataFrame(out)


def table(res: pd.DataFrame, cols: list[str], title: str) -> list[str]:
    if res.empty:
        return []
    out = [f"### {title} (sites={res.n_sites.iloc[0]}, patches={res.n_patches.iloc[0]}, "
           f"pixels={res.n_pixels.iloc[0]:,})", "",
           "| Method | " + " | ".join(c.replace("_%", " %") for c in cols) + " |", "|---|" + "---|" * len(cols)]
    for _, r in res.iterrows():
        cells = [f"{r[c]:.1f} [{r[c.replace('_%', '_lo')]:.1f}, {r[c.replace('_%', '_hi')]:.1f}]" for c in cols]
        out.append(f"| {r.method} | " + " | ".join(cells) + " |")
    return out + [""]


def diff_table(df: pd.DataFrame, label_cols: list[str], mets: list[str]) -> list[str]:
    out = ["| " + " | ".join(label_cols) + " | sites | " + " | ".join(f"Δ{m} [95 % CI] p" for m in mets) + " |",
           "|" + "---|" * (len(label_cols) + 1 + len(mets))]
    for _, r in df.iterrows():
        cells = []
        for m in mets:
            if np.isnan(r[f"{m}_diff"]):
                cells.append("n/a")
            else:
                cells.append(f"{r[f'{m}_diff']:+.1f} [{r[f'{m}_lo']:+.1f}, {r[f'{m}_hi']:+.1f}] {r[f'{m}_p']:.3f}")
        out.append("| " + " | ".join(str(r[c]) for c in label_cols) + f" | {r.n_sites} | " + " | ".join(cells) + " |")
    return out + [""]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=f"r1_{time.strftime('%Y-%m-%d')}")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--n-boot", type=int, default=1000)
    args = ap.parse_args()
    out = ROOT.parent / "results" / args.run
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    log = ["R1 development benchmark, VALIDATION split (test split locked, D-15)",
           "detector inputs: Earth Engine cache (D-17); labels/WorldCover/bundled DL masks: CloudSEN12+"]

    l1, *_ = data.load_tables()
    sel = data.select(l1, "validation")
    gate = pd.read_csv(out / "gee_alignment.csv")
    passed = set(gate.loc[gate.gate_pass, "patch"])
    zero_shift = set(gate.loc[gate.best_shift_B2 == "(0, 0)", "patch"])
    log.append(f"alignment gate: {len(passed)}/{len(gate)} pass; failures excluded from the main tables")
    jobs = []
    for pos in sel.index:
        r = l1.loc[pos]
        tid = r["tortilla:id"]
        jobs.append((tid, {"patch": tid, "roi_id": r["roi_id"], "equi_zone": r["equi_zone"],
                           "date": tid.split("__")[1][:8], "aligned": tid in passed}))
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        res = list(pool.map(work, jobs, chunksize=4))
    counts = pd.DataFrame([r for rr, _, _, _ in res for r in rr])
    sweep = pd.DataFrame([r for _, ss, _, _ in res for r in ss])
    t1 = pd.DataFrame([t for _, _, t, _ in res])
    cal = pd.DataFrame([c for _, _, _, cc in res for c in cc])
    ece = ece_table(cal[cal.aligned])
    ece.to_csv(out / "calibration_ece.csv", index=False, float_format="%.4f")
    pw = counts[counts.stratum == "all"].groupby("patch")["water_frac"].first()
    rich = set(pw[pw >= WATER_RICH_MIN].index)
    counts["patch_group"] = np.where(counts.patch.isin(rich), "water-rich patch", "other patch")
    counts.to_csv(out / "counts.csv", index=False)
    sweep.to_csv(out / "sweep_counts.csv", index=False)
    log.append(f"patches={len(jobs)} water-rich (>= {WATER_RICH_MIN:.0%} water)={len(rich)} "
               f"seconds_scoring={time.time() - t0:.0f}")
    dl_cov = {k: int(t1.has_dl.map(lambda d: d[k]).sum()) for k in DL_MODELS}
    log.append(f"deep-learning masks found in cache: {json.dumps(dl_cov)} of {len(t1)} patches")

    # a method must be scored on every patch, or its pooled numbers are not comparable
    cover = counts[counts.stratum == "all"].groupby("method").patch.nunique()
    partial = sorted(cover[cover < len(jobs)].index)
    if partial:
        log.append(f"DROPPED (not present on every patch): {partial}")
        counts = counts[~counts.method.isin(partial)]
    main_c = counts[counts.aligned]
    nb = args.n_boot
    m_px = metrics.summarize(main_c, ["stratum", "method"], n_boot=nb)
    m_px.insert(0, "grouping", "pixel stratum")
    m_pg = metrics.summarize(main_c[main_c.stratum == "all"], ["patch_group", "method"], n_boot=nb)
    m_pg = m_pg.rename(columns={"patch_group": "stratum"})
    m_pg.insert(0, "grouping", "patch group")
    met = pd.concat([m_px, m_pg], ignore_index=True)
    met.to_csv(out / "metrics.csv", index=False, float_format="%.3f")

    sens = metrics.summarize(counts[counts.stratum.isin(["all", "water", "land"])], ["stratum", "method"], n_boot=nb)
    sens.to_csv(out / "metrics_all_patches_sensitivity.csv", index=False, float_format="%.3f")
    # second sensitivity: keep every patch whose best B2 shift is zero, whatever its r
    # (r < 0.99 at zero shift can come from low-contrast, fully cloudy scenes)
    zs = counts[counts.patch.isin(zero_shift) & counts.stratum.isin(["all", "water", "land"])]
    sens2 = metrics.summarize(zs, ["stratum", "method"], n_boot=nb)
    sens2.to_csv(out / "metrics_zero_shift_sensitivity.csv", index=False, float_format="%.3f")
    log.append(f"sensitivity subsets: all patches={counts.patch.nunique()}, zero best shift={len(zero_shift)}")

    sw = metrics.summarize(sweep[sweep.aligned], ["stratum", "detector", "threshold"], n_boot=nb)
    sw.to_csv(out / "sweep_metrics.csv", index=False, float_format="%.3f")

    methods_present = set(main_c.method)
    pairs = [metrics.paired_diff(main_c, a, b, s, n_boot=nb) for a, b in PAIRS
             if a in methods_present and b in methods_present for s in PAIR_STRATA]
    pairs = pd.DataFrame(pairs)
    pairs.to_csv(out / "paired_differences.csv", index=False, float_format="%.3f")

    h1 = pd.DataFrame([metrics.stratum_diff(main_c, m, "water", "land", n_boot=nb)
                       for m in sorted(methods_present)])
    h1.to_csv(out / "water_minus_land.csv", index=False, float_format="%.3f")

    # T1: dataset summary (aligned patches)
    ta = t1[t1.aligned]
    t1_rows = []
    for name, g in (("all patches", ta), ("water-rich patches", ta[ta.patch.isin(rich)])):
        px = g[["clear_px", "thick_px", "thin_px", "shadow_px"]].sum()
        wpx = g[["water_clear_px", "water_thick_px", "water_thin_px", "water_shadow_px"]].sum()
        t1_rows.append({"subset": name, "patches": len(g), "sites": g.roi_id.nunique(),
                        "valid_px": int(g.valid_px.sum()), "water_px": int(wpx.sum()),
                        "coast_px": int(g.coast_px.sum()),
                        **{f"{k.replace('_px', '')}_%": 100 * v / px.sum() for k, v in px.items()},
                        **{f"{k.replace('_px', '')}_%": 100 * v / max(wpx.sum(), 1) for k, v in wpx.items()},
                        "date_min": g.date.min(), "date_max": g.date.max(),
                        "equi_zones": g.equi_zone.nunique()})
    t1s = pd.DataFrame(t1_rows)
    t1s.to_csv(out / "t1_dataset.csv", index=False, float_format="%.2f")

    # ---------------- summary.md (generated from the CSVs above only) ----------------
    cols = ["leak_%", "discard_%", "BOA_%", "F1_%", "thin_recall_%", "shadow_recall_%"]
    L = [f"# R1 development benchmark — generated by scripts/run_r1.py ({args.run})", "",
         "DEVELOPMENT numbers: CloudSEN12+ **validation** split, expert labels, 509×509 patches, patches that pass",
         "the GEE alignment gate. Not paper test results (test split locked, D-15).",
         "Leak = contaminated share of accepted pixels; discard = share of clear pixels thrown away.",
         "Brackets = 95 % bootstrap CI over sites. Water = ESA WorldCover class 80; coast = ≤ 200 m from the",
         "water/land edge on either side.", "",
         "## T1 Dataset", "",
         "| Subset | patches | sites | valid px | water px | coast px | clear % | thick % | thin % | shadow % | water: thick % | water: thin % | water: shadow % | dates |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in t1s.iterrows():
        L.append(f"| {r.subset} | {r.patches} | {r.sites} | {r.valid_px:,} | {r.water_px:,} | {r.coast_px:,} | "
                 f"{r['clear_%']:.1f} | {r['thick_%']:.1f} | {r['thin_%']:.1f} | {r['shadow_%']:.1f} | "
                 f"{r['water_thick_%']:.1f} | {r['water_thin_%']:.1f} | {r['water_shadow_%']:.1f} | "
                 f"{r.date_min}–{r.date_max} |")
    L += ["", "## T2 Main results by pixel stratum", ""]
    for s in ["all", "water", "land", "coast (<=200 m)", "open water (>200 m)"]:
        L += table(met[(met.grouping == "pixel stratum") & (met.stratum == s)], cols, f"Stratum: {s}")
    L += ["## T2b By patch group", ""]
    for s in ["water-rich patch", "other patch"]:
        L += table(met[(met.grouping == "patch group") & (met.stratum == s)], cols, s)
    L += ["## H1 Water minus land (same method; joint site bootstrap)", "",
          "Positive Δleak = more leak over water. p = two-sided bootstrap p.", ""]
    L += diff_table(h1, ["method"], ["leak", "discard", "BOA", "shadow_recall"])
    L += ["## Paired method differences (a − b; paired site bootstrap)", ""]
    L += diff_table(pairs, ["stratum", "a", "b"], ["BOA", "leak", "discard", "shadow_recall"])
    L += ["## T3 Threshold sweeps (single detectors)", "",
          "Direction: cs/cs_cdf flag where score < T (higher T masks more); s2cloudless flags where",
          "probability > T (higher T masks less).", ""]
    for s in ["all", "water"]:
        L += [f"### Stratum: {s}", "", "| Detector | T | leak % | discard % | BOA % | shadow recall % |", "|---|---|---|---|---|---|"]
        for _, r in sw[sw.stratum == s].iterrows():
            L.append(f"| {r.detector} | {r.threshold:g} | {r['leak_%']:.1f} | {r['discard_%']:.1f} | "
                     f"{r['BOA_%']:.1f} [{r.BOA_lo:.1f}, {r.BOA_hi:.1f}] | {r['shadow_recall_%']:.1f} |")
        best = sw[sw.stratum == s].sort_values("BOA_%", ascending=False).groupby("detector").head(1)
        L += ["", "Best BOA per detector: " + "; ".join(f"{r.detector} T={r.threshold:g} ({r['BOA_%']:.1f} %)"
                                                    for _, r in best.iterrows()), ""]
    L += ["## Calibration of the continuous scores (ECE, 10 equal-width bins)", "",
          "The score is read as P(contaminated). ECE = pixel-weighted mean |mean score − observed contaminated share|.",
          "Lower is better calibrated. No method is recalibrated here (that is module M3).", "",
          "| Score | stratum | pixels | ECE % |", "|---|---|---|---|"]
    for _, r in ece.iterrows():
        L.append(f"| {r.score} | {r.stratum} | {r.pixels:,} | {r['ECE_%']:.1f} |")
    L += ["", "## Sensitivity: all patches including alignment-gate failures", ""]
    for s in ["all", "water"]:
        L += table(sens[sens.stratum == s], ["leak_%", "discard_%", "BOA_%"], f"Stratum: {s}, all patches")
    L += ["## Sensitivity: patches whose best B2 shift is zero (r criterion dropped)", ""]
    for s in ["all", "water"]:
        L += table(sens2[sens2.stratum == s], ["leak_%", "discard_%", "BOA_%"], f"Stratum: {s}, zero-shift patches")
    (out / "summary.md").write_text("\n".join(L), encoding="utf-8")

    import scipy  # noqa: E401
    log += [f"n_boot={nb} seed=0 sweeps={json.dumps(SWEEPS)}",
            f"params={json.dumps(detectors.PARAMS_V102)}",
            f"seconds_total={time.time() - t0:.0f}", f"git={git_hash()}", f"python={platform.python_version()}",
            f"numpy={np.__version__} pandas={pd.__version__} scipy={scipy.__version__}"]
    with open(out / "run.log", "a", encoding="utf-8") as f:
        f.write("\n".join(log) + "\n")
    print("\n".join(log))


if __name__ == "__main__":
    main()
