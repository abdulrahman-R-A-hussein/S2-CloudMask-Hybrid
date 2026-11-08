# Project log: S2-CloudMask-Hybrid

Dated entries, newest at the bottom. One entry per work session: what was done, what was
decided, the results, and what is next.

Entries before 2026-11-07 are **reconstructed**, from git history, the Zenodo record, file dates
on this PC and the author's other repos. They are marked *(reconstructed)*. Anything not
recorded is written as "unknown", not guessed.

**How to add an entry:** append `## YYYY-MM-DD: short title`, then **Done / Decided / Results /
Not done / Next**. Update [`STATE.md`](STATE.md) in the same session. If a decision changed,
add it to [`DECISIONS.md`](DECISIONS.md).

---

## 2025-09-01: project start *(reconstructed)*
- The only source is `start_date: "2025-09-01"` in the author's website entry
  (`D:\dev\Personal Website\data\projects.json`, id `project-sentinel-cloud`).
- No code, notes or commits from this period were found on this PC.

## 2025-11-15: the hybrid mask first appears, inside the AMD Detection Tool *(reconstructed)*
- `D:\dev\Sulfate-Methos\earth-engine\amd_detection_v1.0.0.js` (commit `57f7d8c`, "Initial commit
  - AMD Detection Tool v1.0.0") contains selectable S2 cloud masking: SCL + Sen2Cor cloud
  probability (`MSK_CLDPRB`), Cloud Score+ `cs`, Cloud Score+ `cs_cdf`, and a `Hybrid` that
  requires all of them to say "clear" (logically the same as this repo's union).
- Its thresholds: `CLOUD_PROB` 20, `CS_THRESHOLD` 0.60, `CS_CDF_THRESHOLD` 0.60. QA60 and AOT were
  dropped ("they detect nothing"). It has no s2cloudless join and no shadow projection.
- This is the earliest dated code with the multi-method idea found on this PC. This repo's
  version adds s2cloudless, the tutorial's shadow projection, morphology, the confidence layer
  and the comparison UI.

## 2026-05-26: v1.0.2 released on GitHub and Zenodo *(reconstructed from git + Zenodo)*
- `3719cde` 08:29 −04:00, "Initial release". Adds the GEE script, README, USAGE, the template,
  CITATION.cff, LICENSE (MIT) and .gitignore (1,324 lines). Branch renamed `master` → `main`.
- `2adae41` 09:06: ORCID and Google Scholar links, repository URL fixed (an amend of `0bcbae8`).
- `4e89a07` 09:34: Zenodo DOI badge.
- `4ad6416` 09:52: real DOI and full citation info.
- `1bd472d` 09:53: "remove co-author, sole author Abdulrahman Hussein". Joseph D. Ortiz (ORCID
  0000-0003-1112-3292) was removed from `CITATION.cff`. The reason is not recorded.
- **Zenodo:** record 20395978, "Sentinel-2 Hybrid Cloud Masking Framework", **v1.0.2**,
  published 2026-05-26.
  - Concept DOI 10.5281/zenodo.20395977; record revision 10.
  - One file, `S2-CloudMask-Hybrid-main.zip` (18,484 bytes, md5 `91da75f4dfc48f5a564f208a72543aac`).
  - Software Heritage ID `swh:1:dir:4203251839fc8d6113b9d35e96547d589779eef8`.
  - No GitHub link appears in the record.
- **Unknown:** whether v1.0.0 and v1.0.1 were ever published, and how the zip was uploaded. No
  GitHub release or tag exists.
- Remote: `https://github.com/abdulrahman-R-A-hussein/S2-CloudMask-Hybrid`; local `main` = `origin/main`.

## 2026-06-11: repo copied to this PC *(reconstructed)*
- The folder dates in `D:\dev\Cloud-Masking` are 2026-06-11. The `.git` folder belongs to a
  different Windows account SID, so git now refuses to run with "detected dubious ownership".
  **Workaround:** `git -c safe.directory=D:/dev/Cloud-Masking <command>`. Do not change the global
  git config without asking.

## Date unknown: website listing
- The author's website lists the project (`projects.json`, `project-sentinel-cloud`, status
  "completed", concept DOI). Its description does not match this repo: Python/Rasterio/GDAL,
  "pixel QA", "integrated with VPCA". See AUDIT X-01.

## 2026-11-07: full audit, literature review, hand-off documentation
**Why.** The author asked for a full understanding of the project, a summary of what is done and
what is open, literature-based improvements, and a log good enough that any AI tool could pick
the project up cold.

**Done:**
- Read every file and the git history. Checked GitHub (5 commits, 0 releases) and the Zenodo
  record via its API.
- Literature pass, about 35 searches and fetches → [`LITERATURE_REVIEW.md`](LITERATURE_REVIEW.md).
  It covers the primary sources for all 5 detectors, 8 benchmark studies, water-specific
  problems, deep-learning masks and validation datasets.
- [`AUDIT_2026-11-07.md`](AUDIT_2026-11-07.md): 11 code findings (F), 23 public claims checked (C)
  and 4 external records (X).
- New files: `AGENTS.md`, `CLAUDE.md`, `CHANGELOG.md`, and in `docs/`: `STATE.md`, `LOG.md`
  (this file), `DECISIONS.md`, `ROADMAP.md`.
- Text corrections in `README.md`, `docs/USAGE.md` and the comments of
  `examples/custom_area_template.js`, covering all C-items marked "fixed (docs)".
  `S2_CloudMask_SCIENTIFIC.js` was **not** changed (D-13).
- Registered in the PhD hub: a row in `D:\dev\phd\00_INDEX.md` and an entry in `03_ACTIVITY_LOG.md`.

**Results (most important):**
1. **Tuning advice was inverted** in USAGE and the template (C-01, C-02). Raising
   `CS_CDF_THRESH` masks *more*, not less. Fixed.
2. **The README's performance numbers were never measured** (C-04, C-05). No quantitative
   validation of this method exists. That is the main science gap → ROADMAP Phase C.
3. **Shadow projection is switched off over water** (F-03), yet water is the target. Shadows on
   the lagoon rely on SCL class 3 and Cloud Score+ alone → ROADMAP D1.
4. **`MIN_AGREEMENT` and the "weighting" do not exist in the code** (F-01). The confidence
   score counts `cs` and `cs_cdf` as two independent votes (F-02) → ROADMAP B1.
5. The literature supports **multi-method ensembles**, through voting or learned fusion (Tarrio
   et al. 2020). It also warns that bright turbid water and **blooms get masked as cloud**,
   which a union makes worse. No benchmark over water exists (gap).

**Not done:**
- The script was not run in GEE (no access from this session), so F-05 still needs a GEE check.
- The website entry was not changed (separate repo; proposed as a follow-up).
- (Done after all: committed as `e36ebd5` on `main` and pushed to GitHub at the author's request.)

**Next:** see [`STATE.md`](STATE.md) → "Next actions".

## 2026-11-07 (second session): research program planned; pilot benchmark R0 run
**Why.** The author wants to publish and to build the best cloud-masking tool: Sentinel-2
first, then other sensors; the literature covered from oldest to newest; numbers for every
internal method.

**Decided** (with the author):
- staged, water-first program of three papers (D-14);
- the author will hand-label water scenes;
- GEE access through the existing service account (D-16);
- this session: docs plus a pilot.

**Done:**
- [`RESEARCH_PLAN.md`](RESEARCH_PLAN.md), [`EXPERIMENT_PROTOCOL.md`](EXPERIMENT_PROTOCOL.md)
  (pre-registration draft v0.1; H1–H7), [`PAPER1_OUTLINE.md`](PAPER1_OUTLINE.md).
- `LITERATURE_REVIEW.md` §8: chronological map 1988–2026 and gap matrix G1–G10. 18 more DOIs
  checked against Crossref. The Wen et al. 2007 citation is now complete.
- `python/` benchmark (`cloudbench`, uv, Python 3.11) with 7 passing tests, a pilot runner and
  an alignment gate.
- ROADMAP rebuilt as research phases R0–R6; decisions D-14 to D-17; audit F-12 and X-05.

**Data facts found (all now handled in code):**
1. The CloudSEN12+ reader (`tacoreader` < 1.0, TACO v1) takes a row **position**. Reading by
   index label silently returned the wrong patches. Caught because the labels did not match
   the metadata percentages.
2. 509×509 patches are padded on the **bottom and right**, and the padding is labelled "clear".
   It is cropped.
3. **Provenance:** the bundled Cloud Score+ layers match GEE except at one site (ROI_00009,
   corrupted). SCL and s2cloudless differ from today's GEE on 87 and 55 of 535 patches. All
   inputs are therefore fetched from GEE (D-17).
   - **Correction:** my first diagnosis looked only at ROI_00009 and over-generalised. Fixed
     after the full run.
   - Smoke test before the fix: 277,542 scored pixels. After: 1,554,486.
4. The v1.0.2 morphology leaves a net buffer of about **30 m, not 50 m** (erode 2 px, dilate
   5 px), and it deletes clouds narrower than about 40 m (F-12, unit-tested).
5. Alignment gate (10 patches spread over sites): 8 pass. 2 show a one-pixel offset between
   GEE and the CloudSEN12+ grid (`results/pilot_2026-11-07/gee_alignment.csv`). The pilot did
   not exclude unchecked patches. R1 will gate every patch.

**Results.** PILOT, validation split: 535 patches, 107 sites, 138.6 M labelled pixels.
`results/pilot_2026-11-07/summary.md`. Brackets are 95 % site-bootstrap CIs.

| Method | Leak % all | Discard % all | BOA % all | Leak % water / land | Shadow recall % water / land |
|---|---|---|---|---|---|
| SCL | 24.5 | 7.2 | 79.1 | 29.3 / 23.8 | 10.9 / 38.5 |
| s2cloudless > 50 | 25.1 | 4.9 | 79.2 | 28.9 / 24.5 | 6.2 / 17.7 |
| Cloud Score+ cs < 0.60 (best GEE single) | 7.6 [6.0, 9.2] | 14.8 | 88.6 [87.4, 89.8] | 11.4 / 7.0 | 57.8 / 91.1 |
| Cloud Score+ cs_cdf < 0.60 | 22.4 | 0.8 | 83.2 | 25.0 / 22.0 | 12.5 / 46.7 |
| v1.0.2 union | 5.4 | 19.0 | 87.9 | 10.8 / 4.5 | 58.4 / 92.5 |
| v1.0.2 FINAL (smoothed) | 4.0 | 23.0 | 86.6 | 9.4 / 3.1 | 63.1 / 96.4 |
| QA60 | 30.5 | 9.0 | 72.6 | 35.7 / 29.6 | 10.3 / 22.0 |
| UnetMobV2-v2 (DL, in-domain) | 6.3 | 5.1 | 93.8 [92.9, 94.5] | 6.3 / 6.3 | 76.2 / 90.1 |
| SEnSeIv2 (DL) | 5.8 | 6.6 | 93.4 | 5.4 / 5.8 | 87.8 / 91.6 |

**What the pilot says** (validation data; no paired tests yet; some CIs overlap):
1. Every GEE-native mask leaks more over water than over land. The v1.0.2 union goes from 4.5 %
   to 10.8 %. Both deep-learning masks show no water gap. This is the H1 direction.
2. **The biggest failure is cloud shadow over water.** Cloud Score+ `cs` and the v1.0.2 union
   catch about 58 % of shadow pixels on water against about 91–93 % on land. SCL and
   s2cloudless catch almost none on water (10.9 % and 6.2 %). SEnSeIv2 catches 87.8 %. This
   confirms M4 (shadow over water) as the most valuable new module.
3. The v1.0.2 union lowers leak against the best single detector (5.4 % vs 7.6 %) but throws
   away more clear pixels (19.0 % vs 14.8 %). This is the H2 direction.
4. At 0.60, `cs_cdf` keeps almost everything (0.8 % discard) but leaks 22.4 %, so its default
   threshold is badly placed. `cs` is the strongest GEE input. R1 sweeps both.
5. Deep learning leads GEE-native masks by about 5 BOA points (93–94 % vs 88.6 %). UnetMobV2 was
   trained on this dataset (in-domain), so its lead is optimistic.
6. Our numbers sit near the 2026 audit's test-split figures (Cloud Score+ 7.6/14.8 here vs
   8.5/12.7 there). That is an independent sanity check.

**Not done:**
- The alignment gate on all patches.
- Paired tests, threshold sweeps, OmniCloudMask/CloudS2Mask (R1).
- Labelling setup (R2).
- Nothing committed.

**Next:** R1 and R2 (see STATE).

## 2026-11-08 — R1 development benchmark (validation split)

**Asked:** start R1 (the full comparison).

**Done:**
1. **Alignment gate on every patch** (`check_gee_alignment.py --n 0`, cached as
   `gee_align_<tid>.npz`): **460 of 535 pass**. Of the 75 failures, 52 have a one-pixel best
   shift ((1,0) 34, (0,1) 13, (1,1) 5) and 23 have zero best shift but r < 0.99 (likely
   low-contrast scenes; not verified). Main tables exclude all 75 (protocol §2); two sensitivity
   tables keep them (D-19). `results/r1_2026-11-08/gee_alignment.csv`.
2. **OmniCloudMask v4.0** (package 1.8.1) run on the RTX 5070 Ti (PyTorch 2.11 + CUDA 12.8,
   `uv sync --group dl`) on all 535 patches; 53 s of GPU time in total. CloudS2Mask dropped (D-18).
3. New code: `scripts/run_r1.py`, `scripts/run_dl.py`, `src/cloudbench/strata.py` (coast ≤ 200 m,
   open water), paired and stratum-difference bootstraps in `metrics.py` (vectorised), ECE.
   9 tests pass.
4. Protocol draft v0.2 (change log §7); decisions D-18, D-19.

**Reproducibility check:** the all-patches sensitivity table reproduces the R0 pilot exactly
(`cs<0.60` 7.6 / 14.8 / 88.6), so the code change did not move any number.

**Results** (`results/r1_2026-11-08/summary.md`; 460 aligned patches, 107 sites, 119.2 M pixels;
water 14.9 M px in 67 sites). DEVELOPMENT numbers, not paper results.

| Method | Leak % all | Discard % all | BOA % all | BOA % water | Shadow recall % water / land |
|---|---|---|---|---|---|
| cs < 0.60 | 9.2 | 17.8 | 87.1 [85.8, 88.6] | 84.6 | 59.3 / 91.3 |
| v1.0.2 union | 6.7 | 22.5 | 86.1 | 84.4 | 60.0 / 92.6 |
| v1.0.2 FINAL | 5.1 | 26.9 | 84.7 | 84.1 | 64.8 / 96.4 |
| UnetMobV2-v2 (in-domain) | 7.7 | 6.0 | 93.3 | 93.3 | 74.8 / 90.2 |
| SEnSeIv2 | 7.0 | 7.5 | 93.0 | 93.2 | 87.0 / 91.7 |
| **OmniCloudMask** | 7.7 | 5.7 | 93.4 [92.4, 94.4] | **94.7 [93.3, 96.0]** | **91.8 / 91.3** |

**Findings:**
1. **H1 (water leaks more), development evidence:** water − land leak is positive with a CI above
   0 for SCL (+6.7), QA60 (+7.1), `cs` (+5.6 [+0.2, +11.8]), the v1.0.2 union (+7.8) and FINAL
   (+7.6). For s2cloudless (+5.6 [−0.8, +11.9]) and `cs_cdf` (+4.6 [−2.6, +13.4]) the CI includes
   0. So "every operational mask" is **not yet supported** as written. None of the three
   deep-learning masks shows a water gap (OmniCloudMask −2.8 [−6.1, +0.4]).
2. **Shadow over water is a GEE-native failure, not a universal one.** `cs` catches 59 % of
   shadow pixels on water vs 91 % on land (Δ −32 points, CI [−46, −15]). OmniCloudMask catches 92 %
   on water, and SEnSeIv2 87 %. M4 must therefore be judged against deep learning too, not only
   against `cs`.
3. **Best mask over water: OmniCloudMask**, +10.1 BOA points over `cs` (paired CI [+7.5, +12.6])
   and +1.4 over UnetMobV2 (CI [+0.3, +2.6]). Caveat: whether its training data include these
   validation patches is not verified (D-18).
4. **H2 (union trades discard for leak):** against `cs`, the union lowers leak by 2.5 points
   ([−4.0, −1.3]) and raises discard by 4.6 ([+2.9, +6.9]); BOA −1.0. But the discard increase is
   **smaller over water (+1.4) than over land (+5.1)**, the opposite of H2's "most over water"
   clause.
5. **The v1.0.2 add-ons cost more than they give:** the shadow projection adds 1.4 points of
   shadow recall overall (0.2 on water) for 1.6 points more discard; the morphology lowers leak
   by 1.3 for 2.8 more discard. Both lower BOA (paired CIs exclude 0). Near the coast FINAL throws
   away 32.8 % of clear pixels.
6. **Default thresholds are not the best ones.** Best single-detector BOA: `cs_cdf` at 0.75
   (89.3 %) and `cs` at 0.55 (88.9 %), against 83.4 % and 87.1 % at the 0.60 defaults. These were
   picked on the same data they are scored on, so they are optimistic; R3 must choose thresholds
   on the train split.
7. **Calibration:** read as probabilities, the raw scores are off by 13–17 % ECE; s2cloudless is
   worst over water (22.5 %). This supports M3 (calibration).
8. **Coast (≤ 200 m):** the GEE masks discard more clear pixels there (union 25.2 %), and
   OmniCloudMask's shadow recall falls to 81.9 %. This is a hard stratum for everybody.
9. Excluding the 75 misaligned patches raises every method's leak by about 1–2 points but does
   not change the ranking (sensitivity tables).

**Not done:** the train split (only validation was scored); special strata turbid, bloom and
glint (they need labels or ancillary data, R2/R3); committing.

**Next:** R2 (IRIS + 10-patch timing pilot) and the R3 design, which now has to aim at deep
learning over water, not only at `cs`.
