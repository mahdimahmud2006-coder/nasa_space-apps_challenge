# Research and design decisions — TerraPulse 04/05

Date: 2026-10-14. The user requested research and brainstorming before implementing the flood scenario explorer, explainable escalation score, thermal context, and a stronger visual experience. The attached plans define feature requirements; their example areas, scores and confidence values were not copied into results.

## Findings that changed the implementation

| Finding | Why it matters | Implemented response |
|---|---|---|
| The existing case has three compatible acquisitions across 24 days, not a three-day simulation. | Playback cannot create daily radar observations. | Discrete acquisition playback plus a separate 32-day observed/regional precipitation record. |
| The study AOI has zero overlap with the available independent UNOSAT impact mapping. | That mapping cannot spatially validate the current case. Absence of mapped overlap does not prove absence of physical impact. | A visible geographic check, regional footprint locator, archived source hashes, and no automatic event-validation upgrade. |
| The reported August event involves an upstream ice-avalanche/damming mechanism. | A local rainfall index cannot reconstruct the event's trigger or flood-wave hydraulics. | Explicit model scope: counterfactual rainfall susceptibility, not event reconstruction or flood depth. |
| POWER precipitation has a roughly 50–60 km native grid. | Reprojection to 30 m cannot create neighborhood rainfall detail. | Source resolution remains visible; model spatial variation comes from terrain/radar, with no invented fine-scale rainfall. |
| Min/max normalization recalculated for each scenario can cancel a rainfall multiplier. | A seemingly working slider could have little or no physical effect on its rainfall term. | Fixed, disclosed reference scales; monotonic bounded normalization; all-pixel monotonicity checks. |
| R24, R72 and R168 overlap. | Naively treating them as independent predictors can repeatedly count the same rainfall. | Disjoint 0–24, 24–72 and 72–168 h predictors; a separately disclosed recency-weighted feature. Correlation still remains and is acknowledged. |
| Full-series persistence includes later observations. | An earlier-date score could silently use future data. | Backscatter-decrease repetition uses only acquisitions at or before the selected date. |
| A radar backscatter decrease is ambiguous. | It can reflect several surface/geometry effects and is not a validated flood mask. | Low-weight decrease evidence, explicit terminology, and no water/flood classification. |
| No independently labeled repeat flood cases are supplied. | Historical sensitivity, probabilities, confidence and calibration metrics cannot be fabricated. | Historical sensitivity unavailable; empirical confidence and validation metrics null; effective feature weights disclosed. |
| Event-period thermal scenes are cloudy and uncertain. | A full-frame interpolated heatmap would imply observations where none exist. | Real USGS Landsat thermal/optical subsets, QA masks, uncertainty screening, actual dates, coverage percentages, and visible missing-data hatching. |
| The interface focused on images rather than questions. | Users could not easily investigate “where?”, “why?” or “what if?”. | A unified terrain/evidence studio, ranked analysis tiles, geographic point inspection, additive contributions, counterfactual comparison and evidence export. |

## Primary research sources

- [USGS Landsat Collection 2 Surface Temperature](https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature): Kelvin conversion, cloud/emissivity limitations and product scope. Temperature is a land-surface retrieval, not air temperature.
- [USGS Landsat QA bands](https://www.usgs.gov/landsat-missions/landsat-collection-2-quality-assessment-bands): pixel cloud/shadow/snow flags, radiometric/terrain flags and reported ST_QA uncertainty.
- [USGS Landsat band designations](https://www.usgs.gov/faqs/what-are-band-designations-landsat-satellites): native TIRS detail is 100 m, delivered resampled at 30 m.
- [NASA POWER hourly API](https://power.larc.nasa.gov/docs/services/api/temporal/hourly/): hourly average precipitation rates in mm/hour; UTC must be requested explicitly.
- [NASA POWER download guidance](https://power.larc.nasa.gov/docs/tutorials/service-data-request/api/): native meteorological resolution and data revision considerations.
- [NASA NISAR SAR overview](https://science.nasa.gov/mission/nisar/get-to-know-sar/): the dependence of backscatter on physical scattering properties; radar brightness alone is not a universal water label.
- [USACE terrain requirements for hydraulic modeling](https://www.hec.usace.army.mil/confluence/rasdocs/rmum/6.1/terrain-layer): representative channels, bathymetry, structures and hydraulic geometry are needed for meaningful flood-depth modeling.
- [WHO's Nepal event overview](https://www.who.int/nepal/emergencies/2026-rasuwa-flash-floods): preliminary upstream ice-avalanche/temporary-damming context. This source is used for model-scope interpretation, not as a raster dataset or training label.
- [NSET's Rasuwa debris-flood account](https://nset.org.np/disaster/rasuwa-flood/): the avalanche/debris-flow cascade and secondary impoundment concerns. This does not validate the current AOI's radar candidates.

The previously cached UNOSAT/UNITAR archive, distributed through UNESCO, contains preliminary mudflow/rockflow footprints. It is not a repeated flood-history training set or an open-water classification. Exact intersection with the existing AOI is **0 km²**; the nearest mapped footprint is about **5.65 km** from its boundary. The locator uses simplified display polygons while computing intersection from the original archived geometry.

## Brainstorm and selected experience

| Idea | Value | Decision |
|---|---|---|
| True terrain height mesh with colored evidence layers | Makes topography and valley context understandable without inventing terrain. | Implemented using NASADEM and local WebGL, with a 2D fallback and labeled 4× height exaggeration. |
| Real thermal and optical views | Demonstrates sensor complementarity and why cloud-independent radar is valuable. | Implemented with actual Landsat acquisitions; clouds/uncertainty remain visible. Thermal is excluded from the score. |
| Rainfall-intensity scenario controls | Gives users an active, testable question. | Implemented as a counterfactual replay of actual prior hourly rates. |
| A moving modeled flood-water surface | Could look dramatic but would imply unsupported water levels or dynamics. | Not implemented; the displayed result is a susceptibility index. |
| Explainability at a clicked location | Turns a heatmap into inspectable evidence. | Implemented with geographic cell picking, raw terrain/rainfall values and additive score contributions. |
| Ranked analysis tiles | Helps users find locations rather than search a whole map. | Implemented with explicitly labeled 1.2 km analysis tiles; no settlement/exposure claim. |
| Calibrated flood probability or “high confidence” labels | Requires independent labels and validation. | Not claimed. Model confidence and calibration statistics remain unavailable. |
| Regional source-footprint comparison | Makes a fundamental evidence gap visible. | Implemented as a geographic evidence dialog instead of concealing the mismatch. |

The intended demo path is: select a real acquisition → inspect terrain/radar/thermal coverage → inspect a ranked tile or cell → change rainfall/wetness assumptions → compare the same-date baseline with the counterfactual → inspect contributions → export the evidence and model identity.

## Remaining scientific priorities

An event-validation workflow needs an appropriately located AOI, independent reference observations covering that AOI, and labeled positive/negative cases with temporal separation. Flood-depth or flood-wave work additionally needs catchment/discharge and hydraulic information. The present implementation exposes these gaps and does not present the Kathmandu study case as a validated reconstruction of the Rasuwa disaster.
