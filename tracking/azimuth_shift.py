"""
SAGAR-SAKSHI SAR Azimuth-Shift Correction (tracking/azimuth_shift.py)
Corrects for the Doppler-induced azimuth displacement of moving vessels (§6 Stage 4).
Moving targets with radial velocity vr appear displaced along the SAR flight direction (azimuth)
by: dy = (R / V_sat) * v_r.
"""

import math


def compute_azimuth_shift_m(
    sog_knots: float,
    cog_deg: float,
    orbit_heading_deg: float = 348.0,  # Ascending orbit ~348° (roughly North-Northwest)
    look_direction: str = "RIGHT",      # Sentinel-1 is right-looking
    slant_range_m: float = 850_000.0,   # Nominal ~850 km
    v_satellite_mps: float = 7500.0,    # LEO orbital velocity ~7.5 km/s
) -> float:
    """
    Computes azimuth displacement in meters.
    1 knot = 0.514444 m/s.
    Look angle for right-looking ascending orbit is approx (orbit_heading + 90) % 360 = ~78° (East-Northeast).
    Radial velocity v_r is target velocity projected onto satellite look vector.
    """
    sog_mps = sog_knots * 0.514444

    look_angle_deg = (orbit_heading_deg + 90.0) % 360.0 if look_direction == "RIGHT" else (orbit_heading_deg - 90.0) % 360.0

    # Angle between ship course and radar look direction
    angle_diff_rad = math.radians(cog_deg - look_angle_deg)
    radial_speed_mps = sog_mps * math.cos(angle_diff_rad)

    # Azimuth shift delta_y = (R / V_sat) * v_r
    shift_meters = (slant_range_m / v_satellite_mps) * radial_speed_mps
    return shift_meters


def apply_azimuth_correction(
    lat: float,
    lon: float,
    sog_knots: float,
    cog_deg: float,
    orbit_heading_deg: float = 348.0,
) -> tuple[float, float, float]:
    """
    Applies azimuth shift displacement to convert true ground position into apparent SAR image position.
    Returns (corrected_lat, corrected_lon, shift_meters).
    """
    shift_m = compute_azimuth_shift_m(sog_knots, cog_deg, orbit_heading_deg=orbit_heading_deg)

    # Displace along satellite flight track direction (orbit_heading_deg)
    # 1 deg latitude ~ 111,000 m
    # 1 deg longitude ~ 111,000 * cos(lat) m
    orbit_rad = math.radians(orbit_heading_deg)
    d_north_m = shift_m * math.cos(orbit_rad)
    d_east_m = shift_m * math.sin(orbit_rad)

    d_lat = d_north_m / 111_000.0
    d_lon = d_east_m / (111_000.0 * math.cos(math.radians(lat)))

    corrected_lat = lat + d_lat
    corrected_lon = lon + d_lon
    return corrected_lat, corrected_lon, shift_m
