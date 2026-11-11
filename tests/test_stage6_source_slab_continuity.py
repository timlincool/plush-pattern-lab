"""Synthetic true-source slab connectivity, bad hashes, and capped surfaces."""

from copy import deepcopy

import numpy as np
import pytest

from plush_pattern_lab.validation.stage6_source_slab_continuity import (
    trace_true_source_slab,
)


def box(x, y, ceiling=2):
    points = np.array(
        [
            [x, y, 0],
            [x + 1, y, 0],
            [x + 1, y + 1, 0],
            [x, y + 1, 0],
            [x, y, ceiling],
            [x + 1, y, ceiling],
            [x + 1, y + 1, ceiling],
            [x, y + 1, ceiling],
        ],
        dtype=np.float64,
    )
    faces = np.array(
        [
            [0, 2, 1],
            [0, 3, 2],
            [4, 5, 6],
            [4, 6, 7],
            [0, 1, 5],
            [0, 5, 4],
            [1, 2, 6],
            [1, 6, 5],
            [2, 3, 7],
            [2, 7, 6],
            [3, 0, 4],
            [3, 4, 7],
        ],
        dtype=np.int64,
    )
    return points, faces


def boxes(*positions):
    pts, faces = [], []
    for x, y, top in positions:
        p, f = box(x, y, top)
        faces.append(f + sum(len(v) for v in pts))
        pts.append(p)
    return np.concatenate(pts), np.concatenate(faces)


def detail(points, triangles, levels=(1, 1.5)):
    from plush_pattern_lab.validation.stage6_true_source_contours import (
        real_source_section_series,
    )

    return real_source_section_series(points, triangles, z_levels=levels)


def test_three_lower_original_contours_two_upper_match_by_real_triangle_edges():
    xyz, tri = boxes((-6, 0, 2), (0, 0, 1.2), (6, 0, 2))
    result = trace_true_source_slab(xyz, tri, detail(xyz, tri), 1, 1.5)
    assert result["source_triangle_count_in_open_slab"] > 0
    assert result["source_surface_component_count_in_open_slab"] == 3
    assert len(result["lower_original_source_loops"]) == 3
    assert len(result["upper_original_source_loops"]) == 2
    continued = [
        row
        for row in result["surface_components"]
        if row["source_surface_relation"] == "one_to_one_surface_continuation_not_seam"
    ]
    ended = [
        row
        for row in result["surface_components"]
        if row["source_surface_relation"] == "lower_loop_terminates_before_upper"
    ]
    assert len(continued) == 2 and len(ended) == 1
    assert all(len(r["lower_loop_indices"]) == 1 for r in continued)
    assert result["exact_original_mesh_source_vertex_id_provenance_validated"]
    assert result["approved_industrial_cutting_patterns"] == 0
    assert not result["P4_started"]


def test_two_geometries_touching_at_coordinate_only_are_still_separate():
    xyz, tri = boxes((0, 0, 2), (1, 1, 2))
    result = trace_true_source_slab(xyz, tri, detail(xyz, tri), 1, 1.5)
    assert result["source_surface_component_count_in_open_slab"] == 2
    assert all(
        row["source_surface_relation"] == "one_to_one_surface_continuation_not_seam"
        for row in result["surface_components"]
    )


def test_shared_source_vertex_without_shared_source_edge_not_connected():
    xyz, tri = boxes((0, 0, 2), (1, 1, 2))
    # Source vertex IDs touch but the two triangle shells do not share an edge.
    tri[12:][tri[12:] == 8] = 2
    result = trace_true_source_slab(xyz, tri, detail(xyz, tri), 1, 1.5)
    assert result["source_surface_component_count_in_open_slab"] == 2


@pytest.mark.parametrize(
    "corruption",
    ["bad_sha", "bad_xy", "bad_edge", "bad_count", "bad_z", "bad_source"],
)
def test_wrong_section_source_hash_or_triangle_id_fails_closed(corruption):
    xyz, tri = boxes((0, 0, 2))
    broken = deepcopy(detail(xyz, tri))
    loop = broken["sections"][0]["source_contours"][0]
    if corruption == "bad_sha":
        loop["original_source_edge_and_interpolated_xy_sha256"] = "0" * 64
    elif corruption == "bad_xy":
        loop["true_interpolated_contour_xy_mm"][0][0] += 1
    elif corruption == "bad_edge":
        loop["crossed_original_mesh_vertex_id_edge_pairs"][0] = [0, 1]
    elif corruption == "bad_count":
        broken["sections"][0]["true_source_plane_intersection_component_count"] += 1
    elif corruption == "bad_z":
        broken["sections"][1]["plane_z_mm"] = 1.4
    else:
        broken["factory_cutting_approved"] = 1
    with pytest.raises(ValueError):
        trace_true_source_slab(xyz, tri, broken, 1, 1.5)


def test_reversed_or_vertex_plane_and_nonmanifold_source_are_rejected():
    xyz, tri = boxes((0, 0, 2))
    src = detail(xyz, tri)
    with pytest.raises(ValueError):
        trace_true_source_slab(xyz, tri, src, lower=1.5, upper=1)
    with pytest.raises(ValueError):
        trace_true_source_slab(xyz, tri, src, lower=0, upper=1.5)
    bad = np.vstack([tri, tri[4]])
    with pytest.raises(ValueError, match="nonmanifold"):
        trace_true_source_slab(xyz, bad, src, 1, 1.5)


def test_source_does_not_mutate_original_triangle_geometry():
    xyz, tri = boxes((0, 0, 2))
    first, second = xyz.copy(), tri.copy()
    src = detail(xyz, tri)
    a = trace_true_source_slab(xyz, tri, src, 1, 1.5)
    b = trace_true_source_slab(xyz, tri, src, 1, 1.5)
    assert a == b
    assert np.array_equal(xyz, first) and np.array_equal(tri, second)


def test_source_slab_timeline_svg_marks_geometry_only_and_rejects_empty():
    from plush_pattern_lab.validation.stage6_source_slab_timeline import (
        render_source_slab_timeline,
    )

    xyz, tri = boxes((0, 0, 2))
    one = trace_true_source_slab(xyz, tri, detail(xyz, tri), 1, 1.5)
    svg = render_source_slab_timeline([one] * 5)
    assert svg.startswith("<svg")
    assert svg.count("original triangles") == 5
    assert "NOT CUT PATTERNS" in svg
    assert "NOT EAR ROOT SEAM PROOF" in svg
    with pytest.raises(ValueError, match="five source slab"):
        render_source_slab_timeline([one])
