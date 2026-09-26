# SAGAR-SAKSHI pitch and demo notes

These notes distinguish working prototype behavior from planned capabilities. The competitor comparisons in the supplied notes are unverified claims; do not present them as facts without checking their source material.

The supplied SIH PPTX was copied and revised at `deliverables/Tantragyan_SIH2026_Improved_Updated.pptx`; the original download was left untouched. `scripts/update_pitch_deck.py` reproduces the text edits.

## Accurate opening

“SAGAR-SAKSHI explores how SAR slick characterization, vessel tracks, drift estimates and an explicit unknown-source hypothesis can be combined into an auditable decision-support workflow. Our current demo uses synthetic AIS, may use a generated SAR crop, and uses configured constant forcing. The likelihood ratios are hand-set and uncalibrated, so this prototype demonstrates the workflow rather than operational attribution.”

## Selection Demo Path

1. Install dependencies with `python -m pip install -r requirements.txt`.
2. Run the Kerala workflow with `python pipeline.py`; run the Ennore workflow with `python pipeline.py --config config/ennore_2017.yaml`.
3. Point out the three `[INPUT]` lines. They state whether SAR is synthetic and confirm that AIS and metocean forcing are synthetic/configured.
4. Launch `uvicorn api.main:app --reload --port 8000`, open `/frontend/`, choose either incident, and run the analysis. Review the ranked candidates, download the evidence card, then record an analyst decision.
5. Say that scene IDs are catalogue candidates and the current incident raster is not present. The interface identifies synthetic AIS, generated demo SAR, and constant forcing. The screens at `/frontend/mockups.html` and `/layers` are illustrative only.

Both scenario configs provide a runnable demo fixture, not incident replay. The Ennore candidate scene footprint was corrected to one that covers the Ennore AOI; it still needs full-product download and verification before use with real data.

## Current capability wording

| Topic | Safe description today | Do not claim yet |
| --- | --- | --- |
| Slick geometry | Threshold-derived pixel mask is vectorized and basic morphometry is calculated. | Validated spill boundary or field-validated oil age. |
| Perception | Adaptive threshold plus a compact implementation trained on synthetic patches; experimental bright-pixel clustering for ships. | Production U-Net/DeepLab model, xView3 model, or validated CFAR. |
| AIS | Default track generator is synthetic and labeled as such. | Historic AIS ingestion or always-on receiver coverage. |
| Metocean | YAML constants with a simple spatial multiplier. | Live/replay CMEMS, ERA5, GFS, ECMWF or SAR-retrieved winds. |
| Drift | Custom simplified displacement/spread code. | OpenDrift or a validated probabilistic particle ensemble. |
| Ranking | Hand-set likelihood ratios normalized across hypotheses, including U. | Calibrated Bayesian posterior, an 85% empirical success interpretation, or court-ready attribution. |
| Provenance | JSON manifest with config, source labels, in-memory synthetic inputs and file hash records. Large raster hashes are sampled. | Signed, immutable chain of custody or a full-file hash for every large input. |
| UI | `/frontend/` is the live incident analysis flow; `/frontend/mockups.html` remains static, and `/layers` returns placeholder data. | Every map and dashboard screen is connected to live pipeline layers. |
| Review/alerts | Reviews persist in local SQLite; alerts run in dry-run mode after accepted Grade A/B review. | Production notification delivery or PostgreSQL/PostGIS-backed audit service. |

## Five scenario demonstrations to build and validate

The scenarios below are acceptance goals, not currently verified demo cases. Use synthetic truth labels and keep them separate from operational claims.

1. **Clear candidate:** one generated track has plausible timing and drift; show all evidence terms, the U hypothesis, and why a high grade was assigned.
2. **Dense traffic:** include at least ten tracks and show each exclusion with a reason code and time window.
3. **Coverage-confirmed SAR-only detection:** use a controlled receiver-coverage fixture; classify a non-matched detection as dark only above a documented coverage threshold.
4. **Low-wind/look-alike:** force poor detectability or a look-alike label and verify that the system abstains instead of naming a vessel.
5. **Replay:** rerun from the same stored inputs/config/model versions and compare manifest digest and output. The current prototype has no replay endpoint yet.

Do not hand-set a desired grade or posterior to make a scenario appear successful. A scenario passes only when the pipeline derives the expected behavior from its fixture and the result is recorded.

## Questions from judges

**Is the demo using real AIS?** “No. The current Kerala demo uses generated synthetic tracks, explicitly labeled synthetic. Historic AIS ingestion is future work.”

**Does the system use CMEMS/ERA5 or OpenDrift?** “Not yet. The current prototype uses configured constant forcing and custom simplified drift code; those integrations are planned.”

**How will you validate it?** “We plan controlled synthetic spill-release experiments with separate generation and evaluation assumptions, then report calibration and false-accusation metrics. Those benchmarks have not been run yet, so we do not claim target ECE or false-accusation rates.”

**What is the current differentiator?** “The prototype is designed around an explicit unknown-source option, conservative wording rules, coverage-aware AIS interpretation, and run provenance. Their operational effectiveness remains to be validated.”
