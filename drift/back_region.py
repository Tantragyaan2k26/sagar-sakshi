"""
SAGAR-SAKSHI Backward Drift Reachability & Vessel Gating Engine (drift/back_region.py)
Releases particles across the observed slick at image time, steps backward in time (up to 24h),
and gates candidate vessels whose tracks enter the reachability envelope (§6 Stage 5).
"""

from datetime import datetime, timedelta, timezone
import math
from typing import Any
from shapely.geometry import Polygon, Point, mapping, shape
from ingest.forcing_fetcher import ForcingFetcher


def compute_back_drift_region(
    slick_geojson: dict[str, Any],
    forcing_fetcher: ForcingFetcher,
    window_hours: int = 24,
    ensemble_spread_factor: float = 1.35,  # Inflate current uncertainty per Ennore lessons
    image_time: datetime | None = None,
) -> dict[str, Any]:
    """
    Computes the reverse space-time reachability cone.
    Particles advected backwards in time with negative velocity steps:
    dx/dt = - V_drift + turbulent_dispersion.
    """
    slick_poly = shape(slick_geojson)
    centroid = slick_poly.centroid
    c_lat, c_lon = centroid.y, centroid.x

    if image_time is None:
        image_time = datetime.now(timezone.utc)
    elif image_time.tzinfo is None:
        image_time = image_time.replace(tzinfo=timezone.utc)
    back_lat, back_lon = c_lat, c_lon
    remaining = max(0.0, window_hours * 3600.0)
    current_time = image_time
    while remaining > 0:
        step_seconds = min(3600.0, remaining)
        u_drift, v_drift = forcing_fetcher.compute_drift_velocity(
            back_lat, back_lon, timestamp_iso=current_time.isoformat()
        )
        back_lat -= v_drift * step_seconds / 111_000.0
        back_lon -= u_drift * step_seconds / (111_000.0 * max(0.05, math.cos(math.radians(back_lat))))
        remaining -= step_seconds
        current_time -= timedelta(seconds=step_seconds)
    total_sec = max(0.0, window_hours * 3600.0)

    # Build back-cone envelope polygon:
    # Starts narrow at image time slick, expands upstream with ensemble diffusion spread
    lateral_dispersion_m = math.sqrt(2.0 * 15.0 * total_sec) * ensemble_spread_factor  # Eddy diffusivity
    lat_disp_deg = lateral_dispersion_m / 111_000.0

    cone_poly = Polygon([
        [c_lon - 0.02, c_lat - 0.02],
        [c_lon + 0.02, c_lat + 0.02],
        [back_lon + lat_disp_deg, back_lat + lat_disp_deg],
        [back_lon - lat_disp_deg, back_lat - lat_disp_deg],
        [c_lon - 0.02, c_lat - 0.02],
    ])

    return {
        "type": "BackRegion",
        "slick_centroid": (c_lat, c_lon),
        "back_origin": (round(back_lat, 5), round(back_lon, 5)),
        "window_hours": window_hours,
        "envelope_polygon": mapping(cone_poly),
        "lateral_spread_km": round(lateral_dispersion_m / 1000.0, 2),
        "image_time_utc": image_time.isoformat(),
        "forcing_source": forcing_fetcher.provider_label,
        "drift_method": "time_stepped_advection_approximation_not_opendrift",
    }


def gate_vessels_against_back_region(
    back_region: dict[str, Any],
    vessel_tracks: dict[str, list[dict[str, Any]]],
) -> tuple[list[str], list[dict[str, Any]]]:
    """
    Gating test:
    - Retains vessels whose track points entered the backward reachability cone.
    - Excludes vessels that never came within reach, recording the exculpatory reason.
    """
    cone_poly = shape(back_region["envelope_polygon"])
    surviving_vessels: list[str] = []
    exclusions: list[dict[str, Any]] = []

    for v_id, reports in vessel_tracks.items():
        if not reports:
            exclusions.append({
                "vessel_id": v_id,
                "reason": "No valid track reports in window",
            })
            continue

        # Check if any track point is inside or very close to cone
        entered = False
        min_dist_deg = 999.0

        for r in reports:
            pt = Point(r["lon"], r["lat"])
            if cone_poly.contains(pt):
                entered = True
                break
            d = cone_poly.distance(pt)
            if d < min_dist_deg:
                min_dist_deg = d

        if entered or min_dist_deg < 0.05:  # within ~3 nm tolerance
            surviving_vessels.append(v_id)
        else:
            dist_nm = round(min_dist_deg * 60.0, 1)
            exclusions.append({
                "vessel_id": v_id,
                "reason": f"Track never entered backward reachability envelope (closest approach: {dist_nm} nm)",
            })

    return surviving_vessels, exclusions
