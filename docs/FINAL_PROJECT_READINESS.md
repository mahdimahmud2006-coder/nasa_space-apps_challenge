# TerraPulse final project diagnosis and readiness

14 October 2026 · Local release 1.0.0 · Submission candidate for Dancing with the SARs.

## Outcome

The application includes implementations 01–07, a radar-led entry view, Change DNA, environmental context, transparent scenario/susceptibility models, local exports, a runtime preflight and a portable release builder. Existing analytical results have not been reset.

The strongest contribution is making the behavior of real radar changes understandable and auditable. Prediction claims would weaken the scientific case because labels/calibration are insufficient.

## Diagnosis → implemented improvement

| Issue found | Implemented response |
|---|---|
| Main view emphasized an inferred flood score over the challenge's measured radar | Home now opens on NISAR; its metrics show actual acquisition coverage, successive candidate area and zone magnitude. Inferred model panels are hidden in radar mode. |
| A contracting change mask could be mistaken for recovery | Change DNA separately displays baseline disturbance persistence, transition-mask contraction and return toward baseline. |
| Three dates could imply precise daily onset/half-life | Actual elapsed-time chart, onset bracket, sampled recovery crossing bracket, explicit censoring and missingness. |
| Similarity/confidence examples in plans could become invented outputs | Reference-only similarity implemented but unavailable for the one-zone case; empirical confidence stays null. |
| Rain windows risked repeated counting and hazard confusion | Disjoint rain windows; separate static/dynamic/radar components; additive explanations; shared-footprint comparison. |
| NASA catalog points might be treated as precise or unreported cells as negatives | Retained accuracy fields, rain-trigger filter, spatial blocks, minimum evidence requirements, null classification/calibration metrics. |
| Very small text and tight columns | 16 px main text, ≥14 px supporting text, wider desktop panels, large controls and stacked mobile layouts. |
| Terrain canvas required a pointer | Arrow pan, +/- zoom, Enter geographical inspection and Escape reset added and tested. |
| Missing assets/dependencies could produce an unexplained blank application | `make check-ready`, startup preflight, initialization failure messages and `/api/project` status. |
| A source checkout/release could omit essential ignored runtime rasters | Public COG/runtime-cube exceptions and an explicit release allowlist with SHA-256 manifest; extracted-release verification. |
| Old README described a smaller demo and overstated ready status | Rewritten around the final application, actual dependency requirements, test scope, source reproduction and remaining gaps. |

## Verified scope

- 169 Python tests; 25 JavaScript interaction/math/controller tests.
- All original radar, time-series, context, thermal, flood and new Change Lab analytical validators.
- 508 previously saved analytical artifacts preserved byte-for-byte.
- Real Handler checks for HTML/assets/new APIs, including all three landslide date probes.
- Local runtime preflight passes; no missing runtime files/dependencies. The portable package was extracted and its hashes and preflight checked; a new rainfall scenario computed successfully without raw source datasets, preserving the original packaged file hashes.
- Scientific map comparison visually inspected. It shows the intended different valley/hillside model patterns, but it is not independent hazard validation.

## Honest submission gaps

1. **Browser visual/accessibility/responsive/GPU QA:** automation access is blocked by the app's URL policy. Manually open all views at desktop and mobile widths, exercise controls, keyboard and 2D fallback, inspect clipping and capture actual screenshots/video. No alternate browser workaround was used.
2. **Physical disconnected rehearsal:** launch and exercise every feature with the network disconnected. Local-only code/assets are verified separately; actual disconnection has not been performed.
3. **Empirical susceptibility validation:** NASA historical references are too sparse/imprecise; no aligned 2026 positives/negatives exist. Present these modules as uncalibrated research indices. The plan's spatial validation completion criterion is not met.
4. **Geographic event alignment:** available independent UNOSAT impact polygons do not intersect this AOI. Present a radar investigation case, not a validated reconstruction of the Rasuwa event.
5. **Official challenge/rules:** the global 2026 challenge page returned HTTP 502. The [local organizer's summary](https://hackathlone.com/challenges/dancing-with-the-sars) describes interactive NISAR surface-change visualization and restricts pre-event project work. Confirm the official rules and disclose existing work before submitting. Existing work is not certified eligible.
6. **Publication/submission:** no project was uploaded, registered, submitted or deployed publicly. URLs in this project are local.

These gaps remain recorded even though the software is packaged as the final local project. A release version does not certify scientific accuracy, eligibility or completed visual QA.

## Suggested presentation sequence

1. Home: real radar, three compatible visits and measured evidence.
2. Timeline/comparison: actual before/after and discrete date playback.
3. Change Lab: one real zone; explain why a stable baseline disturbance and shrinking transition mask are compatible.
4. Terrain/rainfall/thermal: independent context and quality gaps.
5. Landslide/scenario: explain model contributions and assumptions explicitly.
6. Export: sources, versions, hashes and limits travel with the evidence.

Start and stop instructions are in the README. `make verify` performs the source-workspace verification; `make release` packages the local runtime. The extracted runtime has its own standard-library integrity verifier.
