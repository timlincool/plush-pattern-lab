"""Genuine source short-open-slit topology and hard source-identity failures."""

from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest
from audit_stage6_protrusion_short_dart_abf import (
    _paired_segmentwise_absolute_mismatch,
    _verify_original_geometry,
)

from plush_pattern_lab.validation.stage6_protrusion_short_dart import (
    CAPS,
    ROUTES,
    _cut_source_fans_once,
    _short_original_path,
)


def _source_cone(count=80):
    theta = 2 * np.pi * np.arange(count) / count
    xyz = np.vstack(
        (
            np.column_stack(
                (np.cos(theta), np.sin(theta), np.zeros(count))
            ),
            [[0, 0, 2]],
        )
    )
    face = np.asarray(
        [[i, (i + 1) % count, count] for i in range(count)], dtype=int
    )
    return xyz, face


def _short_dart():
    xyz, faces = _source_cone()
    path = np.asarray([0, 80], dtype=int)
    split_xyz, split_faces, original, border = _cut_source_fans_once(
        xyz, faces, path, 80
    )
    disk = {
        "source_xyz_mm": split_xyz.tolist(),
        "disk_triangle_vertex_ids": split_faces.tolist(),
        "original_patch_vertex_id_per_disk_vertex": original.tolist(),
        "slit_original_local_vertex_ids": path.tolist(),
        "real_source_3d_slit_length_mm": float(
            np.linalg.norm(xyz[path[0]] - xyz[path[1]])
        ),
        "source_tip_vertex_not_duplicated": True,
        "topological_Euler": 1,
    }
    return xyz, faces, path, border, disk


def test_true_source_short_rim_to_apex_cut_keeps_tip_one_vertex():
    xyz, faces, path, border, disk = _short_dart()
    assert len(border) == 82
    assert len(disk["source_xyz_mm"]) == len(xyz) + len(path) - 1
    assert disk["original_patch_vertex_id_per_disk_vertex"][-1] == 0
    assert disk["original_patch_vertex_id_per_disk_vertex"].count(80) == 1
    assert np.array_equal(
        np.asarray(disk["source_xyz_mm"])[disk["disk_triangle_vertex_ids"]],
        xyz[faces],
    )
    verified, cut_faces, actual = _verify_original_geometry(
        disk,
        {
            "vertices_xyz_mm": xyz.tolist(),
            "triangles_local_vertex_indices": faces.tolist(),
        },
    )
    assert len(verified) == 82 and len(cut_faces) == 80
    assert actual.tolist() == [0, 80]


def test_source_original_seam_has_two_opposite_edges_not_fake_match():
    xyz, _, _, _, disk = _short_dart()
    planar = np.asarray(disk["source_xyz_mm"])[:, :2].copy()
    planar[-1, 0] = 2
    fraction = _paired_segmentwise_absolute_mismatch(disk, planar)
    assert fraction > 0.4
    assert fraction < 1
    assert not np.array_equal(planar[0], planar[-1])


def test_rear_and_inner_half_routes_are_deterministic_not_search_after_ABF():
    full = list(range(25))
    tip, rim = 12, np.asarray([0, 24])
    assert _short_original_path(full, tip, ROUTES[0], CAPS[0], rim).tolist() == (
        list(range(24, 11, -1))
    )
    assert _short_original_path(full, tip, ROUTES[0], CAPS[1], rim).tolist() == (
        list(range(24, 11, -1))
    )
    assert _short_original_path(full, tip, ROUTES[1], CAPS[0], rim).tolist() == (
        list(range(24, 11, -1))
    )
    assert _short_original_path(full, tip, ROUTES[1], CAPS[1], rim).tolist() == (
        list(range(13))
    )


@pytest.mark.parametrize(
    "path,tip,rim",
    (
        ([0, 2, 1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15], 7, [0, 15]),
        (list(range(25)), 80, [0, 24]),
        (list(range(25)), 12, [0, 18, 24]),
        (list(range(8)), 4, [0, 7]),
    ),
)
def test_refuse_false_source_seam_path(path, tip, rim):
    with pytest.raises(ValueError):
        _short_original_path(
            path, tip, ROUTES[0], CAPS[0], np.asarray(rim)
        )


@pytest.mark.parametrize(
    "fault",
    ("bad_vertex", "bad_triangle", "bad_mapping", "duplicated_tip", "fake_euler"),
)
def test_refuse_source_geometry_rewrites_or_fake_disk(fault):
    xyz, faces, _, _, baseline = _short_dart()
    disk = deepcopy(baseline)
    if fault == "bad_vertex":
        disk["source_xyz_mm"][0][0] += 0.3
    elif fault == "bad_triangle":
        disk["disk_triangle_vertex_ids"][0][0] = 80
    elif fault == "bad_mapping":
        disk["original_patch_vertex_id_per_disk_vertex"][-1] = 4
    elif fault == "duplicated_tip":
        disk["source_xyz_mm"].append([0, 0, 2])
        disk["original_patch_vertex_id_per_disk_vertex"].append(80)
    else:
        disk["topological_Euler"] = 0
    with pytest.raises(ValueError):
        _verify_original_geometry(
            disk,
            {
                "vertices_xyz_mm": xyz.tolist(),
                "triangles_local_vertex_indices": faces.tolist(),
            },
        )


def test_no_topological_fake_seam_is_created_from_nonmanifold_triangles():
    xyz, faces = _source_cone()
    bad = np.vstack((faces, faces[0]))
    with pytest.raises(ValueError):
        _cut_source_fans_once(xyz, bad, np.asarray([0, 80]), 80)
