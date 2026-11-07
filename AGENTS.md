# AGENTS.md: start here (for any AI tool or new contributor)

This file is the entry point. It should be enough to understand the project, its history and
its plans, and to continue the work without access to any earlier chat.

## What this project is (10 lines)
- **S2-CloudMask-Hybrid**: a Google Earth Engine (GEE) **JavaScript** script,
  `S2_CloudMask_SCIENTIFIC.js`, for cloud and cloud-shadow masking of **Sentinel-2 L2A** imagery.
- It combines **5 detectors** with a pixel **union (OR)**:
  - SCL classes 3/8/9/10;
  - s2cloudless probability > 50;
  - Cloud Score+ `cs` < 0.60;
  - Cloud Score+ `cs_cdf` < 0.60;
  - a sun-azimuth shadow projection (from the GEE s2cloudless tutorial).
- Then 20 m erosion and a 50 m buffer. Each image is masked **before** the median composite.
- There is an interactive comparison UI and remaining-pixel counts.
- Demo: Indian River Lagoon, Florida; dates 2022-09-15, 2022-11-04, 2022-11-19.
- Purpose: **water-quality** remote sensing (PhD work, Abdulrahman Hussein, Kent State University).
- Released as **v1.0.2** on 2026-05-26: GitHub `abdulrahman-R-A-hussein/S2-CloudMask-Hybrid`, Zenodo
  DOI 10.5281/zenodo.20395978 (concept 10.5281/zenodo.20395977).
- **It has never been quantitatively validated.** That is the main open science task.
- No local runtime and no tests: you run it by pasting it into https://code.earthengine.google.com/.

## Read in this order
1. [`docs/STATE.md`](docs/STATE.md): current status, top issues, next actions.
2. The last entry of [`docs/LOG.md`](docs/LOG.md): what happened most recently.
3. [`docs/ROADMAP.md`](docs/ROADMAP.md): what to build next, with acceptance criteria.
4. As needed:
   - [`docs/AUDIT_2026-11-07.md`](docs/AUDIT_2026-11-07.md): known defects (F), checked
     claims (C), external records (X), each with file:line evidence;
   - [`docs/DECISIONS.md`](docs/DECISIONS.md): why things are the way they are;
   - [`docs/LITERATURE_REVIEW.md`](docs/LITERATURE_REVIEW.md): sources for every method and
     improvement, with DOIs;
   - [`docs/USAGE.md`](docs/USAGE.md): user guide.

## File map
```
S2_CloudMask_SCIENTIFIC.js      the whole method (GEE Code Editor script); unchanged since v1.0.2
examples/custom_area_template.js  adaptation template (not runnable as-is, AUDIT F-09)
README.md                       public description; citation
CITATION.cff                    machine-readable citation (version must match the release)
CHANGELOG.md                    versions
AGENTS.md / CLAUDE.md           this hand-off entry point (CLAUDE.md just imports this file)
docs/
  STATE.md                      snapshot: status, issues, next actions      ← update every session
  LOG.md                        dated history, newest at the bottom         ← append every session
  DECISIONS.md                  design decisions D-01…                      ← append when one changes
  AUDIT_2026-11-07.md           findings F-/C-/X- with status
  LITERATURE_REVIEW.md          literature with DOIs; §7 maps findings to roadmap items
  ROADMAP.md                    phases A–B and research phases R0–R6 with acceptance criteria
  RESEARCH_PLAN.md              research program: water first, papers P1–P3, method M1–M6
  EXPERIMENT_PROTOCOL.md        pre-registration: hypotheses H1–H7, locked test split, metrics
  PAPER1_OUTLINE.md             paper skeleton; every number is "TBD (results/...)"
  USAGE.md                      user guide
python/                         benchmark code (uv project; see python/README.md)
  src/cloudbench/               data (CloudSEN12+ + GEE), detectors (v1.0.2 replica), metrics
  scripts/run_pilot.py          scores the masks, water vs land, with site-bootstrap CIs
  tests/                        pytest
results/<run>/                  committed outputs: counts, metrics, provenance, run.log
```

**Benchmark rules:**
- The CloudSEN12+ **test split is locked** until EXPERIMENT_PROTOCOL v1.0 is tagged (D-15).
- Detector inputs come from Earth Engine, **not** from the CloudSEN12+ bundled Cloud Score+
  layers, which are wrong (D-17).
- `TortillaDataFrame.read()` takes a row position.

## Key code locations (`S2_CloudMask_SCIENTIFIC.js`)
| Lines | What |
|---|---|
| 22–44 | Area of interest, `PARAMS`, `DATES`, `VIS` |
| 49–82 | Build the collection: S2 SR + s2cloudless join + Cloud Score+ link |
| 87–118 | Detectors 1–4 (SCL, s2cloudless, cs, cs_cdf) |
| 123–145 | Detector 5: shadow projection (skips water, AUDIT F-03) |
| 151–186 | `addAllMasks`: union, confidence, morphology |
| 194–222 | Per-image masking → median composites; aggregated layers |
| 229–248 | Map layers (the UI depends on this order, F-08) |
| 253–297 | Pixel-count statistics (a yield metric, not accuracy, F-06) |
| 302–412 | UI panel |

## Rules (same as the author's other research repos)
1. **Never write a number that no run produced.** Accuracy, timing and pixel counts in the docs
   must come from a logged run or a script in the repo. Unknown is written "unknown".
2. **Every literature claim gets a DOI or URL.** Mark it "not verified" if the full text was not
   read.
3. **No "first", "best" or "winner" claims** unless a cited benchmark supports them.
4. **Threshold direction:** detectors flag cloud where `cs`/`cs_cdf` < T (higher T masks more),
   where s2cloudless > T (higher T masks less), and where NIR < T (higher T flags more shadow).
   Check against the code before writing tuning advice.
5. **Code changes are versioned.** Any change to the mask output means a CHANGELOG entry, a new
   minor version, a GitHub release, a Zenodo version, and a `CITATION.cff` bump. Keep the repo
   code identical to the latest Zenodo version between releases.
6. **At the end of every session:** append to `docs/LOG.md`, update `docs/STATE.md`, mark
   finished roadmap and audit items, and add any new decision to `DECISIONS.md`.

## Environment quirks (this PC)
- **Git "dubious ownership":** the repo was created under another Windows account. Use
  `git -c safe.directory=D:/dev/Cloud-Masking <command>`. Do not edit the global git config
  without asking.
- GEE cannot be reached from an AI sandbox. Ask the author to run the script in the Code
  Editor, or set up the Python `earthengine-api` with the author's own credentials.
  **Never read, print or commit credential or key files.**
- Commit or push only when the author asks.

## Related places
| Place | Relation |
|---|---|
| `D:\dev\Sulfate-Methos\earth-engine\amd_detection_v*.js` | The AMD Detection Tool carries its own hybrid cloud mask, which existed earlier (v1.0.0, 2025-11-15): SCL + `MSK_CLDPRB` ≤ 20 + cs + cs_cdf, no shadow projection. Fixes here do not propagate there automatically |
| `D:\dev\VPCA+STEPWISE-REGRESSION` | SpectraLab. Its plugin contract lists "cloud masking" as a future module. It uses its own SCL water/cloud mask |
| `D:\dev\Water-AC` | Atmospheric correction for drone and satellite water reflectance. Cloud masking is upstream of it |
| `D:\dev\phd\00_INDEX.md` | The PhD hub lists this repo as the source of truth for cloud-masking claims |
| `D:\dev\Personal Website\data\projects.json` | Public project entry. Its description is wrong (AUDIT X-01) |

## Release checklist
1. Update `CHANGELOG.md` (move Unreleased → version + date).
2. Bump `version` and `date-released` in `CITATION.cff` and the README citation block. Bump the
   `VERSION` constant in the script once it exists (ROADMAP B7).
3. Commit, tag `vX.Y.Z`, push, and create a GitHub release.
4. Confirm that Zenodo created a new version under concept DOI 10.5281/zenodo.20395977 (or upload
   by hand). Put the new version DOI in the README.
5. Log the release in `docs/LOG.md` and update `docs/STATE.md`.
