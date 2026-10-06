# Limitations

- **NISAR L2 GCOV is PROVISIONAL**, with ongoing calibration and quality assurance.
- All change-region causes are **UNVERIFIED**. No independently validated flood, landslide or disaster classification is provided.
- Backscatter is ambiguous: moisture, vegetation, geometry, terrain effects, speckle and processing artifacts may produce change.
- Mask and number-of-looks gates exclude many unreliable pixels, but are not a complete terrain/layover/shadow or noise-floor validation layer.
- A 3 × 3 median introduces local dependence and suppresses small changes. Strict nodata neighborhood exclusion reduces common valid coverage; that coverage is reported per pair.
- The cutoff and 100-pixel region filter materially affect areas. ±10% threshold sensitivity and alternative multipliers are displayed; neither constitutes a formal confidence interval.
- Zero retained regions does not mean no surface change occurred.
- Area is measured on the actual projected UTM grid, with potential minor map-projection distortion. It is not sloped terrain surface area.
- Only the fixed 24 km square around Kathmandu Valley is analyzed; it is not a Nepal-wide assessment.
- Input comparability uses metadata and footprint checks, not independent subpixel registration validation. We require identical native grids and product versions, refusing incompatible inputs.
- Alternate processing variants are not extra acquisitions. The demo uses a consistent P05023 release and avoids mixing versions.
- Display rasters are reduced-resolution previews using shared contrast; quantitative results and boundaries use full native resolution.
- No live acquisition, arbitrary global processing, automatic reprojection, neighboring-frame mosaicking, or unimplemented disaster mode is claimed.
