"""Pilot benchmark R0: every GEE-native detector, the v1.0.2 fusion and two deep-learning masks,
scored against CloudSEN12+ expert labels on the VALIDATION split, water vs land.

Usage (from python/):  .venv/Scripts/python.exe scripts/run_pilot.py [--limit N] [--workers 6]

Outputs (results/<run>/):
  counts.csv   confusion counts per patch x method x stratum (the raw evidence)
  metrics.csv  pooled scores with 95 % site-bootstrap CIs
  summary.md   the main table, generated from metrics.csv
  run.log      config, inputs, failures, timing, versions, git hash

These are PILOT numbers on the validation split. The test split is locked until
docs/EXPERIMENT_PROTOCOL.md is committed (DECISIONS D-15).
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cloudbench import auth, data, detectors, metrics  # noqa: E402

WATER_CLASS = 80  # ESA WorldCover permanent water bodies
WATER_RICH_MIN = 0.05  # a patch is "water-rich" if >= 5 % of its valid pixels are water


def git_hash() -> str:
    try:
        return subprocess.run(["git", "-c", "safe.directory=*", "rev-parse", "--short", "HEAD"],
                              cwd=ROOT, capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def methods_for(p: dict) -> dict[str, np.ndarray]:
    m = detectors.v102_all(p)
    m["QA60"] = detectors.qa60_mask(p["qa60"])
    m["UnetMobV2-v2 (DL, in-domain)"] = detectors.class_mask(p["unet_v2"])
    m["SEnSeIv2 (DL)"] = detectors.class_mask(p["sensei_v2"])
    return m


def provenance(p: dict, meta: dict) -> dict:
    """How far the CloudSEN12+ bundled layers differ from what GEE serves today (D-17)."""
    lab_ok = (p["b02_l1c"] > 0) & (p["label"] <= 3)
    v = lab_ok & p["gee_ok"]
    vc = v & (p["cs12_cs_cdf"] <= 10000)
    r = (np.corrcoef(p["cs12_cs_cdf"][vc] / 1e4, p["cs_cdf"][vc] / 1e4)[0, 1]
         if vc.sum() > 100 and np.std(p["cs_cdf"][vc]) > 0 and np.std(p["cs12_cs_cdf"][vc]) > 0 else np.nan)
    return {**meta,
            "gee_coverage_%": 100 * v.sum() / max(lab_ok.sum(), 1),
            "r_cs_cdf_cs12_vs_gee": r,
            "cs12_cs_cdf_out_of_range_%": 100 * np.mean(p["cs12_cs_cdf"][v] > 10000) if v.any() else np.nan,
            "scl_agree_%": 100 * np.mean(p["cs12_scl"][v] == p["scl"][v]) if v.any() else np.nan,
            "s2cl_exact_%": 100 * np.mean(p["cs12_s2cl"][v] == np.round(p["s2cl"][v])) if v.any() else np.nan}


def score_patch(p: dict, meta: dict) -> list[dict]:
    valid = data.valid_mask(p)
    water = valid & (p["lc10"] == WATER_CLASS)
    land = valid & (p["lc10"] != WATER_CLASS) & (p["lc10"] > 0)
    water_frac = water.sum() / max(valid.sum(), 1)
    strata = {"all": valid, "water": water, "land": land}
    rows = []
    for name, pred in methods_for(p).items():
        for st, sel in strata.items():
            if not sel.any():
                continue
            c = metrics.counts(pred, p["label"], sel)
            rows.append({**meta, "method": name, "stratum": st, "water_frac": float(water_frac), **c})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="validation")
    ap.add_argument("--limit", type=int, default=0, help="0 = all patches in the split")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--run", default=f"pilot_{time.strftime('%Y-%m-%d')}")
    args = ap.parse_args()
    if args.split == "test":
        sys.exit("The test split is locked until docs/EXPERIMENT_PROTOCOL.md is committed (D-15).")

    out = ROOT.parent / "results" / args.run
    out.mkdir(parents=True, exist_ok=True)
    log = []
    t0 = time.time()
    import ee
    auth.init_ee()
    log.append("detector inputs: Earth Engine (S2_SR_HARMONIZED B8+SCL, S2_CLOUD_PROBABILITY, "
               "CLOUD_SCORE_PLUS V1); labels/WorldCover/DL masks: CloudSEN12+ (D-17)")
    l1, l2, ex, l2pos, expos = data.load_tables()
    sel = data.select(l1, args.split)
    if args.limit:
        sel = sel.head(args.limit)
    log.append(f"split={args.split} label_type=high size=509 patches={len(sel)}")

    def work(pos):
        r = l1.loc[pos]
        tid = r["tortilla:id"]
        cs12 = data.read_patch_cs12(l1, l2, ex, l2pos, expos, pos)
        gee = data.gee_inputs(ee, tid, r["stac:crs"], list(r["stac:geotransform"]))
        p = data.assemble(cs12, gee)
        meta = {"patch": tid, "roi_id": r["roi_id"], "s2_id": r["s2_id"],
                "equi_zone": r["equi_zone"], "date": tid.split("__")[1][:8]}
        return score_patch(p, meta), provenance(p, meta)

    rows, prov, failed = [], [], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(work, int(pos)): int(pos) for pos in sel.index}
        for i, fu in enumerate(as_completed(futs), 1):
            try:
                rr, pv = fu.result()
                rows.extend(rr)
                prov.append(pv)
            except Exception as exc:  # noqa: BLE001
                failed.append((l1.loc[futs[fu], "tortilla:id"], repr(exc)[:200]))
            if i % 25 == 0:
                print(f"{i}/{len(futs)} patches, {time.time() - t0:.0f}s", flush=True)

    counts = pd.DataFrame(rows)
    counts.to_csv(out / "counts.csv", index=False)
    pv = pd.DataFrame(prov)
    pv.to_csv(out / "provenance_cs12_vs_gee.csv", index=False, float_format="%.4f")
    log.append(f"provenance (patches={len(pv)}): median r(cs_cdf CS12 vs GEE)={pv['r_cs_cdf_cs12_vs_gee'].median():.3f}; "
               f"patches with r<0.9: {int((pv['r_cs_cdf_cs12_vs_gee'] < 0.9).sum())}; "
               f"median SCL agreement={pv['scl_agree_%'].median():.1f}%; "
               f"median s2cloudless exact match={pv['s2cl_exact_%'].median():.1f}%; "
               f"median GEE coverage of labelled pixels={pv['gee_coverage_%'].median():.1f}% (min {pv['gee_coverage_%'].min():.1f}%)")
    patch_water = counts[counts.stratum == "all"].groupby("patch")["water_frac"].first()
    rich = set(patch_water[patch_water >= WATER_RICH_MIN].index)
    counts["patch_group"] = np.where(counts["patch"].isin(rich), "water-rich patch", "other patch")

    m_px = metrics.summarize(counts, ["stratum", "method"])
    m_px.insert(0, "grouping", "pixel stratum")
    m_pg = metrics.summarize(counts[counts.stratum == "all"], ["patch_group", "method"])
    m_pg.insert(0, "grouping", "patch group")
    m_pg = m_pg.rename(columns={"patch_group": "stratum"})
    res = pd.concat([m_px, m_pg], ignore_index=True)
    res.to_csv(out / "metrics.csv", index=False, float_format="%.3f")

    # summary.md: generated from metrics.csv only
    cols = ["leak_%", "discard_%", "BOA_%", "F1_%", "thin_recall_%", "shadow_recall_%"]
    lines = [f"# Pilot benchmark ({args.split} split) — generated by scripts/run_pilot.py", "",
             "PILOT numbers: validation split, CloudSEN12+ expert labels, 509x509 patches.",
             "Leak = contaminated share of accepted pixels; discard = share of clear pixels thrown away.",
             "Brackets = 95 % bootstrap CI over sites. Water = ESA WorldCover class 80.", ""]
    for st in ["all", "water", "land"]:
        sub = res[(res.grouping == "pixel stratum") & (res.stratum == st)]
        if sub.empty:
            continue
        lines += [f"## Stratum: {st} pixels (sites={sub.n_sites.iloc[0]}, pixels={sub.n_pixels.iloc[0]:,})", "",
                  "| Method | " + " | ".join(c.replace('_%', ' %') for c in cols) + " |",
                  "|---|" + "---|" * len(cols)]
        for _, r in sub.iterrows():
            cells = [f"{r[c]:.1f} [{r[c.replace('_%','_lo')]:.1f}, {r[c.replace('_%','_hi')]:.1f}]" for c in cols]
            lines.append(f"| {r.method} | " + " | ".join(cells) + " |")
        lines.append("")
    (out / "summary.md").write_text("\n".join(lines), encoding="utf-8")

    import rasterio, scipy, tacoreader  # noqa: E401
    log += [f"scored patches={counts.patch.nunique()} failed={len(failed)}",
            f"water-rich patches (>= {WATER_RICH_MIN:.0%} water)={len(rich)}",
            *[f"FAILED {t}: {e}" for t, e in failed],
            f"params={json.dumps(detectors.PARAMS_V102)}",
            f"seconds={time.time() - t0:.0f}", f"git={git_hash()}", f"python={platform.python_version()}",
            f"numpy={np.__version__} pandas={pd.__version__} scipy={scipy.__version__} "
            f"rasterio={rasterio.__version__} tacoreader={tacoreader.__version__}"]
    (out / "run.log").write_text("\n".join(log) + "\n", encoding="utf-8")
    print("\n".join(log[-8:]))
    print((out / "summary.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
