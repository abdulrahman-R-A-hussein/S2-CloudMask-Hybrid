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
- Committed locally on `main` at the author's request; **not pushed**.

**Next:** see [`STATE.md`](STATE.md) → "Next actions".
