# TerraPulse — Codex Implementation Masterplan

> Project team: **DevAtMad**  
> Project name: **TerraPulse**  
> Challenge: **Dancing with the SARs**  
> Primary data source: **NASA–ISRO NISAR L2 GCOV PROVISIONAL**  
> Initial case study: **Nepal Himalayan surface-change / flood-landslide impact investigation**

---

## 0. Mission

Build a scientifically defensible, offline-capable TerraPulse demo that:

1. ingests real NISAR GCOV `.h5` files,
2. verifies that the chosen observations are actually comparable,
3. computes surface-change evidence with deterministic Python code,
4. exposes the result as a before/after map, change overlay, quantitative area/statistics, evidence panel, and methods panel,
5. clearly labels NISAR data as **PROVISIONAL**,
6. never invents a disaster label unsupported by the data,
7. runs without internet during judging.

The primary product loop is:

```text
COMPARE → DETECT → MEASURE → EXPLAIN
```

The primary judge-facing demo loop is:

```text
before observation
    ↓
after observation
    ↓
before/after swipe
    ↓
SCAN REGION
    ↓
real computed change overlay
    ↓
click / inspect strongest region
    ↓
area + radar-change statistics + dates + dataset provenance
    ↓
methods + uncertainty
```

---

# 1. Non-negotiable implementation rules

## 1.1 Never guess the HDF5 schema

Do **not** hard-code dataset paths from memory.

Before writing extraction logic:

- inspect every `.h5` file,
- print its groups and datasets,
- inspect dimensions,
- inspect CRS/projection metadata,
- inspect nodata/fill values,
- inspect polarization names,
- inspect coordinate arrays / geotransform information,
- inspect acquisition metadata.

Only after confirming the actual structure may extraction code be implemented.

If two files differ in structure, stop and explain the difference before trying to normalize them.

---

## 1.2 Science must be deterministic

All scientific outputs must come from ordinary code, not an LLM.

Allowed:

- NumPy
- SciPy
- rasterio
- h5py
- pyproj
- shapely
- geopandas
- scikit-image if actually needed
- GDAL if already available / necessary

Do not use an LLM to decide:

- whether a pixel flooded,
- whether a pixel is a landslide,
- area in km²,
- threshold values,
- connected regions,
- radar-change magnitude,
- confidence.

An LLM may later explain already-computed results, but must not create scientific numbers.

---

## 1.3 Evidence first, interpretation second

The default output language should be:

- "strong radar backscatter change"
- "candidate surface-change region"
- "candidate inundation-compatible change"
- "surface-state change"

Avoid unsupported labels such as:

- "landslide detected"
- "flood detected"
- "disaster confirmed"

unless an explicit validation layer justifies the interpretation.

---

## 1.4 Offline-first

Judging must not depend on NASA servers or venue Wi-Fi.

The final app must be able to run with:

```bash
OFFLINE=1
```

All demo-critical inputs must exist locally.

---

## 1.5 Preserve provenance

Every quantitative result must retain:

- source file name,
- NISAR product name,
- acquisition timestamp,
- orbit / track / frame metadata if present,
- polarization,
- processing method,
- threshold / parameter values,
- software version / script version if practical,
- source URL / collection identifier when known,
- explicit `PROVISIONAL` status.

---

# 2. Expected repository structure

Create or adapt the repository toward this structure:

```text
terrapulse/
├── LICENSE
├── README.md
├── IMPLEMENTATION.md
├── SKILL.md
├── .gitignore
├── .env.example
├── Makefile
│
├── data/
│   ├── raw/
│   │   └── nisar/
│   │       ├── *.h5
│   │       └── README.md
│   ├── derived/
│   │   └── nepal_case_01/
│   └── demo_fixtures/
│
├── src/
│   ├── ingest/
│   │   ├── inspect_h5.py
│   │   ├── metadata.py
│   │   └── extract_gcove.py
│   ├── compute/
│   │   ├── align.py
│   │   ├── change.py
│   │   ├── threshold.py
│   │   ├── regions.py
│   │   ├── area.py
│   │   ├── uncertainty.py
│   │   └── validate.py
│   ├── export/
│   │   ├── rasters.py
│   │   ├── vectors.py
│   │   ├── evidence.py
│   │   └── previews.py
│   └── api/
│       └── app.py
│
├── tests/
│   ├── test_area.py
│   ├── test_change.py
│   ├── test_regions.py
│   ├── test_metadata.py
│   └── fixtures/
│
├── web/
│   ├── src/
│   └── public/
│       └── cases/
│
└── docs/
    ├── METHODOLOGY.md
    ├── DATASETS.md
    ├── VALIDATION.md
    ├── LIMITATIONS.md
    ├── AI_USE.md
    └── DEMO_RUNBOOK.md
```

Do not create every file immediately if the existing repository is simpler. Prefer the smallest structure that supports the required pipeline.

---

# 3. User involvement checkpoints

Codex should proceed autonomously except at these decision points.

## CHECKPOINT A — Dataset placement

The user will manually place downloaded NISAR `.h5` files into:

```text
data/raw/nisar/
```

Do not rename the original files.

Once files appear, inspect them immediately.

---

## CHECKPOINT B — Comparable observations

Codex must report whether the available files represent:

- same pass / neighboring granules,
- repeat passes on different dates,
- sufficiently overlapping footprints,
- matching or compatible polarization,
- compatible geometry / orbit direction,
- same product level.

If there is no valid repeat-pass pair, stop and tell the user exactly what acquisition/date/geometry is missing.

Do **not** fake a temporal comparison using two granules acquired seconds apart.

---

## CHECKPOINT C — Primary event framing

After visualizing the first valid pair, present one recommendation:

- `surface-change investigation`,
- `flood / surface-water investigation`,
- `ground-disturbance investigation`,
- or another evidence-supported framing.

The user chooses the final public-facing case description.

---

## CHECKPOINT D — Threshold / detection interpretation

Codex may propose candidate thresholds from the actual data distribution, but should show:

- histogram / quantiles,
- threshold candidates,
- resulting area,
- sensitivity to threshold.

The user should approve the final visible interpretation if it materially changes the story.

---

# 4. Phase 1 — Audit the raw NISAR files

## 4.1 First command

Once data is present:

```bash
find data/raw/nisar -maxdepth 1 -type f -name '*.h5' -print
```

Then inspect each file with a Python script.

Create:

```text
src/ingest/inspect_h5.py
```

The script must report:

- filename,
- file size,
- top-level groups,
- complete dataset path list,
- dataset shapes,
- dtypes,
- selected attributes,
- geospatial metadata,
- temporal metadata,
- polarization metadata.

Do not dump giant arrays.

Example output:

```text
FILE: ...
PRODUCT: ...
ACQUISITION START: ...
ACQUISITION END: ...
ORBIT: ...
TRACK/FRAME: ...
POLARIZATIONS: ...
CRS: ...
BOUNDS: ...
DATASETS:
  /science/... shape=(...) dtype=...
```

Save a machine-readable audit:

```text
data/derived/audit.json
```

---

# 5. Phase 2 — Decide which observations are comparable

Build a metadata table.

Each observation should have fields similar to:

```json
{
  "filename": "...",
  "acquisition_start": "...",
  "acquisition_end": "...",
  "product": "...",
  "orbit_direction": "...",
  "track": "...",
  "frame": "...",
  "polarizations": ["..."],
  "bounds_wgs84": [west, south, east, north],
  "crs": "...",
  "pixel_spacing": "...",
  "provisional": true
}
```

Then compute overlap between candidate pairs.

### Required checks

A pair is accepted only if:

- acquisition dates differ meaningfully,
- footprints overlap enough for analysis,
- data geometry is compatible,
- selected polarization exists in both files,
- CRS / grid differences can be resolved safely,
- nodata/fill values are understood.

Prefer matching:

```text
same track
same frame or compatible adjacent coverage
same orbit direction
same polarization
same product type
```

If the user has multiple granules from the same pass, mosaic them first and treat them as one observation date.

---

# 6. Phase 3 — Mosaic same-pass granules when necessary

If two or more granules share the same acquisition/pass and together cover the AOI:

1. extract the same science layer from each,
2. reproject only if required,
3. mosaic them into one observation raster,
4. preserve nodata,
5. record all contributing granule IDs.

Outputs:

```text
data/derived/nepal_case_01/t1_mosaic.tif
data/derived/nepal_case_01/t2_mosaic.tif
```

Do not mosaic different dates into one observation.

---

# 7. Phase 4 — Extract the actual GCOV measurement

Use the actual discovered GCOV dataset path.

Do not assume a particular polarization or array name.

Select the polarization that is:

- present in both observations,
- scientifically useful,
- easiest to interpret,
- and supported by the product metadata.

Record the exact HDF5 source path in:

```text
docs/DATASETS.md
```

and in case metadata.

---

# 8. Phase 5 — Crop to a defensible AOI

Start with a relatively small Nepal AOI around the region actually covered by both observations.

The AOI must satisfy:

- substantial overlap,
- manageable raster size,
- contains visually meaningful terrain / event area,
- avoids processing the entire granule if unnecessary.

Store the AOI as:

```text
data/derived/nepal_case_01/aoi.geojson
```

Do not select the AOI merely to maximize detected change.

Document why the AOI was chosen.

---

# 9. Phase 6 — Preprocessing

For each observation:

1. load the selected GCOV layer,
2. apply nodata/fill mask,
3. reject NaN / infinite values,
4. inspect data units,
5. transform to dB only if mathematically appropriate for the selected layer,
6. align both observations to a common analysis grid,
7. crop to common overlap,
8. preserve the transformation metadata.

If converting linear power-like values to dB:

```python
db = 10 * np.log10(value)
```

but only do this if the selected product layer is appropriate.

Never apply that conversion blindly.

---

# 10. Phase 7 — Baseline change metric

Implement the simplest scientifically defensible metric first.

Candidate metric:

```text
ΔdB = dB_after - dB_before
```

Also consider a ratio metric if more suitable:

```text
R = after / before
```

Save:

```text
change_raw.tif
```

Create a preview PNG.

Inspect distribution statistics:

- min,
- max,
- mean,
- median,
- standard deviation,
- percentiles,
- robust MAD.

---

# 11. Phase 8 — Candidate change mask

Do **not** begin with machine learning.

Start with transparent thresholding.

Possible strategy:

```text
absolute change
    ↓
robust threshold
    ↓
morphological cleanup
    ↓
connected components
    ↓
minimum-area filter
```

Threshold options may include:

- robust z-score,
- percentile threshold,
- MAD-based threshold,
- domain-specific threshold if justified.

Every threshold must be configurable.

Example config:

```yaml
change:
  metric: delta_db
  threshold_method: mad
  threshold_value: 3.0
  min_region_pixels: 100
```

Do not embed unexplained magic numbers.

---

# 12. Phase 9 — Noise cleanup

Possible operations:

- median filter,
- morphological opening,
- morphological closing,
- connected-component removal.

Use the minimum needed.

Do not over-smooth mountainous terrain.

Write all applied operations to the evidence metadata.

---

# 13. Phase 10 — Connected regions and ranking

Vectorize or label significant connected regions.

For each region calculate:

- pixel count,
- area in km²,
- mean change,
- median change,
- peak absolute change,
- bounding box,
- centroid,
- quality flags.

Rank by a transparent score, for example:

```text
region score = area × robust mean magnitude
```

If such a score is used, document it.

Prefer simply ranking by:

1. area,
2. magnitude,

before inventing a compound score.

---

# 14. Phase 11 — Area calculation

Area must be calculated from actual pixel geometry.

If projected pixels are square with known meter resolution:

```python
area_km2 = pixel_count * pixel_width_m * pixel_height_m / 1_000_000
```

If not, use a geodesic or equal-area approach.

Never assume `10 m` pixels.

Read pixel spacing from the actual file / transformation.

---

# 15. Phase 12 — Tests

At minimum implement:

## test_area.py

Synthetic mask:

```text
100 pixels
pixel size = 30 m × 30 m
```

Expected:

```text
0.09 km²
```

Verify exactly within floating-point tolerance.

## test_change.py

Test that:

- identical arrays produce zero change,
- known additive differences produce expected delta,
- nodata does not generate false change.

## test_regions.py

Test:

- small connected regions are removed,
- large ones remain,
- area matches known synthetic geometry.

## test_metadata.py

Ensure:

- acquisition dates are parsed correctly,
- two same-pass granules are not mistaken for two temporal observations.

Run:

```bash
pytest -q
```

Science tests must pass before frontend polishing.

---

# 16. Phase 13 — Uncertainty and sensitivity

For the selected threshold, compute sensitivity.

Example:

```text
threshold -10%
nominal threshold
threshold +10%
```

Report resulting total changed area.

Example evidence:

```json
{
  "nominal_area_km2": 18.7,
  "sensitivity_area_km2": {
    "lower_threshold": 22.4,
    "nominal": 18.7,
    "higher_threshold": 14.9
  }
}
```

Do not label this as formal statistical confidence unless it truly is.

Use wording such as:

```text
Threshold sensitivity
```

rather than:

```text
95% confidence
```

unless statistically justified.

---

# 17. Phase 14 — Validation

Validation is mandatory before calling a region "flood" or "landslide".

Possible validation sources:

- known disaster reports,
- optical imagery where cloud-free,
- NASA GIBS context imagery,
- existing event maps,
- reputable government / UN / scientific sources.

Validation outcomes should be one of:

```text
SUPPORTED
PARTIALLY SUPPORTED
UNVERIFIED
CONTRADICTED
```

Store:

```text
docs/VALIDATION.md
```

and per-region validation fields.

---

# 18. Phase 15 — Export map-ready artifacts

Generate:

```text
data/derived/nepal_case_01/
├── before.tif
├── after.tif
├── change_raw.tif
├── change_mask.tif
├── change_regions.geojson
├── before.webp
├── after.webp
├── change.webp
├── evidence.json
├── metadata.json
├── methodology.json
└── aoi.geojson
```

For the web demo, prefer lightweight assets.

If live COG tiling is too fragile, pre-render the exact assets needed for judging.

The science stays real even if the visualization is pre-rendered.

---

# 19. Evidence JSON schema

Recommended shape:

```json
{
  "case_id": "nepal_case_01",
  "title": "Nepal Himalayan Surface-Change Investigation",
  "dataset": {
    "mission": "NASA-ISRO NISAR",
    "product": "L2 GCOV PROVISIONAL",
    "provisional": true,
    "source_files": ["...", "..."],
    "polarization": "...",
    "acquisition_before": "...",
    "acquisition_after": "..."
  },
  "analysis": {
    "metric": "delta_db",
    "threshold_method": "...",
    "threshold_value": 0,
    "min_region_pixels": 0
  },
  "summary": {
    "changed_area_km2": 0,
    "region_count": 0
  },
  "regions": [
    {
      "id": 1,
      "area_km2": 0,
      "mean_change_db": 0,
      "median_change_db": 0,
      "peak_abs_change_db": 0,
      "interpretation": "candidate surface-change region",
      "validation_status": "UNVERIFIED"
    }
  ],
  "limitations": [
    "NISAR product is provisional",
    "Radar change does not uniquely identify cause"
  ]
}
```

Never put placeholder zeros into the final demo. Replace only with actual computed values.

---

# 20. Phase 16 — Web application

The first real application should have only the interactions that matter.

## Layout

```text
┌─────────────────────────────────────────────────────────┐
│ TerraPulse                                              │
├────────────┬──────────────────────────┬─────────────────┤
│ Controls   │ Map / comparison         │ Evidence        │
│            │                          │                 │
│ case       │ before / after           │ dates           │
│ layers     │ change overlay           │ area            │
│ scan       │ swipe                    │ metric          │
│ timeline   │                          │ method          │
└────────────┴──────────────────────────┴─────────────────┘
```

---

# 21. Killer demo interaction

The core interaction should be reproducible:

1. open Nepal case,
2. show `BEFORE`,
3. switch/show `AFTER`,
4. drag before/after swipe,
5. press `SCAN REGION`,
6. yellow radar animation runs,
7. computed change overlay fades in,
8. total changed area appears,
9. click strongest region,
10. evidence panel updates,
11. open methodology drawer.

The yellow scanning animation is presentation only.

The overlay and numbers after it must come from the actual preprocessing pipeline.

---

# 22. Methods panel

Display:

- NISAR product name,
- `PROVISIONAL`,
- granule IDs,
- acquisition dates,
- selected polarization,
- common AOI,
- preprocessing operations,
- change metric,
- threshold method/value,
- minimum region size,
- area calculation method,
- uncertainty/sensitivity note,
- validation status,
- known limitations.

This panel is a feature, not fine print.

---

# 23. Timeline

Only add timeline mode if there are 3+ valid repeat observations.

If only two dates are valid:

- keep before/after,
- do not fake a timeline.

For 3+ dates, support:

```text
T1 → T2 → T3
```

and calculate metrics per date pair.

---

# 24. API

The simplest version may serve static JSON and files directly.

Only build FastAPI if useful.

Possible endpoints:

```text
GET /api/cases
GET /api/cases/nepal_case_01
GET /api/cases/nepal_case_01/evidence
GET /api/cases/nepal_case_01/regions
GET /api/cases/nepal_case_01/methodology
```

No NASA calls during the demo.

---

# 25. Offline mode

Implement:

```bash
OFFLINE=1
```

When active:

- disable acquisition calls,
- serve only local case assets,
- show a small `LOCAL DEMO DATA` or `CACHED` badge if desired,
- never fail because Earthdata is unavailable.

Test with Wi-Fi actually disabled.

---

# 26. Commands

Prefer simple commands.

Example Makefile:

```make
inspect:
	python -m src.ingest.inspect_h5 data/raw/nisar

process:
	python -m src.compute.pipeline --case nepal_case_01

test:
	pytest -q

demo:
	OFFLINE=1 python -m src.api.app

web:
	cd web && npm run dev
```

Adapt to the repository rather than forcing this exact structure.

---

# 27. Required documentation

## README.md

Must explain:

- what TerraPulse does,
- team: DevAtMad,
- challenge,
- how to run,
- primary dataset,
- provisional status,
- case study,
- architecture,
- limitations,
- exact demo command.

## docs/DATASETS.md

Must contain:

- NASA dataset name,
- collection/product identifier,
- granule filenames,
- acquisition dates,
- access URL,
- selected HDF5 paths,
- polarization.

## docs/METHODOLOGY.md

Must explain the actual processing steps.

## docs/LIMITATIONS.md

Must explicitly state:

- NISAR product provisional,
- limited validation,
- SAR interpretation ambiguity,
- threshold sensitivity,
- terrain effects if applicable,
- no automatic causal attribution.

## docs/AI_USE.md

Record AI assistance honestly:

- code assistance,
- design assistance,
- documentation,
- prompts / workflow summary where appropriate.

---

# 28. Open-source requirements

Use an OSI-approved license.

Default:

```text
Apache-2.0
```

Do not commit:

- Earthdata credentials,
- bearer tokens,
- `.netrc`,
- secrets.

Add raw giant `.h5` files to `.gitignore`.

Document how a reviewer can obtain them.

Commit only the minimum derived demo fixtures needed.

---

# 29. Performance strategy

Do not make the browser read multi-GB HDF5 files.

Processing happens offline once.

Web app reads:

- compact rasters,
- webp/png previews,
- GeoJSON,
- JSON.

If COG serving is fast and reliable locally, use it.

Otherwise use pre-rendered imagery.

Reliability wins.

---

# 30. Failure ladder

## Failure A — no valid repeat pair

Stop.

Report:

- what files exist,
- which geometry/date is missing,
- exact acquisition type needed.

Do not build a fake change result.

---

## Failure B — valid pair but weak change signal

Try:

1. smaller / better AOI,
2. alternate common polarization,
3. alternate repeat pair,
4. alternative transparent metric.

Do not tune until a desired disaster-shaped answer appears.

---

## Failure C — strong surface change but ambiguous cause

Keep the project.

Frame it as:

```text
surface-change prioritization
```

Add contextual validation separately.

---

## Failure D — map tiling too fragile

Export static tiles / imagery.

Keep:

- swipe,
- overlay,
- area,
- evidence,
- methodology.

---

## Failure E — only one excellent case works

Ship one excellent case.

Do not weaken the product by adding fake flood/glacier/forest modes.

---

# 31. Final acceptance criteria

The implementation is ready only when all of the following are true.

## Data

- [ ] at least two different-date observations are verified,
- [ ] common overlap is verified,
- [ ] selected layer path is derived from actual HDF5 inspection,
- [ ] polarization is documented,
- [ ] all source granule IDs are preserved.

## Science

- [ ] change metric is deterministic,
- [ ] threshold is documented,
- [ ] nodata handled,
- [ ] region cleanup documented,
- [ ] area derived from real pixel geometry,
- [ ] tests pass,
- [ ] sensitivity / uncertainty is shown,
- [ ] no unsupported causal classification.

## Demo

- [ ] before/after swipe works,
- [ ] scan animation works,
- [ ] actual change overlay appears,
- [ ] actual computed area/statistics appear,
- [ ] evidence panel works,
- [ ] methods panel works,
- [ ] `PROVISIONAL` visible,
- [ ] works offline.

## Submission

- [ ] repo public,
- [ ] OSI license present,
- [ ] README complete,
- [ ] NASA dataset clearly named,
- [ ] sources cited,
- [ ] AI use documented,
- [ ] no secret credentials committed.

---

# 32. Codex first-run procedure

When this repository is opened with the NISAR `.h5` files already pasted in:

1. read `SKILL.md`,
2. inspect the repository,
3. list raw `.h5` files,
4. run / create HDF5 audit tooling,
5. produce a concise dataset audit,
6. identify valid temporal pair candidates,
7. **before implementing change detection, report the chosen pair and why it is comparable**,
8. continue automatically if the choice is unambiguous,
9. otherwise ask the user to choose only if multiple scientifically different options exist.

The first milestone is not a beautiful UI.

The first milestone is:

```text
two verified NISAR observations
+
one aligned AOI
+
one real radar-change raster
```

Everything else builds on that.

---

# 33. Product philosophy

Keep these constraints visible throughout implementation:

```text
REAL > BROAD
EVIDENCE > CLAIMS
ONE VERIFIED CASE > FIVE MOCK MODES
DETERMINISTIC SCIENCE > AI MAGIC
OFFLINE RELIABILITY > LIVE FRAGILITY
NISAR-FIRST > NASA-BRANDED
```

TerraPulse succeeds when a skeptical judge can ask:

> "Where did this number come from?"

and the application can answer exactly.
