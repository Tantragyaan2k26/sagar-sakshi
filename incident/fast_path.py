"""
SAGAR-SAKSHI Fast-Path Ship-at-Head Matcher (incident/fast_path.py)
Implements the fast-path attribution shortcut (§6, Block 5):
"Fast path: ship at head · bright target at slick head -> high-confidence match · skip drift if matched"
"""

import math
from typing import Any, Optional
from api.schemas import Vessel, Slick


class FastPathMatcher:
    """Evaluates whether an active vessel is detected directly at the fresh discharge apex of a slick."""

    def __init__(self, max_head_distance_km: float = 1.8):
        self.max_dist_km = max_head_distance_km

    def evaluate_fast_path(
        self,
        slick_head_coords: tuple[float, float],
        candidate_vessels: list[Vessel],
    ) -> Optional[dict[str, Any]]:
        """
        If a vessel is situated within the immediate apex radius of the fresh slick end,
        returns high-confidence attribution match data.
        """
        lat1, lon1 = slick_head_coords

        for v in candidate_vessels:
            if not v.last_known_point:
                continue
            lat2, lon2 = v.last_known_point

            # Compute great-circle distance
            r = 6371.0
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = (math.sin(dlat / 2) ** 2 +
                 math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
            dist_km = 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))

            if dist_km <= self.max_dist_km:
                return {
                    "matched": True,
                    "vessel_id": v.vessel_id,
                    "vessel_name": v.name or v.vessel_id,
                    "distance_to_head_km": round(dist_km, 2),
                    "confidence": 0.94,
                    "fast_path_triggered": True,
                    "reason": f"Vessel detected directly at slick release apex ({dist_km:.2f} km distance); contemporaneous discharge signature.",
                }

        return None
