# TerraPulse — Implementation 02: NISAR Time Series

**Implementation record:** 14 October 2026, Asia/Dhaka  
**Case:** Nepal surface-change investigation (`nepal_case_01`)  
**Source specification:** `../implementation/TerraPulse_Impl_02_NISAR_Time_Series.md`

## Implemented behavior and current limit

The local system now supports acquisition navigation, successive signed changes and centered median/MAD scores, fixed-zone tracking, transition-frequency maps, and zone-level return-toward-baseline measurements. Outputs include actual Cloud Optimized GeoTIFFs, a Parquet table, geographic zones, manifests, local APIs and a separate time-series viewer linked from the existing app.

All **16 downloaded HDF5 files in `database for imp2` were audited**. Across the supplied parent dataset directory, the audit examined **27 non-cache HDF5 files**: 22 readable HH/frequency-A GCOV products and five unsupported inputs. Their actual metadata show that the new downloads do **not** extend the existing track 98/frame 16/ascending/HH/frequency-A/40 MHz/P05023 series. The compatible primary series remains **August 19, August 31 and September 12, 2026**. Different tracks or carrier/bandwidth configurations are not treated as equivalent merely because they overlap geographically or bracket August 26.

This completes the requested functional time-series path on compatible observations. It does not establish a scientifically calibrated score cutoff, additional compatible dates from the new folder, independently verified disaster causes, exact onset timing, or long-term recovery. The viewer and exports state those limits explicitly.

## New downloads and selection decisions

The selected measurement is real diagonal `HHHH` gamma-0 power, converted using `10 log10(power)` to dB. The anchor uses track 98/frame 16, ascending left-looking geometry, frequency A, 40 MHz range bandwidth, 1.239 GHz center frequency, product version 1.0.11 and a consistent dual-polarization/dithered acquisition configuration.

| New source file | Actual UTC date | Track / frame | Bandwidth MHz | Why it does not extend the primary series |
| --- | --- | --- | ---: | --- |
| `database for imp2/12/NISAR_L2_PR_GCOV_027_170_A_015_4005_DHDH_A_20260812T233025_20260812T233100_P05023_N_F_J_001.h5` | 2026-08-12 | 170 / 15 | 40 | Different track/frame from the anchor |
| `database for imp2/12/NISAR_L2_PR_GCOV_027_170_A_016_4005_DHDH_A_20260812T233059_20260812T233134_P05023_N_F_J_001.h5` | 2026-08-12 | 170 / 16 | 40 | Different track/frame from the anchor |
| `database for imp2/12/NISAR_L2_PR_GCOV_027_170_A_017_4005_DHDH_A_20260812T233133_20260812T233207_P05023_N_F_J_001.h5` | 2026-08-12 | 170 / 17 | 40 | Different track/frame from the anchor |
| `database for imp2/13/NISAR_L2_PR_GCOV_028_005_D_073_4005_DHDH_A_20260813T132236_20260813T132311_P05023_N_F_J_001.h5` | 2026-08-13 | 5 / 73 | 40 | Different track/frame from the anchor |
| `database for imp2/14/NISAR_L2_PR_GCOV_028_026_A_015_4005_DHDH_A_20260814T234704_20260814T234738_P05023_N_F_J_001.h5` | 2026-08-14 | 26 / 15 | 40 | Different track/frame from the anchor |
| `database for imp2/16/NISAR_L2_PR_GCOV_028_048_D_074_4005_DHDH_A_20260816T125812_20260816T125846_P05023_N_F_J_001.h5` | 2026-08-16 | 48 / 74 | 40 | Different track/frame from the anchor |
| `database for imp2/18/NISAR_L2_PR_GCOV_028_077_D_075_4005_DHDH_A_20260818T131524_20260818T131559_P05023_N_F_J_001.h5` | 2026-08-18 | 77 / 75 | 40 | Different track/frame from the anchor |
| `database for imp2/19/NISAR_L2_PR_GCOV_028_098_A_017_4005_DHDH_A_20260819T233952_20260819T234026_P05023_N_F_J_001.h5` | 2026-08-19 | 98 / 17 | 40 | Frame 17 instead of frame 16; only two dates in this separate compatible group |
| `database for imp2/23/NISAR_L2_PR_GCOV_028_149_D_073_2005_QPDH_A_20260823T130558_20260823T130632_P05023_N_F_J_001.h5` | 2026-08-23 | 149 / 73 | 20 | Different track/frame from the anchor; 20 MHz / 1.229 GHz quad-polarization configuration differs from the 40 MHz / 1.239 GHz dual-polarization series |
| `database for imp2/23/NISAR_L2_PR_GCOV_029_005_D_073_2005_QPDH_A_20260825T132236_20260825T132311_P05023_N_F_J_001.h5` | 2026-08-25 | 5 / 73 | 20 | Different track/frame from the anchor; 20 MHz / 1.229 GHz quad-polarization configuration differs from the 40 MHz / 1.239 GHz dual-polarization series |
| `database for imp2/28/NISAR_L2_PR_GCOV_029_048_D_075_2005_QPDH_A_20260828T125845_20260828T125920_P05023_N_F_J_001.h5` | 2026-08-28 | 48 / 75 | 20 | Different track/frame from the anchor; 20 MHz / 1.229 GHz quad-polarization configuration differs from the 40 MHz / 1.239 GHz dual-polarization series |
| `database for imp2/30/NISAR_L2_PR_GCOV_029_077_D_075_2005_QPDH_A_20260830T131524_20260830T131559_P05023_N_F_J_001.h5` | 2026-08-30 | 77 / 75 | 20 | Different track/frame from the anchor; 20 MHz / 1.229 GHz quad-polarization configuration differs from the 40 MHz / 1.239 GHz dual-polarization series |
| `database for imp2/31/NISAR_L2_PR_GCOV_029_098_A_017_4005_DHDH_A_20260831T233951_20260831T234026_P05023_N_F_J_001.h5` | 2026-08-31 | 98 / 17 | 40 | Frame 17 instead of frame 16; only two dates in this separate compatible group |
| `database for imp2/NISAR_L2_PR_GCOV_027_149_D_073_4005_DHDH_A_20260811T130558_20260811T130633_P05023_N_F_J_001.h5` | 2026-08-11 | 149 / 73 | 40 | Different track/frame from the anchor |
| `database for imp2/NISAR_L2_PR_GCOV_027_149_D_074_4005_DHDH_A_20260811T130632_20260811T130706_P05023_N_F_J_001.h5` | 2026-08-11 | 149 / 74 | 40 | Different track/frame from the anchor |
| `database for imp2/NISAR_L2_PR_GCOV_027_149_D_075_4005_DHDH_A_20260811T130705_20260811T130740_P05023_N_F_J_001.h5` | 2026-08-11 | 149 / 75 | 40 | Different track/frame from the anchor |

The date comes from HDF5 acquisition metadata, not the folder name. In particular, the `23` folder also contains an August **25** product. The complete [source audit](../data/derived/nepal_case_01/timeseries/source_audit.json) retains granule IDs, physical settings, compatible groups and explicit per-file reasons.

Apparent same-track repeats need physical checks too: the August 11/23 track 149/frame 73 pair, August 13/25 track 5/frame 73 pair, and August 18/30 track 77/frame 75 pair switch frequency-A bandwidth/carrier/polarization configuration. The August 16/28 track 48 files also use different frames. The August 19/31 track 98/frame 17 products form a separate two-date group, not a third date for frame 16.

The other five unsupported files comprise two L0 RRSD products requiring a different processing chain and three September 28 GCOV products without the selected frequency-A HHHH layer. The three original alternate 1.0.12 releases are same-date reprocessings, not additional observations.

Only supplied NASA–ISRO data are used for these new measurements. No Chinese government or agency dataset is introduced. No source HDF5 is uploaded.

## Processing and canonical grid

`config.timeseries.json` points to the parent dataset scan, the anchor source and the unchanged legacy AOI settings. Discovery prunes virtual environments and caches, audits named HDF5 datatypes as well as datasets, sorts actual UTC acquisition times, rejects duplicate timestamps and checks track/frame, release, look/pass, selected polarization, bandwidth, carrier and dithered configuration.

The primary canonical grid remains **EPSG:32645, 2400 × 2400 pixels, 10 m spacing**. Selected sources extract directly onto that exact grid without reprojection. The implementation also supports reprojection of physically compatible sources onto the canonical grid when needed, using bilinear interpolation and a contributing-pixel validity mask. Its synthetic tests verify that invalid source contributors remain excluded. Reprojection does not override physical compatibility checks.

Native power must be finite and positive, source mask values 0 and 255 are excluded, and number of looks must be finite and positive. The existing 3 × 3 validity-safe median preprocessing is retained. Each processed observation records valid fraction, acquisition metadata, source size, native-window checksum, processed-array checksum, and alignment method. Source coordinate arrays and granule identity are checked during extraction.

The [GDAL COG driver](https://gdal.org/en/stable/drivers/raster/cog.html) writes tiled, compressed GeoTIFFs with internal overviews. Continuous overviews use averaging; categorical masks/counts use nearest-neighbor. Measurements always use full-resolution native values, not reduced previews or overviews. [Apache Arrow](https://arrow.apache.org/docs/python/parquet) writes the explicit typed `zone_timeseries.parquet` table; validation compares its rows directly with the JSON measurements.

Grid equality and coordinate consistency have been checked. Independent subpixel image-registration accuracy has not been established.

## Successive changes and score calibration

For each consecutive pair:

```text
Δ = after_dB − before_dB
MAD = median(abs(Δ − median(Δ)))
Z = (Δ − median(Δ)) / (1.4826 × MAD + 0.000001)
raw candidate = abs(Z) > τ
```

The strict `>` rule follows the time-series specification. Zero/near-zero robust spread is flagged; it does not fabricate candidate detections. Cleanup repeats the existing one-iteration four-connected opening and 100-native-pixel minimum.

A validation-derived cutoff cannot be claimed because no appropriate labeled calibration set has been provided. The current `τ = 3` is inherited from the existing multiplier solely as an **UNCALIBRATED exploratory setting**. It is not a new optimized threshold and does not establish statistical significance. Calibration metadata is serialized and displayed prominently. A future threshold-validation JSON must describe the metric `centered_successive_delta_mad_z`, provide a numeric cutoff supported by actual validation, include `calibration_status: VALIDATED`, and identify its validation source. Setting a label alone is not independent scientific validation.

The legacy nominal method is centered on zero signed change; this extension centers the score on each successive distribution median. These are different rules, so their candidate counts/areas can differ. All **73 historical analysis artifacts were verified byte-identical** to the archived pre-implementation snapshot. The older nominal results remain 0.0195, 0.7949 and 0.0000 km².

New successive centered-score measurements:

| Interval | Days | Retained candidate area km² | Regions | Median absolute ΔdB over valid pixels |
| --- | ---: | ---: | ---: | ---: |
| 2026-08-19 → 2026-08-31 | 12 | 0.0199 | 1 | 0.9496 |
| 2026-08-31 → 2026-09-12 | 12 | 0.0000 | 0 | 0.8995 |

Candidate-area variation is not a validated geographic spreading rate. Exact onset cannot be resolved between repeat observations.

## Zone tracking, persistence and recovery

The retained masks from successive intervals are combined into a connected spatial union. Each connected footprint receives a deterministic zone ID, which remains fixed across the dates of the same run/reproduction. Touching or splitting components share that union zone; this is not independent moving-object lineage. Extending a series and changing its union geometry can change IDs, so cross-version lineage is not claimed.

Two notions are kept distinct:

1. **Transition frequency:** repeated score detections in successive differences. The specification's fixed `(n−1)` denominator is used only where every interval is valid. Partially observed pixels are nodata in the strict map; a separate available-interval map and count raster expose missing coverage. Both raw-score and cleaned-candidate maps are exported.
2. **Displacement from baseline:** mean signed `B_t − B_first` on the same pixels valid in every observation of the tracked zone. This can remain large even when the next successive interval has no retained candidate.

Recovery uses `1 − abs(S_t)/(abs(S_peak)+epsilon)`, clamped to [0,1], where `S` is the fixed-support zone mean signed displacement. Values are reported only at or after the observed peak. The baseline/pre-peak date is not mislabeled as recovered. Zero disturbance, missing support or insufficient common coverage returns null/nodata. At least 90% common zone coverage is required. Mean absolute displacement is also saved because signed averages can cancel opposing changes.

The 20% and 80% status bands are transparent descriptive bands, not validated ecosystem or infrastructure recovery classes. The August 26 reference marker does not attribute any observed radar change to that event.

Current zone: **NP-Z4ab9a6118de9**.

- Fixed footprint: **0.0199 km²**, **199 native pixels**.
- First-detection bracket: **August 19 → August 31**.
- Transition frequency: **1/2 = 0.50**.
- Peak mean signed displacement: **-7.5263 dB** on August 31.
- Mean signed displacement on September 12: **-7.0766 dB**.
- Latest return-toward-baseline metric: **5.97%**.
- Descriptive status: **REMAINS_NEAR_OBSERVED_PEAK**.
- Cause: **UNVERIFIED**. The previous external-source review used different nominal-region geometry and is not silently transferred to this new zone.

The zero later-interval mask therefore does not mean the earlier disturbance disappeared.

## Viewer and API

Start the existing standard-library server, then open [the time-series viewer](http://127.0.0.1:8000/timeseries.html). A new **Time series** link appears in the main app. The viewer provides date buttons and a slider, observation maps, successive candidate overlays, persistence/recovery layers, three measurement charts, a zone recovery chart, zone selection/zoom, granule provenance, source-audit decisions and downloadable evidence. No external page assets are required.

```http
GET /api/cases/nepal_case_01/observations
GET /api/cases/nepal_case_01/timeline
GET /api/cases/nepal_case_01/zones
GET /api/zones/NP-Z4ab9a6118de9
```

The case zones endpoint returns geographic GeoJSON. An individual-zone request returns its zone summary and observation rows. Missing/invalid IDs return 404. Legacy endpoints retain their behavior.

The compact time-series viewer case is approximately **2 MB**. Full analytical COGs occupy approximately **161 MB** locally and are excluded from Git by the existing raster rules. Standard Python suffices to view the shipped assets; reprocessing additionally requires the scientific environment and PyArrow.

## New and changed files

| File | Purpose |
| --- | --- |
| `config.timeseries.json` | Discovery, canonical AOI reference, validity and calibration settings. |
| `src/ingest/timeseries.py` | Local discovery, physical compatibility, duplicate exclusion and group audit. |
| `src/ingest/inspect_h5.py` | Fixes audit of committed/named datatypes in quad-polarization HDF5 products. |
| `src/compute/time_series.py` | Centered scores, strict/available transition frequency, fixed zones and baseline recovery. |
| `src/compute/timeseries_pipeline.py` | Native extraction/reprojection, real COGs, manifests, vector and Parquet exports. |
| `src/compute/validate_timeseries.py` | Pixel-based reproduction, geometry/area, Parquet and public-copy validation. |
| `src/api/app.py` | Observation/timeline/zone APIs and individual-zone details. |
| `web/timeseries.html`, `.js`, `.css` | Separate local timeline and evidence viewer. |
| `web/index.html` | Navigation link from the original app. |
| `tests/test_time_series.py`, `tests/test_timeseries_api.py` | Scientific edge cases, compatibility, COG/reprojection and HTTP-handler tests. |
| `requirements.txt` | Adds pinned PyArrow 26.0.0. |
| `Makefile` | Adds `timeseries` and `validate-timeseries` targets. |
| `README.md`, `docs/QA.json`, this document | Updated usage, scientific limits and verification status. |
| `docs/reports/imp02-legacy-before.json` | Fixed historical-byte snapshot for preservation verification. |

Artifacts live in `data/derived/nepal_case_01/timeseries/`; compact JSON/GeoJSON/Parquet/PNG/WebP copies live in `web/public/cases/nepal_case_01/timeseries/`:

```text
observations.json / timeline.json / source_audit.json
nisar_t1.tif / nisar_t2.tif / nisar_t3.tif
change_t1_t2.tif / change_t2_t3.tif
score_t1_t2.tif / score_t2_t3.tif
candidate_t1_t2.tif / candidate_t2_t3.tif
persistence.tif / persistence_available.tif
candidate_persistence.tif / valid_interval_count.tif
zone_labels.tif / recovery.tif
zones.json / zones.geojson / zones_display.json
zone_timeseries.json / zone_timeseries.parquet
local observation previews and temporal overlays
```

## Verification and remaining work

**73 automated tests pass.** The time-series validator checks UTC ordering; physically consistent selected observations; canonical grid/COG structure; processed fingerprints; signed differences and centered scores; nodata; cleanup/area/counts; valid persistence denominators; fixed zone IDs/support; recovery; projected vector area; Parquet/JSON agreement; and byte-identical public copies. The historical-byte check confirms all 73 earlier artifacts remain unchanged. Existing nominal export validation also passes. Python compilation and both JavaScript syntax checks pass.

HTTP-handler tests run without sockets, parsing actual request bytes and exercising responses. Real generated artifact requests checked the four API routes, the new HTML/JS/CSS, all three observation previews and the Parquet download. Static checks resolve all 28 literal JavaScript UI IDs. These are automated handler/static checks, not an interactive browser or physical disconnected rehearsal.

The existing browser policy block was not bypassed. Interactive visual/responsive QA and the physically disconnected rehearsal remain pending. No Wi-Fi/Ethernet-disconnected result is invented, and no publication or competition tag was performed in this implementation.

To extend the series, obtain additional **matching track 98/frame 16, ascending, HH frequency-A, 40 MHz / 1.239 GHz, consistent release/configuration** observations and rerun discovery. A different coherent series can be selected through `anchor_source`, but needs at least three distinct compatible acquisitions and a canonical AOI it covers. Calibration needs actual independent labeled or appropriate held-out validation evidence.

Current Python source SHA-256:

```text
026a8e126a1c72cff44dd668b23daab31f174d56eacf9ec6eda1737c3538710a
```

Software versions: `{"gdal": "3.12.4", "h5py": "3.16.0", "numpy": "2.5.3", "pyarrow": "26.0.0", "pyproj": "3.8.0", "python": "3.14.4", "rasterio": "1.5.1", "scipy": "1.18.1", "shapely": "2.1.2"}`.

## Reproduce and view

```bash
cd "/home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1"
make setup                 # first-time science dependencies only
make timeseries
make test
make validate-timeseries
OFFLINE=1 python3 -m src.api.app
```

Open `http://127.0.0.1:8000/timeseries.html`. If a server was already running before these changes, stop it with Ctrl+C and restart it to load the new API routes. To compare the exact archived historical bytes as part of this implementation audit:

```bash
.venv/bin/python -m src.compute.validate_timeseries --check-historical
```

That optional historical comparison is intended for the archived implementation state. A deliberate later regeneration of legacy outputs can update provenance bytes while preserving numerical results, so it is separate from normal reproducibility validation.
