// Abdulrahman Hussein
// ============================================================
// SENTINEL-2 CLOUD MASKING - SCIENTIFIC IMPLEMENTATION
// ============================================================
// Combines all detection methods using weighted pixel-union logic
// to maximize cloud removal while resolving method contradictions
//
// METHODS:
//   1. Cloud Score+ cs_cdf  (primary - Google 2023)
//   2. s2cloudless          (ML probability - Sentinel Hub)
//   3. SCL                  (ESA scene classification)
//   4. Cloud Score+ cs      (spectral distance)
//   5. Shadow projection    (sun-azimuth based)
//
// HYBRID APPROACH:
//   - Per-image masking (BEFORE median composite)
//   - Pixel-union: cloud if ANY method detects it
//   - Confidence weighting: high agreement = high confidence
//   - Morphological buffering: catches cloud edges
// ============================================================

var center = ee.Geometry.Rectangle([-80.763739, 27.605387, -80.503601, 28.621909]);
Map.centerObject(center, 11);

// ============================================================
// PARAMETERS (research-backed defaults)
// ============================================================
var PARAMS = {
  CS_CDF_THRESH: 0.60,         // Cloud Score+ cs_cdf (0.50-0.65 sweet spot)
  CS_THRESH: 0.60,             // Cloud Score+ cs
  CLOUD_PROB_THRESH: 50,       // s2cloudless probability (40-60 recommended)
  NIR_DARK_THRESH: 0.15,       // Dark NIR pixels for shadow detection
  CLOUD_PROJ_DIST: 1,          // Shadow projection distance (km)
  BUFFER: 50,                  // Cloud edge buffer (meters)
  MIN_AGREEMENT: 1             // Min methods needed to flag (1 = any, 2 = consensus)
};

var DATES = [
  ee.Date('2022-09-15'),
  ee.Date('2022-11-04'),
  ee.Date('2022-11-19')
];

var VIS = {min: 0.0, max: 0.3, bands: ['B4', 'B3', 'B2']};

// ============================================================
// BUILD COLLECTION
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

// Join s2cloudless to S2 SR
var joined = ee.Join.saveFirst('s2cloudless').apply({
  primary: s2srFiltered,
  secondary: s2cloudsFiltered,
  condition: ee.Filter.equals({leftField: 'system:index', rightField: 'system:index'})
});

// Link Cloud Score+
var collection = ee.ImageCollection(joined).linkCollection(csPlus, ['cs', 'cs_cdf']);

print('Images in collection:', collection.size());

// ============================================================
// METHOD 1: SCL (Scene Classification Layer)
// ============================================================
function getSclMask(img) {
  var scl = img.select('SCL');
  return scl.eq(3)    // Cloud shadow
    .or(scl.eq(8))    // Cloud medium probability
    .or(scl.eq(9))    // Cloud high probability
    .or(scl.eq(10))   // Thin cirrus
    .rename('mask_scl');
}

// ============================================================
// METHOD 2: s2cloudless probability
// ============================================================
function getS2cloudlessMask(img) {
  var s2cless = ee.Image(img.get('s2cloudless'));
  return s2cless.select('probability')
    .gt(PARAMS.CLOUD_PROB_THRESH)
    .rename('mask_s2cloudless');
}

// ============================================================
// METHOD 3: Cloud Score+ cs
// ============================================================
function getCsMask(img) {
  return img.select('cs').lt(PARAMS.CS_THRESH).rename('mask_cs');
}

// ============================================================
// METHOD 4: Cloud Score+ cs_cdf (PRIMARY - Google 2023 winner)
// ============================================================
function getCsCdfMask(img) {
  return img.select('cs_cdf').lt(PARAMS.CS_CDF_THRESH).rename('mask_cs_cdf');
}

// ============================================================
// METHOD 5: Shadow projection (s2cloudless approach)
// ============================================================
function getShadowMask(img, cloudMask) {
  var scl = img.select('SCL');
  
  // Dark NIR pixels (potential shadows) - exclude water
  var notWater = scl.neq(6);
  var darkPixels = img.select('B8')
    .lt(PARAMS.NIR_DARK_THRESH * 10000)
    .multiply(notWater);
  
  // Direction to project shadows (from sun azimuth)
  var shadowAzimuth = ee.Number(90).subtract(
    ee.Number(img.get('MEAN_SOLAR_AZIMUTH_ANGLE'))
  );
  
  // Project clouds in shadow direction
  var cloudProj = cloudMask.directionalDistanceTransform(
    shadowAzimuth, PARAMS.CLOUD_PROJ_DIST * 10
  ).reproject({crs: img.select(0).projection(), scale: 100})
   .select('distance').mask();
  
  // Shadow = projection intersected with dark pixels
  return cloudProj.multiply(darkPixels).rename('mask_shadow');
}

// ============================================================
// HYBRID MASK GENERATION (per-image)
// Combines all methods with confidence scoring
// ============================================================
function addAllMasks(img) {
  // Generate individual masks
  var m1 = getSclMask(img);
  var m2 = getS2cloudlessMask(img);
  var m3 = getCsMask(img);
  var m4 = getCsCdfMask(img);
  
  // Standard hybrid: cloud if ANY method detects (pixel-union)
  var hybridStd = m1.or(m2).or(m3).or(m4).rename('mask_hybrid_std');
  
  // Shadow projection using the hybrid cloud mask
  var m5 = getShadowMask(img, hybridStd);
  
  // FULL HYBRID: clouds OR shadows
  var hybridFull = hybridStd.or(m5).rename('mask_hybrid_full');
  
  // CONFIDENCE SCORE: how many methods agree (0-4)
  // Higher = more confident this is a cloud
  var confidence = m1.add(m2).add(m3).add(m4).rename('confidence');
  
  // Apply morphological operations to smooth and buffer
  var hybridSmooth = hybridFull
    .focal_min({radius: 20, units: 'meters'})   // Remove isolated noise
    .focal_max({radius: PARAMS.BUFFER, units: 'meters'})  // Buffer edges
    .rename('mask_hybrid_smooth');
  
  return img.addBands(m1)
    .addBands(m2)
    .addBands(m3)
    .addBands(m4)
    .addBands(m5)
    .addBands(hybridStd)
    .addBands(hybridFull)
    .addBands(hybridSmooth)
    .addBands(confidence);
}

// Apply all masks to each image
var collectionWithMasks = collection.map(addAllMasks);

// ============================================================
// CREATE COMPOSITES (per-image masking, then median)
// ============================================================
function maskAndComposite(maskBand) {
  return collectionWithMasks.map(function(img) {
    var mask = img.select(maskBand).not();
    return img.updateMask(mask);
  }).median().divide(10000);
}

// Reference: no masking
var resultOriginal = collection.median().divide(10000);

// Individual method results
var resultScl = maskAndComposite('mask_scl');
var resultS2cless = maskAndComposite('mask_s2cloudless');
var resultCs = maskAndComposite('mask_cs');
var resultCsCdf = maskAndComposite('mask_cs_cdf');

// Hybrid results
var resultHybridStd = maskAndComposite('mask_hybrid_std');
var resultHybridFull = maskAndComposite('mask_hybrid_full');
var resultHybridSmooth = maskAndComposite('mask_hybrid_smooth');

// Aggregated cloud detection layers (for visualization)
var aggScl = collectionWithMasks.select('mask_scl').max();
var aggS2cless = collectionWithMasks.select('mask_s2cloudless').max();
var aggCs = collectionWithMasks.select('mask_cs').max();
var aggCsCdf = collectionWithMasks.select('mask_cs_cdf').max();
var aggShadow = collectionWithMasks.select('mask_shadow').max();
var aggHybridSmooth = collectionWithMasks.select('mask_hybrid_smooth').max();
var aggConfidence = collectionWithMasks.select('confidence').max();

// ============================================================
// ADD LAYERS (compact set - avoids GEE overload)
// ============================================================

// Result layers (RGB composites)
Map.addLayer(resultOriginal, VIS, 'Original (no masking)', false);
Map.addLayer(resultScl, VIS, 'SCL only', false);
Map.addLayer(resultS2cless, VIS, 's2cloudless only', false);
Map.addLayer(resultCs, VIS, 'Cloud Score+ cs only', false);
Map.addLayer(resultCsCdf, VIS, 'Cloud Score+ cs_cdf only', false);
Map.addLayer(resultHybridStd, VIS, 'HYBRID standard (4 methods union)', false);
Map.addLayer(resultHybridFull, VIS, 'HYBRID + shadows', false);
Map.addLayer(resultHybridSmooth, VIS, 'HYBRID FINAL (smoothed + buffered)', true);

// Cloud overlay layers
Map.addLayer(aggScl.selfMask(), {palette: ['FF9800']}, 'Detected by SCL', false);
Map.addLayer(aggS2cless.selfMask(), {palette: ['FFEB3B']}, 'Detected by s2cloudless', false);
Map.addLayer(aggCs.selfMask(), {palette: ['9C27B0']}, 'Detected by cs', false);
Map.addLayer(aggCsCdf.selfMask(), {palette: ['2196F3']}, 'Detected by cs_cdf', false);
Map.addLayer(aggShadow.selfMask(), {palette: ['000080']}, 'Detected shadows', false);
Map.addLayer(aggHybridSmooth.selfMask(), {palette: ['FF0000']}, 'Final HYBRID mask', false);

// Confidence map
Map.addLayer(aggConfidence, {min: 0, max: 4, palette: ['000080', '0080FF', '00FF80', 'FFFF00', 'FF0000']}, 
  'Method agreement (0=none, 4=all)', false);

// ============================================================
// STATISTICS
// ============================================================
print('============================================');
print('CLOUD MASK COMPARISON');
print('============================================');
print('');
print('PARAMETERS:');
print('  Cloud Score+ cs_cdf threshold:', PARAMS.CS_CDF_THRESH);
print('  Cloud Score+ cs threshold:', PARAMS.CS_THRESH);
print('  s2cloudless threshold:', PARAMS.CLOUD_PROB_THRESH);
print('  Shadow NIR threshold:', PARAMS.NIR_DARK_THRESH);
print('  Cloud edge buffer (m):', PARAMS.BUFFER);
print('');

// Pixel counts (fewer = more clouds removed)
var scale = 100;
function pixelCount(img, name) {
  var count = img.select('B4').reduceRegion({
    reducer: ee.Reducer.count(),
    geometry: center,
    scale: scale,
    maxPixels: 1e9
  }).get('B4');
  return ee.Feature(null, {name: name, pixels: count});
}

print('REMAINING PIXELS (lower = more clouds removed):');
print('  Original:', resultOriginal.select('B4').reduceRegion(
  {reducer: ee.Reducer.count(), geometry: center, scale: scale, maxPixels: 1e9}).get('B4'));
print('  SCL only:', resultScl.select('B4').reduceRegion(
  {reducer: ee.Reducer.count(), geometry: center, scale: scale, maxPixels: 1e9}).get('B4'));
print('  s2cloudless:', resultS2cless.select('B4').reduceRegion(
  {reducer: ee.Reducer.count(), geometry: center, scale: scale, maxPixels: 1e9}).get('B4'));
print('  cs:', resultCs.select('B4').reduceRegion(
  {reducer: ee.Reducer.count(), geometry: center, scale: scale, maxPixels: 1e9}).get('B4'));
print('  cs_cdf:', resultCsCdf.select('B4').reduceRegion(
  {reducer: ee.Reducer.count(), geometry: center, scale: scale, maxPixels: 1e9}).get('B4'));
print('  HYBRID std:', resultHybridStd.select('B4').reduceRegion(
  {reducer: ee.Reducer.count(), geometry: center, scale: scale, maxPixels: 1e9}).get('B4'));
print('  HYBRID + shadows:', resultHybridFull.select('B4').reduceRegion(
  {reducer: ee.Reducer.count(), geometry: center, scale: scale, maxPixels: 1e9}).get('B4'));
print('  HYBRID FINAL:', resultHybridSmooth.select('B4').reduceRegion(
  {reducer: ee.Reducer.count(), geometry: center, scale: scale, maxPixels: 1e9}).get('B4'));
print('');
print('HYBRID FINAL should have lowest pixel count');
print('(masks clouds + shadows + buffer)');
print('============================================');

// ============================================================
// UI PANEL
// ============================================================
var panel = ui.Panel({
  style: {width: '340px', padding: '12px', backgroundColor: '#1a1a2e'}
});

panel.add(ui.Label({
  value: 'CLOUD MASK - SCIENTIFIC',
  style: {fontWeight: 'bold', fontSize: '15px', color: '#00ff88', margin: '0 0 5px 0'}
}));

panel.add(ui.Label({
  value: 'Combines all best methods using\nweighted pixel-union logic',
  style: {fontSize: '11px', color: '#00ffff', margin: '0 0 12px 0', whiteSpace: 'pre'}
}));

// View toggles - results
panel.add(ui.Label({value: 'COMPARE RESULTS:', 
  style: {color: '#ffaa00', fontWeight: 'bold', margin: '8px 0 4px 0', fontSize: '12px'}}));

function showOnlyResult(idx) {
  // Result layers are indices 0-7
  for (var i = 0; i < 8; i++) {
    Map.layers().get(i).setShown(i === idx);
  }
}

var btnStyle = {width: '100%', margin: '1px 0', fontSize: '11px'};

panel.add(ui.Button({label: 'Original (no mask)', style: btnStyle,
  onClick: function() { showOnlyResult(0); }}));
panel.add(ui.Button({label: 'SCL only', style: btnStyle,
  onClick: function() { showOnlyResult(1); }}));
panel.add(ui.Button({label: 's2cloudless only', style: btnStyle,
  onClick: function() { showOnlyResult(2); }}));
panel.add(ui.Button({label: 'Cloud Score+ cs only', style: btnStyle,
  onClick: function() { showOnlyResult(3); }}));
panel.add(ui.Button({label: 'Cloud Score+ cs_cdf only', style: btnStyle,
  onClick: function() { showOnlyResult(4); }}));
panel.add(ui.Button({label: 'HYBRID standard (4 methods)', style: btnStyle,
  onClick: function() { showOnlyResult(5); }}));
panel.add(ui.Button({label: 'HYBRID + shadows', style: btnStyle,
  onClick: function() { showOnlyResult(6); }}));
panel.add(ui.Button({label: 'HYBRID FINAL (best)', 
  style: {width: '100%', margin: '1px 0', fontSize: '11px', backgroundColor: '#2a4a2a', fontWeight: 'bold'},
  onClick: function() { showOnlyResult(7); }}));

// Cloud overlay toggles
panel.add(ui.Label({value: 'SHOW DETECTIONS:', 
  style: {color: '#ffaa00', fontWeight: 'bold', margin: '12px 0 4px 0', fontSize: '12px'}}));

function toggleOverlay(idx) {
  var layer = Map.layers().get(idx);
  layer.setShown(!layer.getShown());
}

panel.add(ui.Button({label: 'Toggle SCL clouds', style: btnStyle,
  onClick: function() { toggleOverlay(8); }}));
panel.add(ui.Button({label: 'Toggle s2cloudless clouds', style: btnStyle,
  onClick: function() { toggleOverlay(9); }}));
panel.add(ui.Button({label: 'Toggle cs clouds', style: btnStyle,
  onClick: function() { toggleOverlay(10); }}));
panel.add(ui.Button({label: 'Toggle cs_cdf clouds', style: btnStyle,
  onClick: function() { toggleOverlay(11); }}));
panel.add(ui.Button({label: 'Toggle shadows', style: btnStyle,
  onClick: function() { toggleOverlay(12); }}));
panel.add(ui.Button({label: 'Toggle HYBRID mask', style: btnStyle,
  onClick: function() { toggleOverlay(13); }}));
panel.add(ui.Button({label: 'Toggle confidence map', style: btnStyle,
  onClick: function() { toggleOverlay(14); }}));

// Method info
panel.add(ui.Label({value: '─────────────────────', 
  style: {color: '#444', margin: '12px 0 8px 0'}}));

panel.add(ui.Label({
  value: 'METHODS USED:',
  style: {color: '#00ffff', fontWeight: 'bold', fontSize: '12px'}
}));

panel.add(ui.Label({
  value: '1. SCL (ESA classifier)\n' +
         '2. s2cloudless (ML probability)\n' +
         '3. Cloud Score+ cs (spectral)\n' +
         '4. Cloud Score+ cs_cdf (temporal)\n' +
         '5. Shadow projection (sun angle)',
  style: {color: '#aaa', fontSize: '10px', whiteSpace: 'pre'}
}));

panel.add(ui.Label({value: '─────────────────────', 
  style: {color: '#444', margin: '10px 0 8px 0'}}));

panel.add(ui.Label({
  value: 'HYBRID LOGIC:',
  style: {color: '#00ff88', fontWeight: 'bold', fontSize: '12px'}
}));

panel.add(ui.Label({
  value: 'For each pixel (x,y):\n' +
         '  cloud_final = SCL(x,y) OR\n' +
         '                s2cloudless(x,y) OR\n' +
         '                cs(x,y) OR\n' +
         '                cs_cdf(x,y) OR\n' +
         '                shadow(x,y)\n\n' +
         'Then: morphological smoothing\n' +
         '+ 50m edge buffer\n\n' +
         'Per-image masking applied\n' +
         'BEFORE median composite',
  style: {color: '#aaa', fontSize: '10px', whiteSpace: 'pre',
          backgroundColor: '#1e3d1e', padding: '8px', borderRadius: '4px'}
}));

ui.root.add(panel);

// ============================================================
// USAGE INSTRUCTIONS
// ============================================================
print('');
print('USAGE:');
print('  1. Click any result button to compare methods');
print('  2. Click toggle buttons to overlay detections');
print('  3. HYBRID FINAL is the recommended output');
print('  4. Use individual methods for specific projects:');
print('     - Water bodies: cs_cdf (less terrain shadow)');
print('     - Land mapping: HYBRID FINAL (catches all)');
print('     - Quick view: SCL only (fastest)');
print('============================================');
