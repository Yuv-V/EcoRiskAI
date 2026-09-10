/**
 * EcoRiskAI — Full-landscape feature extraction (Google Earth Engine Code Editor)
 * ------------------------------------------------------------------------------
 * PURPOSE (Phase 3, from the TNC check-in):
 *   Move from a *sample* of grid cells to WALL-TO-WALL coverage. This script
 *   builds a fixed grid over the whole Sierra Nevada study area and extracts the
 *   same feature schema for EVERY cell, then exports the table in TILES so the
 *   job does not time out (the likely cause of the sparse/uneven exports today —
 *   e.g. 2023 came back with 7 rows while 2026 had ~1855).
 *
 * WHY TILING FIXES THE TIMEOUT:
 *   Earth Engine chokes when you ask for one enormous reduceRegions() in the
 *   interactive session. Instead we (1) use Export.table.toDrive (the batch
 *   system, far more tolerant) and (2) split the grid into TILES so each export
 *   task is small and finishes. You launch one task per (year, tile) from the
 *   Tasks tab.
 *
 * OUTPUT SCHEMA (must match src/dataset/merge_yearly_exports.py input):
 *   grid_id, year, month, latitude, longitude, blue, green, red, nir, swir1,
 *   swir2, ndvi, ndmi, nbr, treecover2000, lossyear, forest_loss_next_year,
 *   forested_2000, elevation, slope, aspect, soil_moisture, precipitation,
 *   temperature_c, burned_this_month, night_lights, landsat_image_count
 *
 * HOW TO USE:
 *   1. Paste into https://code.earthengine.google.com
 *   2. Confirm the CONFIG block and the dataset IDs/bands against your original
 *      working script (band scaling differs by collection — see NOTEs).
 *   3. Run. Open the Tasks tab and start each "ecoriskai_full_YYYY_tileNN" task.
 *   4. Download the CSVs from Drive into data/raw/ml/yearly_exports/ (they merge
 *      by grid_id/year/month), OR into a single full-grid CSV for the landscape
 *      scorer at paths.landscape_features_csv.
 *
 * This script is a faithful, standard-pattern scaffold. It cannot be run from
 * this repo (no Earth Engine auth here), so treat dataset specifics as the parts
 * to verify against your own extraction.
 */

// ============================ CONFIG =========================================
var CONFIG = {
  aoi: ee.Geometry.Rectangle([-120.9, 35.9, -118.2, 39.2]), // Sierra Nevada
  cellSizeDeg: 0.017966,   // ~2 km grid (matches config.yaml grid.cell_size_degrees)
  years: [2020, 2021, 2022, 2023, 2024, 2025, 2026],
  months: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
  cloudCoverMax: 20,       // percent; the filter that thinned earlier exports
  tilesX: 4,               // grid columns of tiles (raise if a task still times out)
  tilesY: 4,               // grid rows of tiles
  driveFolder: 'ecoriskai_full_grid',
  scale: 1000              // reduceRegions scale in metres
};

// ============================ FIXED GRID =====================================
// Build a regular grid of square cells covering the AOI. Every cell is kept
// (wall-to-wall), unlike a sampled point export.
function buildGrid(aoi, cellSize) {
  var bounds = aoi.bounds();
  var coords = ee.List(bounds.coordinates().get(0));
  var xmin = ee.Number(ee.List(coords.get(0)).get(0));
  var ymin = ee.Number(ee.List(coords.get(0)).get(1));
  var xmax = ee.Number(ee.List(coords.get(2)).get(0));
  var ymax = ee.Number(ee.List(coords.get(2)).get(1));

  var lonSeq = ee.List.sequence(xmin, xmax, cellSize);
  var latSeq = ee.List.sequence(ymin, ymax, cellSize);

  var cells = lonSeq.map(function (lon) {
    lon = ee.Number(lon);
    return latSeq.map(function (lat) {
      lat = ee.Number(lat);
      var cx = lon.add(cellSize / 2);
      var cy = lat.add(cellSize / 2);
      // Deterministic integer grid_id from the cell centroid.
      var gid = cx.multiply(1000).round().multiply(100000)
                  .add(cy.multiply(1000).round());
      return ee.Feature(ee.Geometry.Point([cx, cy]), {
        grid_id: gid, latitude: cy, longitude: cx
      });
    });
  }).flatten();
  return ee.FeatureCollection(cells).filterBounds(aoi);
}

var GRID = buildGrid(CONFIG.aoi, CONFIG.cellSizeDeg);
print('Total grid cells (wall-to-wall):', GRID.size());
Map.centerObject(CONFIG.aoi, 7);
Map.addLayer(GRID, {color: '1B5E20'}, 'Full grid', false);

// ============================ STATIC LAYERS ==================================
// Hansen Global Forest Change: forest cover + loss year.
var hansen = ee.Image('UMD/hansen/global_forest_change_2023_v1_11');
var treecover2000 = hansen.select('treecover2000');
var lossyear = hansen.select('lossyear');              // 0, or years since 2000
var forested2000 = treecover2000.gte(30).rename('forested_2000');

// Terrain from SRTM.
var srtm = ee.Image('USGS/SRTMGL1_003');
var terrain = ee.Terrain.products(srtm);               // elevation, slope, aspect
var elevation = srtm.rename('elevation');
var slope = terrain.select('slope');
var aspect = terrain.select('aspect');

// ============================ HELPERS ========================================
// NOTE: Landsat 8/9 Collection 2 L2 SR scaling is value*0.0000275 - 0.2.
function scaleL2(img) {
  var optical = img.select('SR_B.').multiply(0.0000275).add(-0.2);
  return img.addBands(optical, null, true);
}

function monthlyLandsat(year, month) {
  var start = ee.Date.fromYMD(year, month, 1);
  var end = start.advance(1, 'month');
  var col = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
      .merge(ee.ImageCollection('LANDSAT/LC09/C02/T1_L2'))
      .filterBounds(CONFIG.aoi)
      .filterDate(start, end)
      .filter(ee.Filter.lt('CLOUD_COVER', CONFIG.cloudCoverMax))
      .map(scaleL2);
  var count = col.size();
  var img = col.median();
  // Band aliases matching the schema.
  var blue = img.select('SR_B2').rename('blue');
  var green = img.select('SR_B3').rename('green');
  var red = img.select('SR_B4').rename('red');
  var nir = img.select('SR_B5').rename('nir');
  var swir1 = img.select('SR_B6').rename('swir1');
  var swir2 = img.select('SR_B7').rename('swir2');
  var ndvi = nir.subtract(red).divide(nir.add(red)).rename('ndvi');
  var ndmi = nir.subtract(swir1).divide(nir.add(swir1)).rename('ndmi');
  var nbr = nir.subtract(swir2).divide(nir.add(swir2)).rename('nbr');
  return blue.addBands([green, red, nir, swir1, swir2, ndvi, ndmi, nbr])
             .set('landsat_image_count', count);
}

function monthlyClimate(year, month) {
  var start = ee.Date.fromYMD(year, month, 1);
  var end = start.advance(1, 'month');
  // SMAP soil moisture, GPM precipitation, ERA5-Land temperature.
  var soil = ee.ImageCollection('NASA/SMAP/SPL4SMGP/007')
      .filterDate(start, end).select('sm_surface').mean().rename('soil_moisture');
  var precip = ee.ImageCollection('NASA/GPM_L3/IMERG_MONTHLY_V07')
      .filterDate(start, end).select('precipitation').mean().rename('precipitation');
  var tempK = ee.ImageCollection('ECMWF/ERA5_LAND/MONTHLY_AGGR')
      .filterDate(start, end).select('temperature_2m').mean();
  var tempC = tempK.subtract(273.15).rename('temperature_c');
  // MODIS burned area -> burned_this_month flag.
  var burned = ee.ImageCollection('MODIS/061/MCD64A1')
      .filterDate(start, end).select('BurnDate').max().gt(0).rename('burned_this_month')
      .unmask(0);
  // VIIRS night lights.
  var lights = ee.ImageCollection('NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG')
      .filterDate(start, end).select('avg_rad').mean().rename('night_lights');
  return soil.addBands([precip, tempC, burned, lights]);
}

// forest_loss_next_year: 1 where Hansen loss is recorded in (year + 1).
function lossNextYear(year) {
  var target = year + 1 - 2000;                        // lossyear is years since 2000
  return lossyear.eq(target).rename('forest_loss_next_year');
}

// ============================ TILING + EXPORT ================================
// Split the AOI into tilesX * tilesY rectangles; export one task per (year,tile).
function buildTiles(aoi, nx, ny) {
  var b = ee.List(ee.Geometry(aoi).bounds().coordinates().get(0));
  var xmin = ee.Number(ee.List(b.get(0)).get(0));
  var ymin = ee.Number(ee.List(b.get(0)).get(1));
  var xmax = ee.Number(ee.List(b.get(2)).get(0));
  var ymax = ee.Number(ee.List(b.get(2)).get(1));
  var dx = xmax.subtract(xmin).divide(nx);
  var dy = ymax.subtract(ymin).divide(ny);
  var tiles = [];
  for (var i = 0; i < nx; i++) {
    for (var j = 0; j < ny; j++) {
      var x0 = xmin.add(dx.multiply(i));
      var y0 = ymin.add(dy.multiply(j));
      tiles.push({
        id: i * ny + j,
        geom: ee.Geometry.Rectangle([x0, y0, x0.add(dx), y0.add(dy)])
      });
    }
  }
  return tiles;
}

var TILES = buildTiles(CONFIG.aoi, CONFIG.tilesX, CONFIG.tilesY);

CONFIG.years.forEach(function (year) {
  var loss = lossNextYear(year);
  TILES.forEach(function (tile) {
    var cells = GRID.filterBounds(tile.geom);
    var monthly = CONFIG.months.map(function (month) {
      var feats = monthlyLandsat(year, month);
      var climate = monthlyClimate(year, month);
      var stack = feats.addBands([climate, treecover2000.rename('treecover2000'),
                    lossyear.rename('lossyear'), loss, forested2000,
                    elevation, slope, aspect]);
      var reduced = stack.reduceRegions({
        collection: cells,
        reducer: ee.Reducer.mean(),
        scale: CONFIG.scale
      });
      var lsCount = feats.get('landsat_image_count');
      return reduced.map(function (f) {
        return f.set({year: year, month: month, landsat_image_count: lsCount});
      });
    });
    var table = ee.FeatureCollection(monthly).flatten();
    var tileName = 'ecoriskai_full_' + year + '_tile' +
                   (tile.id < 10 ? '0' + tile.id : tile.id);
    Export.table.toDrive({
      collection: table,
      description: tileName,
      folder: CONFIG.driveFolder,
      fileFormat: 'CSV',
      selectors: ['grid_id', 'year', 'month', 'latitude', 'longitude',
        'blue', 'green', 'red', 'nir', 'swir1', 'swir2', 'ndvi', 'ndmi', 'nbr',
        'treecover2000', 'lossyear', 'forest_loss_next_year', 'forested_2000',
        'elevation', 'slope', 'aspect', 'soil_moisture', 'precipitation',
        'temperature_c', 'burned_this_month', 'night_lights', 'landsat_image_count']
    });
  });
});

print('Created ' + (CONFIG.years.length * TILES.length) +
      ' export tasks. Open the Tasks tab and run them.');
