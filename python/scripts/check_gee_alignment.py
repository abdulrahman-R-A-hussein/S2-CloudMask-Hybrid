"""Alignment and provenance gate between CloudSEN12+ patches and Earth Engine.

For N cached validation patches, fetch from GEE on the patch's own grid:
  - COPERNICUS/S2_HARMONIZED B2 (L1C) -> compare with the CloudSEN12+ L1C B2
  - GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED cs_cdf -> compare with cloudsen12-extra cs_cdf
Gate (docs/EXPERIMENT_PROTOCOL.md): Pearson r > 0.99 at zero shift, and zero shift is the best
of the 3x3 one-pixel shifts. Writes results/<run>/gee_alignment.csv and appends to run.log.

Needs GEE_SERVICE_ACCOUNT_JSON set to the service-account key path (never printed).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from cloudbench import auth, data  # noqa: E402


def fetch(ee, collection: str, index: str, band: str, crs: str, gt: list[float]) -> np.ndarray:
    img = ee.ImageCollection(collection).filter(ee.Filter.eq("system:index", index)).first().select([band])
    req = {
        "expression": img,
        "fileFormat": "NUMPY_NDARRAY",
        "grid": {
            "dimensions": {"width": data.PATCH, "height": data.PATCH},
            "affineTransform": {"scaleX": gt[1], "shearX": gt[2], "translateX": gt[0],
                                "shearY": gt[4], "scaleY": gt[5], "translateY": gt[3]},
            "crsCode": crs,
        },
    }
    arr = ee.data.computePixels(req)
    return np.asarray(arr[band], dtype=float)


def best_shift(a: np.ndarray, b: np.ndarray, ok: np.ndarray):
    """Pearson r for one-pixel shifts of b relative to a; returns (r at 0,0), best (dr, dc)."""
    res = {}
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            bs = np.roll(np.roll(b, dr, 0), dc, 1)
            m = ok.copy()
            m[:1, :] = m[-1:, :] = m[:, :1] = m[:, -1:] = False
            res[(dr, dc)] = np.corrcoef(a[m], bs[m])[0, 1]
    return res[(0, 0)], max(res, key=res.get)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--run", default="pilot_2026-11-07")
    args = ap.parse_args()

    import ee
    email = auth.init_ee()
    print(f"Earth Engine initialised as service account ({email.split('@')[1]})")

    l1, *_ = data.load_tables()
    sel = data.select(l1, "validation")
    cached = [p for p in sel.index if (data.CACHE / f"{l1.loc[p, 'tortilla:id']}.npz").exists()]
    rows = []
    step = max(1, len(cached) // args.n)  # spread across sites, not just the first one
    for pos in cached[::step][: args.n]:
        r = l1.loc[pos]
        tid = r["tortilla:id"]
        index = tid.split("__", 1)[1]
        with np.load(data.CACHE / f"{tid}.npz") as z:
            b02, cdf = z["b02_l1c"].astype(float), z["cs_cdf"].astype(float)
        ok = (b02 > 0) & (cdf <= 10000)
        crs, gt = r["stac:crs"], list(r["stac:geotransform"])
        g_b2 = fetch(ee, "COPERNICUS/S2_HARMONIZED", index, "B2", crs, gt)
        g_cdf = fetch(ee, "GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED", index, "cs_cdf", crs, gt)
        r_b2, s_b2 = best_shift(b02, g_b2, ok)
        r_cdf, s_cdf = best_shift(cdf / 10000.0, g_cdf, ok)
        mad = float(np.mean(np.abs(cdf[ok] / 10000.0 - g_cdf[ok])))
        rows.append({"patch": tid, "r_B2": r_b2, "best_shift_B2": s_b2, "r_cs_cdf": r_cdf,
                     "best_shift_cs_cdf": s_cdf, "mean_abs_diff_cs_cdf": mad,
                     "gate_pass": bool(r_b2 > 0.99 and s_b2 == (0, 0))})
        print(rows[-1])
    out = ROOT.parent / "results" / args.run
    out.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(out / "gee_alignment.csv", index=False, float_format="%.4f")
    with open(out / "run.log", "a", encoding="utf-8") as f:
        f.write(f"gee_alignment: {int(df.gate_pass.sum())}/{len(df)} patches pass "
                f"(B2 r>0.99 at zero shift); cs_cdf r min={df.r_cs_cdf.min():.4f}\n")


if __name__ == "__main__":
    main()
