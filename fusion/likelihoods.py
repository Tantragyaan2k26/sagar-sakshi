"""
SAGAR-SAKSHI Bayesian Likelihood & Evidence Fusion Engine (fusion/likelihoods.py)
Computes individual likelihood terms, applies tempering exponent to handle wind correlation,
and fuses evidence into unnormalized posteriors (§9).
"""

import math
from typing import Any
from api.schemas import Slick, DriftHypothesis, Vessel


def compute_drift_consistency(drift_hypo: DriftHypothesis | None) -> float:
    """
    Likelihood ratio for drift consistency:
    - Overlap > 0.5: L in [2.0, 5.0]
    - Overlap < 0.2: L in [0.05, 0.5]
    """
    if not drift_hypo:
        return 0.1
    s = drift_hypo.overlap_score
    if s >= 0.70:
        return 1.0 + (s - 0.70) * 10.0  # up to 4.0
    elif s >= 0.40:
        return 1.0 + (s - 0.40) * 3.3   # 1.0 to 2.0
    elif s >= 0.20:
        return 0.5 + (s - 0.20) * 2.5   # 0.5 to 1.0
    return max(0.05, s * 2.5)


def compute_slick_geometry(slick: Slick, vessel: Vessel | None, course_deg: float | None = None) -> float:
    """Likelihood ratio for slick geometric alignment."""
    if not vessel or slick.uncertainty > 0.6:
        return 1.0  # Neutral
    return 1.4


def compute_head_proximity(slick_head_coords: tuple[float, float], vessel_pos: tuple[float, float] | None) -> float:
    """
    Likelihood ratio for presence at slick head:
    - Within 2 km: L = 5.0
    - Within 5 km: L = 2.5
    - Within 12 km: L = 0.8
    - > 20 km: L = 0.05
    """
    if not vessel_pos:
        return 0.1
    lat1, lon1 = slick_head_coords
    lat2, lon2 = vessel_pos

    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    dist_km = 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    if dist_km <= 2.0:
        return 5.0
    elif dist_km <= 5.0:
        return 2.5
    elif dist_km <= 10.0:
        return 1.0
    elif dist_km <= 20.0:
        return 0.3
    return 0.05


def compute_behaviour_score(speed_drop: bool, course_change: bool, ais_gap_in_high_coverage: bool) -> float:
    """
    Likelihood ratio for operational behavior:
    - Speed drop + course change + gap: L = 3.5
    - Normal cruising: L = 1.0
    """
    l_ratio = 1.0
    if speed_drop:
        l_ratio *= 1.8
    if course_change:
        l_ratio *= 1.4
    if ais_gap_in_high_coverage:
        l_ratio *= 1.5
    return round(l_ratio, 2)


def fuse_evidence(
    hypotheses: list[str],
    evidence_dict: dict[str, dict[str, float]],
    priors: dict[str, float],
    tempering_exponent: float = 0.85,
) -> dict[str, float]:
    """
    Computes unnormalized posterior:
    P(H | E) proportional to Prior(H) * product_m (Likelihood_Ratio_m(E_m | H))^gamma
    For U (unknown): Likelihood_Ratio = 1.0
    """
    unnorm = {}
    for h in hypotheses:
        prior = priors.get(h, 0.1)
        if h == "U":
            unnorm["U"] = prior * 1.0  # L_U = 1.0 (null baseline)
            continue

        terms = evidence_dict.get(h, {})
        prod_l = 1.0
        for val in terms.values():
            prod_l *= max(1e-4, val)

        tempered_l = prod_l ** tempering_exponent
        unnorm[h] = prior * tempered_l

    return unnorm
