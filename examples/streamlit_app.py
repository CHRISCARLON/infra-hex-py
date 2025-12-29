import folium
import geopandas as gpd
import pyarrow as pa
import streamlit as st
from folium.plugins import Draw
from infra_hex_py.viz import create_hex_grid_map
from streamlit_folium import st_folium

import infra_hex_py

st.set_page_config(page_title="Cadent Gas Asset Hex Map", layout="wide")

st.title("Cadent Gas Asset Hex Map")

method = st.radio(
    "Select method",
    ["Draw Rectangle", "Built-Up Area (Object ID)"],
    horizontal=True,
)

col1, col2, col3 = st.columns([4, 3, 1])
with col1:
    zoom = st.slider("Hex Zoom Level", min_value=8, max_value=15, value=11)
with col2:
    object_id = st.number_input(
        "ONS Built-Up Area Object ID",
        min_value=1,
        value=1310,
        help="OBJECTID from ONS Open Geography Portal Built-Up Areas 2024",
        disabled=method != "Built-Up Area (Object ID)",
    )
with col3:
    st.write("")
    if st.button("Clear", type="secondary"):
        st.session_state.hex_gdf = None
        st.rerun()

if "hex_gdf" not in st.session_state:
    st.session_state.hex_gdf = None

if method == "Built-Up Area (Object ID)":
    if st.button("Fetch Built-Up Area", type="primary"):
        with st.spinner(f"Fetching hex summary for built-up area {object_id}..."):
            result = infra_hex_py.get_hex_summary_polygon_area(object_id, zoom)

            table = pa.Table.from_batches([result])
            gdf = gpd.GeoDataFrame.from_arrow(table)

            gdf_wgs84 = gdf.to_crs(epsg=4326)
            st.session_state.hex_gdf = gdf_wgs84

            st.success(f"Found {len(gdf)} hexagons")
            st.rerun()
else:
    st.write("Draw a rectangle on the map to fetch hex summary for that area")

m = folium.Map(location=[53.48, -2.24], zoom_start=10, tiles="CartoDB positron")

if method == "Draw Rectangle":
    Draw(
        draw_options={
            "polyline": False,
            "polygon": False,
            "circle": False,
            "marker": False,
            "circlemarker": False,
            "rectangle": True,
        },
        edit_options={"edit": False},
    ).add_to(m)

if st.session_state.hex_gdf is not None and len(st.session_state.hex_gdf) > 0:
    gdf = st.session_state.hex_gdf

    m = create_hex_grid_map(
        gdf,
        value_column="pipe_count",
        palette="grey_blue",
        n_classes=5,
        center=(53.48, -2.24),
        zoom_start=10,
        tooltip_fields=["hex_id", "pipe_count"],
    )

    folium.TileLayer("CartoDB positron", name="Light").add_to(m)
    folium.LayerControl().add_to(m)

    if method == "Draw Rectangle":
        Draw(
            draw_options={
                "polyline": False,
                "polygon": False,
                "circle": False,
                "marker": False,
                "circlemarker": False,
                "rectangle": True,
            },
            edit_options={"edit": False},
        ).add_to(m)

output = st_folium(m, width=1200, height=800, use_container_width=True)

if method == "Draw Rectangle" and output and output.get("last_active_drawing"):
    drawing = output["last_active_drawing"]
    if drawing.get("geometry", {}).get("type") == "Polygon":
        coords = drawing["geometry"]["coordinates"][0]
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        min_lon, max_lon = min(lons), max(lons)
        min_lat, max_lat = min(lats), max(lats)

        st.write(
            f"Bbox: ({min_lat:.4f}, {min_lon:.4f}) to ({max_lat:.4f}, {max_lon:.4f})"
        )

        with st.spinner("Fetching hex summary..."):
            result = infra_hex_py.get_hex_summary(
                min_lat, min_lon, max_lat, max_lon, zoom
            )
            table = pa.Table.from_batches([result])
            gdf = gpd.GeoDataFrame.from_arrow(table)

            gdf_wgs84 = gdf.to_crs(epsg=4326)
            st.session_state.hex_gdf = gdf_wgs84

            st.success(f"Found {len(gdf)} hexagons")
            st.rerun()
