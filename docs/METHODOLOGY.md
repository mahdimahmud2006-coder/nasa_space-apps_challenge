# TerraPulse methodology

## Sources and comparability

All six supplied HDF5s are enumerated in `data/derived/audit.json` and the text inventory `audit.txt`: groups, paths, shapes, types, scalar values, fill values and attributes. Large arrays are not dumped. Object references are described as references; they are not interpreted as numeric metadata. Paths are resolved from the actual inventory, then checked again during extraction.

The three selected P05023 products have identical science-layer structure and grids, GCOV L2 product/version, track 98, frame 16, ascending pass, and left look. Acquisition start dates are 12 days apart. The `(1)` variants are same-date reprocessings. Metadata-string widths and release/software versions differ, but there are no added/missing dataset paths. We use one processing release throughout. Pair checks reject same-date observations and mismatched versions/geometries. Footprints are projected to EPSG:32645 and overlap is intersection area / smaller footprint area, requiring at least 80%; all selected pairs exceed 99%. Exact grid compatibility is required. Differing grids, CRSs and frames fail closed; automatic reprojection and neighboring-frame mosaicking are outside this case.

## Fixed area of investigation

A 24 km square centered near 85.33° E, 27.80° N is snapped to the native UTM pixel boundary, producing a 2400 × 2400 grid. It covers Kathmandu Valley and northern hills. This fixed geographic area was chosen before inspecting change, for local context and bounded memory/disk use; no event boundary is claimed. `aoi.geojson` and metadata retain the actual snapped bounds, transform and extraction window. The same source window is used for every acquisition. All raw granules remain untouched.

## Measurement and masks

Selected audited path: `/science/LSAR/GCOV/grids/frequencyA/HHHH` (real diagonal HH covariance). [ASF's official GCOV guide](https://nisar-docs.asf.alaska.edu/gcov/) identifies real diagonal covariance terms as gamma-0 power. Thus `10 * log10(power)` yields gamma-0 backscatter in dB; complex off-diagonal terms are rejected. Power must be finite and positive, and explicit fill values are excluded. The discovered mask's own attributes define 0 as partially focused/invalid and 255 as outside acquisition extent; only 1–254 are retained. `numberOfLooks` must be finite and positive. Valid counts and window checksums are recorded.

A 3 × 3 median is applied to each dB observation. For an odd-size kernel, the monotonic log transform makes this equivalent to taking the median of positive power before converting to dB. The output is invalid unless **every** source pixel in the kernel is valid. Source-edge and nodata neighborhoods are excluded. This small 30 m footprint reduces isolated SAR speckle; native spacing remains 10 m and filtering does not create new independent observations. Native unfiltered dB rasters are retained as `t1_native.tif`, etc. Display previews use one shared 2nd–98th percentile contrast across all three processed observations. They are reduced to 1200 pixels per side and never used for area/statistics.

## Change and detection

For pixels valid in both processed dates:

```
ΔdB = after_dB - before_dB
median = median(ΔdB)
MAD = median(abs(ΔdB - median))
robust spread = 1.4826 * MAD
nominal cutoff = 3.0 * robust spread
candidate = abs(ΔdB) >= nominal cutoff
```

This is an exploratory robust rule, **not** a statistical significance test. It is centered on zero physical change; the measured distribution median is retained and not subtracted. `mad` and `absolute_db` cutoff methods are supported. Nonpositive/nonfinite parameters are rejected. Degenerate zero-MAD distributions require an explicit absolute cutoff.

Binary opening uses one iteration of a four-connected 3 × 3 cross. Four-connected components smaller than 100 pixels are removed (0.01 km² on this actual grid). No closing, hole filling, or additional smoothing is applied. Candidates are ranked by area, then absolute median change. IDs remain stable for the same source, code and configuration. Mean, median, peak absolute change, centroid, bounding box, count and flags are calculated per region. Polygon boundaries are derived from the **full-resolution** labels, not display previews.

## Area and sensitivity

Pixel grid area is the absolute affine determinant, including rotation if present, multiplied by the CRS axis-unit conversion factors and divided by 1,000,000. Current grid: 100 m² = 0.0001 km² per pixel. Geographic CRSs are rejected rather than assuming degree area. This is **projected grid area**, with modest UTM distortion, not an ellipsoidal terrain surface area.

Every pair repeats detection and identical cleanup at nominal cutoff ×0.9, ×1.0 and ×1.1. The methods panel also lists candidate MAD multipliers 2.0, 2.5 and 3.0 using identical cleanup. These are transparent sensitivity summaries, not formal confidence intervals or flood confidence.

The robust candidate core reruns the **same** cleanup at ×1.1 cutoff and intersects its retained mask with the original nominal region labels. Its area is measured on native pixels and retains nominal IDs; one original region can split into several strict connected components. No nominal mask, region, cutoff or method is overwritten. See [temporal consistency](TEMPORAL_CONSISTENCY.md) for the fixed-pixel subinterval rule. Independent-source intersection in [validation](VALIDATION.md) is contextual evidence only; it does not change radar measurements.

The unfiltered conservative run found zero retained regions. `data/derived/baseline_unsmoothed.json` preserves this outcome and its method. The 3 × 3 filter was selected to address isolated noise, not to produce a disaster-shaped result. No threshold or area was selected to maximize the change story.

## Provenance and reproducibility

Evidence preserves original local filenames, internal full granule IDs, acquisition times (UTC), exact HDF5 paths, track/frame/orbit, look/pass, product/specification versions, DOI, source byte sizes, AOI/grid, validity statistics, all processing parameters, software versions and a SHA-256 of source Python files. Extraction includes a SHA-256 of the actual native power/mask/looks window bytes; this is **not** a checksum of the entire multi-GB raw file. Source file size is checked against the audit. Rerun the audit after modifying files.

`make test` checks numerical, ingestion and temporal behavior. `make validate` reconstructs nominal and robust masks from saved change rasters, verifies nodata and area, checks temporal and validation geometry, and confirms the independent source checksum. No LLM supplies scientific numbers or labels. All interpretations remain UNVERIFIED.
