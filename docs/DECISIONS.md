# Decision record

One entry per design decision, so nobody has to rediscover *why* the code is the way it is.
Decisions D-01 to D-11 were made before this file existed (v1.0.2, May 2026). They are
**reconstructed from the code, the git history and the GEE tutorial the code follows**. Where
the original reasoning is unknown, the entry says so.

**Format:** status (`current` · `under review` · `superseded`) · decision · rationale ·
evidence · revisit when.

To add one, append D-NN at the bottom, set `status: current`, and log it in [`LOG.md`](LOG.md).

---

### D-01 · Platform: one Google Earth Engine Code Editor script (JavaScript)
- **Status:** current
- **Decision:** everything lives in `S2_CloudMask_SCIENTIFIC.js`, which is pasted into the GEE
  Code Editor. There is no local runtime, package or test suite.
- **Rationale:** all inputs (S2 SR, s2cloudless, Cloud Score+) are hosted in GEE; zero install for
  users. *Original reasoning not recorded.*
- **Evidence:** `README.md` Quick Start.
- **Revisit when:** Phase C needs reproducible, scripted validation runs (Python `earthengine-api`),
  or the mask must be shared with other scripts (GEE `require` module, ROADMAP B4).

### D-02 · Fusion rule: pixel union (cloud if ANY detector fires)
- **Status:** under review (ROADMAP B1, C3)
- **Decision:** `mask_hybrid_std = SCL OR s2cloudless OR cs OR cs_cdf` (`js:159`), then OR shadows.
- **Rationale (from the README):** for water quality, a missed cloud (false negative) costs more
  than over-masking.
- **Evidence for:** ensembles beat single algorithms (Tarrio et al. 2020; LITERATURE §2, §4).
- **Evidence against:** a union maximises commission. Bright turbid water and blooms are known
  to be masked as cloud, which matters for algal-bloom work (LITERATURE §3.1). Tarrio tested
  voting and learned fusion, not a union.
- **Revisit when:** Phase C labels exist. Compare the union with family-level k-of-n voting.
- **Note:** the AMD tool (`D:\dev\Sulfate-Methos`, since v1.0.0 on 2025-11-15) uses the same
  logic written as an AND of "clear" tests.

### D-03 · Mask each image before the median composite
- **Status:** current
- **Decision:** `updateMask` per image, then `.median()` (`js:194–199`).
- **Rationale:** masking after compositing cannot remove a cloud that is present on most dates.
  Per-image masking is standard GEE practice (Cloud Score+ and s2cloudless tutorials).
- **Revisit when:** water-quality outputs need single-date products (water changes daily). The
  composite then becomes a visualisation only (ROADMAP B5).

### D-04 · Cloud Score+ thresholds `cs` < 0.60 and `cs_cdf` < 0.60
- **Status:** under review (ROADMAP C3)
- **Decision:** both bands are used, each with threshold 0.60.
- **Rationale:** GEE catalog guidance: 0.50–0.65 generally works, and its example uses 0.60 on
  `cs_cdf` (LITERATURE §1).
- **Caveat:** the two bands come from one model, so they are not independent votes (AUDIT F-02).
  The 0.60 default was never tested on the IRL.
- **Revisit when:** the threshold sweep in Phase C.

### D-05 · s2cloudless threshold 50, shadow parameters and 60 % scene filter from the GEE tutorial
- **Status:** current (parameters), under review (shadow method, ROADMAP D1)
- **Decision:**
  - `CLOUD_PROB_THRESH` 50
  - `NIR_DARK_THRESH` 0.15
  - `CLOUD_PROJ_DIST` 1 km
  - `BUFFER` 50 m
  - `CLOUDY_PIXEL_PERCENTAGE < 60`
- **Rationale:** these are the example values of the GEE community tutorial "Sentinel-2 Cloud
  Masking with s2cloudless" (`CLD_PRB_THRESH`, `NIR_DRK_THRESH`, `CLD_PRJ_DIST`, `BUFFER`,
  `CLOUD_FILTER`). The shadow function follows the tutorial's code.
- **Evidence:** LITERATURE §1 row 5. The tutorial is credited in the README since 2026-11-07.
- **Revisit when:** Phase C (thresholds) and Phase D (shadow method over water).

### D-06 · SCL classes {3, 8, 9, 10} count as cloud or shadow; classes 2 and 7 do not
- **Status:** current
- **Decision:** 3 cloud shadow, 8 cloud medium probability, 9 cloud high probability, 10 thin cirrus.
- **Not included:** 7 (unclassified / cloud low probability) and 2 (dark area / topographic shadow).
- **Rationale:** *not recorded.* Probably to limit commission; class 7 is a broad catch-all.
- **Revisit when:** Phase C shows SCL omission at cloud edges over water.

### D-07 · QA60 is not used
- **Status:** current
- **Decision:** no QA60 bitmask test.
- **Rationale:** QA60 is empty in GEE from 2022-01-25 to 2024-02-28, which covers all three study
  dates. The older L1C mask also had about 37 % omission (Coluzzi et al. 2018). The AMD tool
  dropped QA60 for the same reason.
- **Revisit when:** never for 2022 data. `MSK_CLASSI_*` could be an extra vote for dates after
  2024-02-28.

### D-08 · The shadow test excludes SCL water
- **Status:** under review (ROADMAP D1). This is the most important open issue for the stated use.
- **Decision:** dark-NIR pixels are multiplied by `SCL != 6` (`js:127–130`).
- **Rationale:** inherited from the land-oriented tutorial. Water is NIR-dark everywhere, so a
  dark-NIR test would flag all water.
- **Consequence:** shadows on the lagoon are caught only by SCL class 3 and Cloud Score+ (AUDIT F-03).
- **Revisit when:** Phase D adds a geometric shadow candidate over water.

### D-09 · Morphology: `focal_min` 20 m, then `focal_max` 50 m
- **Status:** under review (ROADMAP B2)
- **Decision:** erode to remove isolated pixels, then dilate as the edge buffer (`js:172–175`).
- **Difference from the tutorial:** the tutorial also does min then max, but reprojects the
  result to 20 m. We do not.
- **Revisit when:** Phase B. Add a fixed reproject, and consider dilation only (the erosion
  removes small clouds).

### D-10 · Study design: Indian River Lagoon, three explicit dates
- **Status:** current (as the demo case)
- **Decision:** bounding box `[-80.763739, 27.605387, -80.503601, 28.621909]`. Dates 2022-09-15,
  2022-11-04 and 2022-11-19, each with a one-day window (`js:22`, `js:38–42`, `js:49–54`).
- **Rationale:** *not recorded.* The author's IRL work covers many more dates. SpectraLab's
  validation averages 34 IRL dates (`D:\dev\VPCA+STEPWISE-REGRESSION\data\validation\IRL_notebook_avgCorrelationMatrix.csv`,
  per that repo's history).
- **Revisit when:** Phase C picks labelling scenes. Choose dates with known cloud *and* known bloom
  conditions.

### D-11 · MIT licence, Zenodo archive, sole author
- **Status:** current
- **Decision:**
  - MIT licence.
  - Zenodo v1.0.2: version DOI 10.5281/zenodo.20395978, concept DOI 10.5281/zenodo.20395977.
  - Joseph D. Ortiz was listed in `CITATION.cff` at first and removed in commit `1bd472d`
    ("sole author Abdulrahman Hussein"), all on 2026-05-26.
- **Rationale:** *the reason for the authorship change is not recorded in the repo.*
- **Revisit when:** a paper or new release. Authorship is the author's decision, not a technical one.

### D-12 · Hand-off documentation system (2026-11-07)
- **Status:** current
- **Decision:**
  - `AGENTS.md` is the entry point for any AI tool or person; `CLAUDE.md` imports it.
  - `docs/` holds STATE, LOG, DECISIONS, AUDIT, LITERATURE_REVIEW and ROADMAP; `CHANGELOG.md`
    sits at the root.
  - Everything is public in the repo.
- **Rationale:** the project's history existed only in 5 commits and on Zenodo, and the README
  carried claims nobody had checked. The structure mirrors the author's other research repos
  (Water-AC: `docs/LOG.md`, `LITERATURE_REVIEW.md`; PhD hub: claims ledger, contradictions register).
- **Revisit when:** the docs drift from the code. The audit's file:line references are the check.

### D-13 · Fix the documentation now, change the code only in Phase B (2026-11-07)
- **Status:** current
- **Decision:**
  - README, USAGE and the template's comments were corrected (AUDIT C-items).
  - `S2_CloudMask_SCIENTIFIC.js` was **not** changed, so the Zenodo v1.0.2 code and the repo
    code stay identical until a deliberate v1.1.0.
- **Rationale:** text errors (inverted tuning advice, unmeasured numbers) mislead users today.
  Code changes alter scientific output and need their own release and test.
- **Revisit when:** Phase B starts.

### D-14 · Research strategy: staged, water first, three papers (2026-11-07)
- **Status:** current
- **Decision:** P1 is a water-stratified benchmark plus a GEE-native water-aware fusion plus water
  labels. P2 is a water-aware deep-learning model and dataset. P3 is cross-sensor transfer. See
  [`RESEARCH_PLAN.md`](RESEARCH_PLAN.md).
- **Rationale:** the independent 2026 audit shows deep learning leading overall and every mask
  leaking more over water. Water is the open, checkable gap and the author's application.
- **Revisit when:** after R1. If deep learning is already near-perfect over water, P1 shifts to
  benchmark + dataset + calibration.

### D-15 · CloudSEN12+ test split locked until the protocol is frozen (2026-11-07)
- **Status:** current
- **Decision:** all development and pilot work uses `train`/`validation`. `run_pilot.py` refuses
  `--split test`. The test split is run once, after [`EXPERIMENT_PROTOCOL.md`](EXPERIMENT_PROTOCOL.md)
  v1.0 is tagged.
- **Rationale:** headline numbers must not be tuned on the data that reports them.

### D-16 · Earth Engine access through the existing service account (2026-11-07)
- **Status:** current
- **Decision:** `python/src/cloudbench/auth.py` (adapted from SpectraLab) reads the key path
  from `GEE_SERVICE_ACCOUNT_JSON`, set per run. It uses the high-volume endpoint. The key is
  never opened by the assistant, printed or committed (`.gitignore` blocks `*key*.json`).

### D-17 · Detector inputs come from Earth Engine, not from CloudSEN12+ "extra" (2026-11-07)
- **Status:** current
- **Decision:** SCL, B8, s2cloudless, `cs` and `cs_cdf` are fetched from GEE on each patch's grid.
  From CloudSEN12+ we use only the labels, WorldCover and the deep-learning masks.
- **Rationale (from all 535 validation patches,
  `results/pilot_2026-11-07/provenance_cs12_vs_gee.csv`):**
  - For most patches the bundled layers match GEE exactly: `cs_cdf` median r = 1.000, and only
    4 patches have r < 0.9.
  - All 5 dates of **one site (ROI_00009)** carry corrupted Cloud Score+ layers: 85–98 % of
    `cs_cdf` values fall outside 0–10000, and the rest are anti-correlated with GEE.
  - SCL differs from today's GEE SCL on more than 5 % of pixels in 87 of 535 patches, and
    s2cloudless in 55. That is consistent with the products having been regenerated since the
    dataset was built (*cause not verified*).
  - Fetching from GEE keeps every input identical to what the operational script uses today.
- **Correction note:** the first diagnosis (same day) examined only ROI_00009 and wrongly
  generalised to "the layers disagree with GEE". The full run showed the problem is one site.
- **Side effect:** an early pilot that read the bundled layers silently dropped the ROI_00009
  pixels through its validity filter. In a 6-patch smoke test that included that site, it
  scored 277,542 pixels, against 1,554,486 after the fix. It was stopped and replaced.
- **Follow-up:** consider reporting ROI_00009 to the dataset maintainers (an outward action; the
  author decides).
