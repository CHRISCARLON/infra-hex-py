# Re-export from compiled Rust extension
from infra_hex_py.infra_hex_py import get_hex_summary, get_hex_summary_polygon_area

__all__ = ["get_hex_summary", "get_hex_summary_polygon_area"]

# Optional viz exports (require infra-hex-py[viz])
try:
    from .viz import PALETTES, create_choropleth_map, jenks_breaks  # noqa: F401

    __all__.extend(["jenks_breaks", "create_choropleth_map", "PALETTES"])
except ImportError:
    pass
