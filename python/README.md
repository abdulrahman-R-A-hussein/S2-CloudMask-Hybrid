# cloudbench: Sentinel-2 cloud-mask benchmark (research code)

Scores every Sentinel-2 cloud/shadow mask that the GEE script uses (and deep-learning references)
against CloudSEN12+ expert labels, split into **water and land**. This is research code for
Paper 1 (`docs/RESEARCH_PLAN.md`, `docs/EXPERIMENT_PROTOCOL.md`).

## Setup (Windows, uv)
```bash
cd python
uv sync --group dev
```

## Earth Engine access
Set the service-account key path for the run only (DECISIONS D-16). The key is never committed.
```bash
GEE_SERVICE_ACCOUNT_JSON='D:\dev\gee-key.json' .venv/Scripts/python.exe scripts/check_gee_alignment.py --n 5
```

## Run
```bash
GEE_SERVICE_ACCOUNT_JSON='D:\dev\gee-key.json' .venv/Scripts/python.exe scripts/run_pilot.py --workers 8
uv run --group dev pytest -q
```
Outputs go to `../results/<run>/`: `counts.csv` (raw confusion counts), `metrics.csv` (with
95 % site-bootstrap CIs), `summary.md`, `provenance_cs12_vs_gee.csv`, `gee_alignment.csv`,
`run.log`. Downloads are cached in `python/data/cache/` (git-ignored), so a re-run is offline
for the cached patches.

## Modules
| File | Role |
|---|---|
| `src/cloudbench/data.py` | CloudSEN12+ reading (legacy TACO v1, position-indexed), GEE input fetch, cache |
| `src/cloudbench/detectors.py` | Numpy replicas of every rule in `S2_CloudMask_SCIENTIFIC.js` v1.0.2, plus k-of-n |
| `src/cloudbench/metrics.py` | Leak, discard, F1, BOA, per-class recall, site bootstrap |
| `src/cloudbench/auth.py` | Earth Engine service-account sign-in |
| `scripts/run_pilot.py` | Pilot benchmark (validation split only; the test split is locked) |
| `scripts/check_gee_alignment.py` | Alignment and provenance gate |

## Known data facts (see `src/cloudbench/data.py`)
- `TortillaDataFrame.read(i)` takes a row **position**, not an index label.
- 509×509 patches are padded to 512 on the bottom and right; the padding is labelled 0.
- The CloudSEN12+ bundled Cloud Score+ layers are unreliable, so the inputs come from GEE (D-17).
