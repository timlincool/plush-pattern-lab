"""Synthetic regression for Stage6 R3 exact dual-sided netline construction."""

from __future__ import annotations

import numpy as np
import pytest
from shapely.geometry import Polygon

from research.stage6_b24_r3.build_r3_matched_body import (
    gore_vertices,
    pieces,
    safe_yoke_blend,
    yoke_triangulation,
)


def rings():
    theta = np.arange(64) * (2 * np.pi / 64)
    return np.asarray(
        [
            np.column_stack(
                (
                    width * np.cos(theta),
                    depth * np.sin(theta) + y,
                )
            )
            for width, depth, y in (
                (56, 83, 20),
                (53, 86, 18),
                (51, 90, 17),
                (47, 82, 12),
                (43, 76, 6),
            )
        ]
    )


def test_shared_2d_side_seams_match_across_four_gores():
    source = rings()
    flattened = [
        gore_vertices(source, [60, 70, 80, 90, 100], f"BAND-{i + 1}", i)[1]
        .reshape(5, 17, 2)
        for i in range(4)
    ]
    for i in range(4):
        ours = flattened[i][:, -1, :]
        next_piece = flattened[(i + 1) % 4][:, 0, :]
        left = np.linalg.norm(np.diff(ours, axis=0), axis=1)
        right = np.linalg.norm(np.diff(next_piece, axis=0), axis=1)
        assert np.max(np.abs(left - right)) < 1e-12
    for i, plane in enumerate(flattened):
        for z, ring in enumerate(source):
            arc = ring[(i * 16 + np.arange(17)) % 64]
            source_lengths = np.linalg.norm(np.diff(arc, axis=0), axis=1)
            flat_lengths = np.linalg.norm(np.diff(plane[z], axis=0), axis=1)
            assert np.max(abs(source_lengths - flat_lengths * 1000)) < 1e-9


def test_4_holes_constrained_source_edges_are_preserved():
    circle = np.arange(64) * (2 * np.pi / 64)
    outer = np.column_stack((62 * np.cos(circle), 62 * np.sin(circle)))
    holes = [
        np.column_stack((8 * np.cos(circle) + x, 8 * np.sin(circle) + y))
        for x, y in ((-23, -23), (23, -23), (-23, 23), (23, 23))
    ]
    triangles = yoke_triangulation(np.vstack((outer, *holes)))
    assert len(triangles) == 326
    shaped, fraction = safe_yoke_blend(
        outer, outer * 0.90, [Polygon(hole) for hole in holes]
    )
    assert 0 <= fraction <= 0.27
    assert Polygon(shaped).is_valid


def test_panel_inventory_and_invalid_yoke_fail_closed():
    inventory = pieces()
    assert len(inventory) == 24
    assert sum(len(ids) for ids in inventory.values()) == 2431
    bad = np.zeros((320, 2))
    with pytest.raises(ValueError):
        yoke_triangulation(bad)
