# Validation record

## Interpretation

**UNVERIFIED** for all retained regions. No independent event, optical or ground reference has established the cause of any candidate. TerraPulse uses only candidate surface-change language and does not claim flood or landslide detection. NASA–ISRO NISAR L2 GCOV remains **PROVISIONAL**.

## Independent-source screen, 1 October 2026

The ten largest August 19 → September 12 regions (IDs **3, 4, 17, 28, 1, 14, 26, 23, 8, 30**, ranked by nominal area then absolute median signed change) were compared with [UNOSAT's preliminary satellite-mapped 26 August mudflow/rockflow extent](https://ihp-wins.unesco.org/en/dataset/nepal-satellite-detected-mudflow-and-rockflow-extent-nepal), [DOI 10.63253/1y26ihdq](https://doi.org/10.63253/1y26ihdq). The official zipped shapefile is archived at `data/context/unosat_20260826_flood_extent.zip` with SHA-256 `867b5bebb4881d1b8f88af31df7f784f5db612fa651c911d81d7304bf5be0dda`. Its polygons are in EPSG:32645. Exact projected intersection finds **zero overlap for all 30 nominal regions**. This source does not support attributing the candidates to the mapped flood; it does not contradict the existence of radar change or prove that no other event occurred. UNOSAT calls its own map preliminary and not field-validated.

The [Copernicus Sentinel-2 L2A STAC catalog](https://stac.dataspace.copernicus.eu/v1/collections/sentinel-2-l2a) was screened for nearby acquisitions from August 15 to September 20. Twelve candidate scenes had tile-level cloud cover of approximately 54–99.9%. The [saved catalog screen](../data/context/sentinel2_catalog_screening.json) contains item URLs, dates and cloud metadata. **No optical image pixels or per-region cloud masks were inspected**, so this is not optical validation. Both independent sources are from UN/UNESCO and European Copernicus channels; no Chinese government or agency source is used.

Region-by-region statuses, source dates/links, overlap, what each source shows and its limits are saved in [validation.json](../data/derived/nepal_case_01/validation.json) and [validated_regions.geojson](../data/derived/nepal_case_01/validated_regions.geojson). Reviewed and unreviewed regions remain explicitly `UNVERIFIED`.

## Actual input verification

Six HDF5 products were audited. Each of three acquisition dates has a P05023/1.0.11 variant and an X05026/1.0.12 variant. Identical acquisition timestamps identify each pair as reprocessings, not six observations. No dataset paths are added or missing between versions; science grid shapes and float types agree. Text widths and processing versions differ. The consistent P05023 series is selected; same-date variants and mixed product versions are rejected by pair checks.

Selected pair footprint overlap, computed in UTM as intersection divided by smaller footprint:

- Aug 19 → Aug 31: 99.8950%, 12 days.
- Aug 19 → Sep 12: 99.8918%, 24 days.
- Aug 31 → Sep 12: 99.2782%, 12 days.

All share track 98, frame 16, ascending left-looking geometry, EPSG:32645 and 10 m frequency-A pixels. Native grid equality is verified from metadata and uniform full coordinate arrays. The extracted area satisfies at least 80% valid common coverage. No independent subpixel registration check is claimed.

## Numerical checks

`make test` passes 38 checks covering the original science and ingestion regressions plus temporal classes, exact reference geometry and robust-core subset behavior.

`make validate` reloads exported GeoTIFFs and proves nominal areas/counts are unchanged, masks reproduce from saved changes and parameters, nodata is consistent, regional sums agree, geographic polygons match raster area, robust-core pixels are a nominal subset and reproduce at the stricter cutoff, temporal/validation GeoJSON preserves original geometry, and all causal statuses remain UNVERIFIED. It also checks the official UNOSAT archive hash.

The unsmoothed baseline produced zero retained regions; it is preserved separately. Final minimally filtered results:

| Pair | Valid analysis km² | Candidate km² | Regions | ±10% cutoff candidate area range km² |
|---|---:|---:|---:|---:|
| Aug 19 → Aug 31 | 565.8349 | 0.0195 | 1 | 0.0178–0.0301 |
| Aug 19 → Sep 12 | 547.8402 | 0.7949 | 30 | 0.4174–1.5218 |
| Aug 31 → Sep 12 | 547.8383 | 0.0000 | 0 | 0.0000–0.0111 |

At +10% cutoff, the robust-core area is 0.0178, 0.4174 and 0.0000 km² respectively. The 24-day core covers 14 nominal regions in 20 connected strict components. These ranges demonstrate threshold dependence. They are not accuracy estimates, confidence intervals, or disaster-impact areas.

## Demo verification

The previous viewer's browser checks are recorded in `docs/QA.json`. The updated viewer has syntax/static checks; interactive browser verification is pending because the browser automation policy blocked the local page. No machine Wi-Fi settings were modified. The application fetches only localhost assets; online source links are optional references activated only on click. A physical disconnected rehearsal remains a user-operated judging preparation step.
