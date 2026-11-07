"""Research-only least-squares conformal parameterization of a CUT full panel.

A positive cylinder control is nearly isometric; the actual nondevelopable
main body may fail by high strain, folds, or UV overlaps. Failures are useful
evidence and must never be promoted to an approved cutting template.
"""

from __future__ import annotations

import numpy as np
import shapely
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import lsmr
from shapely.strtree import STRtree

MAX_ITERATIONS = 8000
MAX_OVERLAP_PAIRS_TO_EXAMINE = 400000


def _intrinsic_triangles(points, faces):
    corners = points[faces]
    edge1 = corners[:, 1] - corners[:, 0]
    edge2 = corners[:, 2] - corners[:, 0]
    width = np.linalg.norm(edge1, axis=1)
    dot = np.einsum("ij,ij->i", edge1, edge2)
    x2 = dot / np.maximum(width, 1e-12)
    y2 = np.sqrt(np.maximum(np.einsum("ij,ij->i", edge2, edge2) - x2 * x2, 0))
    if np.any(width < 1e-10) or np.any(y2 < 1e-10):
        raise ValueError("source 3D panel contains a collapsed triangle")
    gradient_x = np.column_stack((-1 / width, 1 / width, np.zeros(len(faces))))
    gradient_y = np.column_stack(
        ((x2 - width) / (width * y2), -x2 / (width * y2), 1 / y2)
    )
    return corners, width, x2, y2, gradient_x, gradient_y


def _conformal_matrix(faces, width, y2, dx, dy, vertex_count):
    triangle_count = len(faces)
    rows = np.repeat(np.arange(triangle_count), 3)
    ids = faces.ravel()
    scale = np.sqrt((width * y2 / 2))[:, None]
    data = np.concatenate(
        (
            (scale * dx).ravel(),
            (-scale * dy).ravel(),
            (scale * dy).ravel(),
            (scale * dx).ravel(),
        )
    )
    r = np.concatenate((2 * rows, 2 * rows, 2 * rows + 1, 2 * rows + 1))
    c = np.concatenate((2 * ids, 2 * ids + 1, 2 * ids, 2 * ids + 1))
    return coo_matrix(
        (data, (r, c)), shape=(2 * triangle_count, 2 * vertex_count)
    ).tocsr()


def _solve_lscm(disk, iteration_cap):
    if not 50 <= iteration_cap <= MAX_ITERATIONS:
        raise ValueError("bounded LSCM solver iteration budget required")
    points = np.asarray(disk["points_xyz_mm"], dtype=np.float64)
    faces = np.asarray(disk["faces"], dtype=np.int64)
    xyz, width, x2, y2, dx, dy = _intrinsic_triangles(points, faces)
    equations = _conformal_matrix(faces, width, y2, dx, dy, len(points))
    first = int(disk["slit_pin_inner_id"])
    last = int(disk["slit_pin_outer_id"])
    if first == last:
        raise ValueError("slit endpoints are not distinct")
    pins = np.array([2 * first, 2 * first + 1, 2 * last, 2 * last + 1])
    pin_values = np.array([0.0, 0.0, float(disk["slit_path_length_3d_mm"]), 0.0])
    free = np.ones(equations.shape[1], dtype=bool)
    free[pins] = False
    right = -(equations[:, pins] @ pin_values)
    solved = lsmr(
        equations[:, free], right, atol=1e-6, btol=1e-6, maxiter=iteration_cap
    )
    coordinates = np.zeros(equations.shape[1], dtype=np.float64)
    coordinates[pins] = pin_values
    coordinates[free] = solved[0]
    return (
        coordinates.reshape(-1, 2),
        {
            "method": "two_pin_sparse_LSCM_real_3d_triangle_intrinsic_charts",
            "pinned_original_path_3d_length_mm": float(pin_values[2]),
            "solver_status": int(solved[1]),
            "solver_iterations": int(solved[2]),
            "solver_residual_l2": float(solved[3]),
            "converged_before_cap": bool(solved[1] in (1, 2)),
            "max_solver_iterations": iteration_cap,
            "stationary_least_squares_is_not_geometric_quality": True,
        },
        (xyz, width, x2, y2),
    )


def _strain_metrics(uv_faces, intrinsic):
    original, width, x2, y2 = intrinsic
    d1 = uv_faces[:, 1] - uv_faces[:, 0]
    d2 = uv_faces[:, 2] - uv_faces[:, 0]
    signed_area = 0.5 * (d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0])
    positive = int((signed_area > 1e-8).sum())
    negative = int((signed_area < -1e-8).sum())
    sign = 1 if positive >= negative else -1
    inverted = int((signed_area * sign < -1e-8).sum())
    near_zero = int((np.abs(signed_area) <= 1e-8).sum())
    lengths3 = np.linalg.norm(original[:, [1, 2, 0]] - original, axis=2)
    lengths2 = np.linalg.norm(uv_faces[:, [1, 2, 0]] - uv_faces, axis=2)
    discrepancy = np.abs(lengths2 / lengths3 - 1)
    valid = np.abs(signed_area) > 1e-8
    stretch = np.array([], dtype=np.float64)
    if np.any(valid):
        matrix = np.stack((d1[valid], d2[valid]), axis=2)
        intrinsic_2d = np.zeros_like(matrix)
        intrinsic_2d[:, 0, 0] = width[valid]
        intrinsic_2d[:, 0, 1] = x2[valid]
        intrinsic_2d[:, 1, 1] = y2[valid]
        deformation = np.matmul(intrinsic_2d, np.linalg.inv(matrix))
        singular = np.linalg.svd(deformation, compute_uv=False)
        stretch = np.max(np.abs(singular - 1), axis=1)
    return {
        "triangle_count": len(uv_faces),
        "positive_triangle_areas": positive,
        "negative_triangle_areas": negative,
        "inverted_winding_triangles": inverted,
        "near_zero_uv_area_triangles": near_zero,
        "triangle_edge_relative_error": {
            "mean": float(discrepancy.mean()),
            "p95": float(np.quantile(discrepancy, 0.95)),
            "max": float(discrepancy.max()),
        },
        "relative_principal_stretch_from_2d_rest_candidate": {
            "valid_triangles": int(valid.sum()),
            "p95": float(np.quantile(stretch, 0.95)) if len(stretch) else None,
            "max": float(stretch.max()) if len(stretch) else None,
            "material_model": "NOT measured; purely geometric simulated 3D/2D",
        },
    }


def _overlap_metrics(uv_faces):
    polys = shapely.polygons(uv_faces)
    if not shapely.is_valid(polys).all():
        invalid = int((~shapely.is_valid(polys)).sum())
    else:
        invalid = 0
    tree = STRtree(polys)
    overlap_count, observed, checked, witnesses = 0, 0.0, 0, []
    truncated = False
    for start in range(0, len(polys), 512):
        pair = tree.query(polys[start : start + 512], predicate="intersects")
        source = pair[0] + start
        other = pair[1]
        mask = source < other
        source, other = source[mask], other[mask]
        checked += len(source)
        if checked > MAX_OVERLAP_PAIRS_TO_EXAMINE:
            truncated = True
            break
        areas = shapely.area(shapely.intersection(polys[source], polys[other]))
        significant = np.flatnonzero(areas > 1e-6)
        overlap_count += len(significant)
        observed += float(areas[significant].sum())
        for idx in significant[: max(0, 12 - len(witnesses))]:
            witnesses.append([int(source[idx]), int(other[idx])])
    return {
        "invalid_uv_polygon_count": invalid,
        "tested_candidate_triangle_pairs": checked,
        "overlap_search_truncated": truncated,
        "overlapping_nonzero_area_triangle_pairs": overlap_count,
        "sum_detected_overlap_area_mm2": observed,
        "first_12_overlap_face_pairs": witnesses,
        "area_threshold_mm2": 1e-6,
    }


def _boundary_metrics(disk, planar):
    edges = np.asarray(disk["boundary_edges"], dtype=np.int64)
    xy = planar[edges]
    xyz = np.asarray(disk["points_xyz_mm"])[edges]
    two = np.linalg.norm(xy[:, 1] - xy[:, 0], axis=1)
    three = np.linalg.norm(xyz[:, 1] - xyz[:, 0], axis=1)
    delta = np.abs(two / three - 1)
    ids = np.asarray(disk["source_vertex_ids"])[edges]
    original_keys = np.sort(ids, axis=1)
    original = {
        "hoof": {tuple(sorted(v)) for v in disk["source_cuff_edge_global_ids"]},
        "outer": {tuple(sorted(v)) for v in disk["source_outer_edge_global_ids"]},
    }
    if "source_slit_edge_global_ids" in disk:
        original["slit"] = {
            tuple(sorted(v)) for v in disk["source_slit_edge_global_ids"]
        }
    else:
        original["slit"] = {
            tuple(sorted(v))
            for v in zip(
                disk["slit_path_source_vertex_ids"][:-1],
                disk["slit_path_source_vertex_ids"][1:],
            )
        }
    region = {
        kind: np.fromiter(
            (tuple(pair) in keys for pair in original_keys),
            dtype=bool,
            count=len(edges),
        )
        for kind, keys in original.items()
    }
    if np.any(np.sum(np.stack(list(region.values())), axis=0) != 1):
        raise ValueError("unclassified or multiply classified cut boundary edge")
    group_metrics = {
        kind: {
            "edge_count": int(mask.sum()),
            "original_3d_mm": float(three[mask].sum()),
            "candidate_2d_mm": float(two[mask].sum()),
            "p95_edge_relative_error": float(np.quantile(delta[mask], 0.95)),
            "max_edge_relative_error": float(delta[mask].max()),
        }
        for kind, mask in region.items()
    }
    if group_metrics["hoof"]["edge_count"] != disk["source_cuff_edges"]:
        raise ValueError("a measured hoof seam edge was lost during cutting")
    if group_metrics["outer"]["edge_count"] != disk["source_outer_seam_edges"]:
        raise ValueError("an original inter-panel seam edge was lost")
    return {
        "boundary_edge_count": len(edges),
        "original_boundary_3d_length_mm": float(three.sum()),
        "new_cut_boundary_2d_length_mm": float(two.sum()),
        "boundary_edge_relative_error_p95": float(np.quantile(delta, 0.95)),
        "boundary_edge_relative_error_max": float(delta.max()),
        "perimeter_by_source_role": group_metrics,
        "source_seam_vertex_pairs_preserved": True,
        "boundary_edge_source_vertex_ids": ids.tolist(),
        "boundary_edge_uv_ids": edges.tolist(),
    }


def flatten_cut_panel(disk, iteration_cap=8000):
    """Try LSCM, retain ALL failed diagnostic evidence, never approve cutting."""
    uv, solver, charts = _solve_lscm(disk, iteration_cap)
    metric = _strain_metrics(uv[np.asarray(disk["faces"])], charts)
    collisions = _overlap_metrics(uv[np.asarray(disk["faces"])])
    boundary = _boundary_metrics(disk, uv)
    issues = []
    if not solver["converged_before_cap"]:
        issues.append("solver_stopped_without_convergence")
    if metric["inverted_winding_triangles"] or metric["near_zero_uv_area_triangles"]:
        issues.append("triangle_flip_or_collapse")
    if collisions["overlap_search_truncated"]:
        issues.append("uv_overlap_search_truncated")
    if collisions["overlapping_nonzero_area_triangle_pairs"]:
        issues.append("positive_area_triangle_overlaps")
    if metric["triangle_edge_relative_error"]["p95"] > 0.08:
        issues.append("high_relative_triangle_edge_distortion")
    return {
        "schema": "stage6-whole-leftfront-slit-lscm-research-v1",
        "status": "REJECTED_FOR_DIRECT_SINGLE_PIECE"
        if issues
        else "RESEARCH_GEOMETRY_ONLY",
        "solver": solver,
        "strain_screen": metric,
        "global_2d_overlap": collisions,
        "boundary": boundary,
        "rejection_reasons": issues,
        "candidate_geometry_only": True,
        "approved_cutting_pattern": False,
        "factory_grain_or_seam_allowance_exists": False,
        "error_8pct_is_research_trigger_not_fabric_tolerance": True,
    }, uv
