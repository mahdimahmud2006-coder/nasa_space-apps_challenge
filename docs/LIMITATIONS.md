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


## Flood scenario and thermal extensions

- The flood escalation/scenario outputs are weighted, uncalibrated indices with illustrative weights and score bands. They are not flood probabilities, hydraulic simulations, operational alerts, flood depths or flood-wave predictions.
- Scenario duration multiplies actual rainfall rates in the latest selected preceding hours; it does not generate a future storm. Baseline normal wetness is an assumption, not a soil-moisture measurement.
- Model confidence and empirical validation statistics remain unavailable because no labeled independent flood-response training/validation set exists. Measured data coverage is reported separately.
- The available independent UNOSAT mudflow/rockflow footprints have zero overlap with this AOI. No absence of physical impact is inferred. The model does not reconstruct the reported upstream ice-avalanche/damming mechanism of the August 26 event.
- Backscatter-decrease repetition is ambiguous and uses only earlier/current acquisitions; it is not a validated persistent-inundation classifier.
- NASA POWER native precipitation is regional (~50–60 km). Fine model cells do not imply fine rainfall observations.
- Landsat thermal retrievals are cloud/QA screened with an explicitly chosen 5 K reported-uncertainty ceiling; coverage is partial and reported uncertainty remains substantial. Thermal is independent context and excluded from flood scoring. Temporal mean differences cover different valid footprints and are not causal temperature-change estimates.
- Height exaggeration and the terrain mesh are display choices. Quantitative scores use the preserved aligned 30 m grid; original radar outputs remain at 10 m.
- Browser visual/GPU rendering checks are blocked by the app's localhost URL policy. Automated numerical, geometry and mocked interaction checks do not establish visual correctness on every device.

## Final project / Change DNA and landslide susceptibility

A finished application does not establish validated hazard prediction. Change DNA is retrospective, based on three visits and one selected zone. Onset is bracketed, recovery half-life is censored where unobserved, and similar-event search remains unavailable without enough references. A shrinking successive change mask does not prove recovery from persistent baseline disturbance.

Landslide indices use illustrative static/dynamic/radar weights. Lithology, soil strength, measured soil moisture and precise event labels are absent. Historical NASA report locations are mostly too imprecise; only two meet the ≤1 km screen, below the implemented independent spatial reference requirement. No ROC-AUC, PR-AUC, Brier score, trained-model confidence or rainfall-trigger prediction accuracy is claimed.

Current browser visual/GPU/responsive QA is blocked by the application URL policy. Source checks and mocked interaction tests are not visual browser tests. Physical network-disconnected rehearsal and official competition eligibility review remain pending. The local release contains runtime analytical assets, not the complete multi-gigabyte source-data reproduction archive.
