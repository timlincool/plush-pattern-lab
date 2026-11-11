"""Exact source triangle band clipping, paired 3D seams and factory vetoes."""

from copy import deepcopy

import numpy as np
import pytest

from plush_pattern_lab.validation.stage6_true_ear_root_band_cut import (
    _components,
    _ordered_original_seam_keys,
    _paired_seam,
    _source_mesh,
    _surface_area,
    _surface_graph_width,
    analyze_real_source_ear_root_bands,
    clip_original_source_zone,
)


def _box():
    xyz = np.array(
        [
            [-8, -8, 220],
            [8, -8, 220],
            [8, 8, 220],
            [-8, 8, 220],
            [-8, -8, 240],
            [8, -8, 240],
            [8, 8, 240],
            [-8, 8, 240],
        ],
        dtype=float,
    )
    tri = np.array(
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
    return xyz, tri


def _zones():
    xyz, tri = _box()
    zones = {
        "below": clip_original_source_zone(xyz, tri, None, 230),
        "root": clip_original_source_zone(xyz, tri, 230, 235),
        "above": clip_original_source_zone(xyz, tri, 235, None),
    }
    return xyz, tri, zones


def test_synthetic_closed_box_becomes_true_source_paired_3d_annulus():
    xyz, tri, zones = _zones()
    original = xyz.copy()
    faces_before = tri.copy()
    below, root, above = (
        _components(zones[name])[0] for name in ("below", "root", "above")
    )
    assert root["euler"] == 0
    assert len(root["boundary_loops"]) == 2
    assert below["euler"] == above["euler"] == 1
    first = _paired_seam(
        zones["below"], below, zones["root"], root, 230
    )
    second = _paired_seam(
        zones["root"], root, zones["above"], above, 235
    )
    assert first["two_source_3d_sides_exactly_same_with_opposite_face_winding"]
    assert second["two_source_3d_sides_exactly_same_with_opposite_face_winding"]
    assert first["max_source_3d_pair_position_error_mm"] == 0
    assert second["max_source_3d_pair_position_error_mm"] == 0
    assert len(first["original_source_3d_ordered_ring_xyz_mm"]) == 8
    assert np.isclose(first["paired_3d_netline_length_each_side_mm"], 64)
    assert np.isclose(second["paired_3d_netline_length_each_side_mm"], 64)
    source_area = _surface_area(xyz, tri)
    cut_area = sum(_surface_area(zone["xyz"], zone["faces"]) for zone in zones.values())
    assert np.isclose(source_area, cut_area, atol=1e-9)
    assert np.array_equal(xyz, original)
    assert np.array_equal(tri, faces_before)
    assert first["not_a_validated_two_sided_fabric_2d_netline"]


def test_source_graph_width_rejects_synthetic_5mm_high_ring():
    _, _, zones = _zones()
    root = _components(zones["root"])[0]
    width = _surface_graph_width(zones["root"], root, 230, 235)
    assert width["below_two_research_6mm_allowances_somewhere"]
    assert width["fraction_upper_source_seam_under_12mm_graph_width"] == 1.0
    assert width["source_triangle_graph_distance_is_upper_bound_on_real_surface_geodesic"]
    assert width["this_is_not_2d_fabric_usable_allowance"]


@pytest.mark.parametrize("bad", ["vertex_plane", "index", "invalid_z", "nan"])
def test_invalid_original_mesh_or_cut_plane_is_rejected(bad):
    xyz, tri = _box()
    if bad == "vertex_plane":
        xyz[0, 2] = 230
    elif bad == "index":
        tri[0, 0] = 1000
    elif bad == "nan":
        xyz[0, 0] = float("nan")
    with pytest.raises(ValueError):
        _source_mesh(xyz, tri, 230 if bad != "invalid_z" else 235, 235)


def test_source_3d_seam_pair_rejects_wrong_winding_or_vertex_identity():
    _, _, zones = _zones()
    source = _components(zones["below"])[0]
    target = _components(zones["root"])[0]
    altered = deepcopy(zones["root"])
    altered["faces"][:, [1, 2]] = altered["faces"][:, [2, 1]]
    reversed_part = _components(altered)[0]
    with pytest.raises(ValueError, match="winding"):
        _paired_seam(zones["below"], source, altered, reversed_part, 230)
    altered = deepcopy(zones["root"])
    keys = altered["keys"]
    index = next(i for i, key in enumerate(keys) if key[0] == "e" and key[-1] == 230)
    altered["keys"][index] = ("e", 0, 6, 230)
    with pytest.raises(ValueError):
        _paired_seam(zones["below"], source, altered, target, 230)


@pytest.mark.parametrize("bad", ["empty", "branch", "two_loops"])
def test_unclosed_or_false_matched_source_rings_rejected(bad):
    a = ("e", 0, 1, 230)
    b = ("e", 1, 2, 230)
    c = ("e", 2, 3, 230)
    good = {(a, b), (b, c), (a, c)}
    if bad == "empty":
        good = set()
    elif bad == "branch":
        good = {(a, b), (a, c)}
    else:
        d = ("e", 4, 5, 230)
        e = ("e", 5, 6, 230)
        f = ("e", 6, 7, 230)
        good = good | {(d, e), (e, f), (d, f)}
    with pytest.raises(ValueError):
        _ordered_original_seam_keys(good)


def test_non_stage6_box_is_not_mistaken_for_authenticated_full_head():
    xyz, tri = _box()
    with pytest.raises(ValueError, match="1/3/3"):
        analyze_real_source_ear_root_bands(xyz, tri)
