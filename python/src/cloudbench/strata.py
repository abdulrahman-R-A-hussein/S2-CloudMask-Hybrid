"""Pixel strata for the benchmark (EXPERIMENT_PROTOCOL §4).

Water = ESA WorldCover v100 class 80 (permanent water bodies, 2020; static, so seasonal or new
water is counted as land). Coast = pixels within ``COAST_M`` of the water/land edge on either
side. Distances are measured inside the 509x509 patch only: an edge just outside the patch is
not seen, so coast is slightly under-counted near patch borders.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage

WATER_CLASS = 80
COAST_M = 200.0
PIXEL_M = 10.0


def surface_strata(lc10: np.ndarray, valid: np.ndarray, coast_m: float = COAST_M) -> dict[str, np.ndarray]:
    water = lc10 == WATER_CLASS
    land = (lc10 != WATER_CLASS) & (lc10 > 0)
    out = {"all": valid, "water": valid & water, "land": valid & land}
    if water.any() and land.any():
        d_to_water = ndimage.distance_transform_edt(~water) * PIXEL_M  # for land pixels
        d_to_land = ndimage.distance_transform_edt(~land) * PIXEL_M  # for water pixels
        coast = (land & (d_to_water <= coast_m)) | (water & (d_to_land <= coast_m))
        open_water = water & (d_to_land > coast_m)
    else:
        coast = np.zeros_like(valid)
        open_water = water.copy()
    out["coast (<=200 m)"] = valid & coast
    out["open water (>200 m)"] = valid & open_water
    return out
