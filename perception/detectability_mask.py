"""
SAGAR-SAKSHI SAR Wind-Window Detectability Mask (perception/detectability_mask.py)
Classifies SAR oil spill detectability based on surface wind speed (§6 Stage 2).
SAR oil detection works reliably only at moderate winds (~3-10 m/s).
"""

from typing import Literal


def classify_wind_detectability(
    wind_speed_mps: float,
    too_low_threshold: float = 3.0,
    too_high_threshold: float = 10.0,
) -> Literal["too_low", "workable", "too_high"]:
    """
    Classifies wind speed regime:
    - 'too_low': < 3 m/s (look-alike prone; low backscatter from biogenic films / calm sea)
    - 'workable': 3 - 10 m/s (capillary Bragg waves present; mineral oil dampens roughness)
    - 'too_high': > 10 m/s (slick suppressing; wind mixing submerges oil droplet suspension)
    """
    if wind_speed_mps < too_low_threshold:
        return "too_low"
    elif wind_speed_mps > too_high_threshold:
        return "too_high"
    return "workable"


def evaluate_slick_detectability(
    wind_speed_mps: float,
    aoi_wind_speeds: list[float] | None = None,
) -> dict[str, str | float]:
    """Evaluates detectability class and returns metadata dictionary."""
    cls = classify_wind_detectability(wind_speed_mps)
    return {
        "wind_class": cls,
        "wind_speed_mps": wind_speed_mps,
        "is_reliable": 1.0 if cls == "workable" else 0.0,
    }
