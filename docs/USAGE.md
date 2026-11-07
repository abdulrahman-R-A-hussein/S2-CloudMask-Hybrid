# Detailed Usage Guide

## Table of Contents
1. [Getting Started with Google Earth Engine](#getting-started-with-google-earth-engine)
2. [Running the Cloud Mask Script](#running-the-cloud-mask-script)
3. [Customizing for Your Study Area](#customizing-for-your-study-area)
4. [Understanding the UI Panel](#understanding-the-ui-panel)
5. [Interpreting Results](#interpreting-results)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Configuration](#advanced-configuration)

---

## Getting Started with Google Earth Engine

### 1. Create a GEE Account

1. Go to https://signup.earthengine.google.com/
2. Sign in with your Google account
3. Fill out the registration form (typically approved within 24-48 hours for research purposes)

### 2. Access the Code Editor

Once approved, access the Code Editor at: https://code.earthengine.google.com/

The interface has four main panels:
- **Left**: Scripts, Docs, Assets, and Inspector
- **Center**: Code editor
- **Right**: Map visualization
- **Bottom**: Console output

---

## Running the Cloud Mask Script

### Step 1: Create a New Script

1. In the left panel, click the "New" button
2. Select "Repository script" (to save to your GEE repository) or "File" → "New Script"
3. Name it: `S2_CloudMask_Hybrid`

### Step 2: Copy the Code

1. Copy the entire contents of `S2_CloudMask_SCIENTIFIC.js`
2. Paste into the GEE Code Editor
3. Press Ctrl+S (or Cmd+S on Mac) to save

### Step 3: Run the Script

1. Click the "Run" button or press Ctrl+Enter
2. Wait for processing (time depends on area size and server load)
3. The map will display with the UI panel on the right

---

## Customizing for Your Study Area

### Modify the Study Area

Replace the `center` variable with your area:

```javascript
// Option 1: Rectangle (bounding box)
var center = ee.Geometry.Rectangle([west, south, east, north]);
// Example: var center = ee.Geometry.Rectangle([-80.8, 27.5, -80.4, 28.7]);

// Option 2: Point with buffer
var center = ee.Geometry.Point([-80.6, 28.0]).buffer(50000); // 50km radius

// Option 3: Draw on map and import
// Use the geometry drawing tools in GEE, then import
```

### Modify the Dates

```javascript
// Single date
var DATES = [ee.Date('2023-07-15')];

// Multiple dates (for composite)
var DATES = [
  ee.Date('2023-07-01'),
  ee.Date('2023-07-15'),
  ee.Date('2023-08-01')
];

// Date range (using filter instead)
var s2sr = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(center)
  .filterDate('2023-06-01', '2023-09-01')  // Start, End
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 60));
```

---

## Understanding the UI Panel

The script creates an interactive control panel with two sections:

### Compare Results Buttons

Click to see different masking approaches:

| Button | What It Shows |
|--------|--------------|
| Original (no mask) | Unfiltered composite for comparison |
| SCL only | ESA's official scene classification |
| s2cloudless only | ML-based probability masking |
| Cloud Score+ cs only | Spectral distance method |
| Cloud Score+ cs_cdf only | Same Cloud Score+ model, score normalized over time (keeps more pixels) |
| HYBRID standard | Union of 4 cloud methods |
| HYBRID + shadows | Clouds + shadow projection (shadow projection skips water) |
| **HYBRID FINAL** | **Most aggressive: union + shadows, 20 m erosion, 50 m buffer** |

### Show Detections Toggles

Overlay individual detection layers:

| Button | Color | Meaning |
|--------|-------|---------|
| Toggle SCL clouds | Orange | SCL-detected clouds |
| Toggle s2cloudless clouds | Yellow | ML probability clouds |
| Toggle cs clouds | Purple | Spectral distance clouds |
| Toggle cs_cdf clouds | Blue | CDF method clouds |
| Toggle shadows | Dark blue | Shadow projection (land only) |
| Toggle HYBRID mask | Red | Final combined mask, shown as the union over all dates (cloudy on at least one date) |
| Toggle confidence map | Gradient | 0-4 cloud detectors agreeing (highest value over all dates) |

All detection overlays show the **maximum over all dates**, not the mask applied to any single image.

---

## Interpreting Results

### Console Output

The script prints statistics to the console:

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

Counts are computed on each composite at 100 m. To get the share removed, divide by the `Original` count yourself.

**Interpretation**: Lower pixel count = more aggressive cloud removal, **not** more accurate removal. `HYBRID FINAL` always has the lowest count, because a union removes at least as much as any single mask. The counts measure yield; the method has not yet been validated against reference labels (see `docs/ROADMAP.md`, Phase C).

### Shadows over water

The shadow-projection step ignores water pixels (SCL class 6), because water is dark in the near-infrared everywhere. Cloud shadows on water are therefore removed only when SCL (class 3) or Cloud Score+ flags them. Check shadow areas on the water visually.

### Confidence Map Colors

| Color | Methods Agreeing | Interpretation |
|-------|-------------------|----------------|
| Dark blue | 0 | Clear sky (no detection) |
| Light blue | 1 | Weak detection (verify visually) |
| Green | 2 | Moderate confidence |
| Yellow | 3 | High confidence |
| Red | 4 | Very high confidence (all methods) |

Note: cs and cs_cdf come from the same Cloud Score+ model, so a score of 2 can mean "Cloud Score+ only". The agreement count does not include the shadow test.

---

## Troubleshooting

### Problem: "ImageCollection.filter: No images match the filters"

**Cause**: No images for your date/location combination.

**Solution**:
```javascript
// Check what's available
print('Available images:', s2srFiltered.size());
print('Date range:', s2srFiltered.aggregate_array('system:time_start'));
```

### Problem: Mask is too aggressive (removes too much)

**Solution**: Adjust parameters to be less strict. Cloud Score+ flags cloud where the score is **below** the threshold, so *lower* it to mask less; s2cloudless flags cloud where the probability is **above** the threshold, so *raise* it to mask less:
```javascript
var PARAMS = {
  CS_CDF_THRESH: 0.50,      // Lower threshold = less masking (was 0.60)
  CS_THRESH: 0.50,          // Lower threshold = less masking
  CLOUD_PROB_THRESH: 60,    // Higher threshold = less masking (was 50)
  BUFFER: 30,               // Smaller buffer (was 50)
  // ... rest of params
};
```

### Problem: Still seeing clouds in composite

**Solution**: Check individual methods:
1. Toggle on each detection layer
2. See which method is missing the clouds
3. Adjust that method's threshold

### Problem: UI panel not showing

**Cause**: Script error (check the Console for a red error message) or a leftover panel from an earlier run.

**Solution**: Fix any error shown in the Console, then click **Reset** (next to Run) and run the script again. Avoid `ui.root.clear()`: it removes the default `Map` that the script draws its layers on.

---

## Advanced Configuration

### Adjusting for Different Biomes

These are **unvalidated starting points**, not tested settings. Each comment says what the value does relative to the default. Keep all other parameters (only the changed ones are shown).

Direction reminder: Cloud Score+ masks where score < threshold (higher = more masking); s2cloudless masks where probability > threshold (lower = more masking); the shadow test flags NIR < threshold (higher = more shadow, land only).

**Water bodies** (lakes, coastal):
```javascript
var PARAMS = {
  CS_CDF_THRESH: 0.55,      // Masks LESS than 0.60: use if bright, turbid or bloom water is being masked
  NIR_DARK_THRESH: 0.15,    // No effect over water: the shadow test skips water pixels
  BUFFER: 50,               // Keep at least the default: clear pixels next to clouds can be
                            // brightened over km distances; a water-specific buffer is planned
                            // (docs/ROADMAP.md D2)
};
```

**Mountainous terrain**:
```javascript
var PARAMS = {
  CS_CDF_THRESH: 0.55,      // Masks LESS than 0.60: use if terrain shadows are being masked as cloud
  CLOUD_PROJ_DIST: 2,       // Longer shadow projection (km)
  BUFFER: 100,              // Larger buffer
};
```

**Urban areas**:
```javascript
var PARAMS = {
  CLOUD_PROB_THRESH: 55,    // Masks LESS than 50: bright roofs can be mistaken for cloud
  BUFFER: 20,               // Smaller buffer (tight mapping)
};
```

### Exporting Results

Add this to the end of your script:

```javascript
// Export composite to Google Drive
Export.image.toDrive({
  image: resultHybridSmooth,
  description: 'S2_Hybrid_Masked_Composite',
  folder: 'GEE_Exports',
  scale: 10,                    // 10m resolution
  region: center,
  maxPixels: 1e9,
  fileFormat: 'GeoTIFF'
});

// Export mask layer
// Note: aggHybridSmooth is the union over ALL dates (1 = cloudy on at least one date),
// not the mask applied to any single image.
Export.image.toDrive({
  image: aggHybridSmooth,
  description: 'S2_Hybrid_Mask',
  folder: 'GEE_Exports',
  scale: 10,
  region: center,
  maxPixels: 1e9,
  fileFormat: 'GeoTIFF'
});
```

Then click the "Run" button in the **Tasks** tab (right panel) to start the export.

---

## Best Practices

1. **Always check the confidence map** - Pixels detected by only 1 method need visual verification
2. **HYBRID FINAL is the most aggressive option** - It includes all methods + smoothing + buffer; for water work, also check that bloom or turbid areas are not being removed
3. **Compare with original** - Always toggle "Original (no mask)" to see what was removed
4. **Test multiple thresholds** - Run with different parameters to find optimal for your area
5. **Document your settings** - Record which parameters worked for your study area

---

For questions or issues, please open an issue on GitHub or contact the authors.
