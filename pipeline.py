"""
SAGAR-SAKSHI Prototype Pipeline Runner (pipeline.py)
Executes the synthetic/default prototype workflow and creates review artifacts.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
import yaml
from typing import Any
from shapely.geometry import shape

from api.schemas import EvidenceCard
from evidence.manifest import RunManifest
from evidence.card_builder import build_evidence_card_json, export_evidence_card_pdf
from ingest.ais_recorder import generate_synthetic_traffic, load_ais_csv
from ingest.coverage_grid import CoverageGrid
from ingest.forcing_fetcher import ForcingFetcher
from perception.sar_conditioning import SarConditioner
from perception.detectability_mask import classify_wind_detectability
from perception.branch_a_spill import detect_slicks_threshold
from perception.branch_b_ships import run_cfar_detector
from tracking.kalman_smoother import KalmanTrackSmoother
from tracking.association import associate_sar_ais
from drift.opendrift_runner import DriftSimulationRunner
from fusion.hypotheses import HypothesisSet
from fusion.likelihoods import (
    compute_drift_consistency,
    compute_slick_geometry,
    compute_head_proximity,
    compute_behaviour_score,
    fuse_evidence,
)
from fusion.grading import compute_attribution


def run_pipeline(config_path: str = "config/kerala_2025.yaml", run_id: str | None = None) -> EvidenceCard:
    """Executes the full attribution pipeline end-to-end from configuration."""
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    if not run_id:
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        run_id = f"run_kerala_{timestamp_str}"

    manifest = RunManifest(run_id, config)

    # 1. Record inputs and models in manifest
    sc_conf = config.get("scene", {})
    tiff_path = sc_conf.get("tiff_path", "data/02_processed_tiff/Kerala_Processed.tif")
    raw_zip = sc_conf.get("raw_zip")
    manifest.record_input("config_yaml", config_path)
    manifest.record_input("sar_tiff", tiff_path)
    if raw_zip:
        manifest.record_input("sar_raw_zip", raw_zip)

    manifest.record_model("perception_spill", "adaptive_dark_pixel_threshold_unvalidated")
    manifest.record_model("perception_ship", "experimental_global_threshold_cluster_detector")
    manifest.record_model("tracking", "kalman_azimuth_hungarian")
    manifest.record_model("drift", "custom_time_stepped_advection_approximation_not_opendrift")
    manifest.record_model("fusion", "hand_set_likelihood_ratios_not_calibrated")

    # 2. Stage 1: Ingest AIS & Metocean Forcing
    inc = config.get("incident", {})
    image_time = datetime.fromisoformat(sc_conf.get("acquisition_start_utc", "2025-05-28T00:41:12.668533+00:00").replace("Z", "+00:00"))
    demo_reference = inc.get("demo_reference_point", {})
    demo_lat = float(demo_reference.get("lat", (inc.get("aoi", {}).get("min_lat", 9.15) + inc.get("aoi", {}).get("max_lat", 9.45)) / 2))
    demo_lon = float(demo_reference.get("lon", (inc.get("aoi", {}).get("min_lon", 76.05) + inc.get("aoi", {}).get("max_lon", 76.35)) / 2))
    ais_config = config.get("ais", {})
    ais_window = int(ais_config.get("window_hours", config.get("thresholds", {}).get("max_drift_window_hours", 24)))
    if ais_config.get("source", "synthetic") == "csv":
        ais_path = ais_config.get("csv_path")
        if not ais_path:
            raise ValueError("ais.source=csv requires ais.csv_path")
        ais_messages = load_ais_csv(ais_path, image_time, ais_window)
        manifest.record_input("ais_csv", ais_path, metadata={"schema": "timestamp_utc,lat,lon,mmsi,vessel_name,sog,cog"})
        manifest.record_value("ais_messages", ais_messages, description="Rows loaded from the configured historical AIS CSV; source/archive and coverage remain unverified.")
        print(f"[INPUT] Loaded {len(ais_messages)} AIS reports from the configured CSV; archive provenance and receiver coverage are not verified.")
        ais_status = "historic_reconstruction"
    else:
        ais_messages = generate_synthetic_traffic(
            incident_time=image_time,
            window_hours=ais_window,
            target_name=ais_config.get("target_vessel_name", "SYNTHETIC DEMO CANDIDATE"),
            target_mmsi=ais_config.get("target_mmsi", "SYN-DEMO-LEAD-01"),
            target_lat=demo_lat,
            target_lon=demo_lon,
        )
        manifest.record_value("ais_messages", ais_messages, description="Generated synthetic AIS scenario; not historical receiver data.")
        print(f"[INPUT] AIS is synthetic demo data ({len(ais_messages)} messages); no historical receiver feed is used.")
        ais_status = "synthetic"

    cov_grid = CoverageGrid()
    cov_grid.record_messages(ais_messages)
    forcing = ForcingFetcher(config)
    meteo = config.get("metocean", {})
    if forcing.csv_path:
        manifest.record_input("metocean_csv", forcing.csv_path, metadata={"schema": ",".join(sorted(forcing.REQUIRED_CSV_COLUMNS))})
        manifest.record_value("metocean_forcing", {"provider": forcing.provider_label, "sample_count": len(forcing.samples), "selection": "nearest sample in configured space/time bounds; no interpolation"})
        print(f"[INPUT] Metocean uses {len(forcing.samples)} CSV samples with nearest space/time lookup; no grid interpolation.")
    else:
        manifest.record_value(
            "metocean_forcing",
            {"provider": forcing.provider_label, "current_u_mps": forcing.default_u, "current_v_mps": forcing.default_v,
             "wind_speed_mps": forcing.default_w_speed, "wind_from_deg": forcing.default_w_from},
            description="Configured constant demo forcing; no external wind/current files were fetched.",
        )
        print("[INPUT] Wind and current use configured constants; no CMEMS/ERA5 data is fetched.")
    analysis_forcing = forcing.get_forcing_at(demo_lat, demo_lon, image_time.isoformat())

    # 3. Stage 2 & 3: SAR Conditioning, Detectability Mask & Twin-Branch Perception
    sar = SarConditioner(tiff_path, config)
    if sar.synthetic:
        print(f"[INPUT] SAR GeoTIFF is missing at '{tiff_path}'; generating a synthetic demo crop.")
    else:
        print(f"[INPUT] Calibrated SAR GeoTIFF found at '{tiff_path}'; processing configured band.")
    aoi = inc.get("aoi", {"min_lat": 8.90, "min_lon": 75.80, "max_lat": 9.80, "max_lon": 76.60})

    crop_db, crop_meta = sar.extract_aoi_crop(
        min_lat=aoi["min_lat"],
        min_lon=aoi["min_lon"],
        max_lat=aoi["max_lat"],
        max_lon=aoi["max_lon"],
        band=0,
    )
    sar.close()
    manifest.record_value(
        "sar_crop_source",
        {"source": crop_meta.get("source"), "synthetic": crop_meta.get("synthetic", sar.synthetic)},
        description="Identifies whether this run used the configured GeoTIFF or a generated demo crop.",
    )
    crop_pixel_sha256 = hashlib.sha256(memoryview(crop_db)).hexdigest()
    manifest.record_value(
        "sar_crop_pixels",
        {
            "shape": list(crop_db.shape),
            "dtype": str(crop_db.dtype),
            "sha256": crop_pixel_sha256,
        },
        description="SHA-256 of the exact in-memory AOI array processed in this run.",
    )

    # Wind detectability check
    wind_class = classify_wind_detectability(
        analysis_forcing.wind_speed_mps,
        too_low_threshold=config.get("thresholds", {}).get("wind_too_low_mps", 3.0),
        too_high_threshold=config.get("thresholds", {}).get("wind_too_high_mps", 10.0),
    )

    # Branch A: Spill Detection
    slicks = detect_slicks_threshold(crop_db, crop_meta, wind_class=wind_class)
    if not slicks:
        raise RuntimeError("No slicks segmented in the AOI.")
    primary_slick = slicks[0]
    manifest.record_model("perception_spill", primary_slick.model_id)

    # Branch B: Ship Detection
    ship_dets = run_cfar_detector(crop_db, crop_meta, azimuth_time=image_time)

    # 4. Stage 4: Tracking & SAR-AIS Association
    # Group AIS messages by vessel
    tracks_by_vessel: dict[str, list[dict[str, Any]]] = {}
    track_labels: dict[str, str] = {}
    for msg in ais_messages:
        v_name = str(msg.get("mmsi") or msg["vessel_name"])
        track_labels[v_name] = msg.get("vessel_name") or v_name
        tracks_by_vessel.setdefault(v_name, []).append(msg)

    smoother = KalmanTrackSmoother()
    smoothed_states: dict[str, dict[str, Any]] = {}
    for v_name, reports in tracks_by_vessel.items():
        state = smoother.smooth_track(reports, target_time=image_time)
        smoothed_states[v_name] = state

    vessels, assoc_stats = associate_sar_ais(
        sar_detections=ship_dets,
        smoothed_tracks=smoothed_states,
        coverage_grid=cov_grid,
        acquisition_time=image_time,
        track_labels=track_labels,
    )

    # 5. Stage 5: Drift Simulation & Source Likelihood
    drift_runner = DriftSimulationRunner(forcing, config)
    back_region = drift_runner.run_back_cone(primary_slick.polygon, image_time=image_time)
    surviving_vessels, exclusions = drift_runner.gate_vessels(back_region, tracks_by_vessel)

    forward_hypotheses = drift_runner.evaluate_forward_hypotheses(
        surviving_vessels=surviving_vessels,
        vessel_tracks=tracks_by_vessel,
        slick_geojson=primary_slick.polygon,
        image_time=image_time,
    )

    # 6. Stage 6: Hypothesis Building & Bayesian Fusion
    hypo_set = HypothesisSet()
    for v in vessels:
        if v.vessel_id in surviving_vessels:
            hypo_set.add_vessel(v)
        elif v.status == "sar_only_dark":
            hypo_set.add_dark_vessel(v.vessel_id, {"lat": v.last_known_point[0], "lon": v.last_known_point[1]})

    all_hypo_ids = hypo_set.get_all_hypothesis_ids()

    # Compute evidence terms
    # Slick head approximate coordinate (fresh end)
    slick_geometry = shape(primary_slick.polygon)
    if slick_geometry.geom_type == "MultiPolygon":
        slick_geometry = max(slick_geometry.geoms, key=lambda part: part.area)
    slick_coords = list(slick_geometry.exterior.coords)
    slick_head = (slick_coords[0][1], slick_coords[0][0])  # (lat, lon)

    evidence_dict: dict[str, dict[str, float]] = {}
    priors: dict[str, float] = {}

    for h_id in all_hypo_ids:
        if h_id == "U":
            priors["U"] = config.get("thresholds", {}).get("prior_unknown", 0.15)
            continue

        priors[h_id] = 0.85 / max(1, len(all_hypo_ids) - 1)

        # Drift consistency
        drift_h = forward_hypotheses.get(h_id)
        d_score = compute_drift_consistency(drift_h)

        # Geometry
        v_obj = hypo_set.vessels.get(h_id)
        g_score = compute_slick_geometry(primary_slick, v_obj)

        # Head proximity
        pos = v_obj.last_known_point if v_obj else None
        h_score = compute_head_proximity(slick_head, pos)

        # Operational behavior
        v_track_state = smoothed_states.get(h_id, {})
        has_gap = v_track_state.get("gap_detected", False)
        sog = v_track_state.get("sog", 12.0)
        speed_drop = sog < 8.0
        b_score = compute_behaviour_score(speed_drop, False, has_gap)

        evidence_dict[h_id] = {
            "drift_consistency": round(d_score, 3),
            "slick_geometry": round(g_score, 3),
            "head_proximity": round(h_score, 3),
            "behaviour": round(b_score, 3),
        }

    unnorm = fuse_evidence(
        hypotheses=all_hypo_ids,
        evidence_dict=evidence_dict,
        priors=priors,
        tempering_exponent=config.get("thresholds", {}).get("tempering_exponent", 0.85),
    )

    attr_dict = compute_attribution(
        unnormalized_posteriors=unnorm,
        evidence_terms=evidence_dict,
        exclusions=exclusions,
        run_id=run_id,
        threshold_a=config.get("thresholds", {}).get("posterior_a_threshold", 0.70),
        threshold_b=config.get("thresholds", {}).get("posterior_b_threshold", 0.60),
    )

    # Finalize manifest
    manifest.outputs["run_summary"] = {
        "sar_source": crop_meta.get("source"),
        "sar_synthetic": crop_meta.get("synthetic", sar.synthetic),
        "wind_class": wind_class,
        "wind_speed_mps": analysis_forcing.wind_speed_mps,
        "slick_count": len(slicks),
        "ship_detection_count": len(ship_dets),
        "matched_vessels": assoc_stats.get("matched_count", 0),
    }
    manifest.outputs["stage_outputs"] = {
        "slicks": [slick.model_dump(mode="json") for slick in slicks],
        "ship_detections": [det.model_dump(mode="json") for det in ship_dets],
        "vessels": [v.model_dump(mode="json") for v in vessels],
        "back_region": back_region,
        "forward_hypotheses": {
            vessel_id: hypothesis.model_dump(mode="json")
            for vessel_id, hypothesis in forward_hypotheses.items()
        },
    }
    manifest_sha256 = manifest.finalize(attr_dict)

    # Persist a reviewable provenance record alongside the evidence card.
    os.makedirs("runs", exist_ok=True)
    manifest_path = os.path.join("runs", f"{run_id}_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest.to_dict(), f, indent=2, sort_keys=True, default=str)

    # 7. Stage 7: Build Evidence Card JSON & PDF Artifacts
    card = build_evidence_card_json(
        run_id=run_id,
        manifest_sha256=manifest_sha256,
        attribution_data=attr_dict,
        ais_status=ais_status,
        metadata={
            "incident_id": inc.get("incident_id"),
            "incident_name": inc.get("name"),
            "incident_location": inc.get("location_name"),
            "incident_time_utc": inc.get("approximate_time_utc"),
            "scene_id": sc_conf.get("product_id"),
            "satellite": sc_conf.get("satellite"),
            "scene_acquisition_start_utc": sc_conf.get("acquisition_start_utc"),
            "scene_product_status": sc_conf.get("product_status"),
            "scene_orbit_direction": sc_conf.get("orbit_direction"),
            "wind_class": wind_class,
            "wind_speed_mps": analysis_forcing.wind_speed_mps,
            "slick_count": len(slicks),
            "ship_detection_count": len(ship_dets),
            "matched_vessels": assoc_stats.get("matched_count", 0),
            "sar_source": crop_meta.get("source"),
            "sar_synthetic": crop_meta.get("synthetic", sar.synthetic),
            "forcing_source": forcing.provider_label,
            "forcing_live_fetch": False,
            "wind_source": meteo.get("wind_source", forcing.provider_label),
            "current_source": meteo.get("current_source", forcing.provider_label),
            "drift_engine": "custom_time_stepped_advection_approximation",
            "probabilities_calibrated": False,
            "spill_score_semantics": "uncalibrated_dark_patch_heuristic_score_not_oil_probability",
            "spill_model": "adaptive_dark_pixel_threshold_unvalidated",
            "spill_age_status": "unvalidated_heuristic_if_present",
            "manifest_file": manifest_path,
        },
    )

    # Save artifacts to runs directory
    os.makedirs("runs", exist_ok=True)
    json_path = os.path.join("runs", f"{run_id}_evidence_card.json")
    with open(json_path, "w") as f:
        f.write(card.model_dump_json(indent=2))

    pdf_path = os.path.join("runs", f"{run_id}_evidence_card.pdf")
    export_evidence_card_pdf(card, pdf_path)

    return card


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run a SAGAR-SAKSHI prototype incident scenario.")
    parser.add_argument("--config", default="config/kerala_2025.yaml", help="Incident YAML configuration")
    parser.add_argument("--run-id", default=None, help="Optional run identifier")
    args = parser.parse_args()
    card = run_pipeline(config_path=args.config, run_id=args.run_id)
    print("=" * 60)
    print("SAGAR-SAKSHI PIPELINE EXECUTION COMPLETED")
    print("=" * 60)
    print(f"Run ID: {card.run_id}")
    print(f"Manifest SHA256: {card.manifest_sha256}")
    print(f"Evidence Grade: {card.attribution.grade}")
    print(f"Headline: {card.attribution.headline}")
    print("Interpretation: prototype ranking weights are uncalibrated and are not source probabilities.")
    print("Posteriors:")
    for h, p in card.attribution.posteriors.items():
        print(f"  {h}: {p:.4f} ({p*100:.1f}%)")
    print(f"Exclusions count: {len(card.attribution.exclusions)}")
    print("Evidence artifacts saved to runs/")
