# TerraPulse submission narrative draft

**Team:** DevAtMad  
**Target challenge:** Dancing with the SARs  
**Status:** Draft based on implemented local software; not submitted; eligibility/rules unconfirmed.

## Project description

TerraPulse makes radar surface change easier to investigate, explain and share. It turns compatible NASA–ISRO NISAR observations into an interactive record with acquisition playback, before/after comparison, measured change regions and a compact Change DNA profile. Rainfall, terrain and quality-screened Landsat imagery provide context. Transparent susceptibility and counterfactual modules expose their assumptions and contributions instead of presenting a confident disaster label.

## Problem and user benefit

A changed radar pixel is an observation, but users still need to ask when the change appeared, how large it was, whether it persisted and which environmental evidence supports further inspection. TerraPulse brings those questions together in one local, reproducible workspace. Its intended users are geospatial researchers, students and analysts reviewing surface changes. It is not validated for emergency warning or automated hazard decisions.

## Distinctive implemented contribution

Change DNA describes temporal behavior in physical units while preserving uncertain timing. In the supplied Nepal case, the successive anomaly mask contracts even though the baseline radar disturbance remains. TerraPulse explains why those signals differ, rather than falsely labeling the area recovered. A guided evidence story connects measurement, behavior, context and the validation gap. An exported evidence record retains source provenance and caveats.

## NASA data and supporting sources

NISAR L2 GCOV PROVISIONAL HH backscatter supplies three compatible dates on a fixed Kathmandu study grid. NASADEM supplies historical terrain; NASA POWER supplies regional hourly precipitation; NASA/GSFC's landslide catalog supplies an independent historical reference review. USGS Landsat 8/9 supplies thermal/optical context through Microsoft distribution. The added data downloads use explicit non-Chinese source/distribution hosts. NASA LHASA was consulted as methodological context; TerraPulse does not claim to reproduce its validated model.

## What is working

Local interactive radar investigation, three-date playback, measured region inspection, Change DNA, 3D terrain/2D fallback, keyboard map controls, real thermal/optical coverage, rainfall context, additive susceptibility explanations, flood counterfactual comparisons, local evidence export, source hashes, startup preflight and a portable runtime package.

## Testing and limitations

169 Python tests and 25 JavaScript logic tests pass. Analytical validators reproduce actual saved results and preserve 508 prior artifacts. Numerical and route tests do not substitute for browser visual QA, which remains blocked in the assistant environment; manual screenshots/video and a physical disconnected rehearsal remain to be completed.

Only three compatible radar visits and one tracked zone exist. Exact onset/recovery timing, similar historical events, independent event causes and calibrated susceptibility confidence cannot be established. The independent mapping used for the previously reviewed event lies outside the AOI; the application must be presented as a surface-change investigation, not a validated event reconstruction. NASA historical catalog coverage is insufficient for empirical spatial validation of the new landslide model.

## Three-minute presentation draft

**0:00–0:30:** “Radar lets us observe surface changes through cloud cover. TerraPulse helps us understand what those changes actually say.” Show the real NISAR source and acquisition dates.

**0:30–1:10:** Swipe or play the observations. Select the real tracked zone. Show its measured magnitude and candidate area.

**1:10–1:50:** Open Change DNA. Explain the onset bracket, observed persistence, contracting transition mask and censored recovery half-life. State that cause remains unverified.

**1:50–2:25:** Add terrain/rainfall/thermal context. Switch hillside and valley attention to explain different model assumptions; show component contributions rather than a prediction claim.

**2:25–3:00:** Export the evidence. Show that source files, formulas, versions and limits remain attached. End with the next scientific step: independent labels and event-relevant geographic validation.

## Before copying into a submission

Confirm the official challenge statement, event rules and treatment of existing work. Add actual browser screenshots/video and a final public repository/project link if you choose to publish. Do not describe this local build as already submitted, globally validated, operationally certified or guaranteed to win.
