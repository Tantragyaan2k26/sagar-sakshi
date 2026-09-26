"""
Demo SAR raster used when the 2.9GB SNAP GeoTIFF is not on disk.
Places a dark mineral-oil patch and bright ship scatterers inside the Kerala AOI
so the pipeline, tests, and live demo complete without the BigTIFF.
"""

from typing import Any, Literal
import numpy as np


def build_synthetic_sar_crop(
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    mode: Literal["oil", "lookalike"] = "oil",
    height: int = 256,
    width: int = 256,
    seed: int = 42,
    reference_lat: float | None = None,
    reference_lon: float | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    rng = np.random.default_rng(seed)
    sea = rng.normal(-12.5, 1.15, size=(height, width)).astype(np.float32)

    def lonlat_to_rc(lat: float, lon: float) -> tuple[int, int]:
        frac_r = (max_lat - lat) / max(1e-9, max_lat - min_lat)
        frac_c = (lon - min_lon) / max(1e-9, max_lon - min_lon)
        r = int(np.clip(frac_r * (height - 1), 0, height - 1))
        c = int(np.clip(frac_c * (width - 1), 0, width - 1))
        return r, c

    rr, cc = np.ogrid[:height, :width]
    slick_lat = reference_lat if reference_lat is not None else (min_lat + max_lat) / 2
    slick_lon = reference_lon if reference_lon is not None else (min_lon + max_lon) / 2
    r0, c0 = lonlat_to_rc(slick_lat, slick_lon)

    if mode == "lookalike":
        contrast = 2.2
        a, b = 18.0, 16.0
        angle = 0.2
    else:
        contrast = 6.4
        a, b = 38.0, 11.0
        angle = np.deg2rad(155.0)

    dr = rr - r0
    dc = cc - c0
    ca, sa = np.cos(angle), np.sin(angle)
    x = dc * ca + dr * sa
    y = -dc * sa + dr * ca
    ellipse = (x / a) ** 2 + (y / b) ** 2 <= 1.0
    sea[ellipse] -= contrast

    # Bright ship-like peaks (unfiltered CFAR targets)
    ship_pts = [
        (slick_lat, slick_lon),
        (slick_lat + 0.05, slick_lon + 0.04),
        (slick_lat - 0.045, slick_lon - 0.035),
        (slick_lat + 0.14, slick_lon + 0.18),
    ]
    if mode != "lookalike":
        ship_pts.append((slick_lat + 0.015, slick_lon + 0.015))  # extra demo hull

    for lat, lon in ship_pts:
        r, c = lonlat_to_rc(lat, lon)
        r0s, r1s = max(0, r - 1), min(height, r + 2)
        c0s, c1s = max(0, c - 1), min(width, c + 2)
        sea[r0s:r1s, c0s:c1s] = 8.5 + float(rng.normal(0, 0.4))

    meta = {
        "row_offset": 0,
        "col_offset": 0,
        "height": height,
        "width": width,
        "min_lat": min_lat,
        "min_lon": min_lon,
        "max_lat": max_lat,
        "max_lon": max_lon,
        "synthetic": True,
        "synthetic_mode": mode,
        "x_res": (max_lon - min_lon) / max(1, width - 1),
        "y_res": -(max_lat - min_lat) / max(1, height - 1),
        "x_origin": min_lon,
        "y_origin": max_lat,
    }
    return sea, meta
