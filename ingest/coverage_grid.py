"""AIS receiver-coverage evidence lookup.

Message density alone does not prove that a receiver was operating when a vessel
was absent. Coverage must come from an independently monitored receiver or
coverage product; unknown cells therefore remain unverified.
"""

import math
from typing import Any


class CoverageGrid:
    """Spatial lookup for measured AIS receiver-coverage probabilities."""

    def __init__(self, resolution_deg: float = 0.05):
        self.resolution_deg = resolution_deg
        self.dark_threshold = 0.90
        # Message counts are diagnostic only and never establish coverage.
        self.grid_counts: dict[tuple[int, int], int] = {}
        self.coverage_probabilities: dict[tuple[int, int], float] = {}

    def _coord_to_idx(self, lat: float, lon: float) -> tuple[int, int]:
        return (
            int(math.floor(lat / self.resolution_deg)),
            int(math.floor(lon / self.resolution_deg)),
        )

    def record_messages(self, messages: list[dict[str, Any]]):
        """Records seen-message density for diagnostics, not receiver coverage."""
        for msg in messages:
            lat, lon = msg.get("lat"), msg.get("lon")
            if lat is not None and lon is not None:
                idx = self._coord_to_idx(lat, lon)
                self.grid_counts[idx] = self.grid_counts.get(idx, 0) + 1

    def record_coverage(self, lat: float, lon: float, probability: float):
        """Records independently measured coverage for a cell (probability in [0, 1])."""
        if not 0.0 <= probability <= 1.0:
            raise ValueError("coverage probability must be between 0 and 1")
        self.coverage_probabilities[self._coord_to_idx(lat, lon)] = probability

    def get_observability(self, lat: float, lon: float) -> float:
        """Returns measured coverage, or 0 when no coverage evidence was supplied."""
        idx = self._coord_to_idx(lat, lon)
        return self.coverage_probabilities.get(idx, 0.0)
