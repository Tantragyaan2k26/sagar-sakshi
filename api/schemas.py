"""
SAGAR-SAKSHI Data Contracts (api/schemas.py)
Pydantic V2 models defining the data contracts across all pipeline stages (§11).
"""

from datetime import datetime
from typing import Literal, Any
from pydantic import BaseModel, Field


class SarScene(BaseModel):
    scene_id: str
    satellite: str = "Sentinel-1A"
    acquisition_start_utc: datetime
    acquisition_end_utc: datetime
    footprint: dict[str, Any] = Field(..., description="GeoJSON Polygon geometry")
    orbit_direction: str = "ASCENDING"


class Slick(BaseModel):
    slick_id: str = "slick_001"
    polygon: dict[str, Any] = Field(..., description="GeoJSON Polygon geometry")
    p_oil: float = Field(
        ..., ge=0.0, le=1.0,
        description="Legacy field containing an uncalibrated heuristic candidate score, not an oil probability.",
    )
    wind_class: Literal["too_low", "workable", "too_high"]
    uncertainty: float = Field(..., ge=0.0, le=1.0)
    model_id: str
    area_km2: float | None = None
    perimeter_km: float | None = None
    elongation_ratio: float | None = None
    heading_deg: float | None = None
    age_hours_est: float | None = Field(None, description="Unvalidated GRD intensity heuristic; not a measured spill age.")
    age_method: str | None = None
    lookalike_class: str | None = None
    lookalike_reason: str | None = None
    geometry_source: str = "pixel_contour"
    contrast_db: float | None = None


class ShipDetection(BaseModel):
    detection_id: str = "det_001"
    point: tuple[float, float] = Field(..., description="(lat, lon) coordinates")
    azimuth_time_utc: datetime
    position_sigma_m: float = 25.0
    length_m: float | None = None
    vessel_class: Literal["vessel", "fixed_infrastructure", "false_alarm"] = "vessel"
    p_vessel: float = Field(..., ge=0.0, le=1.0)
    heading_axis_deg: float | None = Field(None, description="Heading axis (180° ambiguous)")


class Vessel(BaseModel):
    vessel_id: str
    name: str | None = None
    mmsi: str | None = None
    ais_track_id: str | None = None
    sar_detection_id: str | None = None
    status: Literal["matched", "ais_only", "sar_only_dark", "sar_only_unverified"]
    coverage_p: float = Field(..., ge=0.0, le=1.0)
    last_known_point: tuple[float, float] | None = None
    last_known_time_utc: datetime | None = None


class DriftHypothesis(BaseModel):
    vessel_id: str
    footprint: dict[str, Any] = Field(..., description="GeoJSON Polygon or MultiPolygon")
    overlap_score: float = Field(..., ge=0.0, le=1.0)
    ensemble_spread: float
    forcing_ids: list[str] = Field(default_factory=list)


class AttributionResult(BaseModel):
    schema_version: str = "1.0"
    run_id: str
    posteriors: dict[str, float] = Field(
        ...,
        description="Legacy field containing normalized, uncalibrated prototype ranking weights. 'U' is always present and values sum to 1.0.",
    )
    evidence_terms: dict[str, dict[str, float]] = Field(
        default_factory=dict,
        description="hypothesis_id -> {term_name: likelihood_or_score}",
    )
    grade: Literal["A", "B", "C", "None"]
    exclusions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of excluded candidates: [{'vessel_id': str, 'reason': str}]",
    )
    headline: str = Field(..., description="Enforced wording per the grade rules in Section 9")


class EvidenceCard(BaseModel):
    run_id: str
    manifest_sha256: str
    attribution: AttributionResult
    ais_status: Literal["available", "unavailable", "synthetic", "historic_reconstruction"]
    generated_at_utc: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
