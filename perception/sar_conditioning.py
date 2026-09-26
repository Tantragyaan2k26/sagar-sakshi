"""Read calibrated SAR rasters in geographic AOIs; synthesize only when absent.

Real inputs must declare their radiometric units in the scenario config. Raw
Sentinel-1 GRD DN/amplitude is deliberately rejected: it is not calibrated dB.
"""

from datetime import datetime
import os
from typing import Any

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.enums import Resampling
from rasterio.warp import transform_bounds
from rasterio.windows import Window, from_bounds

from api.schemas import SarScene
from perception.synthetic_scene import build_synthetic_sar_crop


class SarConditioner:
    def __init__(self, tiff_path: str, config: dict[str, Any]):
        self.tiff_path = tiff_path
        self.config = config
        self.exists = os.path.isfile(tiff_path)
        self.synthetic = not self.exists
        self.tif = None

        sc = config.get("scene", {})
        aoi = config.get("incident", {}).get("aoi", {})
        self._aoi = {
            "min_lat": float(aoi.get("min_lat", 9.15)),
            "min_lon": float(aoi.get("min_lon", 76.05)),
            "max_lat": float(aoi.get("max_lat", 9.45)),
            "max_lon": float(aoi.get("max_lon", 76.35)),
        }
        self.synthetic_mode = sc.get("synthetic_mode", config.get("scenario", {}).get("sar_mode", "oil"))
        demo_reference = config.get("incident", {}).get("demo_reference_point", {})
        self.demo_reference_lat = float(demo_reference.get("lat", (self._aoi["min_lat"] + self._aoi["max_lat"]) / 2))
        self.demo_reference_lon = float(demo_reference.get("lon", (self._aoi["min_lon"] + self._aoi["max_lon"]) / 2))

        if not self.exists:
            self.width = self.height = 256
            self.crs = "EPSG:4326"
            self.transform = None
            self.band = 1
            self.value_units = "synthetic_demo_db"
            return

        self.value_units = str(sc.get("tiff_value_units", "")).lower()
        if self.value_units not in {"db", "sigma0_db", "gamma0_db", "sigma0_linear", "gamma0_linear"}:
            raise ValueError(
                "A real SAR raster requires scene.tiff_value_units to be one of "
                "db, sigma0_db, gamma0_db, sigma0_linear, gamma0_linear. "
                "Raw DN/amplitude is not a calibrated backscatter input."
            )
        self.band = int(sc.get("tiff_band", 1))
        try:
            self.tif = rasterio.open(tiff_path)
        except Exception as exc:
            raise ValueError(f"Could not open configured SAR GeoTIFF '{tiff_path}': {exc}") from exc
        if self.tif.crs is None:
            self.close()
            raise ValueError(f"Configured SAR GeoTIFF '{tiff_path}' has no CRS.")
        if not 1 <= self.band <= self.tif.count:
            self.close()
            raise ValueError(f"Configured SAR band {self.band} is outside the raster's {self.tif.count} bands.")
        self.width, self.height = self.tif.width, self.tif.height
        self.crs = self.tif.crs
        self.transform = self.tif.transform

    def close(self) -> None:
        if self.tif is not None:
            self.tif.close()
            self.tif = None

    def __del__(self) -> None:
        self.close()

    def coord_to_pixel(self, lat: float, lon: float) -> tuple[int, int]:
        """Return row, column for WGS84 coordinates in the configured raster."""
        if self.tif is None:
            row = round((self._aoi["max_lat"] - lat) / max(1e-12, self._aoi["max_lat"] - self._aoi["min_lat"]) * (self.height - 1))
            col = round((lon - self._aoi["min_lon"]) / max(1e-12, self._aoi["max_lon"] - self._aoi["min_lon"]) * (self.width - 1))
            return int(row), int(col)
        x, y = Transformer.from_crs("EPSG:4326", self.crs, always_xy=True).transform(lon, lat)
        return tuple(map(int, self.tif.index(x, y)))

    def pixel_to_coord(self, row: int, col: int) -> tuple[float, float]:
        """Return WGS84 latitude, longitude at the center of a raster pixel."""
        if self.tif is None:
            lon = self._aoi["min_lon"] + col / max(1, self.width - 1) * (self._aoi["max_lon"] - self._aoi["min_lon"])
            lat = self._aoi["max_lat"] - row / max(1, self.height - 1) * (self._aoi["max_lat"] - self._aoi["min_lat"])
            return lat, lon
        x, y = self.transform * (col + 0.5, row + 0.5)
        lon, lat = Transformer.from_crs(self.crs, "EPSG:4326", always_xy=True).transform(x, y)
        return lat, lon

    def extract_aoi_crop(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        band: int = 0,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        if self.synthetic:
            crop, meta = build_synthetic_sar_crop(
                min_lat, min_lon, max_lat, max_lon,
                mode=self.synthetic_mode,
                reference_lat=self.demo_reference_lat,
                reference_lon=self.demo_reference_lon,
            )
            meta.update({"source": "synthetic_demo_raster", "synthetic": True, "crs": "EPSG:4326"})
            return crop.astype(np.float32), meta

        if self.tif is None:
            raise RuntimeError("SAR GeoTIFF is closed.")
        selected_band = int(band + 1) if band > 0 else self.band
        if not 1 <= selected_band <= self.tif.count:
            raise ValueError(f"Requested SAR band {selected_band} is outside the raster's {self.tif.count} bands.")
        left, bottom, right, top = transform_bounds(
            "EPSG:4326", self.crs, min_lon, min_lat, max_lon, max_lat, densify_pts=21
        )
        requested = from_bounds(left, bottom, right, top, transform=self.transform)
        requested = requested.round_offsets().round_lengths()
        full = Window(0, 0, self.tif.width, self.tif.height)
        window = requested.intersection(full)
        if window.width <= 0 or window.height <= 0:
            raise ValueError("Configured SAR raster does not overlap the requested incident AOI.")

        values = self.tif.read(selected_band, window=window, masked=True, out_dtype="float32")
        crop = values.filled(np.nan).astype(np.float32, copy=False)
        if self.value_units.endswith("_linear"):
            crop = np.where(crop > 0, 10.0 * np.log10(crop), np.nan).astype(np.float32)
        crop_transform = self.tif.window_transform(window)
        west, south, east, north = transform_bounds(
            self.crs, "EPSG:4326", *self.tif.bounds, densify_pts=21
        )
        crop_west, crop_south, crop_east, crop_north = transform_bounds(
            self.crs, "EPSG:4326", *rasterio.windows.bounds(window, self.transform), densify_pts=21
        )
        meta = {
            "row_offset": int(window.row_off),
            "col_offset": int(window.col_off),
            "height": int(window.height),
            "width": int(window.width),
            "min_lat": crop_south,
            "min_lon": crop_west,
            "max_lat": crop_north,
            "max_lon": crop_east,
            "synthetic": False,
            "source": os.path.abspath(self.tiff_path),
            "crs": self.crs.to_string(),
            "pixel_transform": list(crop_transform)[:6],
            "value_units": self.value_units,
            "band": selected_band,
            "resampling": Resampling.nearest.name,
            "raster_bounds_wgs84": [west, south, east, north],
        }
        return crop, meta

    def get_scene_metadata(self) -> SarScene:
        sc = self.config.get("scene", {})
        if self.tif is None:
            west, south, east, north = (
                self._aoi["min_lon"], self._aoi["min_lat"], self._aoi["max_lon"], self._aoi["max_lat"]
            )
        else:
            west, south, east, north = transform_bounds(self.crs, "EPSG:4326", *self.tif.bounds, densify_pts=21)
        footprint_poly = {"type": "Polygon", "coordinates": [[
            [west, north], [east, north], [east, south], [west, south], [west, north]
        ]]}
        return SarScene(
            scene_id=sc.get("product_id", "S1_SCENE"),
            satellite=sc.get("satellite", "Sentinel-1A"),
            acquisition_start_utc=datetime.fromisoformat(sc.get("acquisition_start_utc", "2025-05-28T00:41:12.668533+00:00").replace("Z", "+00:00")),
            acquisition_end_utc=datetime.fromisoformat(sc.get("acquisition_end_utc", "2025-05-28T00:41:37.668461+00:00").replace("Z", "+00:00")),
            footprint=footprint_poly,
            orbit_direction=sc.get("orbit_direction", "ASCENDING"),
        )
