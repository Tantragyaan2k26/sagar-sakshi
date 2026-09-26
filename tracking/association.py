"""
SAGAR-SAKSHI SAR-AIS Association Engine (tracking/association.py)
Solves global association using Mahalanobis distance cost matrix and Hungarian algorithm,
classifying candidates into matched, ais_only, sar_only_dark, and sar_only_unverified (§6 Stage 4).
"""

from datetime import datetime
import math
from typing import Any
import numpy as np
from scipy.optimize import linear_sum_assignment
from api.schemas import ShipDetection, Vessel
from ingest.coverage_grid import CoverageGrid
from tracking.azimuth_shift import apply_azimuth_correction


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance between two coordinates in meters."""
    r = 6371000.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def associate_sar_ais(
    sar_detections: list[ShipDetection],
    smoothed_tracks: dict[str, dict[str, Any]],  # vessel_id -> smoothed_state
    coverage_grid: CoverageGrid,
    acquisition_time: datetime,
    max_gate_dist_m: float = 3500.0,
    track_labels: dict[str, str] | None = None,
) -> tuple[list[Vessel], dict[str, Any]]:
    """
    Performs global optimal SAR-to-AIS assignment.
    """
    vessels_out: list[Vessel] = []
    ais_ids = list(smoothed_tracks.keys())
    num_sar = len(sar_detections)
    num_ais = len(ais_ids)

    assigned_sar_indices = set()
    assigned_ais_indices = set()

    if num_sar > 0 and num_ais > 0:
        cost_matrix = np.full((num_sar, num_ais), fill_value=1e6)

        for i, det in enumerate(sar_detections):
            det_lat, det_lon = det.point
            for j, v_id in enumerate(ais_ids):
                track = smoothed_tracks[v_id]
                raw_lat, raw_lon = track["lat"], track["lon"]
                sog = track.get("sog", 10.0)
                cog = track.get("cog", 0.0)

                # 1. Apply azimuth shift correction
                app_lat, app_lon, shift_m = apply_azimuth_correction(raw_lat, raw_lon, sog, cog)

                # 2. Distance between SAR detection and azimuth-corrected AIS position
                dist_m = haversine_m(det_lat, det_lon, app_lat, app_lon)

                if dist_m < max_gate_dist_m:
                    # Normalized Mahalanobis-like cost
                    cost = dist_m / 1000.0
                    cost_matrix[i, j] = cost

        # Solve global assignment with Hungarian algorithm
        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        for r, c in zip(row_ind, col_ind):
            if cost_matrix[r, c] < (max_gate_dist_m / 1000.0):
                v_id = ais_ids[c]
                det = sar_detections[r]
                track = smoothed_tracks[v_id]
                cov_p = coverage_grid.get_observability(track["lat"], track["lon"])

                vessels_out.append(Vessel(
                    vessel_id=v_id,
                    name=(track_labels or {}).get(v_id, v_id),
                    ais_track_id=v_id,
                    sar_detection_id=det.detection_id,
                    status="matched",
                    coverage_p=round(cov_p, 3),
                    last_known_point=(track["lat"], track["lon"]),
                    last_known_time_utc=acquisition_time,
                ))
                assigned_sar_indices.add(r)
                assigned_ais_indices.add(c)

    # 3. Unmatched AIS tracks -> 'ais_only'
    for j, v_id in enumerate(ais_ids):
        if j not in assigned_ais_indices:
            track = smoothed_tracks[v_id]
            cov_p = coverage_grid.get_observability(track["lat"], track["lon"])
            vessels_out.append(Vessel(
                vessel_id=v_id,
                name=(track_labels or {}).get(v_id, v_id),
                ais_track_id=v_id,
                sar_detection_id=None,
                status="ais_only",
                coverage_p=round(cov_p, 3),
                last_known_point=(track["lat"], track["lon"]),
                last_known_time_utc=acquisition_time,
            ))

    # 4. Unmatched SAR detections -> evaluate coverage grid:
    # A dark label requires independently recorded high coverage.
    for i, det in enumerate(sar_detections):
        if i not in assigned_sar_indices:
            lat, lon = det.point
            cov_p = coverage_grid.get_observability(lat, lon)
            status = "sar_only_dark" if cov_p >= coverage_grid.dark_threshold else "sar_only_unverified"

            v_id = f"DARK_{det.detection_id}"
            vessels_out.append(Vessel(
                vessel_id=v_id,
                name=f"Uncorrelated SAR Target ({status})",
                ais_track_id=None,
                sar_detection_id=det.detection_id,
                status=status,
                coverage_p=round(cov_p, 3),
                last_known_point=(lat, lon),
                last_known_time_utc=acquisition_time,
            ))

    stats = {
        "total_sar_detections": num_sar,
        "total_ais_tracks": num_ais,
        "matched_count": len(assigned_sar_indices),
        "dark_vessel_count": sum(1 for v in vessels_out if v.status == "sar_only_dark"),
        "unverified_count": sum(1 for v in vessels_out if v.status == "sar_only_unverified"),
    }
    return vessels_out, stats
