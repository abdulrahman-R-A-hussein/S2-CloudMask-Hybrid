"""Numpy replicas of every detector and fusion rule in S2_CloudMask_SCIENTIFIC.js v1.0.2.

Each function returns a boolean array: True = flagged (cloud or shadow), on the 10 m grid.

Replica notes (differences from GEE are deliberate and documented):
- GEE evaluates focal operations at the request scale (AUDIT F-05). Here everything is
  evaluated at 10 m, which is what a 10 m export would use.
- Shadow projection follows the GEE tutorial: cloud mask at 100 m, search toward the sun for a
  cloud within CLOUD_PROJ_DIST km, then AND with dark NIR outside SCL water. GEE's
  directionalDistanceTransform is replaced by explicit pixel shifts along the sun direction.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage

PARAMS_V102 = {
    "CS_CDF_THRESH": 0.60,
    "CS_THRESH": 0.60,
    "CLOUD_PROB_THRESH": 50,
    "NIR_DARK_THRESH": 0.15,
    "CLOUD_PROJ_DIST": 1,  # km
    "BUFFER": 50,  # m
    "ERODE": 20,  # m (hard-coded in the script)
}
SCL_FLAG = (3, 8, 9, 10)  # cloud shadow, cloud medium, cloud high, thin cirrus
PIXEL_M = 10.0


# --- single detectors -------------------------------------------------------------
def scl_mask(scl: np.ndarray) -> np.ndarray:
    return np.isin(scl, SCL_FLAG)


def s2cloudless_mask(prob: np.ndarray, thresh: float = 50) -> np.ndarray:
    return prob > thresh


def cs_mask(cs_x1e4: np.ndarray, thresh: float = 0.60) -> np.ndarray:
    return (cs_x1e4 / 10000.0) < thresh


def class_mask(schema4: np.ndarray) -> np.ndarray:
    """CloudSEN12-schema outputs (UnetMobV2, SEnSeIv2): 1 thick, 2 thin, 3 shadow."""
    return np.isin(schema4, (1, 2, 3))


def qa60_mask(qa: np.ndarray) -> np.ndarray:
    return qa > 0


# --- v1.0.2 shadow projection and morphology --------------------------------------
def _disk(radius_px: int) -> np.ndarray:
    r = int(radius_px)
    y, x = np.ogrid[-r : r + 1, -r : r + 1]
    return (x * x + y * y) <= r * r


def shadow_projection(cloud: np.ndarray, b08_sr: np.ndarray, scl: np.ndarray, sun_azimuth_deg: float,
                      nir_dark: float = 0.15, proj_km: float = 1.0) -> np.ndarray:
    """Tutorial-style shadow candidates.

    For each pixel, look toward the sun for a cloud within ``proj_km``. Work on a 100 m grid
    (10x10 blocks, a block is cloudy if any pixel is), as the script's reproject(scale=100).
    """
    h, w = cloud.shape
    f = 10  # 10 m -> 100 m
    hb, wb = -(-h // f), -(-w // f)
    pad = np.zeros((hb * f, wb * f), dtype=bool)
    pad[:h, :w] = cloud
    coarse = pad.reshape(hb, f, wb, f).any(axis=(1, 3))

    # Direction toward the sun in image coordinates. GEE angle = 90 - azimuth (math convention,
    # counter-clockwise from east); image rows grow southward.
    theta = np.deg2rad(90.0 - sun_azimuth_deg)
    dcol, drow = np.cos(theta), -np.sin(theta)
    steps = int(round(proj_km * 1000 / (PIXEL_M * f)))  # 1 km -> 10 coarse pixels
    proj = coarse.copy()
    for k in range(1, steps + 1):
        sr, sc = int(round(k * drow)), int(round(k * dcol))
        shifted = np.zeros_like(coarse)
        # pixel (r, c) is a candidate if cloud at (r + sr, c + sc)
        r0, r1 = max(0, -sr), min(hb, hb - sr)
        c0, c1 = max(0, -sc), min(wb, wb - sc)
        if r1 > r0 and c1 > c0:
            shifted[r0:r1, c0:c1] = coarse[r0 + sr : r1 + sr, c0 + sc : c1 + sc]
        proj |= shifted
    proj_fine = np.repeat(np.repeat(proj, f, axis=0), f, axis=1)[:h, :w]

    dark = (b08_sr < nir_dark * 10000) & (scl != 6)
    return proj_fine & dark


def morphology(mask: np.ndarray, erode_m: float = 20, buffer_m: float = 50) -> np.ndarray:
    """focal_min(erode_m) then focal_max(buffer_m), circular kernels in metres at 10 m."""
    out = mask
    if erode_m > 0:
        out = ndimage.binary_erosion(out, structure=_disk(erode_m / PIXEL_M), border_value=1)
    if buffer_m > 0:
        out = ndimage.binary_dilation(out, structure=_disk(buffer_m / PIXEL_M))
    return out


# --- fusion -------------------------------------------------------------------------
def k_of_n(masks: list[np.ndarray], k: int) -> np.ndarray:
    """Flag a pixel when at least k of the given masks flag it (k=1 is the union)."""
    return np.sum(np.stack(masks).astype(np.uint8), axis=0) >= k


def v102_all(p: dict, params: dict = PARAMS_V102) -> dict[str, np.ndarray]:
    """Every intermediate mask of addAllMasks() in the GEE script, plus family voting."""
    m_scl = scl_mask(p["scl"])
    m_s2c = s2cloudless_mask(p["s2cl"], params["CLOUD_PROB_THRESH"])
    m_cs = cs_mask(p["cs"], params["CS_THRESH"])
    m_cdf = cs_mask(p["cs_cdf"], params["CS_CDF_THRESH"])
    std = m_scl | m_s2c | m_cs | m_cdf
    shadow = shadow_projection(std, p["b08_sr"], p["scl"], float(p["sun_azimuth"]),
                               params["NIR_DARK_THRESH"], params["CLOUD_PROJ_DIST"])
    full = std | shadow
    smooth = morphology(full, params["ERODE"], params["BUFFER"])
    # Families: {SCL}, {s2cloudless}, {Cloud Score+ = cs OR cs_cdf}  (AUDIT F-02)
    fam = [m_scl, m_s2c, m_cs | m_cdf]
    return {
        "SCL": m_scl,
        "s2cloudless>50": m_s2c,
        "cs<0.60": m_cs,
        "cs_cdf<0.60": m_cdf,
        "v1.0.2 union (std)": std,
        "v1.0.2 union+shadow": full,
        "v1.0.2 FINAL (smoothed)": smooth,
        "family 2-of-3": k_of_n(fam, 2),
        "family 3-of-3": k_of_n(fam, 3),
    }
