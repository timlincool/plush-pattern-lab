"""Research-only bounded Laplacian fairing with immutable 3D sewing seams.

This changes only interior XYZ; triangle identities, source edge IDs, all
hoof/outer/slit positions, and the original Stage6 geometry remain immutable.
No material properties, printable stencils, or factory tolerance are implied.
"""

from __future__ import annotations

import numpy as np
from scipy.sparse import coo_matrix


def _validate_inputs(points, faces, locked, steps, alpha, max_shift_mm):
    xyz = np.asarray(points, dtype=np.float64)
    triangles = np.asarray(faces)
    fixed = np.asarray(locked)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or not np.isfinite(xyz).all():
        raise ValueError("expected finite Nx3 world-mm surface")
    if (
        triangles.ndim != 2
        or triangles.shape[1] != 3
        or not np.issubdtype(triangles.dtype, np.integer)
        or len(triangles) == 0
    ):
        raise ValueError("expected integer Mx3 source triangles")
    if fixed.ndim != 1 or not np.issubdtype(fixed.dtype, np.integer) or not len(fixed):
        raise ValueError("required integer protected source seam vertex IDs")
    if np.any(triangles < 0) or np.any(triangles >= len(xyz)):
        raise ValueError("invalid triangle vertex ID")
    if np.any(fixed < 0) or np.any(fixed >= len(xyz)):
        raise ValueError("invalid protected seam vertex ID")
    if len(np.unique(fixed)) != len(fixed):
        raise ValueError("protected vertices must be unique")
    if not (1 <= steps <= 20 and 0 < alpha <= 0.5 and 0 < max_shift_mm <= 1.0):
        raise ValueError("unbounded fairing research parameters")
    return xyz, triangles.astype(np.int64), fixed.astype(np.int64)


def _uniform_neighbors(faces, count):
    edges = np.concatenate((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]))
    edges = np.unique(np.sort(edges, axis=1), axis=0)
    if np.any(edges[:, 0] == edges[:, 1]):
        raise ValueError("self-loop triangle edge")
    rows = np.r_[edges[:, 0], edges[:, 1]]
    cols = np.r_[edges[:, 1], edges[:, 0]]
    graph = coo_matrix(
        (np.ones(len(rows), dtype=np.float64), (rows, cols)),
        shape=(count, count),
    ).tocsr()
    degree = np.asarray(graph.sum(axis=1)).ravel()
    if np.any(degree == 0):
        raise ValueError("disconnected or unreferenced point in panel")
    return graph, degree


def _surface_screen(original, proposed, faces, fixed):
    drift = np.linalg.norm(proposed - original, axis=1)
    a = original[faces]
    b = proposed[faces]
    normal_before = np.cross(a[:, 1] - a[:, 0], a[:, 2] - a[:, 0])
    normal_after = np.cross(b[:, 1] - b[:, 0], b[:, 2] - b[:, 0])
    area_before = np.linalg.norm(normal_before, axis=1)
    area_after = np.linalg.norm(normal_after, axis=1)
    if np.any(area_before <= 1e-10) or np.any(~np.isfinite(area_after)):
        raise ValueError("collapsed or invalid original geometry")
    dot = np.einsum("ij,ij->i", normal_before, normal_after)
    ratio = area_after / area_before
    return {
        "protected_vertices": len(fixed),
        "max_protected_vertex_drift_mm": float(drift[fixed].max()),
        "all_protected_3d_seam_points_exact": bool(
            np.array_equal(original[fixed], proposed[fixed])
        ),
        "moved_interior_vertices": int(np.count_nonzero(drift > 1e-9)),
        "vertex_displacement_p95_mm": float(np.quantile(drift, 0.95)),
        "vertex_displacement_max_mm": float(drift.max()),
        "face_orientation_reversals": int(np.sum(dot < 0)),
        "face_collapse_count": int(np.sum(area_after <= 1e-10)),
        "face_area_ratio_min": float(ratio.min()),
        "face_area_ratio_p01": float(np.quantile(ratio, 0.01)),
        "face_area_ratio_p95": float(np.quantile(ratio, 0.95)),
        "original_triangle_ids_preserved": True,
        "not_a_self_intersection_or_silhouette_test": True,
    }


def fair_manufacturing_surface(
    points, faces, protected_vertex_ids, *, steps, alpha, max_shift_mm
):
    """Return candidate coordinates plus independent 3D geometric diagnostics."""
    source, triangles, locked = _validate_inputs(
        points, faces, protected_vertex_ids, steps, alpha, max_shift_mm
    )
    graph, degree = _uniform_neighbors(triangles, len(source))
    moving = np.ones(len(source), dtype=bool)
    moving[locked] = False
    candidate = source.copy()
    for _ in range(steps):
        neighbors = (graph @ candidate) / degree[:, None]
        proposed = candidate + alpha * (neighbors - candidate)
        delta = proposed - source
        length = np.linalg.norm(delta, axis=1)
        factor = np.minimum(1.0, max_shift_mm / np.maximum(length, 1e-12))
        candidate[moving] = source[moving] + delta[moving] * factor[moving, None]
    score = _surface_screen(source, candidate, triangles, locked)
    if not score["all_protected_3d_seam_points_exact"]:
        raise ValueError("original sewing seam moved during fairing")
    if score["vertex_displacement_max_mm"] > max_shift_mm + 1e-8:
        raise ValueError("bounded fairing exceeded per-vertex movement cap")
    score["research_parameters"] = {
        "steps": steps,
        "alpha": alpha,
        "max_source_displacement_mm": max_shift_mm,
    }
    score["potential_triangle_area_damage"] = score["face_area_ratio_min"] < 0.5
    score["three_dimensional_surface_screen_rejected"] = (
        score["face_orientation_reversals"] > 0
        or score["face_collapse_count"] > 0
        or score["potential_triangle_area_damage"]
    )
    score["face_area_half_is_research_alert_not_textile_tolerance"] = True
    score["approved_for_sewing_or_cutting"] = False
    return candidate, score
