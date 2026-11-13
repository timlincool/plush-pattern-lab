"""Synthetic topology and failure cases for genuine Stage6 six inter-rim cuts."""

from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest
from audit_stage6_lower_six_cut_disks_abf import PAIRS, _crosszone_sources

from plush_pattern_lab.validation.stage6_ear_slit_lscm import _scale_free_gauge
from plush_pattern_lab.validation.stage6_lower_six_cut_disks import (
    SCHEMA,
    _boundary,
    _cut,
    _paired_source_edges,
    _shortest,
)


def _grid_with_holes(size=25):
    vertices = np.asarray(
        [[float(x), float(y), float(x + y) / 100] for y in range(size)
         for x in range(size)],
        dtype=np.float64,
    )
    triangles = []
    for y in range(size - 1):
        for x in range(size - 1):
            if 6 <= x < 10 and 6 <= y < 10:
                continue
            if 15 <= x < 19 and 15 <= y < 19:
                continue
            first = size * y + x
            triangles.extend(
                (
                    [first, first + 1, first + size + 1],
                    [first, first + size + 1, first + size],
                )
            )
    face = np.asarray(triangles, dtype=np.int64)
    used, inverse = np.unique(face, return_inverse=True)
    return {
        "xyz": vertices[used],
        "faces": inverse.reshape(-1, 3),
        "source_id": used,
    }


def _geometry():
    mesh = _grid_with_holes()
    border, _, _, _ = _boundary(mesh)
    assert len(border) == 3
    return mesh, border


def test_two_original_interrim_paths_turn_three_boundaries_into_one_disk():
    mesh, border = _geometry()
    outer = max(border, key=lambda item: len(item["edges"]))
    holes = sorted(
        (row for row in border if row is not outer),
        key=lambda item: item["vertices"].min(),
    )
    path, distance = _shortest(
        mesh, holes[0]["vertices"], outer["vertices"]
    )
    assert distance > 0
    after = _cut(mesh, path, 3)
    loops, _, _, _ = _boundary(after)
    assert len(loops) == 2

    used = set(map(int, mesh["source_id"][path]))
    next_hole = [
        item for item in loops
        if any(
            int(after["source_id"][v]) in
            set(map(int, mesh["source_id"][holes[1]["vertices"]]))
            for v in item["vertices"]
        )
    ]
    assert len(next_hole) == 1
    other = next(item for item in loops if item is not next_hole[0])
    original_outer = set(map(int, mesh["source_id"][outer["vertices"]]))
    target = [
        p for p in other["vertices"]
        if int(after["source_id"][p]) in original_outer - used
    ]
    forbidden = [
        p for p, original_id in enumerate(after["source_id"])
        if int(original_id) in used
    ]
    second, second_distance = _shortest(
        after, next_hole[0]["vertices"], target, forbidden
    )
    assert second_distance > 0
    disk = _cut(after, second, 2)
    final, edges, _, _ = _boundary(disk)
    assert len(final) == 1
    assert len(disk["xyz"]) - len(edges) + len(disk["faces"]) == 1
    assert np.array_equal(
        disk["source_id"][disk["faces"]],
        mesh["source_id"][mesh["faces"]],
    )
    seams = [
        {"original_3d_clipped_lower_source_vertex_ids":
         mesh["source_id"][path].tolist()},
        {"original_3d_clipped_lower_source_vertex_ids":
         after["source_id"][second].tolist()},
    ]
    assert _paired_source_edges(disk, seams, final[0])
    assert SCHEMA.endswith("disk-cuts-v1")


def test_missing_original_boundary_or_false_topology_is_rejected():
    mesh, loops = _geometry()
    shortened = deepcopy(mesh)
    shortened["faces"] = shortened["faces"][:-1]
    altered, _, _, _ = _boundary(shortened)
    assert len(altered) >= 2
    with pytest.raises(ValueError):
        _cut(mesh, np.asarray([0, 1]), 2)
    with pytest.raises(ValueError):
        _shortest(mesh, loops[0]["vertices"], loops[0]["vertices"])


def test_fabric_identity_cannot_be_claimed_from_valid_3d_wo_faces():
    mesh, loops = _geometry()
    flat = deepcopy(mesh)
    flat["faces"][0][0] = len(flat["xyz"]) + 1
    with pytest.raises((ValueError, IndexError)):
        _boundary(flat)
    assert len(loops) == 3


def _fake_crosszone_2d_original_edge_pairs():
    # Four genuine region-pair groups; each physical source edge occurs once
    # on each of its two adjacent original panels, never on unrelated panels.
    sides = [{}, {}, {}, {}]
    base = 0
    for pair, count in PAIRS.items():
        left, right = map(int, pair.split(":"))
        for i in range(count):
            key = (base + i, 100000 + base + i)
            data = [{
                "original_direction": key,
                "source_3d_length_mm": 1.0,
                "planar_length_mm": 1.01,
            }]
            sides[left][key] = data
            sides[right][key] = [{
                "original_direction": key[::-1],
                "source_3d_length_mm": 1.0,
                "planar_length_mm": 0.99,
            }]
        base += count
    return sides


def test_original_801_shared_region_3d_source_edges_check_real_two_2d_sides():
    rows = _crosszone_sources(_fake_crosszone_2d_original_edge_pairs())
    assert {key: value["edge_count"] for key, value in rows.items()} == PAIRS
    assert all(value["two_2d_mismatch_fraction"] == pytest.approx(0.02)
               for value in rows.values())


def test_original_region_source_edge_pairing_rejects_missing_or_changed_3d():
    rows = _fake_crosszone_2d_original_edge_pairs()
    key = next(iter(rows[0]))
    changed = deepcopy(rows)
    changed[1][key][0]["source_3d_length_mm"] = 2.0
    with pytest.raises(ValueError, match="3D"):
        _crosszone_sources(changed)
    removed = deepcopy(rows)
    removed[1].pop(key)
    with pytest.raises(ValueError, match="interzone"):
        _crosszone_sources(removed)

def test_native_blender_unit_square_pregauge_scaling_is_similarity_invariant():
    # A complete 500mm source region often has Blender UV normalized to 0..1.
    # The old local-patch gauge caps its coefficient at 100; converting UV
    # units before the same minimum-squared-edge gauge cannot change strain.
    xyz = np.asarray([[0.0, 0.0, 0.0], [500.0, 0.0, 0.0],
                      [0.0, 500.0, 0.0]])
    faces = np.asarray([[0, 1, 2]])
    native_uv = np.asarray([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
    with pytest.raises(ValueError, match="invalid uniform"):
        _scale_free_gauge(xyz, faces, native_uv)
    mm_a, strain_a, quality_a = _scale_free_gauge(
        xyz, faces, native_uv * 1000.0
    )
    mm_b, strain_b, quality_b = _scale_free_gauge(
        xyz, faces, native_uv * 500.0
    )
    assert np.allclose(mm_a, mm_b, atol=1e-9)
    assert np.allclose(strain_a, strain_b, atol=1e-12)
    assert quality_a["scaled_2d_p95_abs_edge_relative_error"] == pytest.approx(0)
    assert quality_b["scaled_2d_p95_abs_edge_relative_error"] == pytest.approx(0)
