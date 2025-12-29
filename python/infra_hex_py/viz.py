"""Visualisation helpers for infra-hex-py."""

from typing import List, Optional

import numpy as np

try:
    import branca.colormap as cm
    import folium

    HAS_VIZ_DEPS = True
except ImportError:
    cm = None
    folium = None
    HAS_VIZ_DEPS = False


# TODO: Look into speeding this up - will be slow for larger grids
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
    sorted_values = np.array(sorted(data))
    n_values = len(sorted_values)

    if n_values <= n_classes:
        return sorted_values.tolist()

    # DP tables:
    # - `class_start_index[i, j]` is the (1-based) start index of the j-th class when using first i values.
    # - `min_within_class_variance[i, j]` is the minimum achievable within-class variance for that partition.
    class_start_index = np.zeros((n_values + 1, n_classes + 1))
    min_within_class_variance = np.full((n_values + 1, n_classes + 1), np.inf)
    min_within_class_variance[1, 1] = 0

    for end_idx in range(2, n_values + 1):
        # Running totals for the segment [segment_start..end_idx] as we extend it backwards.
        running_sum = 0.0
        running_sum_squares = 0.0
        segment_count = 0

        for segment_len in range(1, end_idx + 1):
            segment_start = (
                end_idx - segment_len + 1
            )  # 1-based start index for the segment
            value = sorted_values[
                segment_start - 1
            ]  # convert to 0-based for array access

            running_sum_squares += value * value
            running_sum += value
            segment_count += 1

            segment_variance = (
                running_sum_squares - (running_sum * running_sum) / segment_count
            )

            if segment_start > 1:
                for class_idx in range(2, n_classes + 1):
                    candidate = (
                        segment_variance
                        + min_within_class_variance[segment_start - 1, class_idx - 1]
                    )
                    if min_within_class_variance[end_idx, class_idx] >= candidate:
                        class_start_index[end_idx, class_idx] = segment_start
                        min_within_class_variance[end_idx, class_idx] = candidate

            class_start_index[end_idx, 1] = 1
            min_within_class_variance[end_idx, 1] = segment_variance

    breaks = [sorted_values[-1]]
    backtrack_end = n_values
    for class_idx in range(n_classes, 1, -1):
        start_idx = int(class_start_index[backtrack_end, class_idx])  # 1-based
        break_idx = start_idx - 1  # convert to 0-based
        breaks.append(sorted_values[break_idx])
        backtrack_end = start_idx - 1

    breaks.append(sorted_values[0])

    return sorted(set(breaks))


PALETTES = {
    "grey": ["#d0d0d0", "#a0a0a0", "#707070", "#404040", "#101010"],
    "blues": ["#deebf7", "#9ecae1", "#4292c6", "#2171b5", "#08306b"],
    "heat": ["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"],
    "greens": ["#edf8e9", "#bae4b3", "#74c476", "#31a354", "#006d2c"],
    "purples": ["#efedf5", "#bcbddc", "#807dba", "#6a51a3", "#4a1486"],
    "grey_blue": ["#e0e0e0", "#a8c5d8", "#6a9fc0", "#3a7ca5", "#08519c"],
}


def create_hex_grid_map(
    gdf,
    value_column: str = "pipe_count",
    palette: str = "grey_blue",
    n_classes: int = 5,
    center: Optional[tuple] = None,
    zoom_start: int = 10,
    tooltip_fields: Optional[List[str]] = None,
):
    """
    Create a Folium hex grid map from a GeoDataFrame.

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

    assert folium is not None
    assert cm is not None

    if gdf.crs and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    if center is None:
        bounds = gdf.total_bounds
        center = ((bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2)

    # Create map
    m = folium.Map(location=center, zoom_start=zoom_start)

    if len(gdf) == 0:
        return m

    # TODO: Make this a choice
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
