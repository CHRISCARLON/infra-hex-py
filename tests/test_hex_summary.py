import geopandas as gpd
import pyarrow as pa
import pytest

import infra_hex_py


@pytest.fixture
def test_bbox():
    """Test bounding box."""
    return {
        "min_lat": 53.47,
        "min_lon": -2.26,
        "max_lat": 53.49,
        "max_lon": -2.22,
        "zoom": 11,
    }


@pytest.fixture
def hex_summary_result(test_bbox):
    """Get hex summary for test bounding box."""
    result = infra_hex_py.get_hex_summary(
        test_bbox["min_lat"],
        test_bbox["min_lon"],
        test_bbox["max_lat"],
        test_bbox["max_lon"],
        test_bbox["zoom"],
    )
    table = pa.Table.from_batches([result])
    print(table.slice(0, 5))
    return gpd.GeoDataFrame.from_arrow(table)


def test_hex_summary_returns_geodataframe(hex_summary_result):
    """Test that get_hex_summary returns a valid GeoDataFrame."""
    assert isinstance(hex_summary_result, gpd.GeoDataFrame)


def test_hex_summary_has_expected_columns(hex_summary_result):
    """Test that the GeoDataFrame has the expected columns."""
    expected_columns = {"hex_id", "pipe_count", "geometry"}
    assert set(hex_summary_result.columns) == expected_columns


def test_hex_summary_has_rows(hex_summary_result):
    """Test that the GeoDataFrame contains data."""
    assert len(hex_summary_result) > 0, "GeoDataFrame should contain at least one row"


def test_hex_summary_crs_is_set(hex_summary_result):
    """Test that CRS is properly set on the GeoDataFrame."""
    assert hex_summary_result.crs is not None, "CRS should not be None"


def test_hex_summary_crs_is_bng(hex_summary_result):
    """Test that CRS is British National Grid (EPSG:27700)."""
    assert hex_summary_result.crs.to_epsg() == 27700, "CRS should be EPSG:27700 (BNG)"


def test_hex_summary_geometry_column(hex_summary_result):
    """Test that geometry column is properly set."""
    assert hex_summary_result.geometry.name == "geometry"
    assert not hex_summary_result.geometry.isnull().any(), "No geometry should be null"


def test_hex_summary_pipe_counts_are_positive(hex_summary_result):
    """Test that all pipe counts are positive integers."""
    assert (hex_summary_result["pipe_count"] > 0).all(), (
        "All pipe counts should be positive"
    )


def test_hex_summary_hex_ids_are_unique(hex_summary_result):
    """Test that hex IDs are unique."""
    assert hex_summary_result["hex_id"].is_unique, "Hex IDs should be unique"


def test_hex_summary_sorted_by_pipe_count(hex_summary_result):
    """Test that results are sorted by pipe count (descending)."""
    pipe_counts = hex_summary_result["pipe_count"].tolist()
    assert pipe_counts == sorted(pipe_counts, reverse=True), (
        "Results should be sorted by pipe_count descending"
    )


def test_hex_summary_with_different_zoom_levels():
    """Test that different zoom levels return different results."""
    bbox = {"min_lat": 53.47, "min_lon": -2.26, "max_lat": 53.49, "max_lon": -2.22}

    result_z10 = infra_hex_py.get_hex_summary(
        bbox["min_lat"], bbox["min_lon"], bbox["max_lat"], bbox["max_lon"], 10
    )
    result_z11 = infra_hex_py.get_hex_summary(
        bbox["min_lat"], bbox["min_lon"], bbox["max_lat"], bbox["max_lon"], 11
    )

    gdf_z10 = gpd.GeoDataFrame.from_arrow(pa.Table.from_batches([result_z10]))
    gdf_z11 = gpd.GeoDataFrame.from_arrow(pa.Table.from_batches([result_z11]))

    # Higher zoom should have more heaxgons!!
    assert len(gdf_z10) != len(gdf_z11), (
        "Different zoom levels should produce different hex counts"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-vv", "-s"])
