"""CloudSEN12+ access: metadata tables, patch reading, local cache.

Facts established on 2026-11-07 (see docs/LOG.md):
- Tables come from the legacy TACO v1 reader (tacoreader < 1.0).
- ``TortillaDataFrame.read(i)`` takes a *row position*, not an index label, so every table
  here is ``reset_index(drop=True)``.
- 509x509 patches are padded to 512x512. The padding is rows 509-511 and columns 509-511
  (bottom and right), and the label there is 0 ("clear"), so it must be cropped.
- The cloudsen12-extra layers are not normalised (dataset card):
    cloudmask_sen2cor            Sen2Cor SCL classes 0-11
    cloudmask_s2cloudless        probability 0-100
    cloudmask_cloudscore_cs_v1   Cloud Score+ cs x 10000 (a few pixels > 10000 = invalid)
    cloudmask_cloudscore_cs_cdf_v1  same for cs_cdf
    cloudmask_unetmobv2_v2, cloudmask_sensei_v2   CloudSEN12 schema 0 clear,1 thick,2 thin,3 shadow
    cloudmask_qa60               non-zero = flagged (bit values look shifted vs the ESA spec)
    lc10                         ESA WorldCover v100 class (80 = permanent water bodies)
- cloudsen12-l2a has 14 bands; index 7 is B08 surface reflectance x 10000.

PROVENANCE DECISION (2026-11-07, DECISIONS D-17): every detector input the GEE script uses
(SCL, B8 SR, s2cloudless probability, cs, cs_cdf, solar azimuth) is fetched from Earth Engine on
the patch grid (``gee_inputs``), so it is identical to what the operational script sees today.
On the 535 validation patches the bundled CloudSEN12+ Cloud Score+ layers match GEE except at
one site (ROI_00009, corrupted). SCL and s2cloudless differ on 87 and 55 patches. Only the human
label, the L1C B2 validity check, ESA WorldCover and the deep-learning masks come from
CloudSEN12+. The CloudSEN12+ copies are kept with a ``cs12_`` prefix for the provenance
comparison.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

PATCH = 509  # valid size of the small patches
CACHE = Path(__file__).resolve().parents[2] / "data" / "cache"

EXTRA_LAYERS = {
    "scl": "cloudmask_sen2cor",
    "s2cl": "cloudmask_s2cloudless",
    "cs": "cloudmask_cloudscore_cs_v1",
    "cs_cdf": "cloudmask_cloudscore_cs_cdf_v1",
    "unet_v2": "cloudmask_unetmobv2_v2",
    "sensei_v2": "cloudmask_sensei_v2",
    "qa60": "cloudmask_qa60",
    "lc10": "lc10",
}
L2A_B08 = 7  # 0-based band index of B08 in cloudsen12-l2a


def retry(fn, tries: int = 8, wait: float = 3.0):
    """Hugging Face resets connections now and then; retry with a growing pause."""
    last = None
    for i in range(tries):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - network errors come in many types
            last = exc
            time.sleep(wait * (i + 1))
    raise RuntimeError(f"failed after {tries} tries: {last!r}")


def load_tables():
    """Return (l1c, l2a, extra) metadata tables, position-indexed, plus id->position maps."""
    import tacoreader  # v0.x legacy reader

    l1 = retry(lambda: tacoreader.load("tacofoundation:cloudsen12-l1c")).reset_index(drop=True)
    l2 = retry(lambda: tacoreader.load("tacofoundation:cloudsen12-l2a")).reset_index(drop=True)
    ex = retry(lambda: tacoreader.load("tacofoundation:cloudsen12-extra")).reset_index(drop=True)
    l2pos = {t: i for i, t in enumerate(l2["tortilla:id"])}
    expos = {t: i for i, t in enumerate(ex["tortilla:id"])}
    return l1, l2, ex, l2pos, expos


def select(l1, split: str, label_type: str = "high", size: int = PATCH):
    """Rows of one split with expert labels on the small patches."""
    m = (l1["tortilla:data_split"] == split) & (l1["label_type"] == label_type) & (l1["real_proj_shape"] == size)
    return l1[m]


def _read_band(path, band: int = 1):
    import rasterio as rio

    with rio.open(path) as src:
        return src.read(band)[:PATCH, :PATCH]


def read_patch_cs12(l1, l2, ex, l2pos, expos, pos: int, use_cache: bool = True) -> dict:
    """CloudSEN12+ arrays for one patch, cropped to 509x509, cached as .npz.

    The cache file name has no prefix: it is the raw CloudSEN12+ download.
    """
    tid = l1.loc[pos, "tortilla:id"]
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{tid}.npz"
    if use_cache and f.exists():
        with np.load(f) as z:
            return {k: z[k] for k in z.files}

    s1 = retry(lambda: l1.read(int(pos)))
    out = {
        "label": retry(lambda: _read_band(s1.read(1))).astype(np.uint8),
        "b02_l1c": retry(lambda: _read_band(s1.read(0), 2)).astype(np.uint16),
    }
    s2 = retry(lambda: l2.read(int(l2pos[tid])))
    out["b08_sr"] = retry(lambda: _read_band(s2.read(0), L2A_B08 + 1)).astype(np.uint16)
    e = retry(lambda: ex.read(int(expos[tid])))
    names = list(e["tortilla:id"])
    for key, layer in EXTRA_LAYERS.items():
        out[key] = retry(lambda: _read_band(e.read(names.index(layer))))
    np.savez_compressed(f, **out)
    return out


GEE_BANDS = ["B8", "SCL", "probability", "cs", "cs_cdf"]


def gee_inputs(ee, tid: str, crs: str, gt: list, use_cache: bool = True) -> dict:
    """Detector inputs exactly as the GEE script sees them, fetched on the patch grid.

    Returns arrays plus ``gee_ok`` (pixels where all bands are present) and ``sun_azimuth``
    (MEAN_SOLAR_AZIMUTH_ANGLE of the S2_SR_HARMONIZED image). Cached as gee_<tid>.npz.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"gee_{tid}.npz"
    if use_cache and f.exists():
        with np.load(f) as z:
            return {k: z[k] for k in z.files}

    index = tid.split("__", 1)[1]
    pick = lambda c: ee.ImageCollection(c).filter(ee.Filter.eq("system:index", index)).first()  # noqa: E731
    sr = pick("COPERNICUS/S2_SR_HARMONIZED")
    img = ee.Image.cat([
        sr.select(["B8", "SCL"]),
        pick("COPERNICUS/S2_CLOUD_PROBABILITY").select(["probability"]),
        pick("GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED").select(["cs", "cs_cdf"]),
    ]).toFloat()
    # mask -> -1 so that missing data is explicit
    img = img.unmask(-1)
    req = {
        "expression": img,
        "fileFormat": "NUMPY_NDARRAY",
        "grid": {
            "dimensions": {"width": PATCH, "height": PATCH},
            "affineTransform": {"scaleX": gt[1], "shearX": gt[2], "translateX": gt[0],
                                "shearY": gt[4], "scaleY": gt[5], "translateY": gt[3]},
            "crsCode": crs,
        },
    }
    arr = retry(lambda: ee.data.computePixels(req))
    az = retry(lambda: sr.get("MEAN_SOLAR_AZIMUTH_ANGLE").getInfo())
    out = {b: np.asarray(arr[b], dtype=np.float32) for b in GEE_BANDS}
    out["gee_ok"] = np.all(np.stack([out[b] >= 0 for b in GEE_BANDS]), axis=0)
    out["sun_azimuth"] = np.float32(az)
    np.savez_compressed(f, **out)
    return out


def assemble(cs12: dict, gee: dict) -> dict:
    """Detector inputs in the units detectors.py expects (same as the GEE script)."""
    return {
        "label": cs12["label"],
        "b02_l1c": cs12["b02_l1c"],
        "lc10": cs12["lc10"],
        "unet_v2": cs12["unet_v2"],
        "sensei_v2": cs12["sensei_v2"],
        "qa60": cs12["qa60"],
        "scl": gee["SCL"].astype(np.int16),
        "b08_sr": gee["B8"],
        "s2cl": gee["probability"],
        "cs": gee["cs"] * 10000.0,  # detectors.cs_mask takes x10000 like CloudSEN12
        "cs_cdf": gee["cs_cdf"] * 10000.0,
        "sun_azimuth": float(gee["sun_azimuth"]),
        "gee_ok": gee["gee_ok"],
        "cs12_cs_cdf": cs12["cs_cdf"],
        "cs12_scl": cs12["scl"],
        "cs12_s2cl": cs12["s2cl"],
    }


def valid_mask(p: dict) -> np.ndarray:
    """Pixels usable for scoring: real image data, expert-labelled, all GEE inputs present."""
    return (p["b02_l1c"] > 0) & (p["label"] <= 3) & p["gee_ok"]
