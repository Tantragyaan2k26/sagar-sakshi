# SAGAR-SAKSHI (सागर-साक्षी) · Ocean Witness
### SAR and AIS Oil-Spill Attribution Research Prototype
**Team Tantragyan · Smart India Hackathon 2026 (SIH26143)**  
*Space Technology / Software Track*

---

## 1. Overview & Mission

**SAGAR-SAKSHI** is a research prototype for exploring SAR slick characterization and vessel-attribution workflows. The current default run is a synthetic demonstration, not an operational attribution service. It uses:
1. A processed SAR GeoTIFF when one is configured and available; otherwise it generates a synthetic demo crop.
2. Scripted synthetic AIS tracks centered on the selected demonstration scenario.
3. Constant metocean values from YAML configuration. No CMEMS or ERA5 request is made by the current implementation.

The prototype ranks candidate hypotheses and can output **`"insufficient evidence"`**. Its ranking values are not calibrated probabilities and do not support operational or legal attribution.

Demonstration scenario: **Kerala 2025** (*MSC ELSA 3*). The target track in the default configuration is generated synthetic data, not historical AIS evidence.

## Current Status: What the GitHub Repo Demonstrates

| Area | Implemented now | Simulated or still missing |
| --- | --- | --- |
| Scenario runs | Kerala 2025 and Ennore 2017 YAML scenarios; CLI runner; JSON/PDF evidence cards and run manifests | Both scenarios currently use generated SAR crops unless a processed GeoTIFF is supplied |
| Spill and ship perception | Threshold-based slick candidate mask, compact experimental NumPy U-Net, pixel-cluster ship candidates | No real-scene-trained or validated model; no CV-U-Net, CWCM-Net, CV-ViT, or validated CA-CFAR |
| AIS and ocean drift | Track association, coverage-aware status labels, simple forward/backward drift workflow | AIS tracks are synthetic; forcing is constant; drift is not OpenDrift; scores are uncalibrated |
| Data collected | Public incident reports, DARTIS metadata/annotation table, scene catalogue metadata, and Kerala ALOS-2 browse previews | No full Sentinel-1 or PALSAR-2 incident raster, no historical AIS archive, no time-matched metocean files, and no reviewed incident masks |
| Interface | FastAPI, a simple incident analysis page, persisted local review records | `/frontend/mockups.html` screens and `/layers` map features are illustrative; no production auth/queue/monitoring stack |

Scene product IDs in the YAML files are catalogue candidates whose metadata footprints cover the approximate AOIs; the products are not downloaded or processed. The default quickstart intentionally demonstrates the pipeline using synthetic SAR and AIS. See [`data/external/README_downloaded_data.md`](data/external/README_downloaded_data.md) for acquired files and access notes. PALSAR-2 FBD previews are dual-pol browse JPEGs, not quad-pol training data.

The competitor matrix in the supplied pasted notes is unverified and is not evidence of competitor capabilities. Do not present its comparisons as established facts.

---

## 2. Design Choices and Prototype Status

* **Two perception branches (prototype)**:
  * **Branch A** applies adaptive dark-pixel thresholding and attempts a compact U-Net implementation that trains on synthetic patches if no weights exist. This is not a field-trained or validated oil-spill model. The detected mask is vectorized to a polygon; morphometry and a GRD intensity-based age proxy are calculated.
  * **Branch B** uses an experimental global threshold and pixel clustering detector. It is not a validated CA-CFAR implementation.
* **Doppler Azimuth-Shift Correction & Hungarian Association (partial)**:
  * Compensates for radar Doppler displacement $\Delta y = \frac{R}{V_{\text{sat}}} \cdot v_r$.
  * Applies an approximate Doppler shift, then assigns SAR detections to AIS tracks using a distance-thresholded cost matrix and Hungarian optimization (`scipy.optimize.linear_sum_assignment`). The cost is not covariance-normalized Mahalanobis distance.
  * **AIS Coverage Lookup (partial)**: A `sar_only_dark` label now requires independently recorded coverage of at least 90%. The current default run has no coverage feed, so unmatched detections remain unverified.
* **Bidirectional Drift Approximation**: Custom displacement and spread approximations use configured constant forcing. The module named `opendrift_runner.py` does not call OpenDrift or fetch gridded currents/winds.
* **Likelihood-ratio ranking prototype with mandatory null hypothesis ($U$)**:
  * Explicit hypothesis set: $\{V_k\}$ (AIS vessels), $\{D_j\}$ (dark vessels), $\{P\}$ (fixed platforms), and **$\{U\}$ (unknown / natural causes - ALWAYS present)**.
  * Hand-set likelihood ratios are combined and normalized so the candidate weights sum to 1.0000. The legacy API field is named `posteriors`, but the values are not calibrated probabilities and have not been validated for real-world attribution.
  * **Strict Evidence Grades & Legal Wording Rules**:
    * **Grade A**: Strong lead; consistent with discharge by [vessel]
    * **Grade B**: Lead; consistent with [vessel]
    * **Grade C**: Vessels in the area (no vessel named in headline)
    * **Grade None**: Insufficient evidence
    * **Enforced Business Logic**: Words such as "responsible" or "guilty" are strictly barred.
* **Run provenance (prototype)**: Each run writes a JSON manifest with configuration, source status, model labels, and input hashes. Large raster hashing is sampled and explicitly labeled; this is not a full-file checksum or a signed immutable record.

---

## 3. Repository Structure

```
sagar-sakshi/
├── frontend/                       # Working incident flow plus UI previews
│   ├── index.html                  # Incident analysis, evidence, and review flow
│   ├── mockups.html                # Static Stitch dashboard previews
│   ├── live.html                   # Earlier raw API console
│   ├── screen_01_command_overview/ # Indian EEZ Inshore Surveillance & Status
│   ├── screen_02_polarimetric_inspection/ # Sentinel-1 VV/VH Dual-Pol & U-Net Reasoning
│   ├── screen_03_tactical_oceanographic_map/ # Bathymetric Contours & Radar Sweep
│   ├── screen_04_evidence_card_dossier/ # Bayesian Matrix, Excluded Vessels & Dossier
│   ├── screen_05_incident_drift_replay/ # Drift Inversion & AIS Replay Playback
│   ├── screen_06_coastal_vectors_map/ # Peninsular Coastline & Depth Profile Map
│   └── screen_07_composite_preview/ # High-resolution UI Overview
├── config/
│   ├── kerala_2025.yaml            # Kerala scenario (May 2025 scene candidate)
│   └── ennore_2017.yaml            # Ennore scenario (Jan 2017 scene candidate)
├── ingest/
│   ├── ais_recorder.py             # AIS track ingestion and replay generator
│   ├── forcing_fetcher.py          # Constant configured forcing values
│   └── coverage_grid.py            # AIS message counts and optional measured coverage lookup
├── perception/
│   ├── sar_conditioning.py         # GeoTIFF loading, zarr chunking, geotransform
│   ├── detectability_mask.py       # Wind-window (too_low, workable, too_high)
│   ├── branch_a_spill.py           # Slick detection & polygon extraction
│   └── branch_b_ships.py           # Experimental bright-pixel ship candidate detector
├── tracking/
│   ├── kalman_smoother.py          # Track smoothing, covariance, gap detection
│   ├── azimuth_shift.py            # Doppler azimuth displacement correction
│   └── association.py              # Distance gate + Hungarian assignment
├── drift/
│   ├── back_region.py              # Backward reachability cone & vessel gating
│   ├── forward_hypothesis.py       # Forward track release & overlap scoring
│   └── opendrift_runner.py         # Unified Lagrangian drift runner
├── fusion/
│   ├── hypotheses.py               # Hypothesis set builder (V_k, D_j, P, U)
│   ├── likelihoods.py              # Likelihood ratio terms & tempered fusion
│   └── grading.py                  # Grade assignment & legal wording safeguards
├── evidence/
│   ├── manifest.py                 # JSON provenance manifest and hash records
│   └── card_builder.py             # JSON & ReportLab PDF Evidence Card export
├── preprocessing/
│   ├── s1_grd_workflow.xml         # ESA SNAP GPT radiometric calibration graph
│   └── run_s1_batch.bat            # Automated batch execution script for Sentinel-1
├── models/                         # Experimental NumPy U-Net code; no validated pretrained weights shipped
├── api/
│   ├── main.py                     # FastAPI REST API endpoints & static frontend mount
│   └── schemas.py                  # Pydantic V2 data contracts
├── tests/
│   ├── test_fitness_functions.py   # Invariants: sum=1.0, U present, manifest
│   ├── test_wording_rules.py       # Legal wording and grade safeguards
│   └── test_phase0_end_to_end.py   # Full pipeline and REST API tests
├── data/
│   ├── 01_raw_zip/                 # Raw Sentinel-1 GRD zip archive
│   └── 02_processed_tiff/          # Processed 2.9GB BigTIFF (SNAP calibrated)
├── pipeline.py                     # Master CLI pipeline runner
├── requirements.txt                # Pinned dependency specifications
├── Dockerfile                      # Container build definition
└── docker-compose.yml              # Local container deployment stack
```

---

## 4. Dataset

The large processed Sentinel-1 datasets are hosted externally because they exceed GitHub's individual file-size limits.

**[Download the processed Sentinel-1 datasets from Google Drive](https://drive.google.com/drive/folders/1qpOxIK0RiqSlxt6L7Uz62RiSwZVAL46x?usp=sharing)**

After downloading, place the files in:

```text
data/02_processed_tiff/

---

## 5. Quickstart: Running the Pipeline & Frontend

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run a Prototype Scenario (CLI)
```bash
# Default Kerala scenario. Missing GeoTIFF means synthetic SAR is used.
python pipeline.py

# Ennore scenario, also synthetic until its GeoTIFF is supplied.
python pipeline.py --config config/ennore_2017.yaml
```
Outputs:
* Console summary of run ID, manifest SHA256, evidence grade, and posteriors.
* Evidence artifacts saved in `runs/`:
  * `runs/<run_id>_evidence_card.json`
  * `runs/<run_id>_evidence_card.pdf`
* `runs/<run_id>_manifest.json`

Both scenarios use synthetic AIS and constant forcing. They use a synthetic SAR crop when their configured GeoTIFF is absent. The CLI prints the selected input mode; inspect each evidence card and manifest before interpreting a run. Ranking values are not calibrated probabilities. Supplying a real GeoTIFF changes only the SAR input; it does not make AIS or metocean inputs real.

### 3. Run the Test Suites
```bash
python -m pytest tests/ -v
```
The repository contains unit and end-to-end tests. Their current pass status is not asserted here; run the command above in the target environment to check them.

### 4. Launch the Tactical Web Console & REST API
```bash
uvicorn api.main:app --reload --port 8000
```
Interactive endpoints:
* **Incident analysis UI**: `http://localhost:8000/frontend/` (choose Ennore or Kerala, run the prototype, inspect evidence, and record an analyst review)
* **Static dashboard mockups**: `http://localhost:8000/frontend/mockups.html` (visual previews only; not connected to live layers)
* **Interactive OpenAPI Docs**: `http://localhost:8000/docs`

Key API endpoints:
* `POST /runs`: Trigger run from config.
* `GET /runs/{id}`: Fetch status, grade, and shortlist.
* `GET /runs/{id}/card?format=json`: Fetch Evidence Card JSON.
* `GET /runs/{id}/card?format=pdf`: Download Evidence Card PDF report.
* `GET /runs/{id}/manifest`: Fetch the persisted JSON provenance manifest.
* `GET /layers/{name}`: Serve GeoJSON vector layers (`slicks`, `ships`, `back_region`).
* `POST /runs/{id}/review`: Submit analyst review decisions.
* `GET /runs/{id}/reviews`: Retrieve persisted analyst review history.

The `/layers/{name}` endpoint currently returns illustrative placeholder GeoJSON, not layers derived from a particular run. Run cards and analyst reviews are persisted in local SQLite. PostgreSQL/PostGIS, Redis, external-data ingestion, a durable worker queue, and a model registry shown in the architecture blueprint are not wired into this prototype. Alerts are simulated in dry-run mode after an accepted review of a Grade A or B result.

See [`docs/pitch_and_demo.md`](docs/pitch_and_demo.md) for current-safe presentation language and unimplemented scenario-demo acceptance goals.
An updated copy of the supplied presentation is in [`deliverables/Tantragyan_SIH2026_Improved_Updated.pptx`](deliverables/Tantragyan_SIH2026_Improved_Updated.pptx). Recreate it from the source PPTX with `python scripts/update_pitch_deck.py <source.pptx> <output.pptx>`.
