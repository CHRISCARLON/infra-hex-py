"""Visualisation helpers for infra-hex-py."""

from typing import List, Optional

import numpy as np

try:
    import branca.colormap as cm
    import folium

    HAS_VIZ_DEPS = True
except ImportError:
    HAS_VIZ_DEPS = False


def jenks_breaks(data, n_classes: int = 5) -> List[float]:
    """
    Calculate Jenks natural breaks for classification.

    Finds natural groupings in data by minimising within-class variance
    and maximising between-class variance.

    Args:
        data: Array-like of numeric values
        n_classes: Number of classes/bins to create

    Returns:
        List of break points including min and max values
    """
    data = np.array(sorted(data))
    n = len(data)

    if n <= n_classes:
        return data.tolist()

    lower_class_limits = np.zeros((n + 1, n_classes + 1))
    variance_combinations = np.full((n + 1, n_classes + 1), np.inf)
    variance_combinations[1, 1] = 0

    for i in range(2, n + 1):
        s1, s2, w = 0.0, 0.0, 0
        for m in range(1, i + 1):
            i3 = i - m + 1
            val = data[i3 - 1]
            s2 += val * val
            s1 += val
            w += 1
            variance = s2 - (s1 * s1) / w
            if i3 > 1:
                for j in range(2, n_classes + 1):
                    if (
                        variance_combinations[i, j]
                        >= variance + variance_combinations[i3 - 1, j - 1]
                    ):
                        lower_class_limits[i, j] = i3
                        variance_combinations[i, j] = (
                            variance + variance_combinations[i3 - 1, j - 1]
                        )
            lower_class_limits[i, 1] = 1
            variance_combinations[i, 1] = variance

    breaks = [data[-1]]
    k = n
    for j in range(n_classes, 1, -1):
        idx = int(lower_class_limits[k, j]) - 1
        breaks.append(data[idx])
        k = int(lower_class_limits[k, j]) - 1
    breaks.append(data[0])

    return sorted(set(breaks))


PALETTES = {
    "grey": ["#d0d0d0", "#a0a0a0", "#707070", "#404040", "#101010"],
    "blues": ["#deebf7", "#9ecae1", "#4292c6", "#2171b5", "#08306b"],
    "heat": ["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"],
    "greens": ["#edf8e9", "#bae4b3", "#74c476", "#31a354", "#006d2c"],
    "purples": ["#efedf5", "#bcbddc", "#807dba", "#6a51a3", "#4a1486"],
    "grey_blue": ["#e0e0e0", "#a8c5d8", "#6a9fc0", "#3a7ca5", "#08519c"],
}


def create_choropleth_map(
    gdf,
    value_column: str = "pipe_count",
    palette: str = "grey_blue",
    n_classes: int = 5,
    center: Optional[tuple] = None,
    zoom_start: int = 10,
    tooltip_fields: Optional[List[str]] = None,
):
    """
    Create a Folium choropleth map from a GeoDataFrame.

    Args:
        gdf: GeoDataFrame with geometry and value columns
        value_column: Column name to use for coloring
        palette: Color palette name (grey, blues, heat, greens, purples, grey_blue)
        n_classes: Number of Jenks classes
        center: Map center as (lat, lon), auto-calculated if None
        zoom_start: Initial zoom level
        tooltip_fields: Fields to show in tooltip

    Returns:
        Folium Map object
    """
    if not HAS_VIZ_DEPS:
        raise ImportError(
            "Visualisation dependencies not installed. "
            "Install with: pip install infra-hex-py[viz]"
        )

    if gdf.crs and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    if center is None:
        bounds = gdf.total_bounds
        center = ((bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2)

    # Create map
    m = folium.Map(location=center, zoom_start=zoom_start)

    if len(gdf) == 0:
        return m

    colors = PALETTES.get(palette, PALETTES["grey_blue"])

    min_val = gdf[value_column].min()
    max_val = gdf[value_column].max()
    breaks = jenks_breaks(gdf[value_column].values, n_classes=n_classes)

    colormap = cm.StepColormap(
        colors=colors,
        index=breaks,
        vmin=min_val,
        vmax=max_val,
        caption=value_column.replace("_", " ").title(),
    )

    def style_function(feature):
        value = feature["properties"][value_column]
        ratio = (value - min_val) / (max_val - min_val) if max_val > min_val else 0
        opacity = 0.4 + (ratio * 0.5)
        weight = 0.3 + (ratio * 1.2)
        return {
            "fillColor": colormap(value),
            "color": "#555",
            "weight": weight,
            "fillOpacity": opacity,
        }

    if tooltip_fields is None:
        tooltip_fields = [value_column]

    folium.GeoJson(
        gdf,
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(fields=tooltip_fields),
    ).add_to(m)

    colormap.add_to(m)

    bounds = gdf.total_bounds
    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

    return m
