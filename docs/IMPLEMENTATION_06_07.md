# TerraPulse implementations 06 and 07

Implemented 14 October 2026, Asia/Dhaka, in the existing project. Prior analytical results were preserved; all 508 files in `reports/implementation_06_07_prior_artifacts.json` remain byte-identical.

The supplied plans define the requested features. Their sample IDs, normalized scores and confidence values were not treated as observations or copied into outputs.

## Change DNA

`src/compute/change_dna.py` and `dna_pipeline.py` export a profile for every real tracked zone, in `data/derived/nepal_case_01/dna/` and the matching public directory. Outputs are JSON and `change_dna.parquet`.

The magnitude is the maximum visit-level **mean absolute native-pixel baseline change** on fixed all-date common pixels. This avoids cancellation of opposite signed changes; signed means remain in the original time series. Onset is bracketed by valid visits, with an interval-average dB/day rate. Missing intermediate observations widen that bracket rather than create precise timing.

Growth uses successive retained change-mask areas divided by elapsed days. Baseline area stays null. Disturbance persistence is the fraction of valid visits at/after the first illustrative 3 dB crossing that remain ≥3 dB; successive transition-mask frequency remains a separate quantity. Recovery is `1 - latest / peak`, and half-recovery crossings carry an observation bracket. No sampled half-recovery means a null/right-censored half-life, not zero recovery time.

Actual zone `NP-Z4ab9a6118de9`:

| Component | Result |
|---|---:|
| Peak mean absolute baseline change | 7.526309 dB |
| First disturbance bracket | 19–31 Aug 2026 |
| Baseline-to-first disturbed average rate | 0.627192 dB/day |
| Largest observed area-growth rate | −0.00165833 km²/day, contraction |
| Observed disturbance persistence | 2 / 2 visits, 100% |
| Successive transition-mask persistence | 1 / 2 intervals, 50% |
| Latest descriptive return | 5.974931% |
| Recovery half-life | Null; no crossing observed in 12 days after peak |
| Post-baseline variability | 0.224846 dB |
| Peak retained candidate area | 0.0199 km² |
| Prior rain at first disturbed visit | 15.92 / 40.78 mm, 24 / 72 h |
| Mean zone slope | 1.809823° |

Similarity uses cosine similarity on reference-only z-standardized physical features. Missing/constant dimensions are excluded, self-matches are excluded, and minimum reference/dimension requirements are enforced. The actual case has one zone: search returns an explicit insufficient-reference result. No one-zone percentiles, invented previous events or disaster labels are shown. Thermal anomaly and empirical confidence remain null.

## Landslide susceptibility

`config.landslide.json`, `landslide_model.py` and `landslide_pipeline.py` define the separate illustrative index. The source is existing NASADEM derivatives, NASA POWER prior rainfall and compatible NISAR radar.

Static terrain weights: slope .55, roughness .15, absolute curvature .10, TWI .10, modeled drainage proximity .10. Slope is clipped `slope/45°`; drainage is `exp(-distance/300m)`; remaining terrain uses frozen AOI 2nd/98th percentiles. These are model design choices, not calibrated local failure thresholds. Absolute curvature and roughness may be correlated; their combined weights are modest and their interpretation is exploratory. Arbitrary aspect/elevation effects were not added without evidence.

Rainfall uses disjoint 0–24, 24–72 and 72–168 h windows, weights .5/.3/.2 and fixed 100/200/400 mm scales through `x/(x+reference)`. Native rainfall remains coarse regional context. Radar support is `min(mean absolute baseline native-pixel change/6dB,1) × min(slope/45°,1)`; each 30 m block requires all nine contributing radar pixels valid. It uses only the baseline and selected visit.

Combined weights are .55 static/.35 rain/.10 radar. The baseline has no radar comparison; it omits that term and discloses renormalized weights. Spatial nodata stays nodata. Initial index bands 25/50/75 are explicitly uncalibrated, not event probabilities.

| Date | Assessable km² | Mean index | Index ≥50 km² |
|---|---:|---:|---:|
| 19 Aug | 576.0000 | 25.7945 | 5.1534 |
| 31 Aug | 563.3559 | 24.5405 | 1.2123 |
| 12 Sep | 545.4369 | 30.1142 | 12.6486 |

Flood-vs-landslide comparison means use an exact intersected valid footprint. On 12 Sep this is 545.4279 km²; flood mean 27.25935 and landslide mean 30.11388. They remain different formulas, not comparable probabilities. Landslide validity can differ slightly because the flood model also requires earlier valid repetition history.

Outputs include terrain-only COG, date-specific dynamic/radar-support/total COGs and PNGs, latest aliases `landslide_dynamic.tif`/`landslide_total.tif`, zone Parquet, model/manifest and `landslide_validation.json`.

## Independent reference research

Downloaded NASA/GSFC's public [Global Landslide Catalog](https://data.nasa.gov/dataset/global-landslide-catalog-export-f07b6) export, 11,033 records. SHA-256: `2c4898899dd4f373c4320e121c5b655ebb5394d431fa42e57ec4828d07d48b04`.

Only the 10 study-AOI records from an explicit non-Chinese report-host allowlist are retained in `data/context/landslide/nasa_glc_study_subset.csv`. NASA supplied the file; no linked news host was contacted. Origins/hosts and hashes are recorded in `references.json`.

Eight records fail the ≤1 km location-uncertainty/rain-trigger screen. The remaining two occupy two 3 km spatial blocks. The implemented reference review requires at least five eligible independent reports in at least three blocks. **Spatial empirical validation is not achieved.** The review does not call unreported cells negatives or assign ROC/PR/Brier/calibration values.

An official [USGS 2015 earthquake landslide inventory](https://www.usgs.gov/data/map-data-landslides-triggered-25-april-2015-mw-78-gorkha-nepal-earthquake) was researched, but its ScienceBase metadata endpoint returned HTTP 403. It was not downloaded or substituted. An earthquake inventory would only review terrain association, not validate 2026 rainfall-trigger dynamics.

NASA [LHASA](https://github.com/nasa/LHASA) informed the distinction between static susceptibility, dynamic triggers and independently validated forecasting. TerraPulse's index is a separate model and is not claimed to reproduce LHASA.

## Interface and API

`/change-lab.html` adds the guided evidence story, physical-unit DNA profile, actual-time radar chart, recovery censoring, layer switches, date playback, shared-footprint model comparison, cell probe, ranked analysis tiles, source/method dialog and provenance export. Desktop text starts at 16 px with readable supporting text and wide panels. Small screens stack rather than shrink.

APIs:

- `GET /api/cases/nepal_case_01/dna`
- `GET /api/zones/{zone_id}/dna`
- `GET /api/zones/{zone_id}/similar`
- `GET /api/cases/nepal_case_01/landslide`
- `GET /api/zones/{zone_id}/landslide`
- `GET /api/cases/nepal_case_01/landslide-probe?observation_id=...&row=...&col=...`

## Verification and completion status

169 Python tests and 25 JavaScript logic tests pass. The full-source validator independently recalculates DNA magnitude from native common pixels, rainfall from the source hourly cube, weighted maps, coverage, shared footprints and probe additivity. COG metadata, PNG nodata alpha, Parquet counts, producer hashes and all 508 prior outputs are checked.

Software features are implemented. Empirical hazard validation and a historical similarity library remain data-dependent gaps. Browser visual/GPU/responsive verification is blocked by the app URL policy; mock tests and the inspected scientific comparison figure are not browser screenshots. Physical disconnected rehearsal is pending.
