"""
SAGAR-SAKSHI AIS Ingestion & Replay Recorder (ingest/ais_recorder.py)
Ingests historical or recorded AIS logs for the AOI and window.
The current demo generator creates synthetic fixtures, explicitly marked as
synthetic in the manifest; it does not reconstruct historical AIS.
"""

from datetime import datetime, timedelta, timezone
import csv
import os
from typing import Any


def generate_kerala_traffic(
    incident_time: datetime,
    window_hours: int = 24,
    target_name: str = "MSC ELSA 3",
    target_mmsi: str = "SYN-KERALA-LEAD-01",
) -> list[dict[str, Any]]:
    """Backward-compatible wrapper for the Kerala synthetic demo fixture."""
    return generate_synthetic_traffic(
        incident_time=incident_time,
        window_hours=window_hours,
        target_name=target_name,
        target_mmsi=target_mmsi,
        target_lat=9.265,
        target_lon=76.140,
    )


def generate_synthetic_traffic(
    incident_time: datetime,
    window_hours: int = 24,
    target_name: str = "SYNTHETIC DEMO CANDIDATE",
    target_mmsi: str = "SYN-DEMO-LEAD-01",
    target_lat: float = 9.265,
    target_lon: float = 76.140,
) -> list[dict[str, Any]]:
    """Create visibly synthetic demo tracks centered on a configured scenario point.

    These records are workflow fixtures only. They are not a reconstruction of
    historical AIS transmissions and must not be used as incident evidence.
    """
    records: list[dict[str, Any]] = []
    t_start = incident_time - timedelta(hours=window_hours)
    num_steps = max(1, window_hours * 6)

    routes = [
        (target_name, target_mmsi, "Cargo / Container Ship", 2.5, -0.55, 0.0, 0.0, 13.0, 180.0),
        ("SYNTHETIC BACKGROUND TANKER", "SYN-DEMO-BG-02", "Tanker", -1.8, -0.8, -0.2, 0.3, 11.0, 25.0),
        ("SYNTHETIC BACKGROUND CARRIER", "SYN-DEMO-BG-03", "Bulk Carrier", 1.7, 0.8, -0.4, -0.5, 10.0, 200.0),
    ]
    for name, mmsi, vessel_type, lat_start_off, lon_start_off, lat_end_off, lon_end_off, sog, cog in routes:
        for i in range(num_steps + 1):
            frac = i / num_steps
            timestamp = t_start + timedelta(minutes=i * 10)
            current_sog = sog
            current_cog = cog
            hours_to_image = (incident_time - timestamp).total_seconds() / 3600.0
            if mmsi == target_mmsi and 0.5 <= hours_to_image <= 3.0:
                current_sog = 5.5
                current_cog = (cog + 20.0) % 360.0
            records.append({
                "mmsi": mmsi,
                "vessel_name": name,
                "vessel_type": vessel_type,
                "timestamp_utc": timestamp.isoformat(),
                "lat": round(target_lat + lat_start_off + frac * (lat_end_off - lat_start_off), 5),
                "lon": round(target_lon + lon_start_off + frac * (lon_end_off - lon_start_off), 5),
                "sog": round(current_sog, 1),
                "cog": round(current_cog, 1),
                "length_m": 184.0 if mmsi == target_mmsi else 210.0,
                "nav_status": "Synthetic demonstration track",
            })

    return records


def load_ais_csv(
    path: str,
    incident_time: datetime,
    window_hours: int,
) -> list[dict[str, Any]]:
    """Load timestamped historical AIS rows from the documented CSV schema.

    Rows are limited to the incident-time window. This does not establish the
    archive's provenance, identity accuracy, or receiver coverage.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Configured AIS CSV not found: {path}")
    if incident_time.tzinfo is None:
        incident_time = incident_time.replace(tzinfo=timezone.utc)
    start = incident_time - timedelta(hours=window_hours)
    rows: list[dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        required = {"timestamp_utc", "lat", "lon"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError(f"AIS CSV needs columns: {', '.join(sorted(required))}")
        for line_number, row in enumerate(reader, start=2):
            try:
                stamp = datetime.fromisoformat(row["timestamp_utc"].strip().replace("Z", "+00:00"))
                if stamp.tzinfo is None:
                    stamp = stamp.replace(tzinfo=timezone.utc)
                stamp = stamp.astimezone(timezone.utc)
                lat, lon = float(row["lat"]), float(row["lon"])
                if not -90 <= lat <= 90 or not -180 <= lon <= 180:
                    raise ValueError("coordinate out of range")
                if not start <= stamp <= incident_time.astimezone(timezone.utc):
                    continue
                mmsi = (row.get("mmsi") or "").strip()
                vessel_name = (row.get("vessel_name") or "").strip() or mmsi or "UNIDENTIFIED AIS TRACK"
                rows.append({
                    "mmsi": mmsi or vessel_name,
                    "vessel_name": vessel_name,
                    "vessel_type": (row.get("vessel_type") or "unknown").strip(),
                    "timestamp_utc": stamp.isoformat(),
                    "lat": lat,
                    "lon": lon,
                    "sog": float(row["sog"]) if row.get("sog", "").strip() else 0.0,
                    "cog": float(row["cog"]) if row.get("cog", "").strip() else 0.0,
                    "length_m": float(row["length_m"]) if row.get("length_m", "").strip() else None,
                    "nav_status": (row.get("nav_status") or "unknown").strip(),
                    "data_status": "historical_csv_input_unverified",
                })
            except (TypeError, ValueError, KeyError) as exc:
                raise ValueError(f"Invalid AIS CSV row {line_number}: {exc}") from exc
    if not rows:
        raise ValueError("AIS CSV has no valid rows inside the configured time window.")
    return rows
