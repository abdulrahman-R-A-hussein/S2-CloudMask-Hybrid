# Roadmap

Each item has an ID, the finding it answers (AUDIT `F-`/`C-`/`X-`, LITERATURE `L-`), what to do,
and **acceptance criteria**: how anyone can tell it is done. When an item is done, mark it ✅
with the date, and log it in [`LOG.md`](LOG.md) and [`../CHANGELOG.md`](../CHANGELOG.md).

**Rule for every phase:** no accuracy or timing number enters the README unless a script in the
repo produced it and the run is logged.

---

## Phase A: documentation and release hygiene → v1.0.3 (code unchanged)

| ID | Item | Answers | Acceptance criteria |
|---|---|---|---|
| A1 ✅ 2026-11-07 | Correct README / USAGE / template text; create the hand-off docs | C-01…C-23 | AUDIT shows those items as "fixed (docs)". A grep for "weighted", ">95%", "145,230", "indian_river_lagoon.js" and "winner" in README/USAGE finds nothing |
| A2 | Publish GitHub release `v1.0.3`; connect Zenodo to GitHub (or upload manually) so the record links the repo; bump the version in `CITATION.cff` and the README citation | X-02, X-03 | GitHub shows a release. A new Zenodo version under concept DOI 10.5281/zenodo.20395977 lists the GitHub URL as a related identifier. CITATION.cff, README and the release show the same version and date |
| A3 | Fix the website entry: GEE JavaScript, the five detectors, no VPCA integration, no Python | X-01 | `projects.json` matches the repo README's one-line description |

## Phase B: code correctness → v1.1.0 (changes output; needs its own release)

| ID | Item | Answers | Acceptance criteria |
|---|---|---|---|
| B1 | Implement `MIN_AGREEMENT` as **family-level k-of-n**: families {SCL}, {s2cloudless}, {Cloud Score+: cs OR cs_cdf, chosen by a param}. Keep union as k = 1. Rebuild `confidence` as a 0–3 family count, **per image**. Drop "weighted" from the code comments, or add real weights | F-01, F-02, C-06, L1, L2 | With k = 1 the output equals v1.0.2's `mask_hybrid_std` (pixel-identical on the demo dates, checked by `reduceRegion` of the XOR = 0). With k = 2 or 3 the masks shrink monotonically |
| B2 | Morphology at a fixed scale: `.reproject({crs, scale: 20})` before the focal ops, as in the tutorial. Add `ERODE_M` (default 0 = dilation only) and `BUFFER_M` params | F-05, D-09 | The mask's pixel count is identical when the map is viewed at two zoom levels and in a 20 m export (**verify in GEE**) |
| B3 | Input checks: print requested vs. found dates, and images lacking s2cloudless or Cloud Score+. Use `ee.Algorithms.If` / `ee.Join.saveFirst` with an empty-image fallback, so a missing match does not fail the run | F-07 | A date filtered out by `CLOUDY_PIXEL_PERCENTAGE` is named in the console. A run with a deliberately missing s2cloudless image completes |
| B4 | Move the mask functions into a GEE module (`exports.maskS2 = function(img, params)`) loaded with `require('users/<owner>/<repo>:cloudmask')`. The main script and the template both import it | F-09 | The template runs as-is after editing only the area of interest and the dates |
| B5 | Per-image outputs: export a CSV with, per image and per detector, the % cloud over **water** and over **land** (SCL 6 vs. other). Label the composite counts as "yield". Expose a per-image masked collection for single-date water-quality work | F-06, F-10, D-03 | `Export.table.toDrive` produces one row per image × detector. The README describes the counts as yield, not accuracy |
| B6 | Build the UI from a layer registry (name → layer) instead of hard-coded indices | F-08 | Adding a new layer does not break any button |
| B7 | `VERSION` constant; print the version, the params and the image IDs at start. Remove the untested advice in the console text (`js:423`) | F-11, C-14 | The console shows the version and the image list. The script, `CITATION.cff` and the release tag agree |

## Phase C: quantitative validation (the main science gap)

| ID | Item | Answers | Acceptance criteria |
|---|---|---|---|
| C1 | **Reference set:** (a) CloudSEN12 / CloudSEN12+ patches whose labels include water, (b) 10–20 IRL Sentinel-2 scenes hand-labelled (clear / thick / thin cloud / shadow), stratified by season and including known bloom dates. Store the labels as GEE assets plus a manifest CSV (scene ID, labeller, date, licence) | L6 | The manifest exists. The labelling protocol is written in `docs/VALIDATION_PROTOCOL.md`. CloudSEN12's CC BY-NC licence is respected |
| C2 | **Metrics script** (Python `earthengine-api` or GEE): per class, per detector and fusion rule, **split into water and land**: omission, commission, F1, balanced overall accuracy, IoU | L6, F-06 | One script regenerates `results/validation_<date>.csv` and a run log. The README quotes only numbers from that file |
| C3 | **Threshold sweeps:** `cs_cdf` and `cs` 0.40–0.80 in steps of 0.05; s2cloudless 20–60 in steps of 5; k = 1, 2, 3. Reuse the sweep design from `D:\dev\Sulfate-Methos` (cs_cdf 0.40–0.80 in steps of 0.05) | L1, L7, D-02, D-04 | A table and curve of F1 (water) against threshold. The defaults are either confirmed or changed in DECISIONS, with the evidence linked |
| C4 | **Downstream check:** compare Rrs / chlorophyll retrievals with and without each mask against in-situ IRL stations, and against the USF IRL Sentinel-2 chlorophyll dataset | L4, L5 | A matched-pair table: bias and RMSE by mask choice |

## Phase D: water-specific method improvements (after C gives a baseline)

| ID | Item | Answers | Acceptance criteria |
|---|---|---|---|
| D1 | **Shadows over water:** a geometric candidate (project the cloud mask along the azimuth over a range of cloud heights × tan(solar zenith)) that does not need dark NIR over water. Intersect it with a relative-darkness test against the local water median | F-03, F-04, L3 | Shadow omission over water (from C2) improves over v1.1.0 without raising water commission by more than an agreed margin |
| D2 | **Adjacency buffer for water:** measure IRL Rrs bias against distance to the nearest cloud, then set `BUFFER_WATER_M` separately from the land buffer | L4, C-21 | A bias-vs-distance curve exists. The chosen buffer is the distance where the bias falls within the noise. Recorded in DECISIONS |
| D3 | **Bloom / turbid-water guard:** over water, do not let SCL or s2cloudless *alone* mask a pixel that Cloud Score+ rates clear and a floating-algae index (FAI/AFAI) rates as bloom. Make it a flagged option, off by default | L5 | Tested on known bloom dates: fewer bloom pixels lost, with no rise in cloud omission on the C1 labels |
| D4 | **Cirrus:** an optional L1C B10 (1375 nm) test via an L1C join, or the `ee.Algorithms.Sentinel2.CDI` parallax test | L10 | Thin-cloud omission (C2) improves |
| D5 | **Ceiling benchmark:** run OmniCloudMask (and optionally CloudS2Mask) offline on the C1 scenes | L9 | The same metrics table includes the deep-learning model as a reference row |

## Phase E: publication

| ID | Item | Acceptance criteria |
|---|---|---|
| E1 | Release v1.1.0 (Phase B) and v2.0.0 (Phases C and D) on GitHub, with matching Zenodo versions | Each version has a CHANGELOG entry, a tag, a Zenodo version and a CITATION.cff bump |
| E2 | A short write-up (a software or methods note) once Phase C numbers exist | Every number in it is traceable to `results/` |
