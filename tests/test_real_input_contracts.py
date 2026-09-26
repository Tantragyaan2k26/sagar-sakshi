from datetime import datetime, timezone

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import shape

from ingest.ais_recorder import load_ais_csv
from ingest.forcing_fetcher import ForcingFetcher
from perception.geometry import mask_to_polygon
from perception.sar_conditioning import SarConditioner


def _raster_config(path, units="sigma0_linear"):
    return {
        "incident": {"aoi": {"min_lon": 80.2, "min_lat": 13.2, "max_lon": 80.8, "max_lat": 13.8}},
        "scene": {"tiff_value_units": units, "tiff_band": 1},
    }


def test_calibrated_raster_uses_its_transform_crs_and_linear_to_db(tmp_path):
    path = tmp_path / "backscatter.tif"
    data = np.full((2, 10, 10), 10, dtype=np.float32)
    data[0, 2:8, 2:8] = 100
    data[1] = 20
    with rasterio.open(
        path, "w", driver="GTiff", height=10, width=10, count=2, dtype="float32",
        crs="EPSG:4326", transform=from_origin(80.0, 14.0, 0.1, 0.1), nodata=-9999,
    ) as dataset:
        dataset.write(data)

    sar = SarConditioner(str(path), _raster_config(path))
    crop, meta = sar.extract_aoi_crop(13.2, 80.2, 13.8, 80.8)
    lat, lon = sar.pixel_to_coord(2, 2)
    sar.close()

    assert crop.shape == (6, 6)
    assert np.allclose(crop, 20.0)
    assert meta["synthetic"] is False
    assert meta["crs"] == "EPSG:4326"
    assert lon == pytest.approx(80.25)
    assert lat == pytest.approx(13.75)


def test_raw_dn_geotiff_is_rejected_instead_of_misread_as_db(tmp_path):
    path = tmp_path / "raw.tif"
    with rasterio.open(path, "w", driver="GTiff", height=4, width=4, count=1, dtype="uint16", crs="EPSG:4326", transform=from_origin(80, 14, .1, .1)) as dataset:
        dataset.write(np.ones((1, 4, 4), dtype=np.uint16))
    with pytest.raises(ValueError, match="Raw DN/amplitude"):
        SarConditioner(str(path), _raster_config(path, "dn"))


def test_mask_polygonization_preserves_disconnected_components():
    mask = np.zeros((40, 50), dtype=bool)
    mask[5:10, 5:10] = True
    mask[25:30, 35:40] = True
    meta = {"height": 40, "width": 50, "min_lon": 80.0, "max_lon": 81.0, "min_lat": 13.0, "max_lat": 14.0}
    result = mask_to_polygon(mask, meta)
    assert result is not None
    assert result.geom_type == "MultiPolygon"
    assert len(result.geoms) == 2
    assert shape(result.__geo_interface__).is_valid


def test_ais_csv_window_and_required_columns(tmp_path):
    path = tmp_path / "ais.csv"
    path.write_text(
        "timestamp_utc,mmsi,vessel_name,lat,lon,sog,cog\n"
        "2025-05-28T00:30:00Z,123456789,Test Ship,9.2,76.1,8,180\n"
        "2025-05-28T05:30:00Z,123456789,Test Ship,9.3,76.2,9,190\n",
        encoding="utf-8",
    )
    rows = load_ais_csv(str(path), datetime(2025, 5, 28, 1, tzinfo=timezone.utc), 2)
    assert len(rows) == 1
    assert rows[0]["mmsi"] == "123456789"
    assert rows[0]["data_status"] == "historical_csv_input_unverified"


def test_metocean_csv_nearest_sample_and_missing_coverage(tmp_path):
    path = tmp_path / "forcing.csv"
    path.write_text(
        "timestamp_utc,lat,lon,current_u_mps,current_v_mps,wind_speed_mps,wind_from_deg,source_id\n"
        "2025-05-28T00:00:00Z,9.2,76.1,0.3,-0.1,5,180,fixture\n",
        encoding="utf-8",
    )
    fetcher = ForcingFetcher({"metocean": {"forcing_csv": str(path), "max_time_gap_hours": 1, "max_distance_km": 20}})
    vector = fetcher.get_forcing_at(9.2, 76.1, "2025-05-28T00:30:00+00:00")
    assert vector.u_current_mps == pytest.approx(0.3)
    assert vector.source_id == "fixture"
    with pytest.raises(ValueError, match="No metocean sample"):
        fetcher.get_forcing_at(9.2, 76.1, "2025-05-28T05:00:00+00:00")
