// ============================================================
// SENTINEL-2 HYBRID CLOUD MASKING - CUSTOM AREA TEMPLATE
// ============================================================
// Use this template to adapt the cloud masking framework 
// to your own study area
//
// INSTRUCTIONS:
// 1. Replace the geometry with your study area
// 2. Update the date range for your analysis period
// 3. Adjust parameters for your biome/region
// 4. Run and validate visually
// ============================================================

// ============================================================
// STEP 1: DEFINE YOUR STUDY AREA
// ============================================================

// Option A: Bounding box (rectangle)
// [west, south, east, north]
var center = ee.Geometry.Rectangle([-80.763739, 27.605387, -80.503601, 28.621909]);

// Option B: Point with buffer (circular area)
// var center = ee.Geometry.Point([-80.6, 28.0]).buffer(50000); // 50km radius

// Option C: Draw geometry in GEE and import
// Use the drawing tools, then click "Import" to get the geometry variable

Map.centerObject(center, 11);

// ============================================================
// STEP 2: SET YOUR ANALYSIS DATES
// ============================================================

// Example: Single date
// var DATES = [ee.Date('2023-07-15')];

// Example: Multiple dates for composite
var DATES = [
  ee.Date('2022-09-15'),
  ee.Date('2022-11-04'),
  ee.Date('2022-11-19')
];

// Alternative: Use date range with filterDate()
// (Modify the collection definition below instead)

// ============================================================
// STEP 3: ADJUST PARAMETERS FOR YOUR BIOME
// ============================================================

// Default parameters (balanced)
var PARAMS = {
  CS_CDF_THRESH: 0.60,         // Cloud Score+ cs_cdf
  CS_THRESH: 0.60,             // Cloud Score+ cs
  CLOUD_PROB_THRESH: 50,       // s2cloudless probability
  NIR_DARK_THRESH: 0.15,       // Shadow detection
  CLOUD_PROJ_DIST: 1,          // Shadow projection (km)
  BUFFER: 50,                  // Cloud edge buffer (meters)
  MIN_AGREEMENT: 1             // Methods needed to flag
};

// WATER BODIES (uncomment to use):
// var PARAMS = {
//   CS_CDF_THRESH: 0.55,      // More strict
//   CS_THRESH: 0.60,
//   CLOUD_PROB_THRESH: 50,
//   NIR_DARK_THRESH: 0.12,    // More sensitive shadows
//   CLOUD_PROJ_DIST: 1,
//   BUFFER: 30,               // Smaller buffer
//   MIN_AGREEMENT: 1
// };

// MOUNTAINOUS (uncomment to use):
// var PARAMS = {
//   CS_CDF_THRESH: 0.65,      // Less strict (terrain shadows)
//   CS_THRESH: 0.70,
//   CLOUD_PROB_THRESH: 55,
//   NIR_DARK_THRESH: 0.18,    // Less sensitive
//   CLOUD_PROJ_DIST: 2,       // Longer projection
//   BUFFER: 100,              // Larger buffer
//   MIN_AGREEMENT: 1
// };

// ============================================================
// STEP 4: VISUALIZATION SETTINGS
// ============================================================

// True color (RGB)
var VIS = {min: 0.0, max: 0.3, bands: ['B4', 'B3', 'B2']};

// False color (vegetation)
var VIS_FALSE_COLOR = {min: 0.0, max: 0.3, bands: ['B8', 'B4', 'B3']};

// Water quality (NIR-Red-Green)
var VIS_WATER = {min: 0.0, max: 0.3, bands: ['B5', 'B4', 'B3']};

// ============================================================
// STEP 5: DATA COLLECTION (usually no changes needed)
// ============================================================

function filterByDates(collection, dateList) {
  var filters = dateList.map(function(d) {
    return ee.Filter.date(d, d.advance(1, 'day'));
  });
  return collection.filter(ee.Filter.or.apply(null, filters));
}

// Sentinel-2 Surface Reflectance
var s2sr = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(center)
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 60));

// s2cloudless probability
var s2clouds = ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')
  .filterBounds(center);

// Cloud Score+
var csPlus = ee.ImageCollection('GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED');

// Filter by dates
var s2srFiltered = filterByDates(s2sr, DATES);
var s2cloudsFiltered = filterByDates(s2clouds, DATES);

print('Images found:', s2srFiltered.size());
print('Date list:', DATES);

// ============================================================
// STEP 6: JOIN COLLECTIONS (usually no changes needed)
// ============================================================

var joined = ee.Join.saveFirst('s2cloudless').apply({
  primary: s2srFiltered,
  secondary: s2cloudsFiltered,
  condition: ee.Filter.equals({leftField: 'system:index', rightField: 'system:index'})
});

var collection = ee.ImageCollection(joined).linkCollection(csPlus, ['cs', 'cs_cdf']);

// ============================================================
// STEP 7: MASK FUNCTIONS (copy from main script)
// ============================================================

// Copy all mask functions from S2_CloudMask_SCIENTIFIC.js:
// - getSclMask()
// - getS2cloudlessMask()
// - getCsMask()
// - getCsCdfMask()
// - getShadowMask()
// - addAllMasks()
// - maskAndComposite()

// [PASTE FUNCTIONS HERE - see main script]

// ============================================================
// STEP 8: APPLY MASKS AND CREATE COMPOSITES
// ============================================================

// Apply all masks to each image
// var collectionWithMasks = collection.map(addAllMasks);

// Create composites
// var resultOriginal = collection.median().divide(10000);
// var resultHybridSmooth = maskAndComposite('mask_hybrid_smooth');

// ============================================================
// STEP 9: ADD TO MAP (customize as needed)
// ============================================================

// Map.addLayer(resultOriginal, VIS, 'Original');
// Map.addLayer(resultHybridSmooth, VIS, 'Hybrid Masked');

// ============================================================
// STEP 10: EXPORT (optional - uncomment to use)
// ============================================================

// Export.image.toDrive({
//   image: resultHybridSmooth,
//   description: 'My_Study_Area_Hybrid_Composite',
//   folder: 'GEE_Exports',
//   scale: 10,
//   region: center,
//   maxPixels: 1e9,
//   fileFormat: 'GeoTIFF'
// });

// ============================================================
// VALIDATION CHECKLIST
// ============================================================
// 
// Before using results:
// [ ] Visually inspect composite for remaining clouds
// [ ] Check confidence map for method agreement
// [ ] Compare pixel counts between methods
// [ ] Verify no data gaps in critical areas
// [ ] Test with different date combinations
//
// ============================================================
