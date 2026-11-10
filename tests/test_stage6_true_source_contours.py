"""Regression: real triangular contour components are not envelope rectangles."""

import numpy as np
import pytest

from plush_pattern_lab.validation.stage6_source_contour_vs_trial import (
    compare_true_contours_to_split_study,
    render_true_source_contours_svg,
)
from plush_pattern_lab.validation.stage6_true_source_contours import (
    intersect_real_source_at_z,
    real_source_section_series,
)


def _synthetic_column(center_x=0, center_y=0):
    p = np.asarray(
        [
            [center_x - 1, center_y - 1, 0],
            [center_x + 1, center_y - 1, 0],
            [center_x + 1, center_y + 1, 0],
            [center_x - 1, center_y + 1, 0],
            [center_x - 1, center_y - 1, 2],
            [center_x + 1, center_y - 1, 2],
            [center_x + 1, center_y + 1, 2],
            [center_x - 1, center_y + 1, 2],
        ]
    )
    faces = []
    for j in range(4):
        i, nxt = j, (j + 1) % 4
        faces.extend([[i, nxt, 4 + nxt], [i, 4 + nxt, 4 + i]])
    return p, np.asarray(faces)


def test_true_triangle_plane_intersection_is_original_closed_four_edge_loop():
    xyz, faces = _synthetic_column()
    s = intersect_real_source_at_z(xyz, faces, 1)
    assert s["true_source_plane_intersection_component_count"] == 1
    loop = s["source_contours"][0]
    assert loop["closed_loop"]
    assert loop["simple_polygon"]
    assert loop["enclosed_plane_area_mm2"] == pytest.approx(4)
    assert loop["contour_perimeter_mm"] == pytest.approx(8)
    assert loop["crossed_original_source_edges"] == 8
    assert len(loop["crossed_original_mesh_vertex_id_edge_pairs"]) == 8
    assert loop["original_source_edge_and_interpolated_xy_sha256"]


def test_two_disconnected_source_columns_are_two_contours_not_one_bbox():
    one, first = _synthetic_column(-5, 0)
    two, second = _synthetic_column(5, 0)
    xyz = np.vstack((one, two))
    faces = np.vstack((first, second + len(one)))
    s = intersect_real_source_at_z(xyz, faces, 1)
    assert s["true_source_plane_intersection_component_count"] == 2
    assert sorted(round(c["contour_centroid_xy_mm"][0]) for c in s["source_contours"]) == [
        -5, 5
    ]
    assert all(c["enclosed_plane_area_mm2"] == pytest.approx(4) for c in s["source_contours"])


def test_plane_at_a_source_vertex_must_fail_instead_of_guessing_topology():
    xyz, faces = _synthetic_column()
    with pytest.raises(ValueError, match="through original vertex"):
        intersect_real_source_at_z(xyz, faces, 0)


def test_missing_side_triangle_fails_nonclosed_original_source_contour():
    xyz, faces = _synthetic_column()
    with pytest.raises(ValueError, match="open, branched or nonmanifold"):
        intersect_real_source_at_z(xyz, faces[:-1], 1)


def test_true_mesh_source_requires_valid_integral_original_ids():
    xyz, faces = _synthetic_column()
    corrupted = faces.copy()
    corrupted[0, 0] = 100
    with pytest.raises(ValueError, match="source triangle"):
        intersect_real_source_at_z(xyz, corrupted, 1)


def test_source_loop_sha_is_deterministic_even_when_reference_undisturbed():
    xyz, faces = _synthetic_column()
    first = intersect_real_source_at_z(xyz, faces, 1)["source_contours"][0]
    second = intersect_real_source_at_z(xyz, faces, 1)["source_contours"][0]
    assert first["original_source_edge_and_interpolated_xy_sha256"] == second[
        "original_source_edge_and_interpolated_xy_sha256"
    ]


def test_missing_actual_original_contour_study_refuses_false_benchmark():
    xyz, faces = _synthetic_column()
    real = real_source_section_series(xyz, faces, z_levels=(1,))
    with pytest.raises(ValueError):
        compare_true_contours_to_split_study(real, {"schema": "unknown"})


def test_original_source_contours_research_svg_has_static_multiloop_warning():
    one, first = _synthetic_column(-5, 0)
    two, second = _synthetic_column(5, 0)
    xyz = np.vstack((one, two))
    faces = np.vstack((first, second + len(one)))
    series = real_source_section_series(xyz, faces, z_levels=(0.5, 1, 1.5))
    svg = render_true_source_contours_svg(series)
    assert svg.count("source loops") == 3
    assert "2 source loops" in svg
    assert "NOT FABRIC CUTTING" in svg
    assert svg.count("<polygon ") == 6
