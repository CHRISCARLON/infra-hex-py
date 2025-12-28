import pyarrow as pa

def get_hex_summary(
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    zoom: int,
) -> pa.RecordBatch: ...
def get_hex_summary_polygon_area(
    object_id: int,
    zoom: int,
) -> pa.RecordBatch: ...
