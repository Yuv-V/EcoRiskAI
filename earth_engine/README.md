# Earth Engine — full-landscape extraction (Phase 3)

Kirk's main critique was that EcoRiskAI predicts on a **sample** of grid cells,
not the whole Sierra Nevada, and that the sparse/uneven yearly exports (2023 = 7
rows, 2026 = ~1855 rows) point to Earth Engine **timing out** and silently
returning partial data. This folder fixes the extraction side.

## `extract_full_grid.js`

A Google Earth Engine **Code Editor** script that:

- Builds a fixed, wall-to-wall grid over the study area (every cell, not a sample).
- Extracts the same feature schema the pipeline already expects.
- **Tiles** the grid and exports one batch task per `(year, tile)` so no single
  job is large enough to time out.

### Run it

1. Open <https://code.earthengine.google.com> and paste the script.
2. Check the `CONFIG` block (AOI, years, cloud threshold, `tilesX`/`tilesY`).
   If a task still times out, raise `tilesX`/`tilesY` to make each task smaller.
3. **Verify dataset IDs and band scaling against your original working script.**
   Collection 2 Landsat SR scaling and the SMAP/GPM/ERA5/MODIS/VIIRS band names
   are the parts most likely to differ from what you used — those are noted in
   the script.
4. Run, then open the **Tasks** tab and start each `ecoriskai_full_YYYY_tileNN`
   export. They write CSVs to the `ecoriskai_full_grid` Drive folder.

## Feed the output back in

You have two options once the CSVs are downloaded:

- **Per-year merge (existing path).** Drop them in `data/raw/ml/yearly_exports/`
  and run `python main.py`. They merge by `grid_id/year/month`, so denser
  exports simply replace the sparse ones and the whole pipeline gets richer.
- **Dedicated full-grid scorer (new path).** Concatenate them into one CSV at
  `data/processed/feature_tables/ecoriskai_landscape_features.csv`
  (the `paths.landscape_features_csv` value). `python main.py` then also runs
  `run_landscape_prediction`, which scores **every** cell and writes
  `outputs/predictions/ecorisk_landscape_predictions.csv`.

The dashboard already renders predictions as a filled per-cell **risk surface**,
so as coverage fills in, the map goes from scattered cells to the continuous
Sierra-wide picture Kirk asked for — no app changes needed.
