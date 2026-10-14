# Implementation 04/05 — Evidence Studio, flood scenarios and escalation

Implemented 2026-10-14. Research and design rationale are in `docs/RESEARCH_AND_REDESIGN_04_05.md`.

## Delivered experience

The home page is now the **TerraPulse Evidence Studio**. It includes a NASADEM height mesh, a north-up 2D option, optional terrain orbit, radar/thermal/optical/terrain/attention layers, date playback, 32 daily precipitation totals, ranked analysis tiles, geographic point inspection, explainable contributions, and local evidence export.

The scenario lab provides a 0.5×–3× rainfall multiplier, 6/12/24/48/72-hour windows, dry/normal/wet/saturated assumptions, preset runs, same-date baseline comparison, a difference layer, and quantitative category-change metrics. Historical sensitivity is explicitly unavailable because no labeled repeated flood-response history exists.

The original pair-comparison interface remains at `/comparison.html`; the prior time-series/context viewer remains at `/timeseries.html`. All prior analytical data are preserved.

## New real thermal data

Downloaded AOI subsets from **USGS Landsat 8/9 Collection 2 Level-2**, distributed through **Microsoft Planetary Computer**. Only NASA/USGS/Microsoft datasets and the previously approved UN archive are used; no Chinese-hosted dataset service was used.

Four Tier-1 acquisitions are available:

| Date | Screened thermal coverage of the AOI | Mean temperature of valid pixels | Mean reported retrieval uncertainty |
|---|---:|---:|---:|
| 2026-08-18 | 11.82% | 31.88°C | 4.30 K |
| 2026-08-26 | 7.87% | 27.96°C | 4.28 K |
| 2026-09-11 | 5.65% | 25.89°C | 3.96 K |
| 2026-09-19 | 25.40% | 30.99°C | 4.19 K |

These means cover different valid footprints and are **not** an attributed temperature-change series. Thermal dates and their offsets from the selected radar acquisition remain visible.

Conversion: `surface_temperature_C = DN × 0.00341802 + 149 − 273.15`.

Screening rejects fill, dilated cloud, cirrus, cloud, cloud shadow and snow flags; any QA_RADSAT flags; invalid temperature values; and ST_QA uncertainty greater than **5 K**. The 5 K cutoff is an explicit exploratory screening choice, not a validated accuracy guarantee. A stricter 3 K screen yields zero accepted pixels in these downloaded scenes; that coverage is recorded rather than concealed. Cloud/QA gaps remain nodata and are hatched in the viewer. “Find a clear thermal patch” focuses a real screened tile.

Native TIRS detail is **100 m**; USGS delivers a 30 m resampled grid. Temperature is land-surface temperature, not air temperature. It is independent context and **is not a flood-score predictor**.

Saved source windows, unsigned source URLs, STAC metadata and SHA-256 checksums are under `data/context/thermal/`. Temperature and uncertainty COGs, optical/thermal previews and manifests are under `data/derived/nepal_case_01/thermal/`, with local viewer copies under `web/public/cases/nepal_case_01/thermal/`. Anonymous Microsoft read tokens are used in memory and not stored.

## Model definitions

Configuration and version: `config.flood.json`, **flood-escalation-v0.1**. All weights and normalizers are disclosed in the downloadable model card.

Terrain uses the preserved aligned **EPSG:32645, 30 m, 800 × 800** context grid. Quantitative output uses that grid; the terrain mesh is a display-only resampling over the same ground footprint. The original 10 m NISAR science outputs are unchanged.

### Escalation / attention index

Rainfall predictors use disjoint accumulations over the previous 0–24, 24–72 and 72–168 complete hours, plus a separately disclosed exponentially decayed rainfall pressure with a **24-hour half-life**. This reduces repetition caused by treating nested rainfall totals as independent predictors, although correlations remain.

Rainfall normalization is `x / (x + fixed_reference_mm)`. References are fixed design values in the configuration, not refitted per run and not validated local flood thresholds. Terrain wetness uses frozen AOI robust bounds; low slope and modeled drainage proximity have disclosed fixed scales.

The radar-state term is normalized backscatter decrease from the first compatible observation. Repetition is the fraction of available post-baseline observations showing at least a 3 dB decrease from baseline, using only data available **at or before the selected date**. Neither term establishes water or persistent inundation. The first acquisition lacks a temporal radar comparison, so those features are omitted and effective weights are renormalized and disclosed. Missing spatial values remain nodata.

`score = sum(100 × effective_weight_i × normalized_feature_i)`.

The score decomposes into its contributions. Initial bands are Low [0,25), Elevated [25,50), High [50,75), and Very high [75,100]. They are uncalibrated index bands, not probabilities or severity forecasts.

### Counterfactual scenario

Scenario duration has an explicit meaning: multiply the **last D complete observed hourly precipitation rates** before the selected acquisition by the chosen multiplier, then recompute rainfall pressure. This is a counterfactual replay, not a synthetic future storm or hydrodynamic simulation.

The scenario score combines static terrain susceptibility, counterfactual 24/72-hour pressure, an assumed wetness level, and available radar decrease/repetition evidence. The baseline uses the **same date**, unmodified rainfall and the normal wetness assumption. Terrain normalizers and feature availability are held fixed across the comparison.

Returned metrics include high-index area, newly high-index area, no-longer-high area, net high-area change, mean score change and common valid coverage. `elevated_area_km2` means the exclusive 25–49 band; `at_least_elevated_area_km2` includes high bands. Exclusive elevated area can shrink when cells move into higher bands. No population or building exposure is inferred.

A stable scenario identity binds parameters, model version, source/component hashes and relevant model code. Outputs include susceptibility and delta COGs, baseline/scenario/delta previews, contributions, metrics and source identity. Twelve common date/preset combinations are precomputed; other combinations use the local cached component arrays. Generation of the demonstrated 1.5× / 48 h / wet case takes approximately **one second** on this machine; cached retrieval is substantially faster. Performance varies by hardware and cold-start conditions.

### Confidence and missing history

`confidence` is null and `confidence_status` is **UNVALIDATED**. Data coverage is measured and displayed separately. No labeled training set exists, so precision, recall, F1, ROC-AUC, PR-AUC, Brier score and calibration curves remain null. No regression or machine-learning probability was trained.

The previous independent archive is preliminary **mudflow/rockflow mapping**, not repeated flood history or an open-water label. It has zero overlap with the current AOI and is not used as a flood predictor. The regional footprint dialog makes that gap visible. The rainfall-driven model also does not reconstruct the reported upstream ice-avalanche/damming mechanism.

## APIs and artifacts

- `POST /api/cases/nepal_case_01/scenario/flood`
- `GET /api/cases/nepal_case_01/flood-escalation`
- `GET /api/cases/nepal_case_01/flood-model`
- `GET /api/cases/nepal_case_01/flood-probe?observation_id=...&row=...&col=...`
- `GET /api/cases/nepal_case_01/thermal`
- `GET /api/cases/nepal_case_01/thermal-probe?scene_id=...&row=...&col=...`
- `GET /api/zones/{zone_id}/flood-escalation`
- `GET /api/zones/{zone_id}/flood-explanation`

Example scenario request:

```json
{
  "observation_id": "nisar_gc_2026_09_12",
  "rainfall_multiplier": 1.5,
  "duration_hours": 48,
  "wetness": "wet",
  "historical_sensitivity": false
}
```

For that case, the same-date baseline has **11.6199 km²** in the high-index band. The counterfactual has **42.4692 km²**, adding **30.8493 km²**; the mean score rises by approximately **6.61 points**. These are computed model categories, not a validated flood extent.

Escalation maps, the model card, geographic source check, terrain mesh, component cache and `flood_escalation.parquet` are under `data/derived/nepal_case_01/flood/`. Corresponding public files and saved scenario runs are under `web/public/cases/nepal_case_01/flood/`.

## Run and reproduce

```bash
cd "/home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1"
make demo
```

Open `http://127.0.0.1:8000/`. Restart an older server after the API update. Choose **Scenario lab**, select assumptions, and run. The scenario comparison slider shows the same-date baseline on the left and the counterfactual on the right. The Scenario Δ layer shows score-point differences.

Rebuild from cached sources:

```bash
make studio
make validate-flood
make test
make test-ui
```

To reacquire thermal sources: `make download-thermal` (internet required). Saved-viewer and scenario operation use local assets; no runtime external NASA, USGS or Microsoft requests occur.

The interactive scenario server needs the existing Python scientific environment (`make setup`, then `make demo`); no new Python packages were added. Node.js is needed only for development tests, not for viewing. A modern browser with WebGL provides terrain view; a 2D canvas fallback is implemented. The terrain mesh has 10,201 display vertices, and height exaggeration is explicitly labeled. Existing 8 GB RAM guidance remains a practical estimate rather than a benchmark.

## Verification and limits

- **136 Python tests** pass, with four existing Rasterio pending-deprecation warnings.
- **19 JavaScript tests** pass: ten playback-controller checks, five geographic picking checks and four studio interaction-logic checks using explicit DOM/terrain mocks. These mocks do not constitute browser rendering QA.
- The real-data validator checks raw thermal source hashes, all-pixel conversion and masks, thermal missingness, aligned COGs, historical-only radar repetition, escalation decomposition, rainfall monotonicity, baseline invariance, scenario cache reproducibility and area accounting.
- All **146 prior analytical artifacts** remain byte-identical.
- A scientific map comparison is saved as `docs/reports/implementation_04_05_map_comparison.png`; it is **not** a screenshot of the browser UI.
- The historical context validator now treats the recorded producing-code fingerprint as historical provenance by default. `--check-current-source` provides a strict optional comparison; adding unrelated modules does not invalidate old scientific outputs.
- Browser visual/responsive verification is **blocked by the app's localhost URL security policy**. No alternate browser, raw browser command or bypass was used. GPU shader execution and final CSS appearance therefore remain unverified in an actual browser here. The 2D fallback is implemented, but its actual rendering is likewise not claimed as browser-tested.
- Physical disconnected rehearsal, local gauge accuracy, surveyed drainage validation, event validation and score calibration remain open.

Machine-readable QA: `docs/reports/implementation_04_05_qa.json` and `docs/QA.json`.
