"""Time-aware metocean forcing from an explicit CSV or configured constants.

CSV inputs use timestamp_utc,lat,lon,current_u_mps,current_v_mps,
wind_speed_mps,wind_from_deg[,source_id]. Sampling is nearest-in-space/time;
this prototype does not interpolate a gridded ocean model.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import csv
import math
import os
from typing import Any


@dataclass
class MetoceanVector:
    u_current_mps: float
    v_current_mps: float
    wind_speed_mps: float
    wind_from_deg: float
    wind_u_mps: float
    wind_v_mps: float
    source_id: str = "configured_constant_demo"


def _parse_datetime(value: str) -> datetime:
    stamp = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    return stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp.astimezone(timezone.utc)


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


class ForcingFetcher:
    """Resolve time/position samples or return explicitly configured constants."""

    REQUIRED_CSV_COLUMNS = {
        "timestamp_utc", "lat", "lon", "current_u_mps", "current_v_mps",
        "wind_speed_mps", "wind_from_deg",
    }

    def __init__(self, config: dict[str, Any]):
        self.config = config
        met = config.get("metocean", {})
        self.default_u = float(met.get("default_current_u_mps", 0.15))
        self.default_v = float(met.get("default_current_v_mps", -0.25))
        self.default_w_speed = float(met.get("default_wind_speed_mps", 5.8))
        self.default_w_from = float(met.get("default_wind_from_deg", 240.0))
        self.max_time_gap_hours = float(met.get("max_time_gap_hours", 3.0))
        self.max_distance_km = float(met.get("max_distance_km", 75.0))
        self.samples: list[dict[str, Any]] = []
        self.csv_path = met.get("forcing_csv")
        if self.csv_path:
            if not os.path.isfile(self.csv_path):
                raise FileNotFoundError(f"Configured metocean CSV not found: {self.csv_path}")
            with open(self.csv_path, newline="", encoding="utf-8-sig") as stream:
                reader = csv.DictReader(stream)
                if not reader.fieldnames or not self.REQUIRED_CSV_COLUMNS.issubset(set(reader.fieldnames)):
                    raise ValueError("Metocean CSV is missing required timestamp, coordinate, current, or wind columns.")
                for line_number, row in enumerate(reader, start=2):
                    try:
                        sample = {
                            "time": _parse_datetime(row["timestamp_utc"]),
                            "lat": float(row["lat"]), "lon": float(row["lon"]),
                            "u": float(row["current_u_mps"]), "v": float(row["current_v_mps"]),
                            "wind_speed": float(row["wind_speed_mps"]), "wind_from": float(row["wind_from_deg"]),
                            "source_id": (row.get("source_id") or "csv_sample").strip(),
                        }
                        if not -90 <= sample["lat"] <= 90 or not -180 <= sample["lon"] <= 180:
                            raise ValueError("coordinate out of range")
                        if sample["wind_speed"] < 0 or not 0 <= sample["wind_from"] <= 360:
                            raise ValueError("invalid wind speed/direction")
                        self.samples.append(sample)
                    except (TypeError, ValueError, KeyError) as exc:
                        raise ValueError(f"Invalid metocean CSV row {line_number}: {exc}") from exc
            if not self.samples:
                raise ValueError("Configured metocean CSV contains no samples.")
            self.provider_label = "csv_nearest_space_time_sample_no_interpolation"
        else:
            self.provider_label = "configured_constant_defaults"

    @staticmethod
    def _to_vector(u: float, v: float, speed: float, wind_from: float, source_id: str) -> MetoceanVector:
        # Meteorological direction is where wind comes from; components point toward.
        rad = math.radians((wind_from + 180.0) % 360.0)
        return MetoceanVector(
            u_current_mps=u, v_current_mps=v, wind_speed_mps=speed, wind_from_deg=wind_from,
            wind_u_mps=speed * math.sin(rad), wind_v_mps=speed * math.cos(rad), source_id=source_id,
        )

    def get_forcing_at(self, lat: float, lon: float, timestamp_iso: str | None = None) -> MetoceanVector:
        if self.samples:
            if not timestamp_iso:
                raise ValueError("A timestamp is required when a metocean CSV is configured.")
            query_time = _parse_datetime(timestamp_iso)
            candidates = []
            for sample in self.samples:
                age_hours = abs((sample["time"] - query_time).total_seconds()) / 3600.0
                distance_km = _distance_km(lat, lon, sample["lat"], sample["lon"])
                if age_hours <= self.max_time_gap_hours and distance_km <= self.max_distance_km:
                    score = age_hours / max(1e-6, self.max_time_gap_hours) + distance_km / max(1e-6, self.max_distance_km)
                    candidates.append((score, sample))
            if not candidates:
                raise ValueError(
                    f"No metocean sample within {self.max_time_gap_hours:g} h and "
                    f"{self.max_distance_km:g} km of ({lat:.4f}, {lon:.4f}) at {timestamp_iso}."
                )
            _, sample = min(candidates, key=lambda item: item[0])
            return self._to_vector(sample["u"], sample["v"], sample["wind_speed"], sample["wind_from"], sample["source_id"])

        # Clearly marked demo constant: coastal multiplier is not a measured field.
        coastal_factor = 1.15 if lon > 76.2 else 1.0
        return self._to_vector(
            self.default_u * coastal_factor, self.default_v * coastal_factor,
            self.default_w_speed, self.default_w_from, self.provider_label,
        )

    def compute_drift_velocity(
        self,
        lat: float,
        lon: float,
        wind_drift_factor: float = 0.03,
        ekman_deflection_deg: float = 15.0,
        timestamp_iso: str | None = None,
    ) -> tuple[float, float]:
        """Current plus a simple windage vector; coefficients remain assumptions."""
        forcing = self.get_forcing_at(lat, lon, timestamp_iso)
        rad_ekman = math.radians(ekman_deflection_deg)
        cos_ek, sin_ek = math.cos(rad_ekman), math.sin(rad_ekman)
        wind_u_rot = forcing.wind_u_mps * cos_ek - forcing.wind_v_mps * sin_ek
        wind_v_rot = forcing.wind_u_mps * sin_ek + forcing.wind_v_mps * cos_ek
        return (
            forcing.u_current_mps + wind_drift_factor * wind_u_rot,
            forcing.v_current_mps + wind_drift_factor * wind_v_rot,
        )
