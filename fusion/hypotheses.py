"""
SAGAR-SAKSHI Hypothesis Builder (fusion/hypotheses.py)
Constructs the explicit competing hypothesis set (§9):
- V_k: AIS-known vessel k
- D_j: SAR-only vessel j (dark or unverified)
- P: Fixed source (platform/pipeline/known seep)
- U: Unknown or natural cause (MANDATORY, always present)
"""

from typing import Any
from api.schemas import Vessel


class HypothesisSet:
    """Manages the candidate hypothesis set."""

    def __init__(self):
        self.vessels: dict[str, Vessel] = {}
        self.dark_vessels: dict[str, dict[str, Any]] = {}
        self.fixed_sources: dict[str, dict[str, Any]] = {}
        # U is ALWAYS initialized
        self.has_unknown: bool = True

    def add_vessel(self, vessel: Vessel):
        self.vessels[vessel.vessel_id] = vessel

    def add_dark_vessel(self, detection_id: str, metadata: dict[str, Any]):
        self.dark_vessels[detection_id] = metadata

    def add_fixed_source(self, source_id: str, metadata: dict[str, Any]):
        self.fixed_sources[source_id] = metadata

    def get_all_hypothesis_ids(self) -> list[str]:
        ids = list(self.vessels.keys()) + list(self.dark_vessels.keys()) + list(self.fixed_sources.keys())
        ids.append("U")
        return ids
