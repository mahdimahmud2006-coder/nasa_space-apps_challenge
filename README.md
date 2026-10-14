# TerraPulse

**NISAR surface-change investigation · DevAtMad · Dancing with the SARs**

TerraPulse turns compatible NASA–ISRO NISAR radar observations into an interactive, traceable record of surface change. Its final local application includes radar comparison, acquisition playback, Change DNA, terrain/rainfall context, Landsat thermal/optical views, explainable flood counterfactuals and dynamic landslide susceptibility.

The application uses real data and deterministic computation. NISAR products remain **PROVISIONAL**, causes remain **UNVERIFIED**, and susceptibility models remain **UNCALIBRATED**. Application completeness does not establish operational hazard forecasting or competition eligibility.

## Run the project

The existing workspace already has the scientific environment and runtime assets:

```bash
cd "/home/mahdi-mahmud/Downloads/DATASET NASA/NEPALv1"
make run
```

Open [TerraPulse](http://127.0.0.1:8000/). The launcher checks dependencies/assets first, then serves locally. Use `Ctrl+C` to stop. To choose another port:

```bash
./run.sh --port 8001
```

On a new computer, install Python 3.14 (tested), create the environment, and install the pinned requirements once:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
./run.sh
```

Python 3.12+ is declared in project metadata; 3.14 is the verified environment. Internet is needed for the initial dependency install and optional dataset downloads. Runtime processing uses local data and requires no API key, cloud inference, Earthdata login, CDN, font service or map-tile provider. Node.js is only required for JavaScript development tests.

A modern desktop browser and 8 GB RAM are a practical starting point; 16 GB is recommended for comfortable reprocessing alongside the browser. These are planning estimates, not minimum-hardware benchmarks. WebGL enables 3D terrain; a 2D canvas fallback is provided. Raw-source rebuilding requires substantially more disk space than the packaged application.

## Use the application

- **Evidence Studio `/`** starts with actual NISAR HH radar, measured acquisition coverage, successive candidate area and tracked-zone baseline magnitude. Model layers have their own labels and explanations.
- **Change Lab `/change-lab.html`** explains the tracked zone's onset bracket, magnitude, contraction, persistence and recovery. A guided story links this behavior to separate terrain, rainfall and radar-supported landslide layers.
- **Timeline `/timeseries.html`** provides discrete date-range playback and environmental/zone context. Missing acquisition dates are not interpolated.
- **Radar comparison `/comparison.html`** provides before/after swipe, threshold-dependent candidate masks, region inspection and source provenance.

Map controls support mouse/touch. Focus a terrain canvas and use arrow keys to pan, `+`/`-` to zoom, `Enter` to inspect the center and `Escape` to reset. Evidence can be exported locally as JSON, with model versions and source hashes.

## What the case contains

The fixed Kathmandu study AOI is 24 × 24 km, EPSG:32645. Three compatible track 98/frame 16/40 MHz/HH observations cover **19 Aug, 31 Aug and 12 Sep 2026**. Other supplied dates were audited and excluded where geometry or acquisition configuration differs.

| Evidence | Actual scope |
|---|---|
| NISAR | Native 10 m gamma-0 HH backscatter; one tracked successive-change zone |
| Change DNA | Peak 7.5263 dB mean absolute baseline change; 100% observed post-onset disturbance persistence; ~5.97% return toward baseline by latest visit |
| Recovery timing | Half-recovery not observed within 12 days after peak; right-censored |
| Terrain | Historical NASADEM; aligned 30 m derivatives and modeled buffered drainage |
| Rainfall | NASA POWER hourly regional estimates; native 0.5° × 0.625°, approximately 50–60 km |
| Thermal/optical | Four actual USGS Landsat scenes, quality screened; independent acquisition dates and gaps disclosed |
| Landslide reference | 10 NASA catalog nominal AOI reports; only 2 meet the ≤1 km precision screen, too few for spatial validation |

The successive candidate mask contracts while baseline radar disturbance persists. These are different measurements, and TerraPulse shows both. It does not identify the disturbance's physical cause.

Available independent UNOSAT impact mapping has zero overlap with this AOI. It does not validate this case or prove absence of impacts. The reported upstream Rasuwa avalanche/debris-flood mechanism is not reproduced by local rainfall indices.

## Verify and rebuild

```bash
make check-ready       # Fast local runtime preflight
make test              # 169 Python tests
make test-ui           # 25 JavaScript logic tests; Node.js required
make verify            # Full-source checks and all analytical validators
make change-lab        # Rebuild DNA and landslide outputs from retained inputs
make validate-change-lab
```

Individual source workflows remain available: `make process`, `make timeseries`, `make context`, `make thermal`, `make flood`. They require the retained raw/cached scientific inputs. Source download commands use explicit NASA/Microsoft allowlists; the NASA landslide subset also retains only approved non-Chinese report-source hosts. No Chinese government/agency dataset endpoint is used for the added context/reference datasets.

**Verification limits:** automated numerical/route/interaction checks pass; browser visual/responsive QA is blocked by the app's local-URL policy, and a physical disconnected rehearsal is still pending. Mocked UI tests do not establish browser rendering quality.

## Portable release

```bash
make release
```

This creates `dist/terrapulse-1.0.0.zip` and a SHA-256 checksum. It includes the application, public analytical assets, runtime scenario cube and source/documentation. Raw multi-gigabyte HDF5 granules and the full source caches are excluded. After extracting:

```bash
python3 scripts/verify_release.py
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
bash run.sh
```

`verify_release.py` uses only standard Python to verify the packaged hashes. Full-source scientific rebuild/validators require the separately retained input datasets. Runtime assets and scientific source provenance are different bundles.

## Methods and submission preparation

[Implementation 06/07](docs/IMPLEMENTATION_06_07.md) · [Final project diagnosis/readiness](docs/FINAL_PROJECT_READINESS.md) · [Submission narrative draft](docs/SUBMISSION_BRIEF.md) · [Datasets](docs/DATASETS.md) · [Scientific limitations](docs/LIMITATIONS.md) · [AI assistance](docs/AI_USE.md).

The official 2026 challenge page returned HTTP 502 during review. The linked local organizer summary confirms the NISAR interactive surface-change focus; it also describes restrictions on project work before the event. Confirm the official rules and disclose existing work before submission. No registration, upload or submission has been performed.

Code is Apache-2.0. Dataset terms and citations remain those of their producers; see the recorded provenance.
