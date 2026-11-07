# Current state

**Last updated: 2026-11-07 (second session).** Update this file at the end of every work
session, and add a matching entry to [`LOG.md`](LOG.md).

## In one paragraph
`S2_CloudMask_SCIENTIFIC.js` (v1.0.2) is a Google Earth Engine script. It masks clouds and
shadows in Sentinel-2 by combining SCL, s2cloudless, Cloud Score+ `cs`/`cs_cdf` and a shadow
projection with a union (OR).

The project is now a **research program to publish a water-aware cloud-masking method**
([`RESEARCH_PLAN.md`](RESEARCH_PLAN.md)). A Python benchmark (`python/`) scores every mask
against CloudSEN12+ expert labels, water vs land. The **first measured numbers** (pilot,
validation split) are in `results/pilot_2026-11-07/`.

## Version and records
| Item | Value |
|---|---|
| Code version (GEE script) | **1.0.2**. Unchanged since 2026-05-26 |
| Repo | `main`. The second-session work (python/, results/, research docs) is **not committed yet** |
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
| R1 full development benchmark | ⏳ next |
| R2 water labels (author labels) | ⏳ next (IRIS setup + 10-patch timing pilot) |
| R3 water-aware fusion M1–M6 | ⏳ |
| R4 protocol freeze + locked test run | ⏳ (test split locked, D-15) |
| Phase A2 GitHub release / A3 website fix | ⏳ |

## Pilot headline (validation split, PILOT; details in LOG 2026-11-07, second session)
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
4. **Pilot caveats:**
   - validation split only;
   - no paired tests yet;
   - a one-pixel GEE vs CloudSEN12+ offset on 2 of 10 checked patches (gate not yet run on all
     patches);
   - WorldCover water is static (2020).
5. **X-05:** CloudSEN12+ bundled masks: one corrupted site (ROI_00009); SCL and s2cloudless
   differ from today's GEE on a minority of patches.

## Next actions (in order)
1. **Author:** approve a commit (and push) of the second-session work.
2. **R1:**
   - alignment gate on every patch (exclude or shift-correct failures);
   - threshold sweeps (`cs`, `cs_cdf` 0.40–0.80; s2cloudless 20–60);
   - paired site-bootstrap tests;
   - OmniCloudMask + CloudS2Mask locally (RTX 5070 Ti; needs a CUDA 12.8 PyTorch build);
   - coast stratum;
   - dataset summary table T1.
3. **R2:**
   - set up IRIS;
   - the author labels 10 water patches to time it;
   - then plan 150–300 patches;
   - recruit a second annotator for ≥ 10 %.
4. **A2 / A3:** the GitHub release `v1.0.3`; the website entry fix.

## Where to look
- Plan: [`RESEARCH_PLAN.md`](RESEARCH_PLAN.md) · Tests: [`EXPERIMENT_PROTOCOL.md`](EXPERIMENT_PROTOCOL.md) · Paper: [`PAPER1_OUTLINE.md`](PAPER1_OUTLINE.md)
- Why: [`DECISIONS.md`](DECISIONS.md) · Literature: [`LITERATURE_REVIEW.md`](LITERATURE_REVIEW.md) · Issues: [`AUDIT_2026-11-07.md`](AUDIT_2026-11-07.md)
- Code: [`../python/README.md`](../python/README.md) · Results: `../results/`
- History: [`LOG.md`](LOG.md), [`../CHANGELOG.md`](../CHANGELOG.md)
