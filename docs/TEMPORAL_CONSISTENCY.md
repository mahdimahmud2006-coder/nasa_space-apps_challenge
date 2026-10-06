# Temporal consistency of the 24-day candidates

The August 19 → September 12 nominal regions provide fixed reference pixels. For each of the 30 regions, TerraPulse samples the already aligned August 19 → 31 and August 31 → September 12 signed change rasters on **those same native pixels**. It does not move regions to follow a different threshold result. The three changes are algebraically additive on common valid pixels; the maximum measured additivity error is 0.00000095 dB.

The saved [JSON](../data/derived/nepal_case_01/temporal_consistency.json), [CSV](../data/derived/nepal_case_01/temporal_consistency.csv), and [GeoJSON](../data/derived/nepal_case_01/temporal_consistency.geojson) retain area, pixels, centroids, bounding boxes, dates, source granules, subinterval medians/means, sign fractions, absolute median change and fractions above each subinterval's own nominal cutoff. The GeoJSON uses the exact original 24-day region geometry.

Classification is descriptive, not a significance test. It requires at least 90% common valid coverage. A material subinterval magnitude is the greater of 0.5 dB or 20% of the final absolute median. A dominant interval contributes at least 70% of the two absolute subinterval medians while the other is below that material magnitude. Equal-sign material subintervals are `CUMULATIVE_CONSISTENT` when their median sum is within the greater of 1 dB or 30% of the final median. Material opposing signs are `MIXED_SIGN`; other cases are `UNSTABLE`. Rules and constants are serialized in the JSON.

Current result: **29 `CUMULATIVE_CONSISTENT`, 1 `EARLY_DOMINANT`**. These labels describe behavior of radar backscatter only. The August 31 → September 12 pair has zero independently retained connected regions at the nominal rule, while small signed shifts on the 24-day region pixels contribute cumulatively. Zero retained regions therefore does not mean no change in that interval.

Every cause remains **UNVERIFIED**. Speckle, moisture, vegetation, terrain and acquisition effects remain possible.
