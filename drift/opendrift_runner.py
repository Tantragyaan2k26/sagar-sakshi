"""
SAGAR-SAKSHI Drift Simulation Runner (drift/opendrift_runner.py)
Unified interface for running Lagrangian particle drift ensembles (§6 Stage 5).
"""

from datetime import datetime
from typing import Any
from api.schemas import DriftHypothesis
from ingest.forcing_fetcher import ForcingFetcher
from drift.back_region import compute_back_drift_region, gate_vessels_against_back_region
from drift.forward_hypothesis import simulate_forward_vessel_hypothesis


class DriftSimulationRunner:
    """Manages trajectory simulations and bidirectional drift evaluation."""

    def __init__(self, forcing_fetcher: ForcingFetcher, config: dict[str, Any]):
        self.forcing_fetcher = forcing_fetcher
        self.config = config
        self.window_hours = config.get("thresholds", {}).get("max_drift_window_hours", 24)

    def run_back_cone(self, slick_geojson: dict[str, Any], image_time: datetime | None = None) -> dict[str, Any]:
        """Calculate a simplified backward reachability envelope."""
        return compute_back_drift_region(
            slick_geojson,
            self.forcing_fetcher,
            window_hours=self.window_hours,
            image_time=image_time,
        )

    def gate_vessels(
        self,
        back_region: dict[str, Any],
        vessel_tracks: dict[str, list[dict[str, Any]]],
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """Filters vessels entering the backward drift cone."""
        return gate_vessels_against_back_region(back_region, vessel_tracks)

    def evaluate_forward_hypotheses(
        self,
        surviving_vessels: list[str],
        vessel_tracks: dict[str, list[dict[str, Any]]],
        slick_geojson: dict[str, Any],
        image_time: datetime,
    ) -> dict[str, DriftHypothesis]:
        """Runs forward simulation for each candidate vessel."""
        hypotheses = {}
        for v_id in surviving_vessels:
            reports = vessel_tracks.get(v_id, [])
            hypo = simulate_forward_vessel_hypothesis(
                vessel_id=v_id,
                vessel_reports=reports,
                slick_geojson=slick_geojson,
                image_time=image_time,
                forcing_fetcher=self.forcing_fetcher,
            )
            hypotheses[v_id] = hypo
        return hypotheses
