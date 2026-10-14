# Implementation 03 — Rainfall and terrain context

Implemented on 2026-10-14 for `nepal_case_01`. The user authorized researching, downloading, and implementing alternatives from non-Chinese organizations. The attached implementation plan supplied feature requirements; its example values were not used as measurements.

## Delivered

The time-series viewer now includes environmental map layers, precipitation and terrain metrics for the selected zone/date, source information, and the explicit statement: **Context supports interpretation; it does not prove cause.** All radar causes remain UNVERIFIED.

- 24-, 72-, and 168-hour precipitation accumulation at all three compatible NISAR dates.
- Elevation, slope, aspect, curvature, roughness, relative elevation, contributing area, modeled drainage distance, TWI, and depression-fill depth.
- Nineteen actual Cloud Optimized GeoTIFFs, map PNGs, `context.parquet`, `context.json`, and `zone_context.json`.
- `/api/cases/nepal_case_01/context` and `/api/zones/NP-Z4ab9a6118de9/context`.
- One existing tracked zone across three dates; no new zones or causal labels invented.
- The original nominal radar analyses and Implementation 02 analytical outputs remain byte-identical: **105 saved artifacts** checked.

## Downloaded data and alternatives

| Source | Organization / download host | Decision |
|---|---|---|
| NASA POWER hourly PRECTOTCORR | NASA Langley / NASA GMAO; `power.larc.nasa.gov` | Used. Complete 768-hour history, August 12–September 12, 2026 inclusive, for four native cells. |
| NASADEM HGT v001 | NASA / JPL / USGS; Microsoft Planetary Computer and Microsoft Azure | Used. Tiles `n27e085` and `n28e085`, approximately 39.5 MiB combined. |
| GPM IMERG Early V07 scientific GIS service | NASA GES DISC; `gis.earthdata.nasa.gov` | Excluded after a data-access quality check; details below. |
| CHIRPS v3 daily | University of California, Santa Barbara; `data.chc.ucsb.edu` | Reviewed. Daily disaggregation does not provide the requested rolling hourly windows. |

The downloader permits HTTPS requests only to the explicitly listed NASA and Microsoft hosts. No Chinese-hosted data service was used. The saved manifests record the producing organizations, unsigned source URLs, source metadata, and SHA-256 checksums. Anonymous Microsoft read tokens are used in memory and are not written to manifests.

Official documentation:

- [NASA POWER hourly API: hourly average values, precipitation in mm/hour, UTC option](https://power.larc.nasa.gov/docs/services/api/temporal/hourly/).
- [NASA POWER native meteorological grid and revision policy](https://power.larc.nasa.gov/docs/tutorials/service-data-request/api/).
- [NASA POWER meteorological sources: MERRA-2 and GEOS-IT](https://power.larc.nasa.gov/docs/methodology/data/sources/).
- [Microsoft NASADEM collection and providers](https://planetarycomputer.microsoft.com/api/stac/v1/collections/nasadem).
- [NASADEM guide: meters relative to the EGM96 geoid](https://lpdaac.usgs.gov/documents/1273/NASADEM_User_Guide_V11.pdf).
- [CHIRPS v3 daily timing and disaggregation limitations](https://www.chc.ucsb.edu/data/chirps3).

### Why the requested IMERG source was replaced

The NASA GIS catalog listed all 1,536 expected half-hourly timestamps. Scientific F32 TIFF exports had a suspicious pattern: nonzero values clustered in the first one or two bins of each day. A separate `getSamples` call for the cataloged **2026-08-22 12:00 UTC** slice returned a missing-resource **404** within an ArcGIS error, while exportImage returned an all-zero TIFF. Changing among lock-raster, time, and multidimensional selectors did not resolve this slice.

Those zeros cannot safely be interpreted as dry weather. All downloaded IMERG frames were excluded from the implementation. The rejection evidence is saved in `data/context/environment/imerg_rejection.json` and `imerg_missing_slice_sample.json`; the retained partial raw files are diagnostics only. This identifies a problem with the tested access route, not a finding that the underlying NASA IMERG scientific product is invalid.

NASA POWER offers a working official NASA hourly archive without credentials. Its coarser model/reanalysis estimates satisfy the implemented temporal context workflow, with the departure from the original IMERG preference disclosed in the UI and manifests. The optional IMERG diagnostic command writes separate files and cannot overwrite the accepted POWER cube.

## Spatial and temporal definitions

The original NISAR grid remains **EPSG:32645, 10 m, 2400 × 2400 pixels**. Context uses **30 m, 800 × 800 pixels** with identical bounds and origin:

```text
Affine: [30, 0, 323480, 0, -30, 3088170]
Bounds: [323480, 3064170, 347480, 3088170]
```

Each context pixel covers exactly 3 × 3 native radar pixels. This reconciles the plan's requested 30 m context resolution with the existing 10 m radar outputs.

POWER has a **0.5° latitude × 0.625° longitude** native grid, roughly 50–60 km. The four downloaded centers are latitudes 27.5°, 28.0° and longitudes 85.0°, 85.625°. Nearest-neighbor placement preserves those regional values; the 30 m display adds no precipitation detail. These are model/reanalysis estimates, not local gauges or IMERG satellite observations. API metadata lists both MERRA2 and GEOSIT without per-hour source-transition labels; recent data may later be revised.

Hourly precipitation rates in mm/hour are multiplied by one hour before summation. Windows contain exactly 24, 72, or 168 complete UTC hours. At each 23:39:18 UTC radar acquisition, the latest complete hour ends at **23:00 UTC**, a **39 minute 18 second lag**. The partial hour containing the acquisition is excluded. Duplicate, missing, or unordered time bins are rejected; a missing spatial value makes that accumulation cell nodata rather than zero.

NASADEM is bilinearly reprojected from its native one arc-second grid. Vertical units are meters relative to EGM96. It represents historical terrain, not a 2026 terrain survey.

Zone statistics sample aligned 30 m cells at the centers of the fixed zone's 199 equal-area native radar pixels. This weights each intersected context cell by its covered native pixels. The zone intersects **39 terrain cells** and lies within one coarse precipitation cell.

## Terrain calculations and limits

Slope uses centered projected elevation gradients in meters/meters and is reported in degrees. Aspect is downslope clockwise from north; flat terrain has no defined aspect. Curvature is the elevation Laplacian in 1/m. Roughness is the 3 × 3 elevation population standard deviation in meters. Relative elevation is the difference from a 1,050 m square-window mean, not height above drainage.

Hydrology uses a **12 km buffer** beyond the AOI on all sides. A deterministic priority-flood fills depressions for routing, followed by acyclic D8 steepest-descent flow; flats follow their earlier flood parent. Contributing area includes each cell's own 900 m². The 2,560,000-cell buffered domain conserves its **2,304,000,000 m²** area at the open outlets.

Modeled drainage is defined by contributing area ≥ **1 km²**, an uncalibrated parameter. Drainage distance is Euclidean distance to those modeled cells, not surveyed rivers. TWI is `ln((contributing_area_m² / 30 m) / (tan(original_slope) + 0.001))`. Terrain derivatives use the original DEM, not the filled elevations. The largest depression-fill depth in the buffered domain is about **50.3 m**; fill depth is exported for inspection. Catchments entering the outer domain boundary are truncated, so contributing area, drainage and TWI have boundary-dependent uncertainty.

No gauge accuracy assessment, local drainage calibration, hazard classification, or causal attribution is claimed.

## Measured context for the existing tracked zone

All totals below end at 23:00 UTC on the corresponding date.

| Radar date | Previous 24 h | Previous 72 h | Previous 168 h |
|---|---:|---:|---:|
| 2026-08-19 | 14.29 mm | 23.15 mm | 77.25 mm |
| 2026-08-31 | 15.92 mm | 40.78 mm | 65.91 mm |
| 2026-09-12 | 43.66 mm | 69.30 mm | 190.79 mm |

Mean zone elevation is approximately **542.3 m EGM96**; mean slope **1.81°**, maximum slope **3.68°**; mean modeled TWI **8.34**; mean modeled drainage distance **105.0 m**. These describe the fixed zone, not the whole Kathmandu Valley.

## Run the demo

```bash
cd "/home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1"
make demo
```

Open `http://127.0.0.1:8000/timeseries.html`. Select a date and an environmental map layer. If the server was running before the API code changed, stop it with Ctrl+C and run `make demo` again. The saved viewer requires only standard Python and a browser, with no API keys or runtime internet requests.

Reproduce the downloads and context:

```bash
make download-context   # Internet required; resumes from cached verified source files
make context            # Uses local sources, writes context layers and metrics
make validate-context
make test
```

Rebuilding needs the scientific dependencies in `.venv`; no additional packages were required beyond the existing project requirements. The terrain domain has 2.56 million cells and fits comfortably on a typical machine with 8 GB RAM. This is an estimate, not a hardware benchmark. Demo viewing uses the precomputed outputs and is substantially lighter.

## Verification and remaining work

**96 tests pass**, with four existing Rasterio pending-deprecation warnings. Existing nominal and time-series validators pass. `make validate-context` checks source hashes, source time axes, hourly rate conversion, every output rainfall pixel, aligned grids, COG structure, nodata, flow conservation, zone statistics, Parquet/JSON agreement, public copies, and the 105 preserved artifacts.

The elevation/slope/drainage comparison in `docs/reports/implementation_03_terrain_qa.png` was visually inspected: ridges and valley terrain are consistent across elevation and slope, and modeled drainage follows low terrain. This qualitative check does not validate channel accuracy or rainfall accuracy. JavaScript syntax and all 31 referenced HTML element IDs were checked. Saved API responses and static assets are checked without binding network sockets.

Interactive browser QA and a physical disconnected demo rehearsal remain pending. The earlier browser policy block was not bypassed. Scientific threshold calibration and causal verification from the prior implementations also remain open; adding context does not resolve them.

Machine-readable results: `docs/reports/implementation_03_qa.json` and `docs/QA.json`. Sources are in `data/context/environment/`; analytical outputs are in `data/derived/nepal_case_01/context/`; viewer copies are in `web/public/cases/nepal_case_01/context/`.
