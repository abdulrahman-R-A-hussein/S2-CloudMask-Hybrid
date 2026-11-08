# Experiment protocol for Paper 1 (pre-registration)

**Status: DRAFT v0.2, 2026-11-08** (v0.1 2026-11-07; change log in §7). This protocol fixes the hypotheses, data splits, metrics,
statistics and decision rules **before any test-split result is computed**.
- Changes are allowed until it is frozen (v1.0, a tagged commit). Each change is logged at the
  bottom with its date and reason.
- **After the freeze, changes are allowed only as dated amendments, and a test-split result
  can never be the reason for one.**
- The test split is technically locked in code: `run_pilot.py` refuses `--split test`.

This mirrors the author's field-campaign pre-registration in `D:\dev\Sulfate-Methos\validation\`.

---

## 1. Question
How accurate are the operational Sentinel-2 cloud and shadow masks **over water compared with
land**? Can a water-aware fusion of GEE-native detectors close the gap, at no GPU cost?

## 2. Data
| Role | Source | Use |
|---|---|---|
| Development | CloudSEN12+ v1.1.2 (CC0), `train` + `validation` splits, `label_type == high`, 509×509 patches | Fit and tune the fusion model, choose thresholds and operating points, run the pilot |
| **Locked test** | CloudSEN12+ `test` split, `high`, 509×509 (975 patches) **and** the new water label set (§2.1), held-out part | Final numbers only. Each method is run on it **once** |
| Downstream | IRL in-situ water quality; USF IRL Sentinel-2 chl-a/turbidity dataset | H6 |

**Data provenance (DECISIONS D-17).** Every detector input is fetched from Earth Engine on the
patch grid, as the operational script would use it:
- SCL and B8 (`S2_SR_HARMONIZED`);
- s2cloudless (`S2_CLOUD_PROBABILITY`);
- Cloud Score+ `cs` and `cs_cdf` (`CLOUD_SCORE_PLUS/V1`).

From CloudSEN12+ we take only the labels, ESA WorldCover and the published deep-learning masks
(UnetMobV2-v2, SEnSeIv2). Reasons:
- one site's bundled Cloud Score+ layers are corrupted (ROI_00009);
- SCL and s2cloudless differ from today's GEE on 87 and 55 of the 535 validation patches.

Quantified in `results/pilot_2026-11-07/provenance_cs12_vs_gee.csv`.

**Alignment gate.** On every patch (since v0.2), GEE B2 against the CloudSEN12+ L1C B2 must give
r > 0.99, with zero shift as the best of the 3×3 one-pixel shifts. A patch that fails is listed
and excluded, never silently kept (`scripts/check_gee_alignment.py`).

### 2.1 New water label set (author-labelled)
- **Scope:** 150–300 water-rich 509×509 patches (≥ 30 % water by JRC/WorldCover), labelled in the
  CloudSEN12 4-class schema with the IRIS tool.
- **Strata:**
  - inland lakes;
  - coastal and estuarine waters, including the Indian River Lagoon;
  - turbid water;
  - algal blooms (dates with known bloom reports);
  - shadow over water;
  - sun glint.
- **Agreement:** a second annotator re-labels ≥ 10 % of patches; report Cohen's κ per class.
- **Split:** stratified by site, 50 % development / 50 % locked test. Sites never cross splits.

## 3. Methods compared
1. **Single GEE detectors:**
   - SCL {3, 8, 9, 10};
   - s2cloudless > T (T ∈ 20…60, step 5);
   - Cloud Score+ `cs` < T and `cs_cdf` < T (T ∈ 0.40…0.80, step 0.05);
   - QA60 (dates before 2022-01-25) and `MSK_CLASSI` (after 2024-02-28).
2. **v1.0.2 replica** (`python/src/cloudbench/detectors.py`): union, union + shadow, FINAL
   (morphology at 10 m).
3. **Rule-based fusion:** family k-of-n (families {SCL}, {s2cloudless}, {Cloud Score+}),
   k = 1, 2, 3; weighted vote.
4. **Deep-learning references:**
   - UnetMobV2-v2 (in-domain: trained on CloudSEN12+);
   - SEnSeIv2;
   - OmniCloudMask v4;
   - CloudS2Mask.
5. **Ours (water-aware fusion):** modules M1–M6 (RESEARCH_PLAN §4), full model and each ablation.

## 4. Metrics
Positive = contaminated (thick, thin or shadow); negative = clear. Definitions are in
`python/src/cloudbench/metrics.py`:
- **leak** = FN/(FN+TN);
- **discard** = FP/(FP+TN);
- recall, precision, **F1**;
- **balanced overall accuracy (BOA)**;
- per-class recall (thick, thin, shadow);
- calibration: expected calibration error (ECE) and reliability diagrams, for probabilistic methods.

**Strata:**
- pixel: water (WorldCover 80) / land / coast (≤ 200 m from the shoreline);
- patch: water-rich (≥ 5 % water) / other;
- special: turbid, bloom, glint, thin cloud, shadow over water.

**Pooling and uncertainty:**
- micro-pooled confusion counts;
- **95 % CI by bootstrap over sites** (1,000 resamples, seed 0);
- method differences: paired site-level bootstrap of the difference.

## 5. Hypotheses and decision rules
| ID | Hypothesis | Test | Supported if |
|---|---|---|---|
| H1 | Every operational GEE mask leaks more over water than over land | leak(water) − leak(land) per method | 95 % CI of the difference > 0 for every operational mask |
| H2 | The v1.0.2 union lowers leak against the best single detector but raises discard, most over water | paired differences | leak diff CI < 0 and discard diff CI > 0; discard increase larger over water |
| H3 | **Water-aware fusion beats the best single GEE detector on water BOA at matched leak** | operating point set on development data to match that detector's development leak | water BOA difference CI > 0 on the locked test set |
| H4 | M4 (shadow over water) raises shadow recall over water | ablation | CI of the recall difference > 0, with water discard rising by ≤ 1 point |
| H5 | M5 (bloom guard) lowers false cloud on bloom pixels | ablation on bloom-labelled pixels | discard (bloom) falls, CI < 0, with leak rising by ≤ 1 point |
| H6 | Mask choice changes chl-a matchup error | matchups | RMSE differences with CIs reported (descriptive) |
| H7 | Distance between ours and the best deep-learning mask over water | water BOA difference | reported whatever the sign (descriptive) |

**Claim rule:**
- "Breakthrough" or "outperforms" may be written only for hypotheses that are supported.
- H3 failing means Paper 1 is written as **benchmark + dataset + negative result for fusion**.
- "First" is never used without a search log showing no prior work (`LITERATURE_REVIEW.md` §8).

## 6. Pilot (R0) scope, done on the validation split
The pilot exists to:
- prove the pipeline;
- size the effects;
- check data provenance.

Its numbers are labelled PILOT and are **not** paper results. The pilot does not touch the test split.

## 7. Change log
- 2026-11-07 v0.1: first draft, written with the pilot. D-17 (GEE provenance) is added after the
  pilot's provenance check (one corrupted site; SCL/s2cloudless differences on a minority of patches).
- 2026-11-08 v0.2 (R1, validation split only; no test data seen):
  - Alignment gate run on every patch, not ≥ 5; sensitivity tables for all patches and for
    zero-best-shift patches (D-19).
  - Coast stratum defined: ≤ 200 m from the WorldCover water/land edge, either side, measured
    inside the patch; plus "open water" (> 200 m from land). `python/src/cloudbench/strata.py`.
  - CloudS2Mask removed from §3 (D-18). `MSK_CLASSI` is not applicable on CloudSEN12+ (dates
    2018–2020, before 2024-02-28); it moves to the new water label set.
  - Weighted vote moves to R3: its weights must be fitted, which is the fusion model's job.
  - Calibration (ECE, 10 equal bins) computed for `1 − cs`, `1 − cs_cdf` and s2cloudless/100.
  - Paired differences report a two-sided bootstrap p (share of resamples crossing zero, ×2).
