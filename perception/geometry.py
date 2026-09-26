"""
Convert a binary dark-pixel mask into a geographic slick polygon and morphometry.
Age is a literature-style proxy (not SAR phase — GRD has no interferometric phase).
"""

from typing import Any
import numpy as np
from rasterio.features import shapes
from rasterio.transform import Affine
from pyproj import CRS, Geod, Transformer
from shapely.geometry import shape, Polygon, MultiPolygon
from shapely.ops import transform as transform_geometry, unary_union


def pixel_to_lonlat(row: float, col: float, meta: dict[str, Any]) -> tuple[float, float]:
    if "pixel_transform" in meta:
        affine = Affine(*meta["pixel_transform"])
        x, y = affine * (col + 0.5, row + 0.5)
        transformer = Transformer.from_crs(meta.get("crs", "EPSG:4326"), "EPSG:4326", always_xy=True)
        return transformer.transform(x, y)
    h = max(1, meta["height"] - 1)
    w = max(1, meta["width"] - 1)
    lon = meta["min_lon"] + (col / w) * (meta["max_lon"] - meta["min_lon"])
    lat = meta["max_lat"] - (row / h) * (meta["max_lat"] - meta["min_lat"])
    return lon, lat


def mask_to_polygon(mask: np.ndarray, meta: dict[str, Any], max_points: int = 48) -> Polygon | MultiPolygon | None:
    """Polygonize the actual mask boundary; keep separate components separate."""
    binary = np.asarray(mask, dtype=np.uint8)
    if binary.ndim != 2 or int(binary.sum()) < 20:
        return None
    if "pixel_transform" in meta:
        affine = Affine(*meta["pixel_transform"])
    else:
        affine = Affine(
            (meta["max_lon"] - meta["min_lon"]) / max(1, mask.shape[1]), 0, meta["min_lon"],
            0, -(meta["max_lat"] - meta["min_lat"]) / max(1, mask.shape[0]), meta["max_lat"],
        )
    geometries = [shape(geom) for geom, value in shapes(binary, mask=binary > 0, transform=affine) if value == 1]
    if not geometries:
        return None
    geometry = unary_union(geometries)
    source_crs = meta.get("crs", "EPSG:4326")
    if source_crs != "EPSG:4326":
        transformer = Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)
        geometry = transform_geometry(transformer.transform, geometry)
    if not geometry.is_valid:
        geometry = geometry.buffer(0)
    if geometry.is_empty or geometry.area <= 0:
        return None
    # Simplify only to keep evidence-card polygons compact, without bridging
    # disconnected detections or replacing the observed boundary by a hull.
    span = max(geometry.bounds[2] - geometry.bounds[0], geometry.bounds[3] - geometry.bounds[1])
    geometry = geometry.simplify(span / max(24, max_points), preserve_topology=True)
    if geometry.geom_type == "Polygon":
        return geometry
    if geometry.geom_type == "MultiPolygon":
        parts = [part for part in geometry.geoms if part.area > 0]
        return MultiPolygon(parts) if parts else None
    polygons = [part for part in getattr(geometry, "geoms", []) if part.geom_type == "Polygon"]
    return MultiPolygon(polygons) if polygons else None


def morphometry(poly: Polygon, centroid_lat: float) -> dict[str, float]:
    centroid = poly.centroid
    zone = max(1, min(60, int((centroid.x + 180.0) // 6) + 1))
    epsg = (32700 if centroid.y < 0 else 32600) + zone
    to_utm = Transformer.from_crs("EPSG:4326", CRS.from_epsg(epsg), always_xy=True)
    metric = transform_geometry(to_utm.transform, poly)
    minx, miny, maxx, maxy = metric.bounds
    width_m = maxx - minx
    height_m = maxy - miny
    elongation = max(width_m, height_m) / max(1.0, min(width_m, height_m))
    area_m2, perimeter_m = Geod(ellps="WGS84").geometry_area_perimeter(poly)
    area_km2 = abs(area_m2) / 1e6
    peri_km = abs(perimeter_m) / 1000.0
    heading = 90.0 if width_m >= height_m else 0.0
    # Refine the major-axis heading using the metric minimum-rotated rectangle.
    try:
        rect = metric.minimum_rotated_rectangle
        coords = list(rect.exterior.coords)
        dx = coords[1][0] - coords[0][0]
        dy = coords[1][1] - coords[0][1]
        heading = (np.degrees(np.arctan2(dx, dy)) + 360.0) % 180.0
    except Exception:
        pass
    return {
        "area_km2": float(round(area_km2, 3)),
        "perimeter_km": float(round(peri_km, 3)),
        "elongation_ratio": float(round(elongation, 2)),
        "heading_deg": float(round(heading, 1)),
        "bbox_width_m": float(round(width_m, 1)),
        "bbox_height_m": float(round(height_m, 1)),
    }


def estimate_slick_age_hours(
    contrast_db: float,
    wind_speed_mps: float,
    elongation_ratio: float,
    area_km2: float,
) -> dict[str, Any]:
    """
    Empiric weathering proxy (Fay spreading + wind mixing), not interferometric age.
    Sentinel-1 GRD discards phase, so 'phase spreading age' is physically invalid.
    """
    # Fresh mineral oil: high contrast, elongated ship-wake geometry.
    freshness = np.clip((contrast_db - 3.0) / 6.0, 0.0, 1.0)
    spread = np.clip(area_km2 / 8.0, 0.0, 1.0)
    wind_mix = np.clip((wind_speed_mps - 3.0) / 8.0, 0.0, 1.0)
    hours = 2.0 + (1.0 - freshness) * 18.0 + spread * 8.0 + wind_mix * 4.0
    hours = float(np.clip(hours, 1.0, 36.0))
    if elongation_ratio >= 3.0 and contrast_db >= 5.0:
        hours = min(hours, 8.0)
    return {
        "age_hours_est": round(hours, 1),
        "age_method": "unvalidated_grd_intensity_weathering_proxy",
        "age_uncertainty_hours": round(max(2.0, hours * 0.35), 1),
        "note": "Unvalidated heuristic from GRD intensity and configured wind; not a measured age. GRD phase is unavailable.",
    }
