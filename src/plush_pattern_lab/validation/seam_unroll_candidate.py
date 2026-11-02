"""Sparse edge-length optimization for one slitted triangular annulus.

A periodic seam gauge is fixed at its exact measured 3D arclength.
Per-face 2D corners encode one topological slit. Neither a production
pattern nor a physically calibrated static fabric rest shape.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix
from shapely.geometry import Polygon
from shapely.strtree import STRtree

from plush_pattern_lab.validation.triangle_band_topology import (
    analyze_triangle_patch,
)


def _validate_indices(xyz, tri, seam):
    """Reject invalid topology indices before any geometry or scipy work."""
    if np.any(tri < 0) or np.any(tri >= len(xyz)):
        raise ValueError("out-of-range face indices")
    if np.any(seam < 0) or np.any(seam >= len(xyz)):
        raise ValueError("out-of-range seam indices")
    if len(np.unique(seam)) != len(seam):
        raise ValueError("repeated seam vertex indices")
    if any(np.any(tri[:, k] == tri[:, (k + 1) % 3]) for k in range(3)):
        raise ValueError("triangle repeats a vertex")


def _validate(vertices_mm, faces, seam_ids):
    xyz = np.asarray(vertices_mm, dtype=np.float64)
    tri = np.asarray(faces)
    seam = np.asarray(seam_ids)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or not 7 <= len(xyz) <= 20000:
        raise ValueError("expected bounded Nx3 millimetre vertices")
    if not np.isfinite(xyz).all():
        raise ValueError("non-finite 3D vertices")
    if tri.ndim != 2 or tri.shape[1] != 3 or not 1 <= len(tri) <= 40000:
        raise ValueError("expected bounded Mx3 triangle faces")
    if not np.issubdtype(tri.dtype, np.integer):
        raise ValueError("triangle indices must be integers")
    if seam.ndim != 1 or not 4 <= len(seam) < len(xyz):
        raise ValueError("expected ordered seam ring indices")
    if not np.issubdtype(seam.dtype, np.integer):
        raise ValueError("seam indices must be integers")
    _validate_indices(xyz, tri, seam)
    if not analyze_triangle_patch(seam, tri)["candidate_triangular_annulus"]:
        raise ValueError("not a connected two-boundary triangular annulus")
    triangle_xyz = xyz[tri]
    area = 0.5 * np.linalg.norm(
        np.cross(
            triangle_xyz[:, 1] - triangle_xyz[:, 0],
            triangle_xyz[:, 2] - triangle_xyz[:, 0],
        ),
        axis=1,
    )
    if np.any(area <= 1e-10):
        raise ValueError("collapsed 3D triangle")
    return xyz, tri.astype(np.int64), seam.astype(np.int64), area


def _edges(tri, xyz):
    edges = np.concatenate((tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]))
    edges = np.unique(np.sort(edges, axis=1), axis=0)
    lengths = np.linalg.norm(xyz[edges[:, 1]] - xyz[edges[:, 0]], axis=1)
    if np.any(lengths <= 1e-9):
        raise ValueError("zero-length 3D mesh edge")
    return edges, lengths


def _wrap(values, period):
    return values - period * np.round(values / period)


def _seam_stations(xyz, seam):
    distances = np.linalg.norm(xyz[np.roll(seam, -1)] - xyz[seam], axis=1)
    if np.any(distances <= 1e-9):
        raise ValueError("zero-length 3D seam edge")
    return np.r_[0.0, np.cumsum(distances[:-1])], float(distances.sum())


def _outer_neighbours(outer, edges, seam_set):
    neighbors = {int(v): set() for v in outer}
    for a, b in edges:
        if a in seam_set and b in neighbors:
            neighbors[int(b)].add(int(a))
        if b in seam_set and a in neighbors:
            neighbors[int(a)].add(int(b))
    return neighbors


def _seed_outer(xyz, outer, neighbors, phases, period):
    guess = np.zeros((len(outer), 2), dtype=np.float64)
    radius = np.zeros(len(outer), dtype=np.float64)
    for i, vertex in enumerate(outer):
        anchors = np.array(sorted(neighbors[int(vertex)]))
        if len(anchors) == 0:
            raise ValueError("outer vertex has no seam neighbor")
        stations = phases[anchors]
        circle = np.exp(2j * np.pi * stations / period).mean()
        if abs(circle) <= 1e-8:
            raise ValueError("ambiguous circular seam phase")
        x = (np.angle(circle) % (2 * np.pi)) * period / (2 * np.pi)
        length = np.linalg.norm(xyz[vertex] - xyz[anchors], axis=1)
        dx = _wrap(x - stations, period)
        guess[i] = (
            x,
            max(float(np.median(np.sqrt(np.maximum(0, length**2 - dx**2)))), 1e-3),
        )
        radius[i] = float(length.max())
    return guess, radius


def _corner_uv(uv, triangles, period):
    corners = uv[triangles].copy()
    corners[:, :, 0] = corners[:, [0], 0] + _wrap(
        corners[:, :, 0] - corners[:, [0], 0], period
    )
    centers = corners[:, :, 0].mean(axis=1)
    corners[:, :, 0] -= period * np.floor(centers[:, None] / period)
    return corners


def _jacobian_pattern(edges, outer):
    ids = {int(v): i for i, v in enumerate(outer)}
    jac = lil_matrix((len(edges), 2 * len(outer)), dtype=np.int8)
    for row, (a, b) in enumerate(edges):
        for vertex in (int(a), int(b)):
            if vertex in ids:
                j = ids[vertex]
                jac[row, 2 * j] = 1
                jac[row, 2 * j + 1] = 1
    return jac.tocsr()


def _relative_edge_error(uv, edges, lengths, period):
    """Signed edge-length discrepancy in the periodic slit domain."""
    vector = uv[edges[:, 1]] - uv[edges[:, 0]]
    vector[:, 0] = _wrap(vector[:, 0], period)
    return np.linalg.norm(vector, axis=1) / lengths - 1


def _edge_hotspots(uv, edges, lengths, seam, period):
    """Bounded local indices and error magnitudes, never export raw 3D vertices."""
    signed = _relative_edge_error(uv, edges, lengths, period)
    errors = np.abs(signed)
    seam_count = np.isin(edges, seam).sum(axis=1)
    labels = {0: "outer-outer", 1: "seam-outer", 2: "seam-seam"}
    groups = {}
    for kind, label in labels.items():
        subset = errors[seam_count == kind]
        groups[label] = (
            {
                "count": int(len(subset)),
                "p95_abs_relative_error": float(np.quantile(subset, 0.95)),
                "max_abs_relative_error": float(subset.max()),
            }
            if len(subset)
            else {"count": 0}
        )
    indices = np.argsort(-errors, kind="stable")[:8]
    return {
        "vertex_ids_are_local_patch_indices": True,
        "unique_edge_count": len(edges),
        "by_type": groups,
        "worst_edges": [
            {
                "local_vertex_ids": [int(v) for v in edges[i]],
                "type": labels[int(seam_count[i])],
                "length_3d_mm": float(lengths[i]),
                "signed_relative_error": float(signed[i]),
                "abs_relative_error": float(errors[i]),
            }
            for i in indices
        ],
    }


def _optimize(
    uv, outer, guess, radii, edges, lengths, period, budget, weights=None, start=None
):
    if not 5 <= budget <= 100:
        raise ValueError("optimization iteration budget out of bounds")
    low = np.column_stack((guess[:, 0] - period / 8, np.full(len(outer), 1e-4))).ravel()
    high = np.column_stack(
        (guess[:, 0] + period / 8, np.maximum(2 * radii, guess[:, 1] + 1))
    ).ravel()

    if weights is not None:
        weights = np.asarray(weights, dtype=np.float64)
        if weights.shape != lengths.shape or not np.isfinite(weights).all():
            raise ValueError("invalid hotspot reweighting")
        if np.any(weights < 1) or np.any(weights > 4):
            raise ValueError("hotspot weights outside the frozen [1, 4] bounds")

    def relative_residual(variables):
        uv[outer] = variables.reshape(-1, 2)
        discrepancy = _relative_edge_error(uv, edges, lengths, period)
        return discrepancy if weights is None else discrepancy * weights

    initial = guess.ravel() if start is None else np.asarray(start).ravel()
    result = least_squares(
        relative_residual,
        initial,
        bounds=(low, high),
        jac_sparsity=_jacobian_pattern(edges, outer),
        max_nfev=budget,
        ftol=1e-8,
        xtol=1e-8,
        gtol=1e-8,
    )
    uv[outer] = result.x.reshape(-1, 2)
    boundary_hits = np.isclose(result.x, low, atol=1e-4) | np.isclose(
        result.x, high, atol=1e-4
    )
    return result, int(np.count_nonzero(boundary_hits))


def _distortion(xyz, tri, corners, area3):
    triangle_xyz = xyz[tri]
    target = np.linalg.norm(triangle_xyz[:, [1, 2, 0]] - triangle_xyz, axis=2)
    found = np.linalg.norm(corners[:, [1, 2, 0]] - corners, axis=2)
    relative = np.abs(found / target - 1).ravel()
    a = corners[:, 1] - corners[:, 0]
    b = corners[:, 2] - corners[:, 0]
    signed = 0.5 * (a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0])
    preferred = 1 if np.count_nonzero(signed >= 0) >= len(signed) / 2 else -1
    areas = np.abs(signed) / area3
    return {
        "mean_abs_edge_relative_error": float(relative.mean()),
        "p95_abs_edge_relative_error": float(np.quantile(relative, 0.95)),
        "max_abs_edge_relative_error": float(relative.max()),
        "mixed_winding_or_collapsed_triangles": int(
            np.count_nonzero(signed * preferred <= 1e-10)
        ),
        "area_ratio_p05": float(np.quantile(areas, 0.05)),
        "area_ratio_median": float(np.median(areas)),
        "area_ratio_p95": float(np.quantile(areas, 0.95)),
    }


def _cut_edges(tri, corners):
    owners = {}
    for i, triangle in enumerate(tri):
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge = tuple(sorted((int(triangle[a]), int(triangle[b]))))
            coords = {
                int(triangle[a]): corners[i, a],
                int(triangle[b]): corners[i, b],
            }
            owners.setdefault(edge, []).append(coords)
    cuts = []
    for edge, adjacent in owners.items():
        if len(adjacent) == 2:
            max_gap = max(np.linalg.norm(adjacent[0][v] - adjacent[1][v]) for v in edge)
            if max_gap > 1e-5:
                cuts.append(edge)
    return cuts


def _overlap(corners):
    polygons = [Polygon(face) for face in corners]
    if any(not shape.is_valid for shape in polygons):
        return {"invalid_polygon_count": sum(not shape.is_valid for shape in polygons)}
    spatial = STRtree(polygons)
    count, total = 0, 0.0
    for i, shape in enumerate(polygons):
        for candidate in spatial.query(shape):
            j = int(candidate)
            if j > i:
                area = shape.intersection(polygons[j]).area
                if area > 1e-7:
                    count += 1
                    total += area
    return {
        "invalid_polygon_count": 0,
        "overlapping_triangle_pairs": count,
        "overlap_area_mm2": float(total),
    }


def _hotspot_ab(
    xyz,
    tri,
    seam,
    uv,
    outer,
    guess,
    radii,
    edges,
    lengths,
    period,
    area3,
    budget,
    outer_only=False,
):
    """One bounded IRLS-style candidate, never replacing the original solution."""
    error = np.abs(_relative_edge_error(uv, edges, lengths, period))
    if outer_only:
        is_outer_edge = np.isin(edges, seam).sum(axis=1) == 0
        if not is_outer_edge.any():
            raise ValueError("the triangular annulus lacks an outer boundary")
        threshold = float(np.quantile(error[is_outer_edge], 0.98))
        selected = is_outer_edge & (error >= threshold)
        weights = np.where(selected, 1.75, 1.0)
    else:
        scale = max(float(np.quantile(error, 0.95)), 1e-8)
        weights = np.clip(error / scale, 1.0, 4.0)
    trial = uv.copy()
    solver, hits = _optimize(
        trial,
        outer,
        guess,
        radii,
        edges,
        lengths,
        period,
        budget,
        weights=weights,
        start=uv[outer].copy(),
    )
    corners = _corner_uv(trial, tri, period)
    return {
        "status": (
            "OUTER_TOP_2PCT_WEIGHTED_COMPARISON_ONLY"
            if outer_only
            else "HOTSPOT_WEIGHTED_COMPARISON_ONLY"
        ),
        "max_weight": float(weights.max()),
        "upweighted_edge_count": int(np.count_nonzero(weights > 1)),
        "optimized": _distortion(xyz, tri, corners, area3),
        "overlap": _overlap(corners),
        "cut_edges_count": len(_cut_edges(tri, corners)),
        "solver": {
            "converged": bool(solver.success),
            "function_evaluations": solver.nfev,
            "bound_components_at_limit": hits,
        },
        "edge_hotspots": _edge_hotspots(trial, edges, lengths, seam, period),
        "promoted_to_default": False,
    }


def unroll_triangular_band(vertices_mm, faces, seam_ids, budget=60):
    """Return research metrics and per-face coordinates; no approved cut geometry."""
    xyz, tri, seam, area3 = _validate(vertices_mm, faces, seam_ids)
    inner = set(seam.tolist())
    outer = np.array(sorted(set(tri.ravel()) - inner), dtype=np.int64)
    stations, period = _seam_stations(xyz, seam)
    edges, lengths = _edges(tri, xyz)
    phases = np.full(len(xyz), np.nan)
    phases[seam] = stations
    guess, radii = _seed_outer(
        xyz, outer, _outer_neighbours(outer, edges, inner), phases, period
    )
    uv = np.zeros((len(xyz), 2))
    uv[seam, 0] = stations
    uv[outer] = guess
    baseline = _distortion(xyz, tri, _corner_uv(uv, tri, period), area3)
    solver, hits = _optimize(uv, outer, guess, radii, edges, lengths, period, budget)
    corners = _corner_uv(uv, tri, period)
    cuts = _cut_edges(tri, corners)
    hotspots = _edge_hotspots(uv, edges, lengths, seam, period)
    comparison = _hotspot_ab(
        xyz,
        tri,
        seam,
        uv,
        outer,
        guess,
        radii,
        edges,
        lengths,
        period,
        area3,
        budget,
    )
    outer_comparison = _hotspot_ab(
        xyz,
        tri,
        seam,
        uv,
        outer,
        guess,
        radii,
        edges,
        lengths,
        period,
        area3,
        budget,
        outer_only=True,
    )
    return {
        "schema": "stage6-slitted-triangle-band-unroll-v1",
        "status": "SPARSE_EDGE_LENGTH_UNROLL_RESEARCH_NOT_CUT_PATTERN",
        "seam_perimeter_mm": period,
        "fixed_seam_vertex_count": len(seam),
        "outer_vertex_count": len(outer),
        "triangle_count": len(tri),
        "initial": baseline,
        "optimized": _distortion(xyz, tri, corners, area3),
        "baseline_edge_hotspots": hotspots,
        "hotspot_weighted_variant": comparison,
        "outer_worst_edge_variant": outer_comparison,
        "cut_edges_count": len(cuts),
        "cut_edges_local_indices": [list(edge) for edge in cuts],
        "overlap": _overlap(corners),
        "solver": {
            "converged": bool(solver.success),
            "function_evaluations": solver.nfev,
            "bound_components_at_limit": hits,
            "max_evaluations": budget,
        },
        "fixed_original_3d_seam_length": True,
        "approved_cut_pattern": False,
        "limitations": [
            "A radial slit is encoded as duplicated per-triangle 2D corner positions",
            "A constrained straight 2D seam does not mean physically sewable fabric",
            "Optimizing edge lengths can still create inverted or overlapping faces",
            "Weighted hotspot A/B is diagnostic only and cannot replace the baseline",
            "No fabric grain, sewing allowance, stuffing or physical test",
        ],
    }, corners
