"""Unvalidated look-alike heuristics for surfacing possible slick candidates.

SAR darkness and morphology cannot chemically verify mineral oil. These rules
are review flags, not a trained classifier or a probability estimate.
"""

from typing import Any


class LookAlikeClassifier:
    """Apply transparent, deliberately non-verifying candidate heuristics."""

    def __init__(self, damping_threshold_db: float = -4.5):
        self.damping_threshold_db = damping_threshold_db

    def classify_candidate(
        self,
        contrast_db: float,
        wind_speed_mps: float,
        area_km2: float,
        perimeter_km: float,
        elongation_ratio: float = 3.5,
        chlorophyll_proxy_alert: bool = False,
        cross_pol_damping_db: float = -2.0,
    ) -> dict[str, Any]:
        """Return a possible-slick label, heuristic score, and its limitation."""
        if wind_speed_mps < 2.5:
            return {
                "classification": "calm_water_like",
                "is_oil_like_candidate": False,
                "heuristic_score": 0.15,
                "reason": "Configured wind is below 2.5 m/s; calm water can suppress sea clutter. Heuristic only.",
            }
        if wind_speed_mps > 11.0:
            return {
                "classification": "high_wind_lookalike_risk",
                "is_oil_like_candidate": False,
                "heuristic_score": 0.15,
                "reason": "Configured wind is above 11 m/s; high wind reduces slick detectability. Heuristic only.",
            }
        if chlorophyll_proxy_alert:
            return {
                "classification": "chlorophyll_cooccurrence_review",
                "is_oil_like_candidate": False,
                "heuristic_score": 0.25,
                "reason": "A chlorophyll proxy alert overlaps this candidate; it does not identify the material.",
            }
        if contrast_db < 3.5 and elongation_ratio < 2.0:
            return {
                "classification": "weak_contrast_lookalike_risk",
                "is_oil_like_candidate": False,
                "heuristic_score": 0.30,
                "reason": "Weak contrast and low elongation make this an ambiguous dark patch. Heuristic only.",
            }

        score = min(0.75, max(0.35, 0.30 + (contrast_db - 3.0) * 0.035 + (elongation_ratio - 1.0) * 0.025))
        return {
            "classification": "possible_oil_slick",
            "is_oil_like_candidate": True,
            "heuristic_score": round(score, 3),
            "reason": (
                f"Dark-patch contrast ({contrast_db:.1f} dB) and shape ({elongation_ratio:.1f}:1) "
                "fit a simple slick heuristic; this is not oil verification."
            ),
            "descriptors": {
                "area_km2": round(area_km2, 2),
                "perimeter_km": round(perimeter_km, 2),
                "elongation_ratio": round(elongation_ratio, 2),
                "contrast_db": round(contrast_db, 2),
            },
        }
