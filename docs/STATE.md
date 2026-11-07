# Current state

**Last updated: 2026-11-07.** Update this file at the end of every work session, and add a
matching entry to [`LOG.md`](LOG.md).

## In one paragraph
`S2_CloudMask_SCIENTIFIC.js` is a Google Earth Engine script. It masks clouds and cloud shadows
in Sentinel-2 L2A imagery by combining five detectors with a pixel union (OR):
- SCL classes 3/8/9/10;
- s2cloudless > 50;
- Cloud Score+ `cs` < 0.60;
- Cloud Score+ `cs_cdf` < 0.60;
- a sun-azimuth shadow projection.

It then applies erosion and a buffer, masks each image, and builds a median composite. It also
draws a comparison UI and prints remaining-pixel counts. The demo case is the Indian River Lagoon
(FL) on three 2022 dates. It is aimed at water-quality remote sensing.
**It is released (v1.0.2) but has never been quantitatively validated.**

## Version and records
| Item | Value |
|---|---|
| Code version | **1.0.2**. The code is unchanged since 2026-05-26 (`3719cde`) |
| Repo HEAD | `main` = `origin/main`: the 2026-11-07 docs commits on top of `1bd472d`, pushed to GitHub on 2026-11-07 |
| GitHub | https://github.com/abdulrahman-R-A-hussein/S2-CloudMask-Hybrid (0 releases, 0 tags) |
| Zenodo | v1.0.2 version DOI **10.5281/zenodo.20395978**; concept (all versions) DOI **10.5281/zenodo.20395977** |
| Software Heritage | `swh:1:dir:4203251839fc8d6113b9d35e96547d589779eef8` |
| Licence / author | MIT / Abdulrahman Hussein (sole author since `1bd472d`) |
| Website entry | `D:\dev\Personal Website\data\projects.json` → `project-sentinel-cloud` (description is wrong, AUDIT X-01) |

## Status board
| Area | Status |
|---|---|
| Core masking script | ✅ works as released (last confirmed GEE run: **unknown**, not re-run on 2026-11-07) |
| Documentation | ✅ corrected 2026-11-07 (AUDIT C-01…C-23) |
| Hand-off system (AGENTS, STATE, LOG, DECISIONS, AUDIT, LITERATURE, ROADMAP, CHANGELOG) | ✅ created 2026-11-07 |
| Code correctness fixes (ROADMAP Phase B) | ⏳ not started |
| Quantitative validation (Phase C) | ⏳ not started. **This is the main gap** |
| Water-specific improvements (Phase D) | ⏳ not started |
| GitHub release matching Zenodo (A2) | ⏳ not started |
| Website description fix (A3) | ⏳ not started (separate repo) |

## Top known issues (details in [`AUDIT_2026-11-07.md`](AUDIT_2026-11-07.md))
1. **F-03:** shadow projection is off over water, the target surface.
2. **F-01/F-02:** `MIN_AGREEMENT` is not implemented, there are no weights, and the confidence
   score double-counts Cloud Score+.
3. **F-05:** morphology has no fixed scale and erodes before buffering (verify in GEE).
4. **F-06:** the printed "validation" is a tautological yield count.
5. **F-07:** dropped dates and missing s2cloudless matches fail silently.
6. **No accuracy numbers exist.** Do not quote any until Phase C produces them.

## Next actions (in order)
1. **A2:** create the GitHub release `v1.0.3` (docs only, same code), let Zenodo pick it up (or
   upload it by hand), and bump `CITATION.cff` and the README citation to match.
2. **A3:** correct the website entry (`D:\dev\Personal Website\data\projects.json`).
3. **B1–B7:** code-correctness release v1.1.0 (see [`ROADMAP.md`](ROADMAP.md)).
4. **C1–C3:** build the water-focused reference set and run the threshold sweeps.

## Where to look
- Why something is the way it is: [`DECISIONS.md`](DECISIONS.md)
- What the literature says: [`LITERATURE_REVIEW.md`](LITERATURE_REVIEW.md)
- What to build next: [`ROADMAP.md`](ROADMAP.md)
- History: [`LOG.md`](LOG.md), [`../CHANGELOG.md`](../CHANGELOG.md)
