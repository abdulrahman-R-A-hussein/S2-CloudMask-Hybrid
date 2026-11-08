import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from cloudbench import detectors, metrics  # noqa: E402


def test_counts_and_scores_hand_checked():
    label = np.array([0, 0, 0, 0, 1, 2, 3, 1])  # 4 clear, 4 contaminated
    pred = np.array([1, 0, 0, 0, 1, 1, 0, 0], dtype=bool)
    c = metrics.counts(pred, label, np.ones_like(label, dtype=bool))
    assert (c["tp"], c["fp"], c["fn"], c["tn"]) == (2, 1, 2, 3)
    s = metrics.scores(c)
    assert np.isclose(s["leak_%"], 100 * 2 / 5)  # FN / (FN + TN)
    assert np.isclose(s["discard_%"], 100 * 1 / 4)  # FP / (FP + TN)
    assert np.isclose(s["recall_%"], 50.0)
    assert np.isclose(s["BOA_%"], 100 * (0.5 + 0.75) / 2)
    assert np.isclose(s["F1_%"], 100 * 4 / (4 + 1 + 2))
    assert np.isclose(s["shadow_recall_%"], 0.0) and np.isclose(s["thin_recall_%"], 100.0)


def test_summarize_pools_counts_and_gives_ci():
    df = pd.DataFrame([
        {"roi_id": "a", "patch": "p1", "method": "m", "tp": 5, "fp": 0, "fn": 5, "tn": 10,
         "thick_n": 10, "thick_hit": 5, "thin_n": 0, "thin_hit": 0, "shadow_n": 0, "shadow_hit": 0},
        {"roi_id": "b", "patch": "p2", "method": "m", "tp": 10, "fp": 10, "fn": 0, "tn": 10,
         "thick_n": 10, "thick_hit": 10, "thin_n": 0, "thin_hit": 0, "shadow_n": 0, "shadow_hit": 0},
    ])
    out = metrics.summarize(df, ["method"], n_boot=200)
    r = out.iloc[0]
    assert np.isclose(r["recall_%"], 100 * 15 / 20)
    assert r["recall_lo"] <= r["recall_%"] <= r["recall_hi"]
    assert r["n_sites"] == 2 and r["n_pixels"] == 50


def test_assemble_scales_gee_cloud_score_like_the_script():
    from cloudbench import data
    z = np.zeros((3, 3))
    cs12 = {k: z for k in ("label", "b02_l1c", "lc10", "unet_v2", "sensei_v2", "qa60", "cs_cdf", "scl", "s2cl")}
    gee = {"SCL": z + 8, "B8": z + 900, "probability": z + 40, "cs": z + 0.59, "cs_cdf": z + 0.61,
           "sun_azimuth": np.float32(150), "gee_ok": z == 0}
    p = data.assemble(cs12, gee)
    assert detectors.cs_mask(p["cs"]).all() and not detectors.cs_mask(p["cs_cdf"]).any()  # 0.59 < 0.60 <= 0.61
    assert detectors.scl_mask(p["scl"]).all() and not detectors.s2cloudless_mask(p["s2cl"]).any()


def test_union_is_k1_of_the_four_detectors():
    rng = np.random.default_rng(0)
    p = {"scl": rng.integers(0, 12, (60, 60)), "s2cl": rng.integers(0, 101, (60, 60)),
         "cs": rng.integers(0, 10001, (60, 60)), "cs_cdf": rng.integers(0, 10001, (60, 60)),
         "b08_sr": rng.integers(0, 5000, (60, 60)), "sun_azimuth": 140.0}
    m = detectors.v102_all(p)
    four = [detectors.scl_mask(p["scl"]), detectors.s2cloudless_mask(p["s2cl"]),
            detectors.cs_mask(p["cs"]), detectors.cs_mask(p["cs_cdf"])]
    assert np.array_equal(m["v1.0.2 union (std)"], detectors.k_of_n(four, 1))
    assert np.array_equal(m["v1.0.2 union (std)"], four[0] | four[1] | four[2] | four[3])
    assert not np.any(m["v1.0.2 union (std)"] & ~m["v1.0.2 union+shadow"])  # shadow only adds


def test_thresholds_follow_the_script_directions():
    assert detectors.cs_mask(np.array([5999]))[0] and not detectors.cs_mask(np.array([6000]))[0]  # cs < 0.60
    assert detectors.s2cloudless_mask(np.array([51]))[0] and not detectors.s2cloudless_mask(np.array([50]))[0]
    assert set(detectors.SCL_FLAG) == {3, 8, 9, 10}


def test_morphology_erodes_small_clouds_then_buffers():
    m = np.zeros((40, 40), dtype=bool)
    m[20, 20] = True  # a 10 m cloud: removed by the 20 m erosion (AUDIT F-05)
    assert not detectors.morphology(m).any()
    m[5:15, 5:15] = True  # a 100 m cloud (cols 5-14) survives
    out = detectors.morphology(m)
    # erode 2 px then dilate 5 px: the NET buffer beyond the original edge is 3 px = 30 m,
    # not the documented 50 m (AUDIT F-12)
    assert out[10, 10] and out[10, 17] and not out[10, 18]


def test_shadow_search_looks_toward_the_sun():
    cloud = np.zeros((500, 500), dtype=bool)
    cloud[300:310, 200:210] = True  # coarse row 30, col 20
    dark = np.zeros((500, 500), dtype=np.uint16)  # everything NIR-dark
    scl = np.zeros((500, 500), dtype=np.uint8)
    # Sun in the south (azimuth 180): shadows fall north of the cloud (smaller row numbers).
    sh = detectors.shadow_projection(cloud, dark, scl, 180.0)
    assert sh[250, 205] and sh[205, 205]  # 0.5 km and ~1 km north
    assert not sh[350, 205]  # south of the cloud: no shadow
    # SCL water is never a shadow candidate (AUDIT F-03)
    sh_w = detectors.shadow_projection(cloud, dark, np.full((500, 500), 6, np.uint8), 180.0)
    assert not sh_w.any()


def _toy_counts():
    rows = []
    for s in "abcdef":
        for meth, fn in (("good", 1), ("bad", 4)):
            rows.append({"roi_id": s, "patch": s, "method": meth, "stratum": "all", "tp": 10 - fn, "fp": 1,
                         "fn": fn, "tn": 20, "thick_n": 10, "thick_hit": 10 - fn, "thin_n": 0, "thin_hit": 0,
                         "shadow_n": 0, "shadow_hit": 0})
    return pd.DataFrame(rows)


def test_scores_arr_matches_scores():
    df = _toy_counts()
    tot = df[df.method == "bad"][metrics.COUNT_COLS].sum()
    a = metrics.scores_arr(tot.to_numpy(dtype=float))
    s = metrics.scores(tot)
    for k in ("leak_%", "discard_%", "BOA_%", "F1_%"):
        assert np.isclose(a[k], s[k])


def test_paired_diff_detects_a_consistent_difference():
    r = metrics.paired_diff(_toy_counts(), "good", "bad", "all", n_boot=300)
    assert r["n_sites"] == 6
    assert r["leak_diff"] < 0 and r["leak_hi"] < 0  # good leaks less at every site
    assert r["BOA_diff"] > 0 and r["BOA_lo"] > 0 and r["BOA_p"] < 0.05
    same = metrics.paired_diff(_toy_counts(), "good", "good", "all", n_boot=100)
    assert same["BOA_diff"] == 0 and same["BOA_lo"] == 0 == same["BOA_hi"]
