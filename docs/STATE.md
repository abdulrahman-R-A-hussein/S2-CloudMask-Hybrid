# Current state

**Last updated: 2026-11-08 (R1 session).** Update this file at the end of every work
session, and add a matching entry to [`LOG.md`](LOG.md).

## In one paragraph
`S2_CloudMask_SCIENTIFIC.js` (v1.0.2) is a Google Earth Engine script. It masks clouds and
shadows in Sentinel-2 by combining SCL, s2cloudless, Cloud Score+ `cs`/`cs_cdf` and a shadow
projection with a union (OR).

The project is now a **research program to publish a water-aware cloud-masking method**
([`RESEARCH_PLAN.md`](RESEARCH_PLAN.md)). A Python benchmark (`python/`) scores every mask
against CloudSEN12+ expert labels, water vs land. The **first measured numbers** (pilot,
validation split) are in `results/pilot_2026-11-07/`; the full development comparison (R1) is in
`results/r1_2026-11-08/`.

## Version and records
| Item | Value |
|---|---|
| Code version (GEE script) | **1.0.2**. Unchanged since 2026-05-26 |
| Repo | `main` = `origin/main`; R1 work (scripts, results, docs) committed and pushed 2026-11-08 (`f83a415`) |
| GitHub | https://github.com/abdulrahman-R-A-hussein/S2-CloudMask-Hybrid (0 releases) |
| Zenodo | v1.0.2 version DOI **10.5281/zenodo.20395978**; concept DOI **10.5281/zenodo.20395977** |
| Earth Engine | Service account via `GEE_SERVICE_ACCOUNT_JSON` (D-16); works (tested 2026-11-07) |
| Benchmark data | CloudSEN12+ v1.1.2 (CC0), read remotely and cached in `python/data/cache/` (git-ignored) |

## Status board
| Area | Status |
|---|---|
| GEE script | ✅ works as released; not re-run in the Code Editor this session |
| Documentation and hand-off system | ✅ |
| **R0 pilot benchmark** | ✅ 535 validation patches, 107 sites, 138.6 M pixels; 7 tests pass |
| R1 full development benchmark | ✅ validation split, 460 aligned patches; OmniCloudMask run on GPU; 9 tests pass |
| R2 water labels (author labels) | ⏳ next (IRIS setup + 10-patch timing pilot) |
| R3 water-aware fusion M1–M6 | ⏳ |
| R4 protocol freeze + locked test run | ⏳ (test split locked, D-15) |
| Phase A2 GitHub release / A3 website fix | ⏳ |

## R1 headline (validation split, 460 aligned patches; details in LOG 2026-11-08)
- **OmniCloudMask is the best mask over water:** BOA 94.7 % vs 84.6 % for Cloud Score+ `cs < 0.60`
  (paired +10.1 points), and it catches 92 % of shadow pixels on water.
- **Shadow over water is a GEE-native failure:** `cs` 59 % on water vs 91 % on land. Deep-learning
  masks have no water gap.
- H1 (water leaks more) holds for SCL, QA60, `cs`, union and FINAL; the CI includes 0 for
  s2cloudless and `cs_cdf`.
- The v1.0.2 union lowers leak vs `cs` (−2.5) but raises discard (+4.6); its shadow projection and
  morphology each lower BOA. The discard rise is smaller over water than land (against H2's clause).
- Default thresholds are not optimal: `cs_cdf` 0.75 gives BOA 89.3 % vs 83.4 % at 0.60
  (chosen on validation, so optimistic).
- Raw scores are poorly calibrated (ECE 13–22 %).

## Pilot headline (validation split, all 535 patches; details in LOG 2026-11-07, second session)
- The best GEE-native single mask is Cloud Score+ `cs < 0.60`: BOA 88.6 %, leak 7.6 %,
  discard 14.8 %.
- The v1.0.2 union has lower leak (5.4 %) but higher discard (19.0 %).
- Deep-learning masks reach BOA 93–94 %.
- **Over water every GEE-native mask leaks more** (union 10.8 % vs 4.5 % on land). The
  deep-learning masks show no water gap.
- **Shadow over water is the main failure:** about 58 % recall for `cs` and the union, against
  about 92 % on land.

## Top known issues
1. **F-03:** shadow projection skips water. The pilot confirms that shadows on water are the
   weakest point.
2. **F-12 / F-05:** the morphology leaves only about a 30 m net buffer and deletes small clouds.
3. **F-01 / F-02:** `MIN_AGREEMENT` is not implemented, and the confidence score double-counts
   Cloud Score+.
4. **Benchmark caveats:**
   - validation split only (train split not scored; thresholds picked on validation are optimistic);
   - 75/535 patches fail the GEE alignment gate (X-06, D-19); main tables exclude them;
   - OmniCloudMask may have been trained on these patches (not verified, D-18);
   - WorldCover water is static (2020); no turbid/bloom/glint strata yet.
5. **X-05:** CloudSEN12+ bundled masks: one corrupted site (ROI_00009); SCL and s2cloudless
   differ from today's GEE on a minority of patches.

## Next actions (in order)
1. ~~Commit and push R1~~ done 2026-11-08.
2. ~~R1~~ done 2026-11-08 (validation split).
3. **R2:**
   - set up IRIS;
   - the author labels 10 water patches to time it;
   - then plan 150–300 patches;
   - recruit a second annotator for ≥ 10 %.
4. **R3 design decisions for the author:** whether the method may use a GPU step (e.g.
   OmniCloudMask as teacher/feature) or stays GEE-only; score the train split to fit thresholds.
5. **A2 / A3:** the GitHub release `v1.0.3`; the website entry fix.

## Where to look
- Plan: [`RESEARCH_PLAN.md`](RESEARCH_PLAN.md) · Tests: [`EXPERIMENT_PROTOCOL.md`](EXPERIMENT_PROTOCOL.md) · Paper: [`PAPER1_OUTLINE.md`](PAPER1_OUTLINE.md)
- Why: [`DECISIONS.md`](DECISIONS.md) · Literature: [`LITERATURE_REVIEW.md`](LITERATURE_REVIEW.md) · Issues: [`AUDIT_2026-11-07.md`](AUDIT_2026-11-07.md)
- Code: [`../python/README.md`](../python/README.md) · Results: `../results/`
- History: [`LOG.md`](LOG.md), [`../CHANGELOG.md`](../CHANGELOG.md)
