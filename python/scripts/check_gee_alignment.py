"""Alignment and provenance gate between CloudSEN12+ patches and Earth Engine.

For cached validation patches, fetch from GEE on the patch's own grid:
  - COPERNICUS/S2_HARMONIZED B2 (L1C) -> compare with the CloudSEN12+ L1C B2
  - GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED cs_cdf -> compare with cloudsen12-extra cs_cdf
Gate (docs/EXPERIMENT_PROTOCOL.md §2): Pearson r > 0.99 at zero shift, and zero shift is the
best of the 3x3 one-pixel shifts. Writes results/<run>/gee_alignment.csv and appends to run.log.

--n 0 checks every cached patch (R1). Fetched arrays are cached as gee_align_<tid>.npz.
Needs GEE_SERVICE_ACCOUNT_JSON set to the service-account key path (never printed).
"""

from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
        "expression": img.toFloat().unmask(-1),
        "fileFormat": "NUMPY_NDARRAY",
        "grid": {
            "dimensions": {"width": data.PATCH, "height": data.PATCH},
            "affineTransform": {"scaleX": gt[1], "shearX": gt[2], "translateX": gt[0],
                                "shearY": gt[4], "scaleY": gt[5], "translateY": gt[3]},
            "crsCode": crs,
        },
    }
    arr = data.retry(lambda: ee.data.computePixels(req))
    return np.asarray(arr[band], dtype=np.float32)


def gee_align_arrays(ee, tid: str, crs: str, gt: list[float]) -> dict:
    f = data.CACHE / f"gee_align_{tid}.npz"
    if f.exists():
        with np.load(f) as z:
            return {k: z[k] for k in z.files}
    index = tid.split("__", 1)[1]
    out = {"b2": fetch(ee, "COPERNICUS/S2_HARMONIZED", index, "B2", crs, gt),
           "cs_cdf": fetch(ee, "GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED", index, "cs_cdf", crs, gt)}
    np.savez_compressed(f, **out)
    return out


def shift_table(a: np.ndarray, b: np.ndarray, ok: np.ndarray) -> dict:
    """Pearson r for one-pixel shifts of b relative to a (border pixels excluded)."""
    m = ok.copy()
    m[:1, :] = m[-1:, :] = m[:, :1] = m[:, -1:] = False
    res = {}
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            bs = np.roll(np.roll(b, dr, 0), dc, 1)
            mm = m & (bs >= 0)
            if mm.sum() < 100 or np.std(a[mm]) == 0 or np.std(bs[mm]) == 0:
                res[(dr, dc)] = np.nan
            else:
                res[(dr, dc)] = float(np.corrcoef(a[mm], bs[mm])[0, 1])
    return res


def check_patch(ee, tid: str, crs: str, gt: list[float]) -> dict:
    with np.load(data.CACHE / f"{tid}.npz") as z:
        b02, cdf = z["b02_l1c"].astype(float), z["cs_cdf"].astype(float)
    g = gee_align_arrays(ee, tid, crs, gt)
    ok = (b02 > 0) & (cdf <= 10000) & (g["b2"] >= 0)
    t_b2 = shift_table(b02, g["b2"], ok)
    t_cdf = shift_table(cdf / 10000.0, g["cs_cdf"], ok)
    best_b2 = max((k for k in t_b2 if not np.isnan(t_b2[k])), key=t_b2.get, default=(0, 0))
    best_cdf = max((k for k in t_cdf if not np.isnan(t_cdf[k])), key=t_cdf.get, default=(0, 0))
    v = ok & (g["cs_cdf"] >= 0)
    mad = float(np.mean(np.abs(cdf[v] / 10000.0 - g["cs_cdf"][v]))) if v.any() else np.nan
    r0 = t_b2[(0, 0)]
    return {"patch": tid, "r_B2": r0, "best_shift_B2": best_b2, "r_B2_best": t_b2[best_b2],
            "r_cs_cdf": t_cdf[(0, 0)], "best_shift_cs_cdf": best_cdf, "mean_abs_diff_cs_cdf": mad,
            "gate_pass": bool(r0 > 0.99 and best_b2 == (0, 0))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5, help="0 = every cached validation patch")
    ap.add_argument("--run", default="pilot_2026-11-07")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    import ee
    email = auth.init_ee()
    print(f"Earth Engine initialised as service account ({email.split('@')[1]})")

    l1, *_ = data.load_tables()
    sel = data.select(l1, "validation")
    cached = [p for p in sel.index if (data.CACHE / f"{l1.loc[p, 'tortilla:id']}.npz").exists()]
    if args.n:
        step = max(1, len(cached) // args.n)  # spread across sites, not just the first one
        cached = cached[::step][: args.n]
    t0 = time.time()
    rows, failed = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(check_patch, ee, l1.loc[p, "tortilla:id"], l1.loc[p, "stac:crs"],
                            list(l1.loc[p, "stac:geotransform"])): p for p in cached}
        for i, fu in enumerate(as_completed(futs), 1):
            try:
                rows.append(fu.result())
            except Exception as exc:  # noqa: BLE001
                failed.append((l1.loc[futs[fu], "tortilla:id"], repr(exc)[:200]))
            if i % 50 == 0:
                print(f"{i}/{len(futs)} patches, {time.time() - t0:.0f}s", flush=True)
    out = ROOT.parent / "results" / args.run
    out.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows).sort_values("patch")
    df.to_csv(out / "gee_alignment.csv", index=False, float_format="%.4f")
    msg = (f"gee_alignment: {int(df.gate_pass.sum())}/{len(df)} patches pass "
           f"(B2 r>0.99 at zero shift and zero shift best); fetch failures={len(failed)}; "
           f"cs_cdf r at zero shift min={df.r_cs_cdf.min():.4f}")
    with open(out / "run.log", "a", encoding="utf-8") as f:
        f.write(msg + "\n")
        for t, e in failed:
            f.write(f"gee_alignment FAILED {t}: {e}\n")
    print(msg)


if __name__ == "__main__":
    main()
