"""Dependency-free Stage6 ear-root evidence contract for Blender 4.3.2.

Source XY edge samples and IDs are read from pinned offline research JSON.
No Shapely, SciPy, NumPy or source triangle computation in this module.
"""

from __future__ import annotations

from math import isfinite

SCHEMA = "stage6-original-source-ear-root-two-height-ring-ab-v1"


def plan_side_source_samples(side, z, max_samples=48):
    """Spread source intersection points without losing original vertex IDs."""
    xy = side["full_interpolated_original_source_xy_mm"]
    ids = side["full_crossed_original_proxy_vertex_id_pairs"]
    if (
        len(xy) != len(ids)
        or len(xy) != side["original_proxy_crossed_edge_count"]
        or len(xy) < 8
        or not isinstance(max_samples, int)
        or not 1 <= max_samples <= 48
        or not isinstance(z, (int, float))
        or not isfinite(z)
    ):
        raise ValueError("untrusted original source ear-root ring samples")
    for point, pair in zip(xy, ids):
        if (
            len(point) != 2
            or not all(isfinite(x) for x in point)
            or len(pair) != 2
            or any(not isinstance(i, int) or i < 0 for i in pair)
            or pair[0] == pair[1]
        ):
            raise ValueError("invalid source edge identity or actual XY")
    count = min(len(xy), max_samples)
    indices = ((k * len(xy)) // count for k in range(count))
    return [
        {
            "source_edge_ordinal": i,
            "source_vertex_id_pair": ids[i],
            "source_xyz_mm": [*xy[i], z],
        }
        for i in indices
    ]
