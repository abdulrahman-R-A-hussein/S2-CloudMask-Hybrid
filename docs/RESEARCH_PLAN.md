# Research plan: toward the best cloud-masking system, water first

**Written 2026-11-07.** This is the program-level plan. The literature behind it is in
[`LITERATURE_REVIEW.md`](LITERATURE_REVIEW.md) §8, the pre-registered tests are in
[`EXPERIMENT_PROTOCOL.md`](EXPERIMENT_PROTOCOL.md), and the paper skeleton is in
[`PAPER1_OUTLINE.md`](PAPER1_OUTLINE.md).

## 1. Goal
Build and publish the most accurate openly available cloud and cloud-shadow masking for
**water-quality** remote sensing. Start with Sentinel-2, then extend to other sensors
(Landsat 8/9, HLS, PlanetScope, Sentinel-3 OLCI, MicaSense drones).

## 2. Why water first (the honest position)
An independent 2026 audit on the CloudSEN12+ test split reported these numbers
(https://github.com/syre-ai/cloudmask-acceptance-audit, *not peer-reviewed*):

| Mask | Leak | Discard |
|---|---|---|
| OmniCloudMask (deep learning) | 6.1 % | 4.6 % |
| Cloud Score+ | 8.5 % | 12.7 % |

It also found **every mask leaks more over water: 11.0 % vs 6.1 %**. Over all surfaces,
deep learning leads, and a fusion of GEE masks is unlikely to overtake it. **Over water, nobody
has measured the problem properly, nobody has labels, and shadows on water and blooms flagged
as cloud are unsolved.** That is where a real advance is possible and checkable.

## 3. Program: three papers
| Paper | Contribution | Gaps (LIT §8) | Target venue |
|---|---|---|---|
| **P1** | (a) Water-stratified benchmark of all major S2 masks; (b) water-aware fusion that runs natively in GEE with calibrated contamination probabilities; (c) water cloud/shadow label set | G1, G3–G7, G9 | RSE / ISPRS JPRS (fallback IEEE JSTARS / Remote Sensing) |
| **P2** | Water-aware deep-learning model (fine-tuned on P1 labels plus physics features) and a released water cloud dataset | G2, G3, G4 | RSE / IEEE TGRS; dataset in Sci. Data or ESSD |
| **P3** | Cross-sensor transfer, including the author's MicaSense drone data | G8 | ISPRS JPRS / RSE |

## 4. The new method for P1 (working name: water-aware fusion)
| Module | Idea | Gap |
|---|---|---|
| M1 | Per-pixel features: continuous `cs`, `cs_cdf`, s2cloudless probability, SCL one-hot, L1C B10 cirrus, CDI parallax, NDWI/MNDWI, AFAI/MFAI, SWIR, whiteness/HOT, JRC water occurrence, distance to shore, solar geometry | G5 |
| M2 | Surface-conditional learned fusion: gradient-boosted trees, 4 classes. Trained offline, then exported to GEE (`ee.Classifier.decisionTreeEnsemble`), so it needs no GPU | G5 |
| M3 | Isotonic calibration gives a **contamination probability** and user-chosen operating points ("2 % leak") | G6 |
| M4 | Shadow over water: project the cloud along azimuth × (height range · tan SZA), and test darkness relative to the local water median | G3 |
| M5 | Bloom/turbid guard: an AFAI/MFAI plus texture test stops SCL or s2cloudless alone from masking floating algae | G4 |
| M6 | Near-cloud quality tier derived from measured Rrs bias against distance to cloud (IRL) | G7 |

Every module gets an ablation.

## 5. Phases and milestones
| Phase | Output | Done when |
|---|---|---|
| **R0 pilot** (2026-11-07) | Python benchmark, GEE provenance check, validation-split numbers for GEE detectors + v1.0.2 + DL references | `results/pilot_2026-11-07/` exists; tests pass |
| R1 full benchmark ✅ 2026-11-08 | All methods of PROTOCOL §3 on validation, threshold sweeps, OmniCloudMask run locally (RTX 5070 Ti) | `results/r1_2026-11-08/` |
| R2 water labels | IRIS set up; 10-patch timing pilot; 150–300 patches; second annotator on ≥ 10 % | Label manifest plus κ report |
| R3 method | M1–M6 implemented, trained on development data, exported to GEE | Ablation table on validation |
| R4 freeze and test | Protocol v1.0 tagged, then the locked test run once | `results/test_<date>/` plus hypothesis verdicts |
| R5 Paper 1 | Manuscript, data/code release (GitHub + Zenodo), GEE module v2.0 | Submitted |
| R6+ | P2 (deep-learning model and dataset), P3 (cross-sensor) | — |

Durations are not estimated yet. R2's length depends on the labelling-time pilot.

## 5b. What the R0 pilot showed (2026-11-07, validation split; LOG has the table)
- GEE-native masks leak more over water than over land (v1.0.2 union: 10.8 % vs 4.5 %). The
  deep-learning masks do not.
- **Shadow over water is the weakest point:** about 58 % recall for Cloud Score+ `cs` and the
  union, against about 92 % on land. So **M4 is the priority module**.
- Deep learning leads by about 5 BOA points (93–94 % vs 88.6 % for the best GEE single mask,
  `cs < 0.60`).
- The H3 target is therefore realistic in two parts:
  - beat `cs` over water;
  - shrink the gap to deep learning, without a GPU.

## 5c. What R1 showed (2026-11-08, validation split, 460 aligned patches; LOG has the table)
- **OmniCloudMask is the best mask over water** (BOA 94.7 % vs 84.6 % for `cs`; paired +10.1
  points) and catches 92 % of shadow pixels on water. **Shadow over water is a GEE-native
  failure**, not a universal one.
- So the realistic P1 claims are:
  - a GPU-free, GEE-native mask that closes most of the gap to deep learning over water (H3
    against `cs`, H7 against OmniCloudMask, reported whatever the sign);
  - calibrated probabilities (raw scores: ECE 13–22 %), which no compared mask provides;
  - the water benchmark and labels themselves.
- M2 can use OmniCloudMask's output as a teacher or feature only if the user accepts a GPU step;
  the default stays GPU-free (decision for R3).
- Threshold choice matters: `cs_cdf` at 0.75 beats the 0.60 default by ~6 BOA points. Thresholds
  and fusion must be fitted on the train split, never on validation.

## 6. Risks
- **Label effort.** The 10-patch pilot measures it before anything is committed.
- **Dataset errors.** CloudSEN12+ has documented label errors (Aybar et al. 2023,
  doi:10.1109/IGARSS52108.2023.10282381), and its bundled Cloud Score+ layers are unreliable
  (D-17). Answer: inputs come from GEE, and labels are spot-checked.
- **Deep learning stays ahead even over water.** P1 then contributes the benchmark, the dataset,
  calibration and a GEE-native option. P2 tackles accuracy with deep learning.
- **GEE quotas.** Use the high-volume endpoint and cache everything under `python/data/cache`.

## 7. Reproducibility rules
- Every number in a doc or paper comes from a CSV in `results/` written by a script, with a
  `run.log` that records versions and the git hash.
- The test split is touched once, after the protocol freeze.
- The code is MIT-licensed. CloudSEN12+ is CC0. New labels will be released under CC BY 4.0
  (to be confirmed by the author).
