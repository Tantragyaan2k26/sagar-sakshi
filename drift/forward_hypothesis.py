"""
SAGAR-SAKSHI Forward Trajectory Simulation Engine (drift/forward_hypothesis.py)
Simulates forward drift of plausible releases from surviving vessel tracks
and measures spatial-temporal agreement with the observed slick (§6 Stage 5).
"""

from datetime import datetime, timedelta, timezone
import math
from typing import Any
from shapely.geometry import Point, shape, mapping, box
from api.schemas import DriftHypothesis
from ingest.forcing_fetcher import ForcingFetcher


def simulate_forward_vessel_hypothesis(
    vessel_id: str,
    vessel_reports: list[dict[str, Any]],
    slick_geojson: dict[str, Any],
    image_time: datetime,
    forcing_fetcher: ForcingFetcher,
) -> DriftHypothesis:
    """
    Simulates forward advection of hypothetical discharge points along the vessel track
    up to the satellite image acquisition time.
    """
    slick_poly = shape(slick_geojson)
    c_lat, c_lon = slick_poly.centroid.y, slick_poly.centroid.x

    best_overlap = 0.05
    best_footprint = None
    min_dist_km = 999.0

    # Test release points along vessel track within last 12 hours
    for r in vessel_reports[-60:]:
        t_r = datetime.fromisoformat(r["timestamp_utc"].replace("Z", "+00:00"))
        if t_r.tzinfo is None:
            t_r = t_r.replace(tzinfo=image_time.tzinfo or timezone.utc)
        dt_sec = (image_time - t_r).total_seconds()
        if dt_sec < 0 or dt_sec > 48 * 3600:
            continue

        lat0, lon0 = r["lat"], r["lon"]
        adv_lat, adv_lon = lat0, lon0
        current_time = t_r
        remaining = dt_sec
        while remaining > 0:
            step_seconds = min(3600.0, remaining)
            u_drift, v_drift = forcing_fetcher.compute_drift_velocity(
                adv_lat, adv_lon, timestamp_iso=current_time.isoformat()
            )
            adv_lat += v_drift * step_seconds / 111_000.0
            adv_lon += u_drift * step_seconds / (111_000.0 * max(0.05, math.cos(math.radians(adv_lat))))
            current_time += timedelta(seconds=step_seconds)
            remaining -= step_seconds

        # Distance to observed slick centroid
        dlat = math.radians(adv_lat - c_lat)
        dlon = math.radians(adv_lon - c_lon)
        hav = math.sin(dlat / 2) ** 2 + math.cos(math.radians(c_lat)) * math.cos(math.radians(adv_lat)) * math.sin(dlon / 2) ** 2
        dist_km = 6371.0 * 2.0 * math.atan2(math.sqrt(hav), math.sqrt(max(0.0, 1.0 - hav)))
        if dist_km < min_dist_km:
            min_dist_km = dist_km

        # Particle spread envelope at image time
        sigma_m = math.sqrt(2.0 * 15.0 * dt_sec)
        sigma_deg = sigma_m / 111_000.0
        particle_box = box(
            adv_lon - sigma_deg,
            adv_lat - sigma_deg,
            adv_lon + sigma_deg,
            adv_lat + sigma_deg,
        )

        if particle_box.intersects(slick_poly):
            intersection_area = particle_box.intersection(slick_poly).area
            union_area = particle_box.union(slick_poly).area
            iou = intersection_area / max(1e-6, union_area)
            if iou > best_overlap:
                best_overlap = iou
                best_footprint = mapping(particle_box)

    # Compute agreement score based on closest distance and IOU
    if best_overlap > 0.05:
        score = min(0.95, 0.50 + best_overlap * 0.45)
    else:
        # Distance-based score decay
        if min_dist_km <= 2.0:
            score = 0.85
        elif min_dist_km <= 5.0:
            score = 0.65
        elif min_dist_km <= 12.0:
            score = 0.35
        elif min_dist_km <= 25.0:
            score = 0.15
        else:
            score = 0.02

    if not best_footprint:
        # Default bounding box around nearest advected location
        best_footprint = mapping(box(c_lon - 0.02, c_lat - 0.02, c_lon + 0.02, c_lat + 0.02))

    return DriftHypothesis(
        vessel_id=vessel_id,
        footprint=best_footprint,
        overlap_score=round(score, 3),
        ensemble_spread=round(min_dist_km, 2),
        forcing_ids=[forcing_fetcher.provider_label],
    )
