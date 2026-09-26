"""
SAGAR-SAKSHI Branch A: Spill segmentation, morphometry, look-alike class, age proxy.
Vectorizes the actual detected pixels — never a hardcoded MSC ELSA 3 polygon.
"""

from typing import Any, Literal
import numpy as np
from shapely.geometry import mapping
from api.schemas import Slick
from perception.geometry import mask_to_polygon, morphometry, estimate_slick_age_hours
from perception.lookalike_classifier import LookAlikeClassifier


def detect_slicks_threshold(
    crop_db: np.ndarray,
    crop_meta: dict[str, Any],
    wind_class: Literal["too_low", "workable", "too_high"] = "workable",
    relative_threshold_db: float = -4.5,
    wind_speed_mps: float = 5.8,
    chlorophyll_proxy_alert: bool = False,
) -> list[Slick]:
    sample = crop_db[::4, ::4]
    valid_sample = sample[np.isfinite(sample)]
    if len(valid_sample) == 0:
        return []

    sea_mean = float(np.mean(valid_sample))
    thresh_val = sea_mean + relative_threshold_db
    valid_mask = np.isfinite(crop_db)
    threshold_mask = (crop_db < thresh_val) & valid_mask

    # Keep the default transparent and deterministic. The repository's tiny
    # U-Net has only synthetic-shape training and is not an oil-spill model.
    dark_mask = threshold_mask
    used_model = "adaptive_dark_pixel_threshold_unvalidated"

    dark_pixel_count = int(np.sum(dark_mask))
    if dark_pixel_count < 50:
        return []

    poly = mask_to_polygon(dark_mask, crop_meta)
    if poly is None:
        return []

    slick_mean = float(np.mean(crop_db[dark_mask]))
    contrast_db = abs(sea_mean - slick_mean)
    morph = morphometry(poly, poly.centroid.y)
    age = estimate_slick_age_hours(
        contrast_db=contrast_db,
        wind_speed_mps=wind_speed_mps,
        elongation_ratio=morph["elongation_ratio"],
        area_km2=morph["area_km2"],
    )
    verdict = LookAlikeClassifier().classify_candidate(
        contrast_db=contrast_db,
        wind_speed_mps=wind_speed_mps,
        area_km2=morph["area_km2"],
        perimeter_km=morph["perimeter_km"],
        elongation_ratio=morph["elongation_ratio"],
        chlorophyll_proxy_alert=chlorophyll_proxy_alert,
    )

    heuristic_score = float(verdict.get("heuristic_score", 0.2))
    if wind_class != "workable":
        heuristic_score = min(heuristic_score, 0.30)
    uncertainty = 0.65

    return [Slick(
        slick_id="slick_primary",
        polygon=mapping(poly),
        p_oil=round(heuristic_score, 3),
        wind_class=wind_class,
        uncertainty=round(uncertainty, 3),
        model_id=used_model,
        area_km2=morph["area_km2"],
        perimeter_km=morph["perimeter_km"],
        elongation_ratio=morph["elongation_ratio"],
        heading_deg=morph["heading_deg"],
        age_hours_est=age["age_hours_est"],
        age_method=age["age_method"],
        lookalike_class=verdict.get("classification"),
        lookalike_reason=verdict.get("reason"),
        geometry_source="mask_boundary_polygon",
        contrast_db=round(contrast_db, 2),
    )]
