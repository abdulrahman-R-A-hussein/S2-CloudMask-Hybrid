# Sentinel-2 cloud and shadow masking for water-quality work: literature review

**Compiled 2026-11-07** from one web literature pass (about 35 searches and fetches).
Every claim carries a DOI or URL. Two flags are used:
- **"not verified"**: the full text was not opened (paywall, or the fetch was blocked) and the
  claim rests on the abstract, a catalogue record or a secondary source. Re-check before citing
  in a paper.
- **"gap"**: no source was found. Treat it as an open question, not a fact.

**DOI check (2026-11-07).** These DOIs were confirmed to resolve through doi.org or Crossref:
- Pasquarella 2023, Tarrio 2020, Wen et al.
- CloudSEN12, CloudSEN12+, OmniCloudMask, CloudS2Mask, KappaMask, SEnSeIv2
- IdePix ATBD, S2 Cloud Mask Catalogue
- WiPE, CMIX, López-Puigdollers
- Frantz 2018, Hollstein 2016

The remaining DOIs come from publisher or catalogue records found in search.
The DOI the old README gave for Cloud Score+ (10.1038/s41597-023-02543-0) returns **404**.

Last section (§7) maps every finding to an item in [`ROADMAP.md`](ROADMAP.md).

---

## 1. The five detectors this repo combines

| # | Detector (band in our script) | What it is | Primary source | Notes relevant to us |
|---|---|---|---|---|
| 1 | **SCL** classes 3, 8, 9, 10 | Sen2Cor scene classification shipped with L2A. 12 classes, 0–11: 0 no data, 1 saturated/defective, 2 dark area (renamed *topographic cast shadows* in newer baselines), **3 cloud shadow**, 4 vegetation, 5 not-vegetated, **6 water**, 7 unclassified / cloud low probability, **8 cloud medium prob.**, **9 cloud high prob.**, **10 thin cirrus**, 11 snow/ice | ESA Sen2Cor IODD v2.12.04, https://step.esa.int/thirdparties/sen2cor/2.12.0/docs/ (*not verified*, table not opened); class list confirmed on https://custom-scripts.sentinel-hub.com/sentinel-2/scene-classification | It is meant for Sen2Cor's own atmospheric correction, **not as a land-cover map**. Resample it with nearest neighbour. We exclude class 7 (low-probability cloud) and class 2; see [`DECISIONS.md`](DECISIONS.md) D-06 |
| 2 | **s2cloudless** `probability` > 50 | Single-scene, pixel-based gradient-boosting (LightGBM) classifier from Sentinel Hub. It uses 10 L1C bands (B01, B02, B04, B05, B08, B8A, B09, B10, B11, B12). GEE serves it pre-computed as `COPERNICUS/S2_CLOUD_PROBABILITY` | Zupanc 2017, https://medium.com/sentinel-hub/improving-cloud-detection-with-machine-learning-c09dc5d7cf13; code https://github.com/sentinel-hub/sentinel2-cloud-detector | Sentinel Hub states it took part in CMIX and sat on the Pareto front on all 4 test sets (repo README). It **detects clouds only**: shadows need a separate step |
| 3 | **Cloud Score+ `cs`** < 0.60 | Per-pixel "usability" score in [0, 1], 0 = not clear, 1 = clear. Comes from a space-time video model trained with weak supervision (an atmospheric-similarity target). `cs` is the instantaneous score | Pasquarella, Brown, Czerwinski & Rucklidge 2023, *CVPR Workshops (EarthVision)*, pp. 2125–2135, doi:10.1109/CVPRW59228.2023.00206, https://openaccess.thecvf.com/content/CVPR2023W/EarthVision/html/Pasquarella_Comprehensive_Quality_Assessment_of_Optical_Satellite_Imagery_Using_Weakly_Supervised_CVPRW_2023_paper.html (abstract verified, full text *not verified*) | The abstract reports state-of-the-art Sentinel-2 results on two out-of-distribution reference sets for **clouds and cloud shadows**. Cloud Score+ therefore already covers shadows |
| 4 | **Cloud Score+ `cs_cdf`** < 0.60 | The CDF value of the estimated `cs` within the pixel's own distribution of possible scores, i.e. a *temporally normalised* version of the same score | GEE catalog `GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED`, https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_CLOUD_SCORE_PLUS_V1_S2_HARMONIZED (seen via search excerpts; direct fetch blocked); Pasquarella 2023 blog "All Clear with Cloud Score+", https://medium.com/google-earth/all-clear-with-cloud-score-bd6ee2e2235e | Catalog guidance: **thresholds 0.50–0.65 generally work**; higher values also remove thin cloud, haze and cirrus shadows. Blog: `cs` is more sensitive to haze and cloud edges; `cs_cdf` is less sensitive to low-magnitude changes and to terrain shadows, so it keeps more pixels. **`cs` and `cs_cdf` come from the same model, so they are not independent votes** (see §4) |
| 5 | **Shadow projection** (NIR < 0.15, 1 km) | Project the cloud mask along the solar azimuth with `directionalDistanceTransform`, then intersect with dark-NIR, non-water pixels | GEE community tutorial "Sentinel-2 Cloud Masking with s2cloudless" (author jdbcode / J. Braaten), https://developers.google.com/earth-engine/tutorials/community/sentinel-2-s2cloudless; announcement https://medium.com/google-earth/more-accurate-and-flexible-cloud-masking-for-sentinel-2-images-766897a9ba5f | **Our `PARAMS` and `getShadowMask()` follow this tutorial almost line for line**: `CLD_PRB_THRESH` 50, `NIR_DRK_THRESH` 0.15, `CLD_PRJ_DIST` 1 km, `BUFFER` 50 m, the scene filter of 60 %, projection distance ×10 at 100 m. The tutorial **excludes SCL water from the dark-pixel test**, and so does our script. The README did not credit the tutorial before 2026-11-07 |

**Other Sentinel-2 cloud information in GEE, and why it is not used:**
- **QA60** (L1C/L2A bitmask) is **empty from 2022-01-25 to 2024-02-28**. After that GEE rebuilds
  it from the `MSK_CLASSI_*` bands (opaque, cirrus, snow) (GEE catalog `COPERNICUS/S2_SR`, via
  search excerpts). All three of our 2022 dates fall inside the empty window. Your AMD tool
  (`D:\dev\Sulfate-Methos`) dropped QA60 for the same reason ("they detect nothing").
- The **L1C mask behind QA60** under-detected clouds: about 37 % mean omission, with cirrus the
  hardest (Coluzzi et al. 2018, *RSE* 217:426–443, doi:10.1016/j.rse.2018.08.009).
- **CDI** (Cloud Displacement Index, parallax between MSI bands) separates clouds from bright
  surfaces. It is available as `ee.Algorithms.Sentinel2.CDI` and needs L1C (Frantz et al.
  2018, *RSE* 215:471–481, doi:10.1016/j.rse.2018.04.046).
- `MSK_CLDPRB` (Sen2Cor's own cloud probability, in L2A) is used by the AMD tool instead of
  s2cloudless.

---

## 2. How the detectors compare (benchmarks)

| Study | Data | Main result | Caveat |
|---|---|---|---|
| **Baetens, Desjardins & Hagolle 2019**, *Remote Sens.* 11(4):433, doi:10.3390/rs11040433 | 32 S2 scenes, reference masks made with an active-learning tool (ALCD) | Overall accuracy: MAJA ≈ 91 %, Fmask 4.0 ≈ 90 %, Sen2Cor ≈ 84 %. Sen2Cor varied the most from scene to scene. Reference masks and ALCD were released | Land-dominated scenes |
| **Sanchez et al. 2020**, *Remote Sens.* 12(8):1284, doi:10.3390/rs12081284 | Amazon, > 8,000 points | Fmask 4 90 %, Sen2Cor 79 %, MAJA 69 %, s2cloudless 52 % | Tropical forest; the ranking flips between studies |
| **Tarrio et al. 2020**, *Science of Remote Sensing* 2:100010, doi:10.1016/j.srs.2020.100010 (DOI resolves; details from the abstract, *full text not verified*; NASA record https://ntrs.nasa.gov/citations/20210014061) | 5 algorithms (Sen2Cor, MAJA, LaSRC, Fmask, Tmask), 28 images | **No single algorithm was best for both clouds and shadows. Ensembles (majority vote, random forest, conditional logic) left fewer clouds undetected and raised overall accuracy by up to 2.7 % over the best single algorithm** | Closest published support for our multi-method idea. It tested *voting / learned* fusion, not a plain union |
| **Skakun et al. 2022 (CMIX)**, *RSE* 274:112990, doi:10.1016/j.rse.2022.112990 | 10 algorithms, 5 reference datasets, Landsat 8 + Sentinel-2 | Average Sentinel-2 overall accuracy ≈ 80–89 % (from conference slides, *not verified* in the paper). Scores depend strongly on the reference dataset, and rise when thin/semi-transparent cloud is ignored | s2cloudless was one of the 10 |
| **Qiu, Zhu & He 2019 (Fmask 4.0)**, *RSE* 231:111205, doi:10.1016/j.rse.2019.05.024 | Landsat 4–8 + S2 | Adds global surface-water occurrence and a DEM. On S2: 94.30 % vs Sen2Cor 87.10 % | Not available as a ready band in GEE |
| **Pasquarella et al. 2023 (Cloud Score+)**, see §1 | Two out-of-distribution S2 reference sets | Better than the ML and physical cloud/shadow detectors they compared | Authors are the product's developers; the full text was not opened |
| **Rodríguez-Puerta et al. 2024**, *Remote Sens.* 16(24):4791, doi:10.3390/rs16244791 | Hawai'i, monthly mosaics 2019–2023 | Cloud-free pixel success: Cloud Score+ ≈ 89.4 %, s2cloudless ≈ 80.8 % | A **yield** metric (usable pixels), **not accuracy against labels**. One abstract gives the 79.3 % figure differently; *not verified* |
| **López-Puigdollers et al. 2021**, *Remote Sens.* 13(5):992, doi:10.3390/rs13050992 | Deep-learning models, Landsat 8 → S2 | Within one dataset DL beats operational masks. Across datasets or sensors it is only on par with threshold methods | Results depend on the training data |

**Takeaway.** No published benchmark ranks all five of our detectors together. None evaluates
them **over water** specifically: **gap**.

---

## 3. Problems specific to water (our use case)

1. **Bright water flagged as cloud (commission).** Over turbid water, cloud-free pixels are
   sometimes classified as cloud or land, and Fmask performs worse there than a water-specific
   method (Ngoc et al. 2019, WiPE, *RSE* 223:208–228, doi:10.1016/j.rse.2019.01.024). Ocean-colour
   cloud masks can remove **intense cyanobacteria blooms** and river sediment plumes (JRC
   Baltic Sea study, https://publications.jrc.ec.europa.eu/repository/handle/JRC90628, *authors
   and details not verified*). Floating-algae blooms are often flagged as cloud. An AFAI-based
   recovery step cut masked pixels by about 30–50 % in turbid Chinese waters (Wang & Jiang 2025,
   *Int. J. Appl. Earth Obs. Geoinf.*, https://doaj.org/article/cf2a2e6be6c843f7841b8a8c2daeec16,
   *not verified*). **For harmful-algal-bloom work, a union of masks can delete the very signal
   being studied.** **Gap:** no study measures this for Sentinel-2 SCL, s2cloudless or
   Cloud Score+ over blooms.
2. **Cloud shadows over water.** Shadows are spectrally close to dark water, and few methods
   handle cloud shadows over water (WiPE paper; DINEOF shadow study,
   https://www.bohrium.com/paper-details/detection-of-shadows-in-high-spatial-resolution-ocean-satellite-data-using-dineof/812528625294245889-3747,
   *not verified*). Sentinel-2 has no thermal band, so cloud-height-based shadow projection
   is harder than for Landsat. **Our shadow step (tutorial design) skips SCL water entirely**,
   so only SCL class 3 and Cloud Score+ can catch shadows on the lagoon.
3. **Cloud-edge contamination and buffers.** Clear pixels near clouds are brighter than they
   should be because of 3-D radiative effects. In a MODIS case study the enhancement was still
   present about 2–3 km from clouds and biased aerosol retrievals high (Wen et al. 2007, "3-D
   aerosol-cloud radiative interaction observed in collocated MODIS and ASTER images of cumulus
   cloud fields", *JGR Atmospheres*, doi:10.1029/2006JD008267, Crossref-verified; NASA summary
   https://espo.nasa.gov/ave-costarica2/node/15825). Water Rrs is a small signal, so the same
   bias matters more for water than for land. Water processors flag a cloud buffer:
   IdePix-S2 has *cloud sure / ambiguous / buffer / cirrus / shadow* flags with the buffer set
   in pixels (Wevers et al., IdePix S2 ATBD v1.0, doi:10.5281/zenodo.5788067). Sen2Water
   buffers cloud-ambiguous pixels too
   (https://step.esa.int/main/wp-content/help/versions/13.0.0/snap-supported-plugins/eu.esa.opt.sen2water.adapter/s2w/AlgorithmDescription.html).
   Fmask and MAJA dilate their masks by default and Sen2Cor's SCL does not (Baetens 2019;
   *exact Fmask dilation distances not verified*). **Gap:** no published Sentinel-2 study gives
   a recommended cloud-buffer distance for water Rrs. Our 50 m buffer is a land-tutorial default.
4. **Land adjacency (not cloud, but related).** Retrieval errors grow within about 200 m of
   shorelines, and corrections exist (2024 *RSE* study, seen via search, *not verified*). The
   Indian River Lagoon is long and narrow, so shoreline adjacency and cloud adjacency overlap.
5. **Thin cirrus and haze.** SCL class 10 and Cloud Score+ `cs` (more haze-sensitive than
   `cs_cdf`) are our only cirrus tests. `S2_SR_HARMONIZED` has no B10 (1375 nm). ACOLITE screens
   cirrus with the 1375 nm band from L1C, and masks non-water pixels with TOA reflectance at
   1.6 µm > 0.0215 by default (ACOLITE forum, maintainer replies,
   https://odnature.naturalsciences.be/remsem/acolite-forum/viewtopic.php?p=2302).
6. **Sen2Cor was built for land.** A 2025 coastal Sentinel-2 chlorophyll paper notes that
   Sen2Cor cloud detection was designed for land and can struggle over water (*Remote Sens.*
   17(20):3503, https://www.mdpi.com/2072-4292/17/20/3503, *not verified*).

**Regional comparison data for the Indian River Lagoon.** A USF dataset gives Sentinel-2
chlorophyll-a and turbidity for the IRL, 2016–2023 at 20 m, with a dynamic shallow-water mask
(https://digitalcommonsdata.usf.edu/datasets/wp7p6srdvy/1). Its methods paper was under review when
the dataset was posted. Its cloud handling is not documented on the page (*not verified*).
It is a possible cross-check for Phase C.

---

## 4. Combining masks: union, k-of-n voting, weighting

- **Union (OR)**, our current rule, gives the highest recall a set of detectors can reach. It
  also has the highest commission: every detector's false positives add up. CMIX and Tarrio
  both frame cloud masking as an omission/commission trade-off.
- **k-of-n voting** (cloud if at least *k* of *n* fire) and **learned fusion** (random forest)
  beat the best single algorithm in Tarrio et al. 2020. Our `MIN_AGREEMENT` parameter was meant
  for k-of-n but **is not implemented** (AUDIT F-01).
- **Correlated voters.** `cs` and `cs_cdf` are two outputs of one model. s2cloudless and SCL
  both read the same scene's spectra. Counting them as four equal votes overstates agreement.
  A defensible scheme votes by **family**: {SCL}, {s2cloudless}, {Cloud Score+ (cs or cs_cdf)},
  with the shadow test handled separately. This is our own reasoning; **gap**: no source tests it.
- **Weighting.** Cloud Score+ is designed to be used either as a threshold or as a weight in
  compositing ("mask or weight", Pasquarella 2023 blog). A `qualityMosaic` on `cs`/`cs_cdf` is
  an alternative to the median of masked images.

---

## 5. Newer deep-learning masks (outside GEE, for comparison)

| Model | Source | Reported performance | Use for us |
|---|---|---|---|
| **CloudS2Mask** | Wright et al. 2024, *RSE* 306:114122, doi:10.1016/j.rse.2024.114122; `pip install clouds2mask` | On CloudSEN12, balanced overall accuracy improved over the next best published model by 1.2 % (cloud), 2.8 % (shadow), 1.1 % (clear). Trained on CloudSEN12, KappaSet, the S2 Cloud Mask Catalogue, ALCD masks and its own data | Offline benchmark |
| **OmniCloudMask** | Wright et al. 2025, *RSE*, doi:10.1016/j.rse.2025.114694; `pip install omnicloudmask` | Sentinel-2: 92.2 % clear, 91.2 % cloud, 80.5 % shadow. Needs only Red, Green and NIR; classes clear / thick / thin / shadow. Successor to CloudS2Mask | Offline benchmark; it could also run on our drone data (R, G, NIR) |
| **KappaMask** | Domnich et al. 2021, *Remote Sens.* 13(20):4100, doi:10.3390/rs13204100 | Dice 80 % (L2A), 76 % (L1C) on its held-out test set | Lower priority |
| **SEnSeIv2** | Francis 2024, *IEEE TGRS*, doi:10.1109/TGRS.2024.3391625 | Sensor-independent; can add S1 SAR and a DEM. *Benchmark numbers not verified* | Lower priority |

None of these models was evaluated over water specifically (**gap**).

---

## 6. Validation datasets and metrics (for Phase C)

**Reference datasets (Sentinel-2):**
- **CloudSEN12**: Aybar et al. 2022, *Sci. Data* 9, doi:10.1038/s41597-022-01878-2. 49,400
  patches; classes clear / thick cloud / thin cloud / shadow. It already includes outputs of
  8 algorithms (among them s2cloudless, Sen2Cor SCL, Fmask, QA60). CC BY-NC 4.0. Mirror:
  https://huggingface.co/datasets/tacofoundation/cloudsen12
- **CloudSEN12+**: Aybar et al. 2024, *Data in Brief* 56:110852, doi:10.1016/j.dib.2024.110852.
  50,249 patches; doubles the expert labels.
- **Sentinel-2 Cloud Mask Catalogue**: Francis & Mrziglod 2020, doi:10.5281/zenodo.4172871. 513
  subscenes of 1022×1022 px at 20 m from the 2018 L1C archive; clear / cloud / shadow.
- **ALCD reference masks**: Baetens et al. 2019 (32 scenes).
- **Hollstein et al. 2016**, *Remote Sens.* 8:666, doi:10.3390/rs8080666: a manually labelled
  spectral database with ready-to-use classifiers.
- **Gap:** none of these is designed around water. Phase C needs water patches pulled from
  them, plus our own labels over the IRL.

**Metrics.** Report per class (cloud, shadow, clear):
- omission (1 − recall), commission (1 − precision), F1;
- **balanced overall accuracy** (used by CloudS2Mask/OmniCloudMask);
- IoU.

Report them **separately for water and land pixels**. Remaining-pixel counts, the metric our
script prints, measure **yield**, not accuracy: the union always "wins" by construction
(AUDIT F-06).

---

## 7. Implications for this project

| # | Finding | Action | Roadmap item |
|---|---|---|---|
| L1 | Ensembles help, but via voting or learned fusion; union maximises commission | Implement `MIN_AGREEMENT` as family-level k-of-n and compare it with the union | B1, C3 |
| L2 | `cs` and `cs_cdf` are not independent | Vote by family; use one Cloud Score+ band per run, or count the pair as one vote | B1 |
| L3 | Cloud Score+ already flags shadows; our projection skips water | Add a geometric shadow candidate over water. At minimum, document that lagoon shadows rely on Cloud Score+ and SCL 3 | D1 |
| L4 | Near-cloud brightening reaches km scales; 50 m is a land default | Measure Rrs bias against distance to the nearest cloud on IRL scenes, then pick a water buffer | D2 |
| L5 | Bright blooms and turbid water can be masked as cloud | Bloom guard: flag pixels that only SCL or s2cloudless call cloud while Cloud Score+ says clear over water. Test against known bloom dates | D3 |
| L6 | No over-water benchmark exists | Build a water-focused reference set (CloudSEN12 water patches plus hand-labelled IRL scenes); report water and land separately | C1, C2 |
| L7 | Threshold guidance for `cs_cdf` is 0.50–0.65; the default 0.60 has never been tested here | Sweep `cs_cdf` 0.40–0.80 and s2cloudless 20–60 against the labels | C3 |
| L8 | QA60 is empty for our 2022 dates | Keep QA60 out; document why | done (D-07) |
| L9 | Deep-learning masks lead current benchmarks | Run OmniCloudMask offline on the same reference set as a ceiling | D5 |
| L10 | Thin cirrus is poorly caught without B10 | Optional L1C B10 test, or the CDI | D4 |

---

## 8. Chronological map, oldest to newest, and the gap matrix (added 2026-11-07)

Every DOI in this section was checked against Crossref on 2026-11-07, unless it is marked.

### 8.1 Eras
| Era | Year | Work | What it introduced | Source |
|---|---|---|---|---|
| **1. Thresholds** | 1988 | Saunders & Kriebel (APOLLO, AVHRR) | Multi-test spectral/spatial thresholds for clear vs cloudy | doi:10.1080/01431168808954841 |
| | 1991 | Rossow & Schiffer (ISCCP) | Global operational cloud climatology from thresholds against clear-sky composites | doi:10.1175/1520-0477(1991)072<0002:ICDP>2.0.CO;2 |
| | 1998 | Ackerman et al. (MODIS MOD35) | Confidence-graded multi-test cloud mask, a precursor of "probability" masks | doi:10.1029/1998JD200032 |
| | 2000/2006 | Irish; Irish et al. (Landsat 7 ACCA) | Scene-level automatic cloud cover assessment for Landsat | doi:10.1117/12.410358; doi:10.14358/PERS.72.10.1179 |
| **2. Physics + objects** | 2010 | Hagolle et al. (MAJA multitemporal) | Uses the previous clear date: time series against single date | doi:10.1016/j.rse.2010.03.002 |
| | 2012 | Zhu & Woodcock (Fmask) | Object-based cloud, plus shadow by geometric projection over a cloud-height search | doi:10.1016/j.rse.2011.10.028 |
| | 2014 | Zhu & Woodcock (Tmask) | Multitemporal model of expected reflectance | doi:10.1016/j.rse.2014.06.012 |
| | 2015 | Zhu, Wang & Woodcock (Fmask 3.x) | Extended to Landsat 4–8 and Sentinel-2 | doi:10.1016/j.rse.2014.12.014 |
| | 2016 | Hollstein et al. | Labelled spectral database; ready-to-use S2 classifiers | doi:10.3390/rs8080666 |
| | 2017 | Main-Knorn et al. (Sen2Cor) | Scene classification (SCL) shipped with every L2A product | doi:10.1117/12.2278218 |
| | 2017 | Foga et al. (CFMask, L8 Biome) | Operational Landsat comparison and validation set | doi:10.1016/j.rse.2017.03.026 |
| | 2018 | Frantz et al. (CDI) | S2 band parallax separates clouds from bright surfaces | doi:10.1016/j.rse.2018.04.046 |
| | 2019 | Qiu, Zhu & He (Fmask 4.0) | Adds water occurrence and DEM | doi:10.1016/j.rse.2019.05.024 |
| **3. Machine learning** | 2014 | Hughes & Hayes (SPARCS) | Neural network plus spatial post-processing for cloud and shadow | doi:10.3390/rs6064907 |
| | 2017 | Zupanc (s2cloudless) | Single-scene gradient boosting; pre-computed in GEE | Medium post, §1 |
| | 2019 | Jeppesen et al. (RS-Net) | U-Net cloud detection | doi:10.1016/j.rse.2019.03.039 |
| | 2019 | Mohajerani & Saeedi (Cloud-Net, 38-Cloud) | End-to-end CNN for Landsat 8 | doi:10.1109/IGARSS.2019.8898776 |
| | 2019 | Wieland et al. | **Multi-sensor** CNN for cloud and shadow (an early cross-sensor attempt) | doi:10.1016/j.rse.2019.05.022 |
| | 2021 | López-Puigdollers et al. | DL beats rules within one dataset but not across datasets | doi:10.3390/rs13050992 |
| | 2021 | Domnich et al. (KappaMask) | Operational S2 DL processor | doi:10.3390/rs13204100 |
| **4. Benchmarks** | 2019 | Baetens et al. (ALCD) | 32-scene S2 reference masks; MAJA ≈ Fmask > Sen2Cor | doi:10.3390/rs11040433 |
| | 2020 | Tarrio et al. | **Ensembles beat single algorithms (up to +2.7 % OA)** | doi:10.1016/j.srs.2020.100010 |
| | 2022 | Skakun et al. (CMIX) | 10 algorithms × 5 datasets; rankings depend on the reference | doi:10.1016/j.rse.2022.112990 |
| | 2022/2024 | Aybar et al. (CloudSEN12, CloudSEN12+) | 50k patches, 4 classes, CC0 | doi:10.1038/s41597-022-01878-2; doi:10.1016/j.dib.2024.110852 |
| | 2023 | Aybar et al. | Documents incorrect labels in CloudSEN12 | doi:10.1109/IGARSS52108.2023.10282381 |
| **5. Large models** | 2023 | Pasquarella et al. (Cloud Score+) | Space-time video model; per-pixel usability score; global in GEE | doi:10.1109/CVPRW59228.2023.00206 |
| | 2024 | Wright et al. (CloudS2Mask) | S2 DL, best published balanced accuracy at the time | doi:10.1016/j.rse.2024.114122 |
| | 2024 | Francis (SEnSeIv2) | Sensor-independent, multimodal | doi:10.1109/TGRS.2024.3391625 |
| | 2024 | Wang et al. (survey) | Open problems: thin cloud, **cross-sensor generality**, labels | doi:10.3390/rs16234583 |
| | 2025 | Wright et al. (OmniCloudMask) | Sensor-agnostic (R, G, NIR), mixed resolution | doi:10.1016/j.rse.2025.114694 |
| | 2026 | Cairns (independent audit, *not peer-reviewed*) | CloudSEN12+ test: DL leads; **water leak 11.0 % vs 6.1 % overall** | github.com/syre-ai/cloudmask-acceptance-audit |
| **Aquatic thread** | 2007 | Wen et al. | Near-cloud 3-D brightening of "clear" pixels | doi:10.1029/2006JD008267 |
| | 2019 | Ngoc et al. (WiPE) | Water-pixel extraction; Fmask fails on turbid water; shadows over water confused | doi:10.1016/j.rse.2019.01.024 |
| | 2021 | IdePix S2 ATBD | Cloud sure / ambiguous / buffer flags for water processors | doi:10.5281/zenodo.5788067 |
| | 2024 | Wieland et al. (S1S2-Water) | Water segmentation set; authors call for more cloud/shadow-over-water samples | doi:10.1109/JSTARS.2023.3333969 |
| | 2025 | Wang & Jiang | Floating algae masked as cloud; AFAI recovery | §3 (*not verified*) |
| | 2026 | Ducar et al. | US inland-water S2 reflectance: ACOLITE has no shadow mask; shadows have NDWI > 0 | doi:10.1002/lol2.70112 |

### 8.2 Gap matrix (what is missing, the evidence, and how this project answers it)
| Gap | What is missing | Evidence | Our answer | Paper |
|---|---|---|---|---|
| G1 | Water-stratified benchmark of S2 masks, including Cloud Score+ and DL | No peer-reviewed study found (§2). Only the 2026 non-peer-reviewed audit gives one water number | Benchmark with water/land/coast/turbid/bloom strata and site-bootstrap CIs | P1 |
| G2 | Water cloud/shadow label set | S1S2-Water authors ask for it; CloudSEN12+ is not water-focused | 150–300 author-labelled water patches with κ | P1 → P2 release |
| G3 | Cloud shadow over water | WiPE; Ducar 2026 (NDWI > 0); our script skips water (F-03) | M4 geometric + relative-darkness module | P1 |
| G4 | Bloom/turbid water flagged as cloud, unquantified for S2 | Ocean-colour and Sargassum literature only (§3) | Bloom stratum + M5 guard | P1 |
| G5 | Fusion of *modern* masks | Tarrio 2020 fused older algorithms on land; no Cloud Score+ fusion study found | Learned, surface-conditional fusion exported to GEE | P1 |
| G6 | Calibrated probabilities from masks | Rarely evaluated; uncertainty heuristics in DL papers | Isotonic calibration, ECE, reliability diagrams | P1 |
| G7 | Near-cloud buffer distance for water Rrs | Wen 2007 (aerosols); no S2 water value found | Measured Rrs bias against distance to cloud; graded flag | P1 |
| G8 | Cross-sensor generality | Wang et al. 2024 survey; early attempts Wieland 2019, OmniCloudMask 2025 | Transfer to Landsat/HLS/Planet/OLCI/drones | P3 |
| G9 | Effect of mask choice on water-quality retrievals | Rarely reported | IRL chl-a/Rrs matchups by mask | P1 |
| G10 (found 2026-11-07) | Dataset provenance: bundled third-party masks can be stale or corrupted | CloudSEN12+ v1.1.2: one site (ROI_00009) has corrupted Cloud Score+ layers; SCL/s2cloudless differ from today's GEE on 87/55 of 535 validation patches (`results/pilot_2026-11-07/provenance_cs12_vs_gee.csv`) | Fetch inputs from the source and report the check | P1 (methods note) |

**Search log for "first" claims.** Before any "first" appears in a paper, record the
database, query string, date and hit count here. None has been recorded yet.
