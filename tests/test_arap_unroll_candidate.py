"""Developable positive control and rejected ARAP/scale negative cases."""

import numpy as np
import pytest

from plush_pattern_lab.patterns.arap_unroll_candidate import (
    best_similarity_scale,
    solve_research_arap,
)
from plush_pattern_lab.patterns.mesh_lscm_candidate import _overlap_metrics


def _cut_cylinder(n=32):
    angles = np.arange(n + 1) * 2 * np.pi / n
    bottom = np.column_stack(
        (20 * np.cos(angles), 20 * np.sin(angles), np.zeros(n + 1))
    )
    top = bottom.copy()
    top[:, 2] = 25
    points = np.vstack((bottom, top))
    faces = []
    for i in range(n):
        j = i + 1
        faces.extend(((i, j, n + 1 + j), (i, n + 1 + j, n + 1 + i)))
    triangles = np.asarray(faces, dtype=np.int64)
    rest = np.vstack(
        (
            np.column_stack((20 * angles, np.zeros(n + 1))),
            np.column_stack((20 * angles, np.full(n + 1, 25))),
        )
    )
    disk = {
        "points_xyz_mm": points,
        "faces": triangles,
        "slit_pin_inner_id": 0,
        "slit_pin_outer_id": n + 1,
    }
    return disk, rest


@pytest.mark.parametrize("seed", ["pca", "lscm"])
def test_developable_open_cylinder_arap_recovers_isometry_without_uv_overlap(seed):
    disk, source_uv = _cut_cylinder()
    source = disk["points_xyz_mm"].copy()
    result, method = solve_research_arap(
        disk, source_uv, iterations=20, seed=seed
    )
    metric = best_similarity_scale(disk["points_xyz_mm"], disk["faces"], result)
    overlap = _overlap_metrics(result[disk["faces"]])
    assert metric["unscaled_relative_edge_error_p95"] < 1e-6
    assert overlap["overlapping_nonzero_area_triangle_pairs"] == 0
    assert not overlap["overlap_search_truncated"]
    assert np.array_equal(disk["points_xyz_mm"], source)
    assert method["pin_distance_policy"] == "3d_euclidean_chord_not_mesh_path_length"
    assert not method["fabric_cutting_approved"]


def test_uniform_similarity_scaling_is_only_a_diagnostic_not_manufacturing():
    disk, real_uv = _cut_cylinder()
    report = best_similarity_scale(
        disk["points_xyz_mm"], disk["faces"], 0.1 * real_uv
    )
    assert report["unscaled_relative_edge_error_p95"] > 0.8
    assert report["rescaled_relative_edge_error_p95"] < 0.01
    assert report["best_fit_uniform_similarity_scale"] == pytest.approx(
        10.0, rel=0.01
    )
    assert not report["approval_after_rescaling"]


def test_nonuniform_stretch_survives_optimal_similarity_scale():
    disk, real_uv = _cut_cylinder()
    deformed = real_uv * np.array([2.0, 0.2])
    report = best_similarity_scale(
        disk["points_xyz_mm"], disk["faces"], deformed
    )
    assert report["rescaled_relative_edge_error_p95"] > 0.1


@pytest.mark.parametrize(
    ("iterations", "seed"),
    [(0, "pca"), (61, "pca"), (15, "unknown")],
)
def test_arap_rejects_unbounded_iterations_and_unknown_seed(iterations, seed):
    disk, rest = _cut_cylinder()
    with pytest.raises(ValueError):
        solve_research_arap(disk, rest, iterations=iterations, seed=seed)


def test_arap_rejects_corrupt_faces_or_nonfinite_source():
    disk, rest = _cut_cylinder()
    disk["faces"][0, 0] = 100000
    with pytest.raises(ValueError):
        solve_research_arap(disk, rest)
    disk, rest = _cut_cylinder()
    disk["points_xyz_mm"][3, 0] = np.nan
    with pytest.raises(ValueError):
        solve_research_arap(disk, rest)


def test_uniform_scale_rejects_collapsed_uv():
    disk, _ = _cut_cylinder()
    with pytest.raises(ValueError):
        best_similarity_scale(
            disk["points_xyz_mm"],
            disk["faces"],
            np.zeros((len(disk["points_xyz_mm"]), 2)),
        )
