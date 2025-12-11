# infra-hex-py

Python bindings for infra-hex-rs.

## Usage

```python
import geopandas as gpd
import pyarrow as pa
import infra_hex_py

result = infra_hex_py.get_hex_summary(53.47, -2.26, 53.49, -2.22, zoom=11)
gdf = gpd.GeoDataFrame.from_arrow(pa.Table.from_batches([result]))
```

## Environment

Requires `CADENT_API_KEY` - you'll need an account with Cadent's open data portal for this to work.
