"""Original triangle-edge route tests, tampering negative controls and no fabric."""

from copy import deepcopy
import hashlib
import struct

import numpy as np
import pytest

from plush_pattern_lab.validation.stage6_dart_paths import (
    SCHEMA,
    _candidate,
    _route_to_tip,
    _validated_anchor_endpoint,
    _validated_original_section_arc,
    original_edges,
)
from plush_pattern_lab.validation.stage6_dart_paths_svg import (
    render_dart_tip_comparison_svg,
)


def _mesh():
    points = np.array(
        [
            [0, 0, 229],
            [0, 0, 231],
            [4, 0, 229],
            [4, 0, 231],
            [1, 0, 226],
            [3, 0, 226],
            [2, 0, 224],
            [2, 2, 226],
        ],
        dtype=float,
    )
    faces = np.array(
        [
            [0, 1, 4],
            [2, 3, 5],
            [0, 4, 7],
            [4, 6, 7],
            [2, 5, 7],
            [5, 6, 7],
        ],
        dtype=int,
    )
    return points, faces


def _arc():
    return {
        "hypothesis": "medial",
        "source_side": "left",
        "source_height_mm": 230,
        "sample_count": 12,
        "original_arc_endpoints_unpaired": 2,
        "approved_as_hidden_seam": False,
        "original_source_edge_id_pair_start": [0, 1],
        "source_xyz_start_mm": [0, 0, 230],
        "original_source_edge_id_pair_end": [2, 3],
        "source_xyz_end_mm": [4, 0, 230],
        "source_original_plane_arc_length_mm": 4,
    }


def _ring():
    xy = [[float(i), 0.0] for i in range(16)]
    edges = [[i, i + 1] for i in range(16)]
    encoded = b"".join(struct.pack("<qq", *pair) for pair in edges)
    encoded += b"".join(struct.pack("<dd", *point) for point in xy)
    digest = hashlib.sha256(encoded).hexdigest()
    arc = {
        "source_contour_sha256": digest,
        "original_source_edge_ordinal_start": 3,
        "original_source_edge_ordinal_end": 8,
        "original_source_edge_id_pair_start": edges[3],
        "original_source_edge_id_pair_end": edges[8],
        "source_xyz_start_mm": [*xy[3], 230],
        "source_xyz_end_mm": [*xy[8], 230],
        "source_original_plane_arc_length_mm": 5,
    }
    ring = {
        "source_contour_sha256": digest,
        "full_interpolated_original_source_xy_mm": xy,
        "full_crossed_original_proxy_vertex_id_pairs": edges,
    }
    return arc, ring


def test_original_source_mesh_edges_unchanged_and_unique():
    points, triangles = _mesh()
    original, faces = points.copy(), triangles.copy()
    xyz, edges, length = original_edges(points, triangles)
    assert len(edges) == len(np.unique(edges, axis=0))
    assert np.all(length > 0)
    assert np.array_equal(points, original)
    assert np.array_equal(triangles, faces)
    assert xyz.shape == (8, 3)


def test_candidate_source_dart_branches_remain_vertex_disjoint_except_tip():
    xyz, edges, length = original_edges(*_mesh())
    item = _candidate(xyz, edges, length, "left", _arc(), 225.0)
    first, second = item["disjoint_original_source_route_ids"]
    assert first[0] == 0 and second[0] == 2
    assert first[-1] == second[-1] == item["chosen_original_source_tip_vertex_id"]
    assert not set(first[:-1]) & set(second[:-1])
    assert len(item["source_3d_dart_route_identity_sha256"]) == 64
    assert item["source_original_triangles_not_cut"]
    assert item["not_a_validated_two_sided_sewing_netline"]


@pytest.mark.parametrize(
    "mutation", ["bad_pair", "bad_xy", "same_z", "nonfinite"]
)
def test_arc_endpoint_must_be_on_claimed_actual_source_mesh_edge(mutation):
    xyz, edges, _ = original_edges(*_mesh())
    pair, point = [0, 1], [0, 0, 230]
    if mutation == "bad_pair":
        pair = [0, 3]
    elif mutation == "bad_xy":
        point = [1, 0, 230]
    elif mutation == "same_z":
        pair = [0, 4]
    else:
        point = [float("nan"), 0, 230]
    with pytest.raises(ValueError):
        _validated_anchor_endpoint(xyz, edges, pair, point)


def test_full_original_source_contour_identity_and_true_arc_distance():
    arc, ring = _ring()
    result = _validated_original_section_arc(arc, ring)
    assert len(result) == 6
    assert result[0] == [3, 0, 230]
    assert result[-1] == [8, 0, 230]


@pytest.mark.parametrize(
    "mutation", ["digest", "internal_xy", "wrong_end", "wrong_len"]
)
def test_false_original_full_contour_or_source_arc_identity_rejected(mutation):
    arc, ring = _ring()
    ring = deepcopy(ring)
    if mutation == "digest":
        arc["source_contour_sha256"] = "0" * 64
    elif mutation == "internal_xy":
        ring["full_interpolated_original_source_xy_mm"][5][1] += 1
    elif mutation == "wrong_end":
        arc["original_source_edge_id_pair_end"] = [9, 10]
    else:
        arc["source_original_plane_arc_length_mm"] = 1
    with pytest.raises(ValueError):
        _validated_original_section_arc(arc, ring)


def test_missing_or_cyclic_original_mesh_predecessor_rejected():
    predecessor = np.array([-9999] * 8)
    with pytest.raises(ValueError, match="disconnected"):
        _route_to_tip(predecessor, 4, 0, 8)


def test_source_route_svg_rejects_any_factory_pattern_claim():
    xyz, edges, lengths = original_edges(*_mesh())
    item = _candidate(xyz, edges, lengths, "left", _arc(), 225.0)
    item["original_source_section_arc_xyz_mm"] = [
        [0, 0, 230],
        [4, 0, 230],
    ]
    study = {
        "schema": SCHEMA,
        "candidates": [item] * 4,
        "factory_cutting_patterns_approved": 0,
    }
    svg = render_dart_tip_comparison_svg(study)
    assert "NOT 2D FABRIC PATTERNS" in svg
    assert svg.count("<polyline") == 12
    study["factory_cutting_patterns_approved"] = 1
    with pytest.raises(ValueError):
        render_dart_tip_comparison_svg(study)
