# Sentinel-2 Hybrid Cloud Masking Framework

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Google Earth Engine](https://img.shields.io/badge/Google%20Earth%20Engine-Ready-green.svg)](https://earthengine.google.com/)
[![Sentinel-2](https://img.shields.io/badge/Sentinel--2-MSI-blue.svg)](https://sentinel.esa.int/web/sentinel/missions/sentinel-2)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20395978.svg)](https://doi.org/10.5281/zenodo.20395978)

> **A multi-method hybrid approach for cloud and shadow detection in Sentinel-2 imagery**  
> Built for water quality monitoring and coastal remote sensing applications.

---

## Table of Contents
- [Overview](#overview)
- [The Science Behind This Project](#the-science-behind-this-project)
- [Methods & Algorithms](#methods--algorithms)
- [Installation & Usage](#installation--usage)
- [Repository Structure](#repository-structure)
- [Parameters & Tuning](#parameters--tuning)
- [Validation Status](#validation-status)
- [Known Limitations](#known-limitations)
- [Project Documentation](#project-documentation)
- [Citation](#citation)
- [Related Publications & Links](#related-publications--links)
- [Authors & Contact](#authors--contact)
- [License](#license)

---

## Overview

### What This Project Does

This repository contains a Google Earth Engine (GEE) implementation for cloud and shadow masking of Sentinel-2 Level-2A imagery. The framework combines five established cloud detection methods using pixel-union logic with an agreement (confidence) layer. A union maximizes cloud removal (recall). The trade-off is that it also masks more valid pixels (false positives); see [Known Limitations](#known-limitations).

The code is designed for **water quality remote sensing** applications, where accurate cloud masking is critical for monitoring optically active water constituents (chlorophyll, suspended sediments, colored dissolved organic matter) in coastal and inland water bodies.

### Key Features

- **Multi-Method Fusion**: Combines SCL, s2cloudless, Cloud Score+ cs, Cloud Score+ cs_cdf, and shadow projection
- **Pixel-Union Logic**: Cloud detected if ANY method flags it (maximizes recall)
- **Agreement Layer**: Counts how many of the four cloud detectors flag each pixel (0-4). Note that cs and cs_cdf come from the same model.
- **Morphological Operations**: 20 m erosion followed by a 50 m buffer around detected clouds and shadows
- **Interactive UI Panel**: Built-in GEE interface for method comparison
- **Per-Image Masking**: Applied before median composite for cleaner results
- **Remaining-Pixel Counts**: Per method, a measure of how many pixels survive masking (yield, not accuracy)

### Study Area & Application

- **Primary Region**: Indian River Lagoon, Florida, USA
- **Satellite/Sensor**: Sentinel-2 MSI (10-60m resolution)
- **Inputs Used**: B2, B3, B4 (display), B8 (shadow test), SCL, s2cloudless `probability`, Cloud Score+ `cs` and `cs_cdf`
- **Target Use Case**: Water quality monitoring, harmful algal bloom detection
- **Date Range**: Three dates, September-November 2022 (configurable)

---

## The Science Behind This Project

### Background

Coastal and inland water bodies face increasing pressure from eutrophication, harmful algal blooms, and climate change. Sentinel-2 satellite imagery provides high-resolution (10-60m), frequent revisit (5-day repeat) coverage ideal for monitoring water quality parameters. However, accurate atmospheric correction and cloud masking remain major challenges, particularly in subtropical regions like Florida where cloud cover is persistent.

Clouds and their shadows contaminate spectral measurements, leading to erroneous water quality retrievals. The five detectors work differently (sources in [docs/LITERATURE_REVIEW.md](docs/LITERATURE_REVIEW.md)):
- **SCL** (ESA Sen2Cor Scene Classification Layer): rule-based, shipped with every L2A product; built for Sen2Cor's own processing, and less accurate than Fmask/MAJA in published benchmarks (Baetens et al., 2019)
- **s2cloudless**: single-scene machine-learning cloud probability (Sentinel Hub); detects clouds only, not shadows
- **Cloud Score+ cs**: per-pixel "clear" score from Google's Cloud Score+ model (Pasquarella et al., 2023); more sensitive to haze and cloud edges
- **Cloud Score+ cs_cdf**: the same model's score normalized against the pixel's own score distribution over time; keeps more pixels and is less sensitive to haze and terrain shadow
- **Shadow projection**: geometric, projects detected clouds along the sun azimuth and keeps dark-NIR pixels (method from the GEE s2cloudless community tutorial); skipped over water

### The Hybrid Approach

The script implements a **pixel-union framework** that:
1. Runs all five methods on each image
2. Flags a pixel as "cloud" if ANY method detects it (maximizes recall)
3. Records how many of the four cloud detectors agree (0-4)
4. Applies 20 m erosion and a 50 m buffer
5. Performs per-image masking BEFORE creating median composites

The design assumes that in water quality studies false negatives (missed clouds) cost more than false positives (over-masking). That assumption has limits: a union also removes more valid water pixels, and bright turbid or bloom water can be flagged as cloud (see [docs/LITERATURE_REVIEW.md](docs/LITERATURE_REVIEW.md) §3).

### What This Repository Provides

- **Side-by-side comparison**: one GEE script that runs five detectors on the same images, with an interactive UI and a per-pixel agreement map
- **Per-image masking** before compositing
- **Suggested starting points (not yet tested)**:
  - Water bodies → compare `HYBRID FINAL` with `cs_cdf only`, and check that bloom or turbid areas are not being masked
  - Land mapping → `HYBRID FINAL`
  - Quick view → `SCL only`
- **Remaining-pixel counts** per method (how much each mask removes; not a measure of accuracy)

---

## Methods & Algorithms

### Detection Methods

| Method | Source | Type | Notes | Cloud if |
|--------|--------|------|-------|----------|
| **SCL** | ESA Sen2Cor | Rule-based classifier | Fast, included in L2A | Class 3, 8, 9 or 10 |
| **s2cloudless** | Sentinel Hub | ML probability (single scene) | Clouds only | probability > 50 |
| **Cloud Score+ cs** | Google (Pasquarella et al., 2023) | Deep-learning clear score | More sensitive to haze and edges | cs < 0.60 |
| **Cloud Score+ cs_cdf** | Google (Pasquarella et al., 2023) | Same score, temporally normalized | Keeps more pixels | cs_cdf < 0.60 |
| **Shadow Projection** | GEE s2cloudless tutorial | Sun azimuth + dark NIR | Land only (water is skipped) | projected cloud AND NIR < 0.15 |

### Processing Pipeline

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Sentinel-2 L2A │───▶│  Apply 4 Cloud  │───▶│  Pixel-Union:   │
│  Imagery Input  │    │  Detectors      │    │  cloud = ANY    │
└─────────────────┘    └─────────────────┘    └────────┬────────┘
                                                         │
┌─────────────────┐    ┌─────────────────┐    ┌────────┴────────┐
│  Per-Image      │◀───│  20 m erosion + │◀───│  Shadow         │
│  Mask Applied   │    │  50 m buffer    │    │  Projection     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐
│  Median         │───▶│  Clean Composite│
│  Composite      │    │  Output         │
└─────────────────┘    └─────────────────┘
```

### Parameters (Defaults)

Most defaults come from the GEE community tutorial *Sentinel-2 Cloud Masking with s2cloudless*. The Cloud Score+ threshold follows the GEE catalog guidance (0.50-0.65). None has been tuned for water yet.

```javascript
var PARAMS = {
  CS_CDF_THRESH: 0.60,      // Cloud Score+ cs_cdf (GEE guidance: 0.50-0.65)
  CS_THRESH: 0.60,          // Cloud Score+ cs
  CLOUD_PROB_THRESH: 50,    // s2cloudless probability
  NIR_DARK_THRESH: 0.15,    // Dark NIR for shadow detection
  CLOUD_PROJ_DIST: 1,       // Shadow projection distance (km)
  BUFFER: 50,               // Cloud edge buffer (meters)
  MIN_AGREEMENT: 1          // NOT IMPLEMENTED YET: the script always uses union (see docs/ROADMAP.md B1)
};
```

---

## Installation & Usage

### Prerequisites

- Google Earth Engine account (free for research: https://signup.earthengine.google.com/)
- Access to GEE Code Editor (https://code.earthengine.google.com/)

### Quick Start

1. **Open GEE Code Editor**: https://code.earthengine.google.com/

2. **Create new script**: File → New → Repository Script (or new blank script)

3. **Copy code**: Paste the contents of `S2_CloudMask_SCIENTIFIC.js`

4. **Configure your area of interest**:
   ```javascript
   // Replace with your study area
   var center = ee.Geometry.Rectangle([-80.763739, 27.605387, -80.503601, 28.621909]);
   ```

5. **Set your dates**:
   ```javascript
   var DATES = [
     ee.Date('2022-09-15'),
     ee.Date('2022-11-04'),
     ee.Date('2022-11-19')
   ];
   ```

6. **Run**: Click "Run" button or press Ctrl+Enter

7. **Use the UI panel**: Click buttons to compare different masking methods

### Method-Specific Usage

| Use Case | Suggested Method | Why |
|----------|-------------------|-----|
| Water quality studies | `HYBRID FINAL`, compared with `cs_cdf only` | Untested on water: check that bloom or turbid areas are not masked |
| Land cover mapping | `HYBRID FINAL` | Catches the most cloud types |
| Quick visualization | `SCL only` | Fastest processing |
| Method comparison | Compare all methods | See the agreement map |

---

## Repository Structure

```
S2-CloudMask-Hybrid/
├── S2_CloudMask_SCIENTIFIC.js    # Main GEE script
├── README.md                      # This file
├── AGENTS.md                      # Hand-off guide for contributors and AI tools (start here)
├── CLAUDE.md                      # Imports AGENTS.md for Claude Code
├── CHANGELOG.md                   # Version history
├── CITATION.cff                   # Machine-readable citation
├── LICENSE                        # MIT License
├── docs/
│   ├── USAGE.md                   # Detailed usage guide
│   ├── STATE.md                   # Current status and next actions
│   ├── LOG.md                     # Dated project history
│   ├── DECISIONS.md               # Design decisions and their reasons
│   ├── AUDIT_2026-11-07.md        # Known issues and checked claims
│   ├── LITERATURE_REVIEW.md       # Literature with DOIs
│   └── ROADMAP.md                 # Planned work with acceptance criteria
├── examples/
│   └── custom_area_template.js    # Template for your area
└── .gitignore                     # Git ignore rules
```

---

## Parameters & Tuning

### Adjusting Cloud Sensitivity

Each detector flags cloud on one side of its threshold, so the direction matters:

| Parameter | Test in the code | Raise it to... | Lower it to... |
|-----------|------------------|----------------|----------------|
| `CS_CDF_THRESH` / `CS_THRESH` | cloud if score **<** threshold | mask **more** (also thin cloud and haze) | mask **less** (keep more pixels) |
| `CLOUD_PROB_THRESH` | cloud if probability **>** threshold | mask **less** | mask **more** |
| `NIR_DARK_THRESH` | shadow candidate if NIR **<** threshold | flag **more** shadow (land only) | flag **less** shadow |
| `BUFFER` | dilation radius (m) | exclude a wider cloud edge | exclude a narrower edge |

### Pixel Count Interpretation

The script prints the number of remaining (unmasked) pixels in each composite at 100 m:
- **Lower count = more aggressive masking**, not better masking
- `HYBRID FINAL` will always have the lowest count, because a union of masks removes at least as much as any single mask
- These counts measure **yield**. They do not tell you whether a removed pixel was really cloud (see [Validation Status](#validation-status))

---

## Validation Status

**This method has not yet been quantitatively validated.** No accuracy, recall or timing figures are claimed. The planned validation (reference labels over water and land, omission/commission and F1 per detector and per fusion rule, threshold sweeps) is described in [docs/ROADMAP.md](docs/ROADMAP.md), Phase C.

### Current Checks (qualitative)

1. **Visual inspection** of masked composites vs. original imagery
2. **Remaining-pixel counts** per method (yield)
3. **Agreement map** showing where detectors agree
4. **Cross-method comparison** to find edge cases

### Console Output Format

```
REMAINING PIXELS (lower = more clouds removed):
  Original: <count>
  SCL only: <count>
  s2cloudless: <count>
  cs: <count>
  cs_cdf: <count>
  HYBRID std: <count>
  HYBRID + shadows: <count>
  HYBRID FINAL: <count>
```

---

## Known Limitations

Full list with code references: [docs/AUDIT_2026-11-07.md](docs/AUDIT_2026-11-07.md).

- **Shadows over water**: the shadow projection excludes water pixels (SCL class 6), so cloud shadows on water are caught only by SCL class 3 and Cloud Score+.
- **`MIN_AGREEMENT` is not implemented**: the script always uses the union.
- **Agreement layer**: cs and cs_cdf are two outputs of the same model, so "4 methods agree" overstates independence. The map layer shows the maximum over all dates.
- **Morphology** runs without a fixed scale, so results may vary with map zoom or export scale (to be verified), and the erosion step can remove very small clouds before buffering.
- **Dates can drop silently**: the 60% scene-cloudiness filter can exclude a requested date; check the image count printed in the console.

---

## Project Documentation

New contributors and AI assistants should start with [AGENTS.md](AGENTS.md), then [docs/STATE.md](docs/STATE.md).

| File | Purpose |
|------|---------|
| [docs/STATE.md](docs/STATE.md) | Current status, known issues, next actions |
| [docs/LOG.md](docs/LOG.md) | Dated project history |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Why the method is designed the way it is |
| [docs/AUDIT_2026-11-07.md](docs/AUDIT_2026-11-07.md) | Code findings and checked claims |
| [docs/LITERATURE_REVIEW.md](docs/LITERATURE_REVIEW.md) | Literature for every method and planned improvement |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Planned work with acceptance criteria |
| [CHANGELOG.md](CHANGELOG.md) | Version history |

---

## Citation

If you use this code in your research, please cite:

### Software Citation

```bibtex
@software{hussein_2026_s2cloudmask,
  author       = {Hussein, Abdulrahman},
  title        = {Sentinel-2 Hybrid Cloud Masking Framework},
  year         = {2026},
  publisher    = {Zenodo},
  version      = {1.0.2},
  doi          = {10.5281/zenodo.20395978},
  url          = {https://doi.org/10.5281/zenodo.20395978}
}
```

### APA Format

> Hussein, A. (2026). *Sentinel-2 Hybrid Cloud Masking Framework* (Version 1.0.2) [Software]. Zenodo. https://doi.org/10.5281/zenodo.20395978

### Zenodo DOI

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20395978.svg)](https://doi.org/10.5281/zenodo.20395978)

All versions (concept DOI): https://doi.org/10.5281/zenodo.20395977

---

## Related Publications & Links

- **Cloud Score+**: Pasquarella, V.J., Brown, C.F., Czerwinski, W., Rucklidge, W.J. (2023). Comprehensive Quality Assessment of Optical Satellite Imagery Using Weakly Supervised Video Learning. *CVPR Workshops (EarthVision)*, 2125-2135. https://doi.org/10.1109/CVPRW59228.2023.00206
- **Cloud Score+ dataset in GEE**: https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_CLOUD_SCORE_PLUS_V1_S2_HARMONIZED
- **s2cloudless**: https://github.com/sentinel-hub/sentinel2-cloud-detector
- **GEE tutorial, Sentinel-2 Cloud Masking with s2cloudless** (source of the shadow projection and default parameters): https://developers.google.com/earth-engine/tutorials/community/sentinel-2-s2cloudless
- **Full literature review**: [docs/LITERATURE_REVIEW.md](docs/LITERATURE_REVIEW.md)
- **Google Earth Engine**: https://earthengine.google.com/
- **Sentinel-2 Mission**: https://sentinel.esa.int/web/sentinel/missions/sentinel-2
- **Google Scholar**: https://scholar.google.com/citations?user=TQEmmAoAAAAJ&hl=en
- **ORCID**: https://orcid.org/0009-0003-0401-9219

---

## Authors & Contact

- **Abdulrahman Hussein** — PhD Candidate, Department of Earth Sciences, Kent State University  
  Email: ahusse12@kent.edu | ORCID: https://orcid.org/0009-0003-0401-9219

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- Google Earth Engine team for the cloud computing platform
- ESA for Sentinel-2 data and SCL algorithm
- Sentinel Hub for s2cloudless
- Google for Cloud Score+ development
- The authors of the GEE community tutorial *Sentinel-2 Cloud Masking with s2cloudless*, whose shadow-projection method and default parameters this script uses

---

**Last Updated**: November 2026
