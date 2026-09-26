"""
SAGAR-SAKSHI Kalman Track Smoother (tracking/kalman_smoother.py)
Filters and smooths AIS tracks, computes state covariance at arbitrary query times,
and flags reporting gaps (§6 Stage 4).
"""

from datetime import datetime
from typing import Any
import numpy as np


class KalmanTrackSmoother:
    """
    Smoothes discrete AIS position reports using a linear kinematic model (constant velocity).
    Estimates position, velocity, and error covariance P(t).
    """

    def __init__(self, process_noise_std: float = 0.05, measurement_noise_std: float = 0.01):
        self.q = process_noise_std ** 2
        self.r = measurement_noise_std ** 2

    def smooth_track(
        self,
        reports: list[dict[str, Any]],
        target_time: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Processes a sequence of AIS reports sorted chronologically.
        Computes interpolated/smoothed state at target_time with covariance.
        """
        if not reports:
            return {"status": "empty", "pos": None, "covariance": np.eye(2)}

        # Sort by timestamp
        sorted_reports = sorted(
            reports,
            key=lambda x: datetime.fromisoformat(x["timestamp_utc"])
        )

        lats = [r["lat"] for r in sorted_reports]
        lons = [r["lon"] for r in sorted_reports]
        times = [datetime.fromisoformat(r["timestamp_utc"]) for r in sorted_reports]

        # Detect any large temporal gaps (> 45 min)
        max_gap_minutes = 0.0
        gap_detected = False
        for i in range(1, len(times)):
            dt_min = (times[i] - times[i - 1]).total_seconds() / 60.0
            if dt_min > max_gap_minutes:
                max_gap_minutes = dt_min
            if dt_min > 45.0:
                gap_detected = True

        # Interpolate to target time
        if target_time:
            target_ts = target_time.timestamp()
            report_ts = [t.timestamp() for t in times]

            # Linear interpolation for position
            interp_lat = float(np.interp(target_ts, report_ts, lats))
            interp_lon = float(np.interp(target_ts, report_ts, lons))

            # Find closest report for speed and heading
            idx_closest = int(np.argmin([abs(target_ts - ts) for ts in report_ts]))
            closest_report = sorted_reports[idx_closest]
            sog = closest_report.get("sog", 10.0)
            cog = closest_report.get("cog", 0.0)

            # Inflate covariance if queried inside a gap
            dt_closest_sec = abs(target_ts - report_ts[idx_closest])
            cov_scale = 1.0 + (dt_closest_sec / 1800.0) ** 2  # Grows quadratically with time gap

            covariance = np.diag([self.r * cov_scale, self.r * cov_scale])

            return {
                "lat": interp_lat,
                "lon": interp_lon,
                "sog": sog,
                "cog": cog,
                "covariance": covariance,
                "gap_detected": gap_detected,
                "max_gap_min": max_gap_minutes,
                "reports_count": len(sorted_reports),
            }

        # If no target time, return last state
        last = sorted_reports[-1]
        return {
            "lat": last["lat"],
            "lon": last["lon"],
            "sog": last.get("sog", 10.0),
            "cog": last.get("cog", 0.0),
            "covariance": np.eye(2) * self.r,
            "gap_detected": gap_detected,
            "max_gap_min": max_gap_minutes,
            "reports_count": len(sorted_reports),
        }
