# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow
[Semantic Versioning](https://semver.org/). A version that changes the mask output is at least
a minor bump.

## [Unreleased]
`S2_CloudMask_SCIENTIFIC.js` is unchanged.

### Added (research, 2026-11-08, R1)
- `python/scripts/run_r1.py` (all methods, sweeps, coast stratum, paired and water-minus-land
  bootstraps, ECE, T1), `python/scripts/run_dl.py` (OmniCloudMask on GPU),
  `python/src/cloudbench/strata.py`; alignment gate on every patch; `dl` dependency group
  (PyTorch CUDA 12.8 + OmniCloudMask).
- `results/r1_2026-11-08/`: development results on the validation split.
- Decisions D-18, D-19; audit X-06; protocol draft v0.2.

### Added (research, 2026-11-07, second session)
- `python/` benchmark package `cloudbench`:
  - CloudSEN12+ reader and Earth Engine input fetch;
  - numpy replica of every v1.0.2 rule;
  - metrics with site-bootstrap CIs;
  - pilot runner, alignment and provenance gate;
  - 7 unit tests.
- `results/pilot_2026-11-07/`: first measured accuracy numbers (validation split, water vs land).
- `docs/RESEARCH_PLAN.md`, `docs/EXPERIMENT_PROTOCOL.md` (pre-registration draft), `docs/PAPER1_OUTLINE.md`.
- `LITERATURE_REVIEW.md` §8: chronological map 1988–2026 and gap matrix G1–G10.
- Decisions D-14 to D-17; audit items F-12 (net buffer is about 30 m) and X-05 (CloudSEN12+ bundled masks:
  one corrupted site, SCL/s2cloudless differ from today's GEE on a minority of patches); roadmap R0–R6.

### Earlier in Unreleased (first session)
Documentation only.

### Added
- `AGENTS.md` (hand-off entry point for any AI tool or person) and `CLAUDE.md`.
- `docs/STATE.md`, `docs/LOG.md`, `docs/DECISIONS.md`, `docs/AUDIT_2026-11-07.md`,
  `docs/LITERATURE_REVIEW.md`, `docs/ROADMAP.md`, and this changelog.

### Fixed (documentation)
- Inverted threshold advice in `docs/USAGE.md` and the template's preset comments. Masking fires
  where the score is *below* the threshold, so raising `CS_CDF_THRESH` masks more.
- Removed performance figures and sample outputs that were never measured. The README now says
  the method has not yet been quantitatively validated.
- Removed the "weighted" and "first open-source" claims; corrected the bands list and the cirrus
  claim; replaced the broken Cloud Score+ link with Pasquarella et al. 2023; credited the GEE
  s2cloudless tutorial; documented that `MIN_AGREEMENT` is not implemented and that shadow
  projection is off over water.

## [1.0.2] - 2026-05-26
Reconstructed from git history and the Zenodo record. No earlier version is documented.

### Added
- GEE script combining SCL, s2cloudless, Cloud Score+ `cs` and `cs_cdf` (pixel union), plus a
  sun-azimuth shadow projection, morphology (20 m erosion, 50 m buffer), a confidence layer,
  per-image masking before the median composite, a comparison UI and remaining-pixel counts.
- README, `docs/USAGE.md`, `examples/custom_area_template.js`, `CITATION.cff`, MIT `LICENSE`.
- Zenodo archive: DOI 10.5281/zenodo.20395978 (concept 10.5281/zenodo.20395977).

### Changed
- Same day: ORCID and Scholar links, DOI badge and citation, sole authorship in `CITATION.cff`.
