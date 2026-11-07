"""Convex boundary disk must preserve topology, not claim fabric low strain."""

import numpy as np
import pytest

from plush_pattern_lab.patterns.mesh_lscm_candidate import _overlap_metrics
from plush_pattern_lab.patterns.tutte_disk_candidate import tutte_convex_disk_candidate


def _fan(z=0):
    vertices = np.array(
        [[-1, -1, 0], [1, -1, 0], [1, 1, 0], [-1, 1, 0], [0, 0, z]],
        dtype=float,
    )
    faces = np.asarray([[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]])
    return {
        "points_xyz_mm": vertices,
        "faces": faces,
        "boundary_edges": [[0, 1], [1, 2], [2, 3], [0, 3]],
    }


def _signed_areas(triangles):
    a = triangles[:, 1] - triangles[:, 0]
    b = triangles[:, 2] - triangles[:, 0]
    return a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]


def test_convex_disk_flattens_valid_fan_without_moving_original_xyz():
    disk = _fan()
    original = disk["points_xyz_mm"].copy()
    uv, report = tutte_convex_disk_candidate(disk)
    assert uv.shape == (5, 2)
    assert np.all(_signed_areas(uv[disk["faces"]]) > 0)
    assert np.array_equal(original, disk["points_xyz_mm"])
    assert report["source_3d_boundary_perimeter_mm"] == pytest.approx(8)
    assert report["interior_vertex_count"] == 1
    assert report["source_boundary_vertex_count"] == 4
    assert report["no_manufacturing_cut_approval"]


def test_convex_border_can_be_overlap_free_but_stretched():
    disk = _fan(z=5)
    uv, report = tutte_convex_disk_candidate(disk)
    source = disk["points_xyz_mm"][disk["faces"]]
    flat = uv[disk["faces"]]
    original_lengths = np.linalg.norm(source[:, [1, 2, 0]] - source, axis=2)
    uv_lengths = np.linalg.norm(flat[:, [1, 2, 0]] - flat, axis=2)
    assert np.quantile(np.abs(uv_lengths / original_lengths - 1), 0.95) > 0.5
    assert np.all(_signed_areas(flat) > 0)
    assert _overlap_metrics(flat)["overlapping_nonzero_area_triangle_pairs"] == 0
    assert report["does_not_limit_interior_nonuniform_stretch"]


@pytest.mark.parametrize(
    "change",
    [
        "wrong_boundary",
        "duplicate_boundary",
        "nonmanifold",
        "nan",
        "unused",
        "bad_face",
    ],
)
def test_invalid_original_geometry_or_topology_refused(change):
    disk = _fan()
    if change == "wrong_boundary":
        disk["boundary_edges"] = [[0, 1], [1, 2], [2, 4], [0, 3]]
    elif change == "duplicate_boundary":
        disk["boundary_edges"] = [[0, 1], [0, 1], [2, 3], [0, 3]]
    elif change == "nonmanifold":
        disk["faces"] = np.vstack((disk["faces"], disk["faces"][:2]))
    elif change == "nan":
        disk["points_xyz_mm"][4, 2] = np.nan
    elif change == "unused":
        disk["points_xyz_mm"] = np.vstack((disk["points_xyz_mm"], [2, 2, 0]))
    else:
        disk["faces"][0, 0] = 99
    with pytest.raises(ValueError):
        tutte_convex_disk_candidate(disk)
