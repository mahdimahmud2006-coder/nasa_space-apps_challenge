# 🛰️ TerraPulse: Radar Surface-Change Investigation

[![Python 3.14](https://img.shields.io/badge/Python-3.14-blue.svg)](https://www.python.org/)
[![NASA NISAR L2 GCOV](https://img.shields.io/badge/NASA%20NISAR-L2%20GCOV%20Provisional-orange.svg)](https://doi.org/10.5067/NIL2GCOV-P1)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-green.svg)](LICENSE)
[![Tests: Passing](https://img.shields.io/badge/Tests-38%20Passed-brightgreen.svg)]()
[![Offline Capable](https://img.shields.io/badge/Deployment-100%25%20Offline%20Ready-purple.svg)]()

**NASA Space Apps Challenge · Challenge: Dancing with the SARs**  
**Team: DevAtMad**

---

## 📌 Overview

**TerraPulse** is an offline surface-change investigation system and interactive decision-support viewer powered by real **NASA–ISRO Synthetic Aperture Radar (NISAR) L2 GCOV PROVISIONAL** repeat-pass radar backscatter observations. 

Synthetic Aperture Radar (SAR) penetrates cloud cover and functions independently of solar illumination. TerraPulse compares repeat radar acquisitions across a fixed 24 km × 24 km investigation area centered over Kathmandu Valley, Nepal, to systematically detect anomalous surface-change candidates, inspect connected regions, and trace every measurement back to its raw scientific source.

Every scientific calculation is written in deterministic, test-covered Python. The interactive browser interface operates **100% offline with zero cloud or API dependencies**, rendering precomputed analytical assets directly via a lightweight local server.

![TerraPulse Interactive Demo Interface](docs/demo.png)
*TerraPulse Web Interface: Interactive dual-layer swipe inspection, anomalous change candidate masks, region attribute breakdown, and scientific evidence provenance.*

---

## 🎯 The Judge-Facing Path

To evaluate TerraPulse as a competition judge or technical reviewer, follow the core workflow:

$$\text{Before Layer} \longrightarrow \text{After Layer} \longrightarrow \text{Interactive Swipe} \longrightarrow \text{Scan Candidates} \longrightarrow \text{Measured Change} \longrightarrow \text{Audit Evidence}$$

1. **Select Observation Pair**: Default investigation pair is **August 19 → September 12, 2026** (24-day span). The two complementary 12-day pairs (**August 19 → August 31** and **August 31 → September 12**) provide crucial temporal context.
2. **Visual Swipe & Inspection**: Swipe between radar backscatter ($\gamma^0\text{ dB}$) layers at 10 m native resolution to inspect terrain reflectivity differences.
3. **Anomalous Candidate Overlay**: Toggle the candidate mask and robust candidate core overlay to visualize statistically significant backscatter changes.
4. **Region Inspector**: Click any detected region polygon to inspect its area ($\text{km}^2$), mean $\Delta\text{dB}$, peak change, and geographic centroid.
5. **Scientific Provenance**: Inspect the full evidence card to audit exact granule IDs, HDF5 internal paths, CRS parameters, and checksums.

---

## 🚀 Quickstart: Launching the Demo

The repository includes pre-processed, lightweight analytical assets in `web/public/cases/`, allowing anyone to launch and explore the full interactive demo immediately without downloading multi-gigabyte raw radar files:

```bash
make demo
```

Then open your browser to **[http://127.0.0.1:8000](http://127.0.0.1:8000)**.

Alternatively, launch using standard Python directly without `make`:

```bash
OFFLINE=1 python3 -m src.api.app
```

> **Zero Cloud Dependencies:** The server binds strictly to loopback (`127.0.0.1`). It makes zero outbound network requests. No API key, NASA Earthdata login, Node.js installation, external CDN, third-party font, or online map tile provider is required.

---

## 🔬 Reproducing the Science Pipeline

If you have access to the raw NASA NISAR HDF5 source granules and wish to re-execute the complete scientific extraction, alignment, change detection, and asset export pipeline:

### Prerequisites
- Python 3.14 (tested)
- `uv` or standard `pip`
- The raw NISAR L2 GCOV HDF5 files placed in the project root

### Reproduction Commands

```bash
make setup      # Install scientific dependencies (numpy, scipy, rasterio, h5py)
make inspect    # Audit raw HDF5 schemas, groups, datasets, and metadata
make test       # Execute test suite (38 unit, scientific, and temporal tests)
make process    # Run windowed extraction, 3-pair change computation, and exports
make validate   # Cross-check rasters, masks, region statistics, and geometries
make demo       # Launch the interactive offline review application
```

To run with `pip` instead of `uv`:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make test
make process
```

---

## 📊 Observations & Verified Findings

### Audited NISAR Granules
TerraPulse utilizes three real NISAR observations from the consistent **P05023 / product version 1.0.11** processing release:

| Local Identifier | Acquisition Start (UTC) | Track / Frame | Geometry / Pass | Granule ID |
|---|---|---|---|---|
| `aug19.h5` | 2026-08-19 23:39:18 | 98 / 16 | Ascending, Left looking | `NISAR_L2_PR_GCOV_028_098_A_016_4005_DHDH_A_20260819T233918_20260819T233953_P05023_N_F_J_001` |
| `aug31.h5` | 2026-08-31 23:39:18 | 98 / 16 | Ascending, Left looking | `NISAR_L2_PR_GCOV_029_098_A_016_4005_DHDH_A_20260831T233918_20260831T233952_P05023_N_F_J_001` |
| `sept12.h5` | 2026-09-12 23:39:18 | 98 / 16 | Ascending, Left looking | `NISAR_L2_PR_GCOV_030_098_A_016_4005_DHDH_A_20260912T233918_20260912T233952_P05023_N_F_J_001` |

- **Dataset Reference:** [DOI 10.5067/NIL2GCOV-P1](https://doi.org/10.5067/NIL2GCOV-P1)
- **HDF5 Path:** `/science/LSAR/GCOV/grids/frequencyA/HHHH` (diagonal HH covariance term = real $\gamma^0$ power)
- **Grid Projection:** EPSG:32645 (UTM zone 45N), 10 m × 10 m pixel spacing
- **Investigation AOI:** 24 km × 24 km window (2400 × 2400 pixels) centered over Kathmandu Valley ($85.33^\circ\text{ E}, 27.80^\circ\text{ N}$)

### Empirical Surface-Change Detection Results

All three temporal combinations were processed using identical parameters:

| Temporal Comparison | Time Delta | Candidate Area ($\text{km}^2$) | Retained Regions | Nominal Cutoff ($\text{dB}$) |
|---|---|---:|---:|---:|
| **Aug 19 → Aug 31** | 12 days | 0.0195 | 1 | 4.1190 |
| **Aug 19 → Sep 12** | 24 days | **0.7949** | **30** | **4.3204** |
| **Aug 31 → Sep 12** | 12 days | 0.0000 | 0 | 3.9954 |

- **Robust Candidate Core:** The 24-day change analysis exhibits a **$0.4174\text{ km}^2$ robust core** that persists even when applying a stricter $+10\%$ threshold cutoff across 14 of the 30 nominal candidate regions.
- **Temporal Consistency:** Analysis of the 30 candidate regions across subintervals reveals that 29 exhibit a *cumulative-consistent* change profile and 1 exhibits an *early-dominant* profile.
- **Unsmoothed Baseline:** An unfiltered baseline run retained 0 regions under conservative rules; this baseline is preserved in `data/derived/baseline_unsmoothed.json`.

---

## 📐 Scientific Methodology

1. **Backscatter Computation**: Diagonal covariance power is validated for positivity and non-fill attributes, then converted to decibels:
   $$\gamma^0\ (\text{dB}) = 10 \cdot \log_{10}(\text{power})$$
2. **Speckle Mitigation**: A spatial $3 \times 3$ median filter is applied to the valid dB grid. Source boundaries and nodata neighborhoods are strictly rejected.
3. **Difference & Robust Thresholding**:
   $$\Delta\text{dB} = \text{dB}_{\text{after}} - \text{dB}_{\text{before}}$$
   $$\text{Spread} = 1.4826 \cdot \text{MAD}(\Delta\text{dB})$$
   $$\text{Cutoff} = 3.0 \cdot \text{Spread}$$
   $$\text{Candidate} = |\Delta\text{dB}| \ge \text{Cutoff}$$
4. **Morphological Spatial Filtering**: Binary morphological opening using a 4-connected $3 \times 3$ cross kernel, removing clusters smaller than 100 pixels ($0.01\text{ km}^2$).
5. **Exact Geographic Vectorization**: Region boundaries are polygonized directly from full-resolution rasters (not downsampled preview images) and projected into standard WGS84 GeoJSON.

---

## 🏛️ Repository Architecture

```text
├── config.json                     # Central configuration (AOI, thresholds, kernel sizes)
├── Makefile                        # Reproduction targets (setup, inspect, test, process, demo)
├── pyproject.toml                  # Project packaging specifications
├── requirements.txt                # Fixed Python dependencies
├── LICENSE                         # Apache-2.0 open-source license
├── README.md                       # Comprehensive project documentation
├── data/
│   ├── context/                    # Independent contextual screening data (UNOSAT, Sentinel-2)
│   └── derived/                    # Audited metadata, baseline records, and case outputs
├── docs/                           # Deep-dive scientific & operational documentation
│   ├── METHODOLOGY.md              # Detailed mathematical and processing specifications
│   ├── DATASETS.md                 # NISAR product specifications and download guide
│   ├── TEMPORAL_CONSISTENCY.md     # Multi-temporal subinterval evaluation
│   ├── VALIDATION.md               # Independent validation checks and spatial screens
│   ├── LIMITATIONS.md              # Scientific limits, sensor constraints, and non-claims
│   ├── AI_USE.md                   # Transparent statement on AI assistance
│   └── DEMO_RUNBOOK.md             # Reviewer guide for local execution
├── src/
│   ├── api/                        # Offline Python standard-library static & REST server
│   ├── compute/                    # Processing pipeline (align, threshold, regions, validation)
│   ├── export/                     # Exporters for GeoJSON, GeoTIFF, WebP, and evidence manifests
│   └── ingest/                     # HDF5 inspection, metadata parser, and window extractor
├── tests/                          # 38 automated test cases covering science, ingest, and geometry
└── web/
    ├── index.html                  # Responsive offline web interface
    ├── styles.css                  # UI styling (dark mode, swipe comparison, split views)
    ├── app.js                      # Vanilla JavaScript client logic (zero external dependencies)
    └── public/cases/               # Shipped lightweight analytical assets for review
```

---

## ⚠️ Scientific Integrity & Operational Limitations

- **Provisional Data:** The NISAR products used are provisional test releases ([DOI 10.5067/NIL2GCOV-P1](https://doi.org/10.5067/NIL2GCOV-P1)). Radiometric and geometric calibrations are subject to revision by the NASA/ISRO science teams.
- **Candidate Detections $\ne$ Ground Truth:** All identified change polygons represent **threshold-dependent radar-backscatter anomalies**. Radar backscatter changes may stem from soil moisture variation, vegetation changes, speckle, or topographic effects, not solely ground-surface disasters.
- **No Disaster Attribution Claimed:** Cross-referencing against an independent [UNOSAT 26 August flood extent map](https://ihp-wins.unesco.org/en/dataset/nepal-satellite-detected-mudflow-and-rockflow-extent-nepal) revealed **zero spatial overlap** with detected nominal regions. Therefore, TerraPulse makes **no claim** of flood or landslide classification.
- **Deterministic & Audited:** No generative AI or large language model was used to calculate scientific numbers, thresholds, or region boundaries.

For detailed discussions, see [docs/METHODOLOGY.md](docs/METHODOLOGY.md), [docs/VALIDATION.md](docs/VALIDATION.md), and [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

---

## 📄 License & Credits

- **Code License:** [Apache License 2.0](LICENSE)
- **NASA Data:** Distributed under NASA Earth Science Open Data policy.
- **Created by:** Team **DevAtMad** for the NASA Space Apps Challenge 2026.
