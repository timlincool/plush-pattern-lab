"""Convex-border Tutte disk embedding; diagnostic only, never a fabric pattern.

Positive uniform vertex weights and a strictly convex 2D border give a useful
fold-free control on suitable triangulated disks. Interior strain can be huge.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from scipy.sparse import coo_matrix, diags
from scipy.sparse.linalg import splu


def _validate_disk(disk):
    xyz = np.asarray(disk["points_xyz_mm"], dtype=np.float64)
    faces = np.asarray(disk["faces"])
    boundary = np.asarray(disk["boundary_edges"])
    if xyz.ndim != 2 or xyz.shape[1] != 3 or not np.isfinite(xyz).all():
        raise ValueError("expected finite world-millimetre 3D vertices")
    if (
        faces.ndim != 2
        or faces.shape[1] != 3
        or not np.issubdtype(faces.dtype, np.integer)
        or not len(faces)
    ):
        raise ValueError("expected nonempty integer triangular faces")
    if (
        boundary.ndim != 2
        or boundary.shape[1] != 2
        or not np.issubdtype(boundary.dtype, np.integer)
        or len(boundary) < 3
    ):
        raise ValueError("expected a nonempty closed source boundary")
    if np.any(faces < 0) or np.any(faces >= len(xyz)):
        raise ValueError("face references an invalid source vertex")
    if np.any(boundary < 0) or np.any(boundary >= len(xyz)):
        raise ValueError("border references an invalid source vertex")
    if not np.array_equal(np.unique(faces), np.arange(len(xyz))):
        raise ValueError("mesh contains unused or unconnected vertices")
    corners = xyz[faces.astype(np.int64)]
    normal = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    if np.any(np.linalg.norm(normal, axis=1) <= 1e-10):
        raise ValueError("source 3D triangle has zero area")
    return xyz, faces.astype(np.int64), boundary.astype(np.int64)


def _unique_edges(faces):
    arcs = np.concatenate((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]))
    return np.unique(np.sort(arcs, axis=1), axis=0, return_counts=True)


def _ordered_border(source, unique_edges, counts):
    actual = unique_edges[counts == 1]
    supplied = np.sort(source, axis=1)
    if len(np.unique(supplied, axis=0)) != len(source):
        raise ValueError("duplicate boundary arc")
    ordered = supplied[np.lexsort((supplied[:, 1], supplied[:, 0]))]
    if not np.array_equal(actual, ordered):
        raise ValueError("boundary edges disagree with source faces")
    adjacent = defaultdict(list)
    for a, b in actual:
        adjacent[int(a)].append(int(b))
        adjacent[int(b)].append(int(a))
    if any(len(neighbors) != 2 for neighbors in adjacent.values()):
        raise ValueError("branched or open source border")
    start = min(adjacent)
    current, previous, cycle = start, -1, []
    while True:
        if current in cycle:
            raise ValueError("source border revisits a vertex")
        cycle.append(current)
        neighbor = sorted(adjacent[current])
        nxt = neighbor[0] if neighbor[0] != previous else neighbor[1]
        if nxt == start:
            break
        previous, current = current, nxt
        if len(cycle) > len(actual):
            raise ValueError("source border is not one simple ring")
    if len(cycle) != len(actual) or len(adjacent) != len(actual):
        raise ValueError("source boundary has multiple loops")
    return np.asarray(cycle, dtype=np.int64)


def _positive_harmonic_embedding(xyz, edges, cycle, target):
    size = len(xyz)
    r = np.r_[edges[:, 0], edges[:, 1]]
    c = np.r_[edges[:, 1], edges[:, 0]]
    graph = coo_matrix(
        (np.ones(len(r), dtype=np.float64), (r, c)), shape=(size, size)
    ).tocsr()
    degree = np.asarray(graph.sum(axis=1)).ravel()
    inside = np.setdiff1d(np.arange(size), cycle)
    if not len(inside) or np.any(degree[inside] <= 0):
        raise ValueError("no valid connected interior vertices")
    lap = (diags(degree) - graph).tocsr()
    matrix = lap[inside][:, inside].tocsc()
    boundary_rhs = -(lap[inside][:, cycle] @ target)
    factor = splu(matrix)
    uv = np.zeros((size, 2), dtype=np.float64)
    uv[cycle] = target
    uv[inside] = factor.solve(boundary_rhs)
    if not np.isfinite(uv).all():
        raise ValueError("harmonic disk coordinates are not finite")
    return uv, len(inside)


def tutte_convex_disk_candidate(disk):
    """Source-perimeter-proportional circle with positive uniform graph weights."""
    xyz, faces, boundary = _validate_disk(disk)
    edges, counts = _unique_edges(faces)
    if np.any(counts > 2):
        raise ValueError("nonmanifold source triangle edge")
    cycle = _ordered_border(boundary, edges, counts)
    points = xyz[cycle]
    lengths = np.linalg.norm(points - np.roll(points, -1, axis=0), axis=1)
    if np.any(lengths <= 1e-10):
        raise ValueError("collapsed source boundary arc")
    circumference = float(lengths.sum())
    angles = (2 * np.pi / circumference) * np.r_[0, np.cumsum(lengths[:-1])]
    radius = circumference / (2 * np.pi)
    fixed_uv = np.column_stack((radius * np.cos(angles), radius * np.sin(angles)))
    uv, inside = _positive_harmonic_embedding(xyz, edges, cycle, fixed_uv)
    return uv, {
        "method": "uniform_positive_weight_Tutte_convex_circle_research_control",
        "source_3d_boundary_perimeter_mm": circumference,
        "convex_circle_radius_mm": radius,
        "source_boundary_vertex_count": len(cycle),
        "interior_vertex_count": inside,
        "pin_policy": "all_boundary_vertices_fixed_to_convex_circle",
        "boundary_arc_weights": "original_source_3d_edge_lengths_normalized_by_perimeter",
        "boundary_2d_edges_may_appear_to_match_3d_by_construction": True,
        "guarantees_require_valid_disk_and_independent_numerical_checks": True,
        "does_not_limit_interior_nonuniform_stretch": True,
        "no_manufacturing_cut_approval": True,
    }
