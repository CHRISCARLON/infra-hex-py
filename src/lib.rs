use infra_hex_rs::{BBox, CadentClient, InfraClient, to_hex_summary};
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

#[pyo3::pymodule]
mod infra_hex_py {
    #[pymodule_export]
    use super::get_hex_summary;
}
