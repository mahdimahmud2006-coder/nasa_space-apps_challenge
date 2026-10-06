---
name: terrapulse-nisar-implementation
description: >
  Implement and validate TerraPulse using real NASA-ISRO NISAR GCOV data.
  Use when ingesting NISAR HDF5 files, building change detection, producing
  evidence artifacts, integrating the TerraPulse map, or preparing the
  offline NASA Space Apps demo. Inspect real files before coding, keep
  scientific computation deterministic, preserve provenance, and never
  invent HDF5 paths, metadata, classifications, or results.
license: Apache-2.0
---

# TerraPulse NISAR Implementation Skill

## Purpose

Build the smallest scientifically defensible TerraPulse implementation from the
actual NISAR files present in the repository.

Primary goals:

1. inspect reality before assuming structure,
2. produce one verified temporal surface-change workflow,
3. preserve provenance for every result,
4. separate measurement from interpretation,
5. keep the demo offline-capable,
6. verify the science before polishing the UI.

---

# Operating loop

Always follow:

```text
UNDERSTAND
→ INSPECT
→ VERIFY INPUTS
→ REDUCE SCOPE
→ IMPLEMENT SCIENCE
→ TEST
→ VALIDATE
→ EXPORT
→ INTEGRATE UI
→ OFFLINE TEST
→ REVIEW
```

Do not skip `INSPECT`, `VERIFY INPUTS`, or `TEST`.

---

# Rule 1 — Never invent the HDF5 structure

Before using any dataset path:

```python
/file/group/dataset
```

verify that it exists in the actual `.h5` file.

Never rely on remembered NISAR schemas.

Required first action when new data appears:

```bash
find data/raw/nisar -type f -name '*.h5' -print
```

Then inspect:

- groups,
- datasets,
- shapes,
- dtypes,
- attributes,
- CRS,
- geotransform / coordinates,
- fill values,
- acquisition metadata,
- polarization.

If the required field cannot be found, report it as unknown.

Do not fabricate a substitute.

---

# Rule 2 — Distinguish granules from observations

Two files are not automatically two time points.

Before change detection, verify:

- acquisition timestamp,
- temporal separation,
- orbit direction,
- track/frame,
- footprint,
- polarization,
- product type.

Granules acquired seconds apart are normally pieces of the same pass.

Mosaic them if necessary.

Do not use them as before/after.

---

# Rule 3 — Pick the smallest valid case

The default target is:

```text
one event
one AOI
two valid dates
one common polarization
one change metric
one excellent demo
```

Do not implement global live processing first.

Do not implement flood + landslide + glacier + forest simultaneously.

Add breadth only after the first case passes verification.

---

# Rule 4 — Science is deterministic

All scientific numbers must come from deterministic code.

Use ordinary numerical / geospatial libraries.

An LLM must never calculate or infer:

- affected area,
- pixel classification,
- backscatter change,
- threshold,
- confidence,
- region ranking,
- disaster type.

AI may explain a result **after** it is computed.

---

# Rule 5 — Measurement before interpretation

Preferred terminology:

```text
candidate surface-change region
strong radar-change region
surface-water-compatible signal
observed backscatter change
```

Avoid:

```text
landslide detected
flood confirmed
disaster identified
```

unless independent validation supports that statement.

Every interpretation must be traceable to evidence.

---

# Rule 6 — NISAR is PROVISIONAL

Any interface, README, methods panel, or video text referring to current NISAR
products must include:

```text
PROVISIONAL
```

Also state that validation is limited where relevant.

Never present provisional NISAR output as operationally certified.

---

# Rule 7 — Preserve provenance

Every derived artifact must be able to answer:

```text
Which source files?
Which acquisition dates?
Which product?
Which polarization?
Which HDF5 dataset path?
Which AOI?
Which preprocessing?
Which metric?
Which threshold?
Which area method?
Which software produced it?
```

Store this in JSON / Markdown next to the output.

No unexplained numbers in the UI.

---

# Rule 8 — Never assume pixel area

Never use a hard-coded pixel resolution such as `10 m` unless verified from the
actual raster/grid.

For area:

- use actual affine transform if projected,
- or use an equal-area/geodesic method if necessary.

Test the area calculation with a synthetic mask.

---

# Rule 9 — Start with transparent change detection

Default sequence:

```text
before
after
↓
common mask
↓
common grid
↓
change metric
↓
robust threshold
↓
minimal cleanup
↓
connected regions
↓
area/statistics
```

Do not start with deep learning.

Do not add ML simply to make the project sound advanced.

---

# Rule 10 — Thresholds require evidence

A threshold must be:

- configurable,
- documented,
- derived from the actual data distribution or justified scientifically,
- sensitivity-tested.

Never copy a threshold from a Sentinel-1 tutorial into NISAR blindly.

For each threshold, inspect:

- histogram,
- quantiles,
- robust spread,
- map output,
- resulting changed area.

---

# Rule 11 — Keep preprocessing minimal

Only apply operations that are necessary and explainable.

Examples:

- nodata masking,
- dB conversion when appropriate,
- reprojection/alignment,
- light median filtering,
- morphological cleanup,
- minimum connected-region filtering.

Every operation must have a reason.

Do not create a complicated pipeline that cannot be defended in judging.

---

# Rule 12 — Tests before UI polish

Minimum tests:

```text
test_area
test_identical_arrays_zero_change
test_known_delta
test_nodata
test_connected_component_filter
test_metadata_date_parsing
test_same_pass_not_temporal_pair
```

If science tests fail, do not move on to animations or styling.

---

# Rule 13 — Validate interpretations

Change detection does not prove cause.

When public-facing language says flood, landslide, erosion, deformation, etc.,
validate using at least one independent contextual source where practical.

Store a validation status:

```text
SUPPORTED
PARTIALLY_SUPPORTED
UNVERIFIED
CONTRADICTED
```

Never silently convert `UNVERIFIED` to a strong claim.

---

# Rule 14 — Offline-first demo

The demo must not depend on Earthdata availability.

Required:

```text
OFFLINE=1
```

Demo-critical assets must be local.

Preferred architecture:

```text
NASA acquisition
    ↓
local raw cache
    ↓
deterministic preprocessing
    ↓
small derived artifacts
    ↓
local API/static assets
    ↓
TerraPulse frontend
```

No live NASA fetch is required during judging.

---

# Rule 15 — Optimize for the killer demo

Protect this interaction above all optional features:

```text
open verified case
→ before
→ after
→ swipe
→ SCAN REGION
→ yellow radar sweep
→ real change overlay
→ area/statistics
→ evidence
→ methodology
```

If behind schedule, cut in this order:

1. geographic scope,
2. number of dates,
3. optional analysis modes,
4. advanced interactivity,
5. live queries.

Never cut the real evidence pipeline before decorative features.

---

# Rule 16 — Yellow scan is presentation, not science

The scanning animation may be dramatic.

But it must never pretend to be computing live if the result is precomputed.

Allowed UI copy:

```text
Loading processed change evidence…
Rendering verified change regions…
```

Avoid misleading copy such as:

```text
AI scanning the Earth live…
```

unless that is literally true.

---

# Rule 17 — Prefer precomputed reliability

For judging, it is acceptable and preferred to preprocess data before the demo.

Large NISAR HDF5 files stay out of the browser.

The frontend should consume:

- compact rasters,
- tiles,
- previews,
- GeoJSON,
- JSON evidence.

A precomputed result is not fake if it was produced by the documented real
pipeline.

---

# Rule 18 — No fake multi-mode UI

Do not show clickable flood/glacier/forest/deformation modes that have no real
backend result.

If only Nepal works:

```text
Nepal — verified case
```

may be the only enabled case.

Other modes may appear only as clearly labeled:

```text
planned
future workflow
```

or be omitted.

---

# Rule 19 — Keep the repository judgeable

A reviewer should quickly find:

```text
src/compute/
tests/
docs/METHODOLOGY.md
docs/DATASETS.md
docs/LIMITATIONS.md
docs/AI_USE.md
```

Scientific code should be physically separate from explanation/AI code.

Make the path from source data to result obvious.

---

# Rule 20 — Handle credentials safely

Never commit:

- Earthdata username,
- Earthdata password,
- `.netrc`,
- bearer token,
- API secrets.

Use:

```text
.env.example
```

only for variable names.

Large raw `.h5` files should normally be gitignored.

---

# Required first-run behavior

When Codex opens the project after the user has copied datasets:

## Step 1

Read:

```text
IMPLEMENTATION.md
SKILL.md
README.md
```

if present.

## Step 2

Inspect repository structure.

Do not reorganize it unnecessarily.

## Step 3

Locate `.h5` files.

## Step 4

Audit the actual HDF5 structures.

## Step 5

Produce a concise report:

```text
DATASET AUDIT
- files:
- acquisition dates:
- same-pass groups:
- candidate repeat pairs:
- overlap:
- common polarizations:
- candidate AOI:
- blockers:
```

## Step 6

Select the best repeat pair only if clearly supported.

If ambiguous, ask one precise question.

## Step 7

Build the minimal science pipeline.

## Step 8

Run tests.

## Step 9

Generate the first real artifacts:

```text
before preview
after preview
raw change
change mask
regions
evidence JSON
```

## Step 10

Only after those exist, integrate with TerraPulse UI.

---

# Stop conditions

Stop implementation and report instead of guessing if:

- no temporal repeat pair exists,
- there is no meaningful footprint overlap,
- product layers cannot be identified,
- polarization cannot be matched,
- CRS cannot be interpreted safely,
- a required number would need to be invented,
- the science result contradicts the desired story.

Scientific contradiction is not a bug to hide.

---

# Review checklist

Before declaring a milestone complete, ask:

## Input integrity

- Did I inspect the actual files?
- Am I using real different-date observations?
- Are the footprints actually overlapping?

## Scientific integrity

- Is every number computed?
- Is the metric defensible?
- Is threshold choice documented?
- Are nodata and projection handled?
- Is area calculation tested?

## Interpretation integrity

- Did I separate observed change from event cause?
- Is validation status explicit?
- Is `PROVISIONAL` visible?

## Demo integrity

- Does it work with Wi-Fi off?
- Can a judge reproduce the core flow?
- Can every number be traced to source files?

## Scope integrity

- Did I avoid unnecessary features?
- Is one strong case better than several weak ones?

---

# Definition of done

A TerraPulse implementation is not done because the map looks good.

It is done when:

```text
real NISAR source
→ verified temporal pair
→ deterministic change calculation
→ tested quantitative output
→ preserved provenance
→ honest uncertainty
→ offline interactive demo
```

and every visible scientific claim can be defended.
