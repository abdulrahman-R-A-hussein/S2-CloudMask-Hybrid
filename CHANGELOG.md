# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow
[Semantic Versioning](https://semver.org/). A version that changes the mask output is at least
a minor bump.

## [Unreleased]
Documentation only. `S2_CloudMask_SCIENTIFIC.js` is unchanged.

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
