"""Source-only bisect regression: real edge identity, topology, negative cases."""

from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

from plush_pattern_lab.validation.stage6_real_protrusion_bisect import (
    ROUTES,
    _one_source,
    _ordered_boundary,
    _panels,
    _source,
    _source_meridian,
)


def _dome(n=400):
    angles = 2 * np.pi * np.arange(n) / n
    ring = np.column_stack((np.cos(angles), np.sin(angles), np.zeros(n)))
    vertices = np.vstack((ring, [0, 0, 2]))
    faces = np.asarray([[i, (i + 1) % n, n] for i in range(n)])
    return {
        "id": "left_high_protrusion",
        "source_topological_Euler": 1,
        "vertices_xyz_mm": vertices.tolist(),
        "triangles_local_vertex_indices": faces.tolist(),
        "original_rim_vertex_ids_in_cap_local_order": list(range(n)),
        "source_original_rim_edge_ids_sha256": "synthetic-not-original",
    }


def test_two_source_edge_routes_partition_all_faces_once():
    original = _dome()
    for route in ROUTES:
        result = _one_source(original, "left_high_protrusion", 400, 400, route)
        assert len(result["panels"]) == 2
        assert result["original_z230_rim_edge_count"] == 400
        assert result["original_three_dimensional_source_seam_shared_twice"]
        assert sum(len(p["source_original_cap_face_ids"]) for p in result["panels"]) == 400
        assert sum(
            p["source_original_z230_boundary_edges_on_panel"]
            for p in result["panels"]
        ) == 400
        for panel in result["panels"]:
            assert panel["topological_Euler"] == 1
            assert not panel["physical_fabric_allowance_or_hidden_seam_verified"]
            assert len(panel["seam_panel_vertex_ids_in_order"]) >= 3


@pytest.mark.parametrize(
    "fault", ("missing_face", "bad_rim", "bad_vertex", "bad_euler")
)
def test_real_source_cap_must_reject_fake_faces_and_identity(fault):
    cap = deepcopy(_dome())
    if fault == "missing_face":
        cap["triangles_local_vertex_indices"].pop()
    elif fault == "bad_rim":
        cap["original_rim_vertex_ids_in_cap_local_order"][0] = 1
    elif fault == "bad_vertex":
        cap["triangles_local_vertex_indices"][0][0] = 9999
    else:
        cap["source_topological_Euler"] = 2
    with pytest.raises(ValueError):
        _source(cap, "left_high_protrusion", 400, 400)


def test_geodesic_must_follow_internal_original_mesh_edges_not_boundary():
    cap = _dome()
    xyz, faces, rim, owners, _ = _source(cap, "left_high_protrusion", 400, 400)
    path, cut = _source_meridian(xyz, rim, owners, 1)
    assert len(path) == 3 and set(path[1:-1]) == {400}
    assert all(len(owners[key]) == 2 for key in cut)
    groups = _panels(faces, owners, cut)
    assert len(groups) == 2 and all(len(group) >= 100 for group in groups)


def test_branched_boundary_cannot_be_auto_connected_to_fake_single_panel():
    with pytest.raises(ValueError):
        _ordered_boundary({(0, 1), (1, 2), (2, 0), (0, 3)})
