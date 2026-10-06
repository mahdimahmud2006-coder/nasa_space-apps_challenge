# Dataset provenance

Primary dataset: **NASA–ISRO NISAR Provisional Geocoded Polarimetric Covariance, Version 1**, Level 2, L band. Collection identifier: `NISAR_L2_GCOV_PROVISIONAL_V1`. Product DOI from the actual identification datasets: [10.5067/NIL2GCOV-P1](https://doi.org/10.5067/NIL2GCOV-P1). Official [NASA collection description](https://data.nasa.gov/dataset/nisar-provisional-geocoded-polarimetric-covariance-product-version-1-d9e04) and [ASF GCOV guide](https://nisar-docs.asf.alaska.edu/gcov/). Product status: **PROVISIONAL**; partially validated.

## Supplied files

| Local filename | UTC acquisition start | Internal product version | Release | Selected |
|---|---|---|---|---|
| aug19.h5 | 2026-08-19T23:39:18 | 1.0.11 | P05023 | Yes |
| aug19(1).h5 | 2026-08-19T23:39:18 | 1.0.12 | X05026 | No |
| aug31.h5 | 2026-08-31T23:39:18 | 1.0.11 | P05023 | Yes |
| aug31(1).h5 | 2026-08-31T23:39:18 | 1.0.12 | X05026 | No |
| sept12.h5 | 2026-09-12T23:39:18 | 1.0.11 | P05023 | Yes |
| sept12(1).h5 | 2026-09-12T23:39:18 | 1.0.12 | X05026 | No |

The archive `aug19.zip` is retained without extraction; its already available HDF5 contents are audited. Local filenames are preserved, while original granule identity comes from the file's own `identification/granuleId`.

Selected granule IDs:

```
NISAR_L2_PR_GCOV_028_098_A_016_4005_DHDH_A_20260819T233918_20260819T233953_P05023_N_F_J_001
NISAR_L2_PR_GCOV_029_098_A_016_4005_DHDH_A_20260831T233918_20260831T233952_P05023_N_F_J_001
NISAR_L2_PR_GCOV_030_098_A_016_4005_DHDH_A_20260912T233918_20260912T233952_P05023_N_F_J_001
```

Track 98, frame 16, ascending, left looking, EPSG:32645. HH and HV terms exist in both frequency A (10 m) and frequency B (80 m). Selected term **HHHH / HH / frequency A** is real-valued, dimensionless diagonal covariance. Science image shape: 33840 × 34488; coordinates are pixel centers. Actual x spacing 10 m and y spacing −10 m, first center x=126725 m, y=3347275 m. Native fill is NaN in `_FillValue`; allocation fill is zero. Both are invalid for positive-power dB conversion.

Discovered paths used:

```
/science/LSAR/identification/{granuleId,zeroDopplerStartTime,zeroDopplerEndTime,productType,productLevel,productVersion,productDoi,trackNumber,frameNumber,absoluteOrbitNumber,orbitPassDirection,lookDirection,boundingPolygon}
/science/LSAR/GCOV/grids/frequencyA/HHHH
/science/LSAR/GCOV/grids/frequencyA/mask
/science/LSAR/GCOV/grids/frequencyA/numberOfLooks
/science/LSAR/GCOV/grids/frequencyA/{xCoordinates,yCoordinates,xCoordinateSpacing,yCoordinateSpacing,projection,listOfCovarianceTerms}
```

The actual inventory includes all source datasets, not only these paths. Mask descriptions are read from the source attributes; 0 and 255 are excluded. No cloud mask, rainfall record, optical scene or event ground truth is available here.

## Obtain source data

Search [ASF Vertex](https://search.asf.alaska.edu/) for NISAR GCOV track 98/frame 16 on the dates above, selecting the matching granule IDs and product release, or find the collection in [NASA Earthdata Search](https://search.earthdata.nasa.gov/). Downloads may require an Earthdata account. Direct per-granule download URLs were not supplied and are not invented. Place the matching local files at the project root, or edit `config.json` to point to their original filenames and raw directory; then run the audit on that directory before processing.

Demo assets are included locally so judging never depends on NASA availability. NASA data and Copernicus ancillary DEMs retain their own access/licensing terms; the Apache-2.0 code license does not relicense those products.
