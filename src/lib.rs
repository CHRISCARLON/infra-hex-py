use geo::BoundingRect;
use infra_hex_rs::{
    BBox, BuiltUpAreaClient, CadentClient, InfraClient, to_hex_summary,
    to_hex_summary_for_multipolygon,
};
use pyo3::prelude::*;
use pyo3_arrow::PyRecordBatch;

#[pyfunction]
fn get_hex_summary(
    py: Python<'_>,
    min_lat: f64,
    min_lon: f64,
    max_lat: f64,
    max_lon: f64,
    zoom: u8,
) -> PyResult<Py<PyAny>> {
    let runtime = tokio::runtime::Runtime::new()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

    let client = CadentClient::new()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

    let bbox = BBox::new(min_lat, min_lon, max_lat, max_lon);

    let result = runtime.block_on(async { client.fetch_all_by_bbox(&bbox).await });

    if !result.errors.is_empty() {
        return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
            "Fetch had {} errors: {:?}",
            result.errors.len(),
            result.errors
        )));
    }

    let batch = to_hex_summary(&result.records, zoom)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

    PyRecordBatch::new(batch)
        .into_pyarrow(py)
        .map(|bound| bound.unbind())
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
}

/// Get hex summary for pipelines within a built-up area polygon.
///
/// # Arguments
/// * `object_id` - The OBJECTID of the built-up area from ONS Open Geography Portal
/// * `zoom` - Hex grid zoom level (0-15)
///
/// # Returns
/// A PyArrow RecordBatch with columns: hex_id, pipe_count, geometry
#[pyfunction]
fn get_hex_summary_polygon_area(py: Python<'_>, object_id: i64, zoom: u8) -> PyResult<Py<PyAny>> {
    let runtime = tokio::runtime::Runtime::new()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

    let area_client = BuiltUpAreaClient::new();

    let built_up_area = runtime
        .block_on(async { area_client.fetch_by_object_id(object_id).await })
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

    let rect = built_up_area.geometry.bounding_rect().ok_or_else(|| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid polygon geometry")
    })?;

    let bbox = BBox::new(rect.min().y, rect.min().x, rect.max().y, rect.max().x);

    let cadent_client = CadentClient::new()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

    let result = runtime.block_on(async { cadent_client.fetch_all_by_bbox(&bbox).await });

    if !result.errors.is_empty() {
        return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
            "Fetch had {} errors: {:?}",
            result.errors.len(),
            result.errors
        )));
    }

    let batch = to_hex_summary_for_multipolygon(&result.records, zoom, &built_up_area.geometry)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

    PyRecordBatch::new(batch)
        .into_pyarrow(py)
        .map(|bound| bound.unbind())
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
}

#[pyo3::pymodule]
mod infra_hex_py {
    #[pymodule_export]
    use super::get_hex_summary;
    #[pymodule_export]
    use super::get_hex_summary_polygon_area;
}
