# TerraPulse — Complete Change and Progress Report

**Report date:** 2026-10-01 21:28:46 +0600 (Asia/Dhaka)  
**Team:** DevAtMad  
**Challenge:** Dancing with the SARs  
**Case:** Nepal Himalayan Surface-Change Investigation  
**Workspace:** `/home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1`

## 1. Current position

TerraPulse has a working local implementation that audits the supplied NISAR HDF5 products, processes three repeat observations, exports measurable radar-change candidates, and displays saved evidence in an offline viewer. The second implementation phase adds temporal consistency, stricter-threshold robust cores, independent-source review, and clearer judge-facing evidence.

The last recorded implementation verification passed **38 tests**, validated all **three** exported comparisons and the new evidence layers, and passed Python compilation and JavaScript syntax checks. During preparation of this report, the current Python source fingerprint was checked again and matches all three pair evidence files.

The previous conversational estimate was **approximately 90% complete**, with approximately 10% of this implementation phase remaining. This is a rough work estimate, not a measured checklist percentage. The remaining phase work is interactive verification of the updated viewer, an actual physically disconnected rehearsal, and repository/science-freeze finalization. Repository publication and competition submission are additional actions that have not been performed.

**Scientific interpretation:** NISAR products remain **PROVISIONAL**. Every candidate's cause remains **UNVERIFIED**. The measurements establish threshold-dependent radar backscatter changes; they do not establish confirmed flood or landslide impact.

This report consolidates the first milestone and the next-phase changes. The older [PROJECT_PROGRESS.md](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/PROJECT_PROGRESS.md>) is retained as a historical record. This reporting task does not rerun the expensive HDF5 pipeline or repeat browser testing.

## 2. Work completed across both phases

| Workstream | Current state | Evidence or result |
| --- | --- | --- |
| Actual HDF5 schema and metadata audit | Complete | Six supplied HDF5 products inventoried; real paths, dimensions, attributes, fill values and dates inspected. |
| Repeat-observation selection | Complete | Three distinct dates selected from consistent P05023 / 1.0.11 products. |
| Geometry and comparability checks | Complete | Shared track/frame, pass/look, product release and exact native grid; all pair footprint overlaps exceed 99%. |
| Fixed area of investigation | Complete | 24 km square around Kathmandu Valley and northern hills; 2400 × 2400 native pixels. |
| Deterministic processing | Complete | Quality masking, power-to-dB, validity-safe median filtering, signed change, MAD cutoff, cleanup and region measurement. |
| Nominal outputs | Complete and preserved | 0.0195, 0.7949 and 0.0000 km²; 1, 30 and 0 retained regions. |
| Threshold sensitivity | Complete | Identical cleanup at −10%, nominal and +10% cutoffs. |
| Temporal consistency | Complete | All 30 24-day nominal regions sampled over the same native pixels in both subintervals. |
| Robust candidate cores | Complete | Native masks, vector geometry, regional measurements and lightweight viewer layers for all three pairs. |
| Independent-source review | Complete as a source screen | Top ten regions reviewed; official mapped extent intersects none of all 30 nominal candidates. Causes remain unverified. |
| Viewer changes | Implemented; interactive QA pending | New default pair, robust toggle, temporal fields, validation notes and explicit zero-result explanation. |
| Automated scientific checks | PASS in last implementation run | 38 tests and all export validation checks passed. |
| Source/output fingerprint | Matches | Rechecked for this report. |
| Physical offline rehearsal | Pending | Wi-Fi and Ethernet have not been physically disabled for the required rehearsal. |
| Competition science freeze/tag | Pending | Rehearsal pending; current folder is not an initialized Git repository. |
| Public repository/submission | Not performed | No repository upload or competition submission. |

## 3. What changed in the latest phase

| Area | Earlier state | Implemented change |
| --- | --- | --- |
| Default comparison | Aug 19 → Aug 31 | Aug 19 → Sep 12, with the other two comparisons still selectable. |
| Temporal evidence | Each pair inspected independently | Per-region subinterval metrics on the exact 24-day nominal region pixels; deterministic descriptive classification. |
| Robustness | Summary sensitivity values | Explicit robust-core raster, GeoJSON, region measurements, display boundaries and overlay. |
| Region evidence | Area/change statistics and unverified cause | Added robust area/fraction, temporal class, same-pixel subinterval medians and independent-source review notes. |
| Independent evidence | No source review recorded | UNOSAT/UNESCO mapped-extent intersection plus a Copernicus Sentinel-2 catalog screen. |
| Overlay controls | Nominal candidate overlay | Added “Show robust candidate core”; nominal remains the default layer. |
| Robust region counts | No separate count | Displays nominal regions retaining a core separately from connected strict components. |
| Threshold language | Sensitivity shown | Explicitly labeled “not statistical confidence.” |
| Zero-result explanation | No retained candidates | Explains that zero nominal regions does not prove no real change; looser cutoff retains 0.0111 km². |
| Automated tests | 27 passing | 38 passing, adding temporal classes and robust-core behavior. |
| Export validation | Nominal raster/vector checks | Added baseline preservation, core subset/reproduction, temporal/validation geometry and source-archive checksum checks. |
| Reproduction | Original pipeline | `make process` now also builds evidence extensions; `make augment` updates extensions from existing rasters. |
| Documentation | Original local milestone notes | Added temporal notes; updated validation, methodology, README, QA and disconnected-demo runbook. |

## 4. Dataset audit and selected observations

Primary source: **NASA–ISRO NISAR L2 GCOV PROVISIONAL**, collection `NISAR_L2_GCOV_PROVISIONAL_V1`, [DOI 10.5067/NIL2GCOV-P1](https://doi.org/10.5067/NIL2GCOV-P1).

| Local file | Acquisition start, UTC | Product version | Release | Selected |
| --- | --- | --- | --- | --- |
| `aug19.h5` | 2026-08-19T23:39:18 | 1.0.11 | P05023 | Yes |
| `aug19(1).h5` | 2026-08-19T23:39:18 | 1.0.12 | X05026 | No: same-date alternate release |
| `aug31.h5` | 2026-08-31T23:39:18 | 1.0.11 | P05023 | Yes |
| `aug31(1).h5` | 2026-08-31T23:39:18 | 1.0.12 | X05026 | No: same-date alternate release |
| `sept12.h5` | 2026-09-12T23:39:18 | 1.0.11 | P05023 | Yes |
| `sept12(1).h5` | 2026-09-12T23:39:18 | 1.0.12 | X05026 | No: same-date alternate release |

The `(1)` products are alternate releases of the same acquisitions. They are not extra observation dates or neighboring coverage. The implementation avoids mixing same-date reprocessings or different product versions. Raw HDF5s retain their original names and locations. The large supplied archive is retained without redundant extraction.

Exact selected granule IDs:

```text
NISAR_L2_PR_GCOV_028_098_A_016_4005_DHDH_A_20260819T233918_20260819T233953_P05023_N_F_J_001
NISAR_L2_PR_GCOV_029_098_A_016_4005_DHDH_A_20260831T233918_20260831T233952_P05023_N_F_J_001
NISAR_L2_PR_GCOV_030_098_A_016_4005_DHDH_A_20260912T233918_20260912T233952_P05023_N_F_J_001
```

Selected measurement and geometry:

- Track **98**, frame **16**, ascending pass, left-looking geometry.
- Frequency **A**, real diagonal covariance term **HHHH**, **HH** polarization.
- Audited path: `/science/LSAR/GCOV/grids/frequencyA/HHHH`.
- Full science-layer shape: **33840 × 34488**.
- Native grid: **EPSG:32645**, **10 m × 10 m**; y-coordinate spacing is −10 m.
- Requested AOI center: **85.33° E, 27.80° N**; fixed **24 km × 24 km**, snapped to **2400 × 2400 pixels**.
- Source window starts at row **25911**, column **19676**.
- AOI affine transform: `[10, 0, 323480, 0, -10, 3088170]`.

The AOI was chosen for geographic context and manageable processing before inspecting change. It is not an asserted event boundary. No resampling or mosaicking is needed for the selected products; incompatible grids are rejected.

Pair footprint overlap, measured as projected intersection divided by the smaller footprint:

| Pair | Separation | Overlap |
| --- | --- | --- |
| Aug 19 → Aug 31 | 12 days | 99.8950% |
| Aug 19 → Sep 12 | 24 days | 99.8918% |
| Aug 31 → Sep 12 | 12 days | 99.2782% |

### Quality gates and source fingerprints

Power must be finite and positive, source mask values 0 and 255 are excluded, and number of looks must be finite and positive. The median output is valid only when every contributing source pixel is valid.

| Observation | Valid extracted pixels | Valid after median preprocessing | Native-window SHA-256 |
| --- | ---: | ---: | --- |
| aug19.h5 | 5,749,602 | 5,735,334 | `39bc00456c0571f8e9623a1455b9ebc25a22534567faf85556c25d9881e3a35f` |
| aug31.h5 | 5,672,910 | 5,658,643 | `3b3d5458da8fc62a2ffb6982063259c0edd74bcae2ae963535a2f1d33b2966e0` |
| sept12.h5 | 5,492,956 | 5,478,640 | `039a403ec9cd7518d11ada865e20b87043edc45b3f793ff8357dee0014d9f49b` |

Each window fingerprint covers the row-major native power, mask and number-of-looks bytes. It is **not** a whole-file checksum of a multi-gigabyte HDF5.

## 5. Scientific method and preserved baseline

The nominal method remains:

```text
backscatter_dB = 10 × log10(real diagonal gamma-0 power)
preprocessing = 3 × 3 validity-safe median per observation
signed ΔdB = after_dB − before_dB
MAD = median(abs(ΔdB − median(ΔdB)))
robust spread = 1.4826 × MAD
nominal cutoff = 3.0 × robust spread
candidate rule = abs(ΔdB) ≥ nominal cutoff
cleanup = one four-connected opening iteration
minimum retained connected region = 100 native pixels
```

The cutoff is centered on zero physical change; the observed distribution median is recorded rather than subtracted. This is an exploratory deterministic rule, not a formal significance test. Region ranking uses area descending, then absolute median signed change descending.

Projected area is measured from the native affine determinant and CRS unit factors. Each pixel represents **100 m² = 0.0001 km²** in this grid. Areas are projected grid areas, not sloped terrain-surface areas. Display previews do not supply scientific measurements.

The initial unsmoothed conservative run retained zero regions. Its output remains in [baseline_unsmoothed.json](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/data/derived/baseline_unsmoothed.json>). The subsequent minimal median filter is documented explicitly. The next phase preserves the established filtered nominal results; it adds separate evidence layers without changing the AOI, source series, HDF5 measurement, polarization, grid, MAD multiplier or cleanup.

## 6. Nominal results

| Comparison | Common valid area, km² | Nominal candidate area, km² | Retained regions | Nominal cutoff, dB |
| --- | ---: | ---: | ---: | ---: |
| 2026-08-19 → 2026-08-31 | 565.8349 | 0.0195 | 1 | 4.1190 |
| 2026-08-19 → 2026-09-12 | 547.8402 | 0.7949 | 30 | 4.3204 |
| 2026-08-31 → 2026-09-12 | 547.8383 | 0.0000 | 0 | 3.9954 |

The 24-day comparison is the strongest visible nominal result and the default demo comparison. The two 12-day comparisons remain available as supporting temporal evidence.

## 7. Threshold sensitivity and robust cores

Each pair is processed with the same cleanup at nominal cutoff ×0.9, ×1.0 and ×1.1. Values below are **area km² / connected region count**.

| Comparison | −10% cutoff | Nominal cutoff | +10% cutoff |
| --- | ---: | ---: | ---: |
| 2026-08-19 → 2026-08-31 | 0.0301 / 2 | 0.0195 / 1 | 0.0178 / 1 |
| 2026-08-19 → 2026-09-12 | 1.5218 / 45 | 0.7949 / 30 | 0.4174 / 20 |
| 2026-08-31 → 2026-09-12 | 0.0111 / 1 | 0.0000 / 0 | 0.0000 / 0 |

The robust core consists of original nominal retained pixels that also survive the +10% cutoff and identical cleanup. Original nominal region IDs are preserved, so one nominal region may split into several strict connected components.

| Comparison | Robust area, km² | Fraction of nominal area | Nominal regions with a core | Connected strict components |
| --- | ---: | --- | ---: | ---: |
| 2026-08-19 → 2026-08-31 | 0.0178 | 91.28% | 1 | 1 |
| 2026-08-19 → 2026-09-12 | 0.4174 | 52.51% | 14 | 20 |
| 2026-08-31 → 2026-09-12 | 0.0000 | N/A: nominal area is zero | 0 | 0 |

For the 24-day comparison, **0.4174 km²**, or **52.51%** of the nominal area, persists at the stricter rule. This is threshold persistence, not a calibrated confidence score. The zero-area pair has no defined robust fraction because its nominal denominator is zero.

Every pair exports `robust_core_mask.tif`, `robust_core.json`, `robust_core_regions.geojson`, `robust_core_display.json` and `robust_core_overlay.png`.

## 8. Temporal consistency

The reference geometry is the unchanged set of **30 nominal Aug 19 → Sep 12 regions**. The already aligned Aug 19 → Aug 31 and Aug 31 → Sep 12 rasters are sampled over the same native pixels of each reference region. No temporal threshold retuning or new AOI is introduced.

Saved regional metrics include area, pixel count, valid coverage, centroid, bounding box, source granules and dates; both subintervals retain median/mean signed change, positive/negative fractions, median absolute change and fraction above their own nominal cutoff. The 24-day signed median/mean and sign are retained too.

Descriptive classification rules:

- At least **90%** common valid coverage is required.
- Material change is the greater of **0.5 dB** or **20%** of the final absolute median.
- A dominant interval contributes at least **70%** of the sum of the two absolute subinterval medians, while the other interval is below the material threshold.
- Material same-sign intervals are cumulative-consistent when the median sum differs from the final median by no more than the greater of **1 dB** or **30%** of the final absolute median.
- Material opposite signs produce `MIXED_SIGN`; insufficient or unclear behavior produces `UNSTABLE`.

| Temporal class | Region count |
| --- | ---: |
| CUMULATIVE_CONSISTENT | 29 |
| EARLY_DOMINANT | 1 |
| LATE_DOMINANT | 0 |
| MIXED_SIGN | 0 |
| UNSTABLE | 0 |

The maximum pixelwise signed-change additivity error is **9.53674316406e-07 dB**. This checks consistency of the exported differences; it is not independent validation of physical causes. Medians themselves need not be exactly additive.

Zero nominal connected regions in Aug 31 → Sep 12 can coexist with small same-sign shifts on the 24-day reference pixels. Subthreshold shifts can accumulate toward the longer-interval result.

Outputs: [temporal JSON](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/data/derived/nepal_case_01/temporal_consistency.json>), [CSV](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/data/derived/nepal_case_01/temporal_consistency.csv>), [GeoJSON](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/data/derived/nepal_case_01/temporal_consistency.geojson>) and [method notes](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/docs/TEMPORAL_CONSISTENCY.md>).

## 9. Independent-source research and validation status

The user instructed that dataset sources must not involve Chinese government agencies. The sources used for this phase are UNOSAT/UNITAR through UNESCO IHP-WINS and the European Copernicus catalog. This records the project's source-selection constraint; it is not a separate assessment of NASA competition eligibility rules.

The official [UNOSAT/UNESCO mudflow and rockflow extent](https://ihp-wins.unesco.org/en/dataset/nepal-satellite-detected-mudflow-and-rockflow-extent-nepal), [DOI 10.63253/1y26ihdq](https://doi.org/10.63253/1y26ihdq), describes preliminary impacts from the **26 August 2026** Rasuwa/Nuwakot event using imagery from **26–27 August**. The source was published **28 August**, is in EPSG:32645, and is not field-validated.

The compact official archive is retained at `data/context/unosat_20260826_flood_extent.zip`. Its SHA-256 is:

```text
867b5bebb4881d1b8f88af31df7f784f5db612fa651c911d81d7304bf5be0dda
```

Exact projected polygon intersection found **no overlap with any of the 30 nominal candidates**. The ten largest regions received individual source-review records. The source therefore does not support attributing these candidates to its mapped flood footprint. It also does not prove that no other physical change or event occurred outside that footprint.

| Review rank | Region ID | Nominal area, km² | Median signed ΔdB | Robust area, km² | Temporal class | UNOSAT overlap, km² | Cause status |
| --- | ---: | ---: | ---: | ---: | --- | ---: | --- |
| 1 | 3 | 0.0970 | +5.67 | 0.0714 | CUMULATIVE_CONSISTENT | 0.0000 | UNVERIFIED |
| 2 | 4 | 0.0931 | +5.70 | 0.0650 | CUMULATIVE_CONSISTENT | 0.0000 | UNVERIFIED |
| 3 | 17 | 0.0905 | +5.86 | 0.0679 | CUMULATIVE_CONSISTENT | 0.0000 | UNVERIFIED |
| 4 | 28 | 0.0423 | +5.81 | 0.0324 | CUMULATIVE_CONSISTENT | 0.0000 | UNVERIFIED |
| 5 | 1 | 0.0419 | +5.94 | 0.0352 | CUMULATIVE_CONSISTENT | 0.0000 | UNVERIFIED |
| 6 | 14 | 0.0404 | +5.32 | 0.0000 | CUMULATIVE_CONSISTENT | 0.0000 | UNVERIFIED |
| 7 | 26 | 0.0307 | +5.54 | 0.0232 | CUMULATIVE_CONSISTENT | 0.0000 | UNVERIFIED |
| 8 | 23 | 0.0305 | +5.78 | 0.0246 | CUMULATIVE_CONSISTENT | 0.0000 | UNVERIFIED |
| 9 | 8 | 0.0280 | +5.72 | 0.0173 | CUMULATIVE_CONSISTENT | 0.0000 | UNVERIFIED |
| 10 | 30 | 0.0222 | +5.85 | 0.0135 | CUMULATIVE_CONSISTENT | 0.0000 | UNVERIFIED |

The [Copernicus Sentinel-2 L2A catalog](https://stac.dataspace.copernicus.eu/v1/collections/sentinel-2-l2a) was screened for nearby scenes from August 15 to September 20. Twelve acquisitions had tile-level cloud cover of **54.29–99.9%**. Dates, item URLs, bounds and cloud metadata are saved in [sentinel2_catalog_screening.json](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/data/context/sentinel2_catalog_screening.json>). Optical image pixels and region-specific cloud masks were **not** inspected; this is catalog screening, not optical validation.

The allowed status vocabulary is `SUPPORTED`, `PARTIALLY_SUPPORTED`, `UNVERIFIED`, and `CONTRADICTED`. All current statuses remain `UNVERIFIED`. The top-ten review distinguishes source evidence, dates, URL, mapped overlap, review notes and limits from the twenty regions not prioritized for individual review.

Outputs: [validation.json](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/data/derived/nepal_case_01/validation.json>), [validated_regions.geojson](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/data/derived/nepal_case_01/validated_regions.geojson>) and [validation notes](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/docs/VALIDATION.md>).

## 10. Viewer and local server

Existing features retained:

- Real locally processed before/after radar previews and draggable swipe comparison.
- Scan animation that reveals saved results.
- Candidate overlay, all three date-pair selections and measured summary values.
- Actual region-polygon interaction, ranked buttons and region-centered zoom.
- Signed-change histogram, threshold sensitivity, methods/provenance dialog and evidence downloads.
- PROVISIONAL labeling and an honest zero-result state.

New behavior:

- Default comparison: **Aug 19 → Sep 12**.
- Nominal candidate overlay is the initial evidence layer; the robust-core toggle switches saved overlay and selection geometry.
- The robust summary distinguishes nominal regions containing a core from the number of connected strict components.
- Selected regions show nominal/robust areas, persistence fraction, signed median and peak absolute change, temporal class and validation review.
- The top ten nominal candidates are available through region buttons; map geometry provides additional selections.
- The zero-result pair explains the detection rule and the 0.0111 km² looser-threshold result.

The Python standard-library server binds to loopback and serves local assets. The viewer does not require API keys, NASA availability, an online basemap, external fonts or a CDN. External source links are optional references opened on click; they are not required page assets. Compact public demo assets are approximately **18 MB**; raw HDF5s are not loaded into the browser.

Top-level legacy `before`, `after` and `evidence` aliases still refer to Aug 19 → Aug 31. The viewer correctly uses pair-specific assets selected by `manifest.default_pair = t1_t3`.

## 11. Files created or changed

### Initial implementation

- `src/ingest/inspect_h5.py`, `metadata.py`, `extract_gcov.py`: inventory, metadata, actual native-window extraction.
- `src/compute/align.py`, `preprocess.py`, `change.py`, `threshold.py`, `regions.py`, `area.py`, `uncertainty.py`, `pipeline.py`, `validate.py`: deterministic science and validation.
- `src/export/artifacts.py`: native GeoTIFFs, geographic polygons, previews, overlays and evidence.
- `src/api/app.py`: local static/API server.
- `web/index.html`, `app.js`, `styles.css`: dependency-free viewer.
- `tests/test_science.py`, `config.json`, `Makefile`, `requirements.txt`, `pyproject.toml`.
- README, datasets, methodology, limitations, validation, AI-use, QA and demo runbook; Apache-2.0 license and raw-data/credential exclusions.

### Latest phase

| File | Purpose |
| --- | --- |
| `src/compute/temporal_consistency.py` | Same-native-pixel subinterval metrics, descriptive classes, JSON/CSV/GeoJSON. |
| `src/compute/robust_core.py` | Strict-rule intersection with nominal pixels; native mask, vectors and regional core statistics. |
| `src/compute/validation_context.py` | Hash-checked official mapped extent and independent region-overlap screen. |
| `src/compute/extend_evidence.py` | Builds extensions, augments pair evidence, sets viewer default and copies compact assets. |
| `src/compute/validate.py` | Additional baseline, robust-core, geometry and source checks. |
| `src/compute/pipeline.py` | Clarifies limits of independent causal validation. |
| `tests/test_temporal_consistency.py` | Eleven additional temporal/geometry/robustness tests. |
| `Makefile` | Runs extensions after processing; adds `make augment`. |
| `web/index.html`, `web/app.js` | Default pair, core toggle, temporal and validation evidence, count labels and zero-result explanation. |
| `data/context/unosat_20260826_flood_extent.zip` | Compact official validation source with a fixed checksum. |
| `data/context/sentinel2_catalog_screening.json` | Screened Copernicus scene metadata. |
| `.gitignore` | Allows the compact official source archive while excluding large raw archives/HDF5 and credentials. |
| `docs/TEMPORAL_CONSISTENCY.md` | New temporal method/result documentation. |
| `README.md`, `docs/VALIDATION.md`, `docs/METHODOLOGY.md`, `docs/DEMO_RUNBOOK.md`, `docs/QA.json`, `PROJECT_PROGRESS.md` | Updated results, provenance, interpretation and pending verification. |

All three pair directories contain signed-change rasters, masks, nominal labels, nominal geographic/display regions, methodology/evidence, previews and overlays. New temporal and validation outputs live at case level; robust outputs live inside each pair directory. Lightweight JSON/GeoJSON/CSV/image artifacts are copied into `web/public/cases/nepal_case_01/`.

## 12. Verification and its limits

The last implementation run completed:

```bash
make process
make test
make validate
.venv/bin/python -m compileall -q src
node --check web/app.js
```

Results: **38 tests passed**, all three comparison exports and evidence extensions passed validation, and both syntax checks passed. Current checks include nominal-area/count preservation, reproducibility from saved signed-change rasters, nodata, region pixel/area totals, geographic polygon area, robust-core subset/reproduction, exact temporal/validation geometry preservation and the official source checksum.

Static viewer checks found all **45** JavaScript-referenced UI element IDs in the HTML and verified **19** required public assets were byte-identical to the corresponding derived outputs. A broader earlier asset-copy check covered 27 files. A targeted credential-pattern scan of source/docs/config/compact evidence reported no matches; this is not an exhaustive security audit.

The original viewer passed browser checks on **30 September 2026**, including interactions, desktop/phone layout and local page-asset loading. Those results precede the new temporal panel and core toggle. The updated viewer's interactive and responsive checks are **pending** because browser automation blocked access to the local page under its URL policy. The previous `docs/demo.png` is historical and is not proof of the updated UI.

Physical Wi-Fi and Ethernet disconnection have **not** been performed. `docs/QA.json` correctly leaves the physical-disconnection fields false. Code/asset inspection supports local-only operation, but it does not substitute for the required disconnected rehearsal.

Current source SHA-256, matching all three saved evidence files:

```text
6a9041ac47bf182d0085dc6ba34520ee862f0483d93fb169b590132327afd2b2
```

Software recorded with the outputs: TerraPulse 1.0.0, Python 3.14.4, NumPy 2.5.3, SciPy 1.18.1, h5py 3.16.0, rasterio 1.5.1, pyproj 3.8.0, Shapely 2.1.2 and Pillow 12.3.0.

## 13. Repository and submission preparation

The source, tests, documentation, compact public case, data acquisition guidance, granule IDs, DOI and Apache-2.0 code license are prepared locally. `.gitignore` excludes raw `.h5`, large `.zip`, environment files, credentials, caches, virtual environments and reproducible analytical GeoTIFFs. The specific compact UNOSAT archive is allowed because it supports reproducible source review.

The current `.git` directory is empty rather than an initialized repository; the last `git status` attempt reported “not a git repository.” No commit, remote publication, `v1.0-competition` tag or competition submission was performed. The science version has not been declared frozen because the required final offline/browser checks remain incomplete.

The code license does not relicense NASA or independent-source data; upstream terms remain applicable.

## 14. Remaining work

| Priority | Remaining task | Completion evidence required |
| --- | --- | --- |
| 1 | Verify updated viewer interactions and responsive layout | Confirm default pair, modes, swipe, scan, nominal/core toggle, all three pairs, region selection/zoom, methodology, validation and downloads. |
| 2 | Perform physical disconnected rehearsal | User disables Wi-Fi and Ethernet, restarts demo, repeats interactions and records actual date/machine/browser/result in QA. |
| 3 | Complete repository setup and final review | Initialized Git repository; reviewed raw-data/credential exclusions and intended files. |
| 4 | Freeze competition science after prerequisites | Final checks, recorded source fingerprint and `v1.0-competition` tag or equivalent. |
| 5 | Publish/submit if separately authorized | Intended repository destination and competition submission reviewed and completed. |

Independent positive causal validation remains a scientific gap if stronger flood/landslide claims are desired. The completed source screen supports keeping the current neutral surface-change framing; it does not justify upgrading cause labels. Formal classification accuracy, independent subpixel registration accuracy and calibrated statistical confidence have not been established.

Broad new features—arbitrary global ingestion, automatic mosaicking, additional cases/polarizations, deformation workflows, accounts, forecasting and AI chat—remain outside the current requested phase.

## 15. Run and reproduce

Run the included local demo:

```bash
make demo
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/). A reviewer can view the shipped compact assets with standard Python alone:

```bash
OFFLINE=1 python3 -m src.api.app
```

Reproduce the science from the selected raw products:

```bash
make setup       # first-time dependency installation; internet required
make inspect     # audit actual HDF5 schema and metadata
make test        # scientific and ingestion checks
make process     # all nominal pairs plus evidence extensions
make validate    # saved raster, geometry and evidence consistency
make demo        # local viewer
```

To rebuild only the added layers from existing processed rasters:

```bash
make augment
```

For the disconnected rehearsal, follow [docs/DEMO_RUNBOOK.md](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/docs/DEMO_RUNBOOK.md>) and record only observed results in [docs/QA.json](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/docs/QA.json>).

Supporting documentation: [README](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/README.md>), [datasets](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/docs/DATASETS.md>), [methodology](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/docs/METHODOLOGY.md>), [temporal consistency](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/docs/TEMPORAL_CONSISTENCY.md>), [validation](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/docs/VALIDATION.md>), [limitations](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/docs/LIMITATIONS.md>) and [AI assistance](</home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1/docs/AI_USE.md>).
