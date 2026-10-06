# TerraPulse — Full Project Progress and Verification Report

**Report generated:** 2026-09-30 21:56:12 +06 (UTC+06:00)  
**Team:** DevAtMad  
**Challenge:** Dancing with the SARs  
**Case:** Nepal Himalayan Surface-Change Investigation  
**Workspace:** `/home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1`

## 1. Current project status

The **local implementation is complete and verified for the supplied Nepal case**. TerraPulse now converts real NISAR HDF5 measurements into an offline interactive surface-change investigation. Six source products have been audited, three repeat observations identified, and all three temporal comparisons computed and exported.

Fresh verification for this report: **27 automated tests passed, zero failed**, and **all three exported comparisons validated**. Python compilation and JavaScript syntax checks passed. The current Python source-code fingerprint matches the fingerprint stored with the outputs.

This completes the local processing/demo milestone. It does not establish independently validated disaster causes or publication/submission readiness. NISAR is **PROVISIONAL** and every causal interpretation remains **UNVERIFIED**.

### Milestones

| Workstream | Status | Evidence |
| --- | --- | --- |
| Raw audit | Complete | All six HDF5s inventoried: actual schema, attributes, timestamps, coordinates and fill values. |
| Repeat observations | Complete | Three distinct dates; same-date releases excluded from temporal mixing. |
| Comparability | PASS | All three selected pairs share compatible geometry, processing version and native grid; >99% footprint overlap. |
| Fixed analysis area | Complete | 24 km square around Kathmandu Valley/northern hills; chosen before inspecting change. |
| Deterministic science | Complete | Quality masking, power-to-dB, median filter, signed change, MAD cutoff, cleanup, connected regions and projected area. |
| Scientific outputs | Complete | All three comparisons have real rasters, region statistics, GeoJSON, sensitivity and provenance. |
| Science tests | PASS | 27 cases passed in the fresh run for this report. |
| Export validation | PASS | All three saved comparisons validate against raster/mask/region geometry. |
| Interactive viewer | Complete; previously verified | Before/after/swipe, scan reveal, overlay, date-pair selector, region inspection, zoom and methods. |
| Responsive layout | PASS in original QA | Desktop 1366 × 900 and phone 390 × 844, without horizontal overflow. |
| Offline asset loading | PASS in original QA | All observed page resources loaded from localhost; no CDN/font/basemap dependency. |
| Documentation/license | Complete for local milestone | Methods, datasets, limitations, validation, AI-use, runbook and Apache-2.0 code license. |
| Physical disconnected rehearsal | Not performed | Machine Wi-Fi was not turned off. |
| Independent causal validation | Not performed | All causes remain UNVERIFIED; no confirmed flood/landslide claim. |
| Public repository / submission | Not performed | No upload or competition submission was made. |

## 2. How the project looks now

The viewer is a dark earth-observation workspace with muted green panels and yellow scan/highlight accents. One real Nepal case is enabled.

| Area | Current features |
| --- | --- |
| Header | TerraPulse branding, local-data context, NISAR PROVISIONAL labels and Methodology. |
| Left controls | Kathmandu Valley case, three dates, all three date pairs, Before/Swipe/After controls, overlay toggle and SCAN REGION. |
| Central radar viewer | Real local radar previews, draggable swipe handle, north indicator, scale bar, zoom/reset controls and computed change overlay. |
| Summary strip | Common valid analysis area, candidate change area and retained region count. |
| Evidence panel | Dates, repeat interval, selected-region statistics, histogram, threshold rule, sensitivity and cause-UNVERIFIED status. |
| Region interaction | Select actual map polygons or ranked region buttons; center/zoom on a selected region. |
| Methods dialog | Granule IDs, exact source path, polarization, AOI/grid, preprocessing, thresholds, cleanup, area method, alternatives, versions and limits. |
| Zero-result state | Aug 31 → Sep 12 displays no retained nominal candidates; it does not claim no real change occurred. |
| Downloads | Selected-pair evidence JSON; geographic GeoJSON available in methods. |

The yellow radar sweep reveals **saved deterministic evidence**. It is presentation, not live AI inference. Yellow marks increased backscatter; blue marks decreased backscatter. Quantities come from native-resolution processing, not display-image pixels.

### Saved interface screenshot

The original browser-verification screenshot shows Aug 19 → Sep 12: **0.7949 km² and 30 candidate regions**. It was not recaptured during this reporting turn.

![TerraPulse verified demo](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/docs/demo.png>)

## 3. Dataset audit

Source: **NASA–ISRO NISAR L2 GCOV PROVISIONAL**, collection `NISAR_L2_GCOV_PROVISIONAL_V1`, product DOI `10.5067/NIL2GCOV-P1` from source metadata.

| Local HDF5 | Acquisition date, UTC | Product version | Release | Selected |
| --- | --- | --- | --- | --- |
| `aug19(1).h5` | 2026-08-19 | 1.0.12 | X05026 | No: alternate same-date release |
| `aug19.h5` | 2026-08-19 | 1.0.11 | P05023 | Yes |
| `aug31(1).h5` | 2026-08-31 | 1.0.12 | X05026 | No: alternate same-date release |
| `aug31.h5` | 2026-08-31 | 1.0.11 | P05023 | Yes |
| `sept12(1).h5` | 2026-09-12 | 1.0.12 | X05026 | No: alternate same-date release |
| `sept12.h5` | 2026-09-12 | 1.0.11 | P05023 | Yes |

The `(1)` products are alternate processing releases of the same acquisitions, not extra dates or adjacent coverage. The consistent **P05023 / 1.0.11** series is used. Science dataset paths/grids agree between variants; processing metadata and some string widths differ. No same-date or mixed-version temporal comparison is used.

Raw filenames and locations are preserved. The archive is retained without redundant extraction. All six HDF5 sizes still match the saved audit. Byte-size agreement is not a whole-file checksum.

### Verified measurement and geometry

- Track **98**, frame **16**, ascending and left-looking.
- Term **HHHH / HH polarization / frequency A**, real diagonal covariance power.
- Exact path: `/science/LSAR/GCOV/grids/frequencyA/HHHH`.
- Source shape **33840 × 34488**.
- Native CRS **EPSG:32645**, spacing **10 m × 10 m**, with y spacing −10 m.
- AOI: requested center **85.33° E, 27.80° N**, **24 km × 24 km**, snapped to **2400 × 2400 pixels**.
- Fixed geographic extent was chosen before inspecting change, for context and bounded processing.
- No reprojection or mosaicking is needed for this set. Incompatible grids are rejected.

### Accepted repeat pairs

Overlap is intersection area divided by the smaller footprint area, after projecting footprints to UTM.

| Pair | Separation, days | Footprint overlap | Status |
| --- | --- | --- | --- |
| aug19.h5 → aug31.h5 | 12 | 99.8950% | PASS |
| aug19.h5 → sept12.h5 | 24 | 99.8918% | PASS |
| aug31.h5 → sept12.h5 | 12 | 99.2782% | PASS |

### Source quality counts

| Source | AOI pixels | Valid after source quality gates | Valid after median filtering |
| --- | --- | --- | --- |
| aug19.h5 | 5,760,000 | 5,749,602 | 5,735,334 |
| aug31.h5 | 5,760,000 | 5,672,910 | 5,658,643 |
| sept12.h5 | 5,760,000 | 5,492,956 | 5,478,640 |

Median-filter outputs require every contributing source pixel to be valid. Common valid coverage is then calculated independently per pair.

## 4. Implemented scientific workflow

```text
Actual HDF5 audit → repeat-date / geometry / version / overlap checks
→ fixed native-grid AOI extraction
→ finite positive power, valid source mask and positive number of looks
→ 10 × log10(real diagonal gamma-0 power)
→ nodata-safe 3 × 3 median per observation
→ common finite-pixel mask
→ signed ΔdB = after − before
→ robust threshold → minimal opening → connected-region size filtering
→ native-pixel areas and regional statistics
→ sensitivity, geographic boundaries, local previews and evidence JSON
```

| Parameter | Current value |
| --- | --- |
| Metric | Signed after-minus-before dB change |
| Robust spread | 1.4826 × median(abs(ΔdB − median(ΔdB))) |
| Nominal detection rule | abs(ΔdB) ≥ 3.0 × robust spread |
| Threshold center | Zero physical change; measured distribution median is recorded, not subtracted. |
| Median preprocessing | 3 × 3, with strict all-valid contributing neighborhoods |
| Opening | One iteration, four-connected 3 × 3 cross |
| Minimum region | 100 native pixels |
| Connectivity | Four-connected |
| Ranking | Area descending, then absolute median change descending |
| Area method | Absolute affine determinant × CRS linear-unit factors |
| Actual pixel grid area | 100 m² = 0.0001 km² |
| Sensitivity | Cutoff −10%, nominal, +10%; identical cleanup |
| Other candidates reported | MAD multipliers 2.0, 2.5 and 3.0 |

Area is projected grid area, not sloped terrain surface area. Geographic-degree grids are rejected rather than assumed to have constant area. Display previews use shared contrast and at most 1200 pixels per side; native rasters determine measurements.

### Preserved baseline

The first unsmoothed conservative run retained **zero regions**. It remains in `data/derived/baseline_unsmoothed.json`. The final small median filter reduces isolated SAR speckle and is explicitly recorded. No disaster classification or desired event shape was manufactured.

## 5. Computed results

These are **threshold-dependent radar-change candidate areas**, not confirmed disaster-impact areas.

| Comparison, UTC dates | Common valid km² | Nominal cutoff dB | Candidate km² | Regions |
| --- | --- | --- | --- | --- |
| 2026-08-19 → 2026-08-31 | 565.8349 | 4.1190 | 0.0195 | 1 |
| 2026-08-19 → 2026-09-12 | 547.8402 | 4.3204 | 0.7949 | 30 |
| 2026-08-31 → 2026-09-12 | 547.8383 | 3.9954 | 0.0000 | 0 |

### Threshold sensitivity

Sensitivity is not statistical confidence or classification accuracy.

| Comparison | Area at −10% cutoff, km² | Nominal area, km² | Area at +10% cutoff, km² |
| --- | --- | --- | --- |
| 2026-08-19 → 2026-08-31 | 0.0301 | 0.0195 | 0.0178 |
| 2026-08-19 → 2026-09-12 | 1.5218 | 0.7949 | 0.4174 |
| 2026-08-31 → 2026-09-12 | 0.0111 | 0.0000 | 0.0000 |

### Alternative MAD thresholds

The final nominal method uses multiplier 3.0. Other rows document parameter sensitivity.

| Comparison | MAD multiplier | Cutoff dB | Candidate km² | Regions |
| --- | --- | --- | --- | --- |
| 2026-08-19 → 2026-08-31 | 2.0 | 2.7460 | 0.3666 | 18 |
| 2026-08-19 → 2026-08-31 | 2.5 | 3.4325 | 0.0569 | 4 |
| 2026-08-19 → 2026-08-31 | 3.0 | 4.1190 | 0.0195 | 1 |
| 2026-08-19 → 2026-09-12 | 2.0 | 2.8803 | 4.2159 | 100 |
| 2026-08-19 → 2026-09-12 | 2.5 | 3.6003 | 2.0201 | 52 |
| 2026-08-19 → 2026-09-12 | 3.0 | 4.3204 | 0.7949 | 30 |
| 2026-08-31 → 2026-09-12 | 2.0 | 2.6636 | 0.2798 | 17 |
| 2026-08-31 → 2026-09-12 | 2.5 | 3.3295 | 0.0197 | 1 |
| 2026-08-31 → 2026-09-12 | 3.0 | 3.9954 | 0.0000 | 0 |

## 6. All automated test cases that passed

Fresh `make test` result: **27 passed in 0.57 s**, no failures or skips. Parameterized cases are listed separately. Actual test source: `tests/test_science.py`.

| # | Exact collected test name | Behavior checked | Result |
| --- | --- | --- | --- |
| 1 | `test_area_100_thirty_metre_pixels` | 100 pixels of 30 m × 30 m yield exactly 0.09 km² within tolerance. | PASS |
| 2 | `test_rotated_area_uses_determinant` | Rotated/sheared affine geometry uses the determinant. | PASS |
| 3 | `test_geographic_area_rejected` | Longitude/latitude grids are rejected for projected-area calculation. | PASS |
| 4 | `test_identical_arrays_zero_change` | Identical observations produce zero change. | PASS |
| 5 | `test_known_signed_delta` | Known increases/decreases produce correct signed differences. | PASS |
| 6 | `test_nodata_not_change` | NaN/Inf never become false change candidates. | PASS |
| 7 | `test_unaligned_arrays_rejected` | Mismatched array shapes are rejected. | PASS |
| 8 | `test_components_and_area` | Small regions are removed; retained areas and statistics match known geometry. | PASS |
| 9 | `test_cleanup_never_fills_invalid` | Cleanup cannot turn invalid pixels into candidates. | PASS |
| 10 | `test_no_change_no_regions` | Zero change produces no connected candidates. | PASS |
| 11 | `test_mad_cutoff` | The configured robust MAD formula gives the expected cutoff. | PASS |
| 12 | `test_zero_mad_requires_explicit_threshold` | Zero MAD requires an explicit absolute-dB cutoff. | PASS |
| 13 | `test_bad_threshold_rejected[0]` | Invalid threshold parameter is rejected; separate zero, negative and NaN cases. | PASS |
| 14 | `test_bad_threshold_rejected[-1]` | Invalid threshold parameter is rejected; separate zero, negative and NaN cases. | PASS |
| 15 | `test_bad_threshold_rejected[nan]` | Invalid threshold parameter is rejected; separate zero, negative and NaN cases. | PASS |
| 16 | `test_sensitivity_uses_same_cleanup` | Sensitivity uses the same cleanup and yields expected areas. | PASS |
| 17 | `test_date_nanoseconds_and_utc` | Nanosecond source dates are interpreted with UTC semantics. | PASS |
| 18 | `test_same_observation_versions_not_temporal` | Same-date processing variants cannot form a temporal comparison. | PASS |
| 19 | `test_real_repeat_pair` | Actual Aug 19/Aug 31 metadata passes repeat-date and overlap checks. | PASS |
| 20 | `test_incompatible_geometry_rejected[track-1]` | The altered track, orbit direction, product version or spacing is rejected. | PASS |
| 21 | `test_incompatible_geometry_rejected[orbit_direction-Descending]` | The altered track, orbit direction, product version or spacing is rejected. | PASS |
| 22 | `test_incompatible_geometry_rejected[product_version-other]` | The altered track, orbit direction, product version or spacing is rejected. | PASS |
| 23 | `test_incompatible_geometry_rejected[spacing-value3]` | The altered track, orbit direction, product version or spacing is rejected. | PASS |
| 24 | `test_extract_masks_and_converts_power` | Synthetic HDF5 extraction masks invalid samples and converts valid power to dB. | PASS |
| 25 | `test_median_removes_isolated_speckle` | Median filtering removes an isolated spike and protects raster edges. | PASS |
| 26 | `test_median_does_not_leak_nodata` | Invalid neighborhoods cannot leak through preprocessing. | PASS |
| 27 | `test_histogram_zero_is_centered_and_preserves_pixel_count` | Histogram zero is centered and counts preserve finite pixels. | PASS |

These numerical/ingestion tests include synthetic arrays/HDF5 and saved real metadata. They do not prove independent event-classification accuracy, exhaustive test coverage or subpixel image-registration accuracy.

### Fresh terminal output

```text
$ make test
.venv/bin/python -m pytest -q
...........................                                              [100%]
27 passed in 0.57s

$ make validate
.venv/bin/python -m src.compute.validate
PASS t1_t2: raster, mask, region statistics and geographic polygons agree (0.0195 km²)
PASS t1_t3: raster, mask, region statistics and geographic polygons agree (0.7949 km²)
PASS t2_t3: raster, mask, region statistics and geographic polygons agree (0.0000 km²)
All exported comparisons validated.
```

## 7. Export validation and additional fresh checks

`make validate` passed for all three comparisons:

| Check | Result |
| --- | --- |
| Mask grid and CRS agree with saved change raster | PASS |
| Summary candidate area agrees with actual retained pixels | PASS |
| Invalid pixels are never classified as candidate change | PASS |
| Mask nodata matches invalid change pixels | PASS |
| Saved mask reproduces exactly from saved change and processing parameters | PASS |
| Evidence region count agrees with regional records | PASS |
| Summed region areas agree with total candidate area | PASS |
| GeoJSON feature count agrees with retained regions | PASS |
| Projected geographic-vector area agrees with raster area within coordinate-rounding tolerance | PASS |
| Region polygons are geometrically valid | PASS |
| Every exported causal status remains UNVERIFIED | PASS |

| Other check | Fresh result |
| --- | --- |
| python -m compileall -q src | PASS: Python modules compile |
| node --check web/app.js | PASS: JavaScript syntax valid |
| Current/exported Python source-code fingerprint | PASS: exact match |
| Six raw source sizes versus audit | PASS: unchanged byte sizes |
| Saved screenshot | Present |
| Unsmoothed baseline | Present |

Source-window SHA-256 values cover the extracted native power, quality mask and number-of-looks bytes. They are **not** checksums of the complete multi-GB source files. Ingestion also checks identity, layer shape and coordinates/CRS against audited metadata.

## 8. Browser, responsive and offline verification

The following results are the **existing browser-verification record in `docs/QA.json`**, not new browser tests in this reporting turn. Scientific/export/syntax/fingerprint checks above were refreshed for this report.

| Browser behavior | Recorded result |
| --- | --- |
| Before/after view | PASS |
| Slider enabled only in swipe mode | PASS |
| Direct drag of swipe handle | PASS |
| Scan reveal animation | PASS |
| Actual area/statistics | PASS |
| All three acquisition pair selections | PASS |
| Actual geographic-region polygon selection | PASS |
| Region-centered zoom | PASS |
| Overlay toggle | PASS |
| Methodology dialog open/close | PASS |
| Zero-region state | PASS |

| Environment check | Recorded result |
| --- | --- |
| Browser | Codex in-app browser |
| Console | 0 errors; 0 warnings |
| Desktop | 1366 × 900; no horizontal overflow |
| Phone | 390 × 844; no horizontal overflow |
| Radar/overlay loading | PASS |
| Observed asset sources | All localhost; 0 external page asset requests |
| Runtime | OFFLINE=1, local assets only |
| External CDN / font / basemap dependency | None |
| Earthdata login / runtime API key | Not required |
| Wi-Fi physically disabled | No: not tested |

Online NASA/ASF links are optional references activated on click. They are not needed for the local demo. A physical disconnected rehearsal remains a separate user-operated preparation step; machine networking settings were not changed.

## 9. Current project structure

```text
NEPALv1/
├── six original .h5 files and aug19.zip
├── IMPLEMENTATION.md / SKILL.md
├── README.md / PROJECT_PROGRESS.md / LICENSE
├── Makefile / config.json / pyproject.toml / requirements.txt
├── .env.example / .gitignore
├── src/
│   ├── ingest/
│   │   ├── inspect_h5.py           complete actual schema audit
│   │   ├── metadata.py             inventory and pair checks
│   │   └── extract_gcov.py         window extraction and source checks
│   ├── compute/
│   │   ├── align.py                compatible grids / common mask
│   │   ├── preprocess.py           validity-safe median filter
│   │   ├── change.py               delta and histogram/statistics
│   │   ├── threshold.py            configurable MAD/absolute cutoff
│   │   ├── regions.py              cleanup, regions and ranking
│   │   ├── area.py                 real projected pixel geometry
│   │   ├── uncertainty.py          cutoff sensitivity
│   │   ├── pipeline.py             complete scientific orchestration
│   │   └── validate.py             exported-data consistency
│   ├── export/artifacts.py         rasters, previews, boundaries, JSON
│   └── api/app.py                  local standard-library server
├── tests/test_science.py           27 collected cases
├── data/derived/
│   ├── audit.json / audit.txt / inventory.json
│   ├── baseline_unsmoothed.json
│   └── nepal_case_01/
│       ├── native/processed observations and previews
│       ├── t1_t2/ / t1_t3/ / t2_t3/
│       └── metadata, AOI, config, manifest and primary-pair aliases
├── web/
│   ├── index.html / styles.css / app.js
│   └── public/cases/nepal_case_01/  compact local demo assets
└── docs/
    ├── DATASETS.md / METHODOLOGY.md / VALIDATION.md
    ├── LIMITATIONS.md / AI_USE.md / DEMO_RUNBOOK.md
    ├── QA.json / RESULTS.json / demo.png
    └── reports/progress-verification.json
```

The repository uses the smallest structure supporting this verified case rather than every optional file in the plan. The server exposes local JSON endpoints without requiring FastAPI.

## 10. Artifacts and reports available now


| Output group | Files | Size |
| --- | --- | --- |
| Full analytical case | 53 | 211.56 MiB |
| Compact public demo case | 34 | 16.02 MiB |


Each comparison has `change_raw.tif`, `change_mask.tif`, `region_labels.tif`, `change_regions.geojson`, `regions_display.json`, change previews, `overlay.png`, `evidence.json` and `methodology.json`.

Case-level outputs include the three native unfiltered dB rasters, three processed rasters, shared-contrast previews, `aoi.geojson`, `metadata.json`, `manifest.json` and configuration. Top-level before/after/evidence aliases refer to the primary Aug 19 → Aug 31 pair. No raw HDF5 is loaded by the browser.

### Supporting reports

- [README.md](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/README.md>): project overview and operation.
- [DATASETS.md](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/docs/DATASETS.md>): granule IDs, dates, release selection and actual layer paths.
- [METHODOLOGY.md](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/docs/METHODOLOGY.md>): implemented science and preprocessing.
- [VALIDATION.md](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/docs/VALIDATION.md>): input, numerical and interpretation checks.
- [LIMITATIONS.md](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/docs/LIMITATIONS.md>): provisional status, ambiguity and scope.
- [AI_USE.md](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/docs/AI_USE.md>): AI assistance and deterministic computation.
- [DEMO_RUNBOOK.md](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/docs/DEMO_RUNBOOK.md>): demo/rehearsal sequence.
- [QA.json](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/docs/QA.json>): original browser, responsive and offline verification record.
- [RESULTS.json](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/docs/RESULTS.json>): saved numerical comparison summaries.
- [progress-verification.json](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/docs/reports/progress-verification.json>): fresh verification snapshot supporting this report.
- [test_science.py](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/tests/test_science.py>): actual test implementation.


## 11. Software versions and provenance

| Component | Exported version |
| --- | --- |
| terrapulse | 1.0.0 |
| python | 3.14.4 |
| numpy | 2.5.3 |
| scipy | 1.18.1 |
| h5py | 3.16.0 |
| rasterio | 1.5.1 |
| pyproj | 3.8.0 |
| shapely | 2.1.2 |
| pillow | 12.3.0 |

Current/exported Python-source SHA-256:

```text
d5376750574d465ec875fc9b1013da8125080b0639097a6748a78414c8335157
```

Evidence preserves original source filenames and internal granule IDs, UTC timestamps, exact HDF5 path, product/specification versions, track/frame/orbit/look/pass, DOI, source sizes, actual AOI/window/grid, validity counts, window checksums, preprocessing, thresholds, cleanup, measured regions, sensitivity, software versions and validation status.

## 12. Run and reproduce

From the project folder:

```bash
make demo
```

Open **http://127.0.0.1:8000/**. The exact command is:

```bash
OFFLINE=1 .venv/bin/python -m src.api.app
```

The already-shipped viewer can run with standard Python without installing the scientific stack:

```bash
OFFLINE=1 python3 -m src.api.app
```

The server binds to loopback; `--port 8001` can select another port. This report does not independently verify that the server is still active at the moment the report is read.

To reproduce the science:

```bash
make setup       # initial dependency download requires internet
make inspect     # actual source schema and metadata audit
make test        # all numerical/ingestion tests
make process     # all three comparisons and viewer assets
make validate    # saved raster/mask/region/vector checks
```

Audit again after changing raw files; process again after changing configuration. Scientific values are computed by ordinary code, with no LLM runtime or generated causal classification. Code assistance is documented in AI_USE.md.

## 13. Remaining work and limitations

| Item | Current state / next step |
| --- | --- |
| Independent causal validation | Not done. Independent optical/event/ground evidence is needed before confirmed flood or landslide language. |
| Physical offline rehearsal | Not done. Manually disable Wi-Fi and repeat the runbook. |
| Public event-specific framing | Neutral surface-change framing is implemented; stronger claims need evidence and review. |
| Public repository | Not uploaded; review sharing scope and exclusions before publication. |
| Competition submission | Not submitted; submission material and event readiness remain separate steps. |
| Arbitrary/global data operation | Outside this case; live global acquisition, automatic reprojection and neighboring-frame mosaicking are not implemented. |
| Formal performance assessment | No independent classification accuracy, calibrated confidence interval, registration accuracy or operational certification is claimed. |

NISAR remains **PROVISIONAL**. Radar changes can reflect moisture, vegetation, terrain, speckle or processing effects. Median preprocessing introduces local dependence and suppresses small changes. Cutoffs and minimum-region filtering influence areas, as the sensitivity tables show. Projected area is not sloped terrain area. Zero retained regions does not prove no change.

The completed milestone is a reproducible local **surface-change investigation demo** with real measurements, tested outputs, visible uncertainty and source provenance. Independent causal validation, a physical offline rehearsal and external publication/submission remain unfinished workstreams.

## 14. Next-phase update — 1 October 2026

The earlier sections record the first implementation milestone. The next phase now adds fixed-pixel temporal analysis for all 30 August 19 → September 12 regions (29 descriptive cumulative-consistent, one early-dominant), +10% threshold robust cores for all three pairs (0.0178, 0.4174, 0.0000 km²), and a top-ten independent source screen. The archived UNOSAT/UNESCO mapped flood polygons intersect none of the 30 nominal candidates, so every cause remains **UNVERIFIED**. Sentinel-2 catalog metadata was screened, but no optical pixels were validated. The research uses no Chinese government or agency source.

The viewer now defaults to the 24-day pair and exposes nominal/robust overlay, temporal class, source-review note and the zero-region explanation. `make process` reproduces the new outputs; `make test` passes 38 tests and `make validate` checks nominal preservation, robust geometry/area, temporal geometry and source checksum. Python compilation and JavaScript syntax checks pass. The current source fingerprint is saved in pair evidence.

The updated viewer has **not** passed an interactive browser test because the browser tool blocked access to the local page under its URL policy. The physical Wi-Fi/Ethernet-disabled rehearsal also remains pending user action, as recorded in `docs/QA.json`. The empty `.git` directory is not an initialized repository (`git status` fails), so no competition tag or publication was performed. The science version should not be marked frozen until those checks and repository setup are complete.
