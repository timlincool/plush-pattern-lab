"""Diagnostic planar ARAP and best uniform scale for a triangle disk.

All length and coordinate units are millimetres. Never approve fabric cutting.
"""

from __future__ import annotations

import numpy as np
from scipy.sparse import coo_matrix, diags
from scipy.sparse.linalg import splu

MAX_ARAP_ITERATIONS = 60


def _triangle_charts(xyz, faces):
    corners = xyz[faces]
    e1 = corners[:, 1] - corners[:, 0]
    e2 = corners[:, 2] - corners[:, 0]
    w = np.linalg.norm(e1, axis=1)
    if np.any(w <= 1e-10):
        raise ValueError("collapsed 3D edge in panel")
    x2 = np.einsum("ij,ij->i", e1, e2) / w
    y2 = np.sqrt(np.maximum(np.einsum("ij,ij->i", e2, e2) - x2 * x2, 0))
    if np.any(y2 <= 1e-10):
        raise ValueError("collapsed source triangle")
    gx = np.column_stack((-1 / w, 1 / w, np.zeros(len(faces))))
    gy = np.column_stack(((x2 - w) / (w * y2), -x2 / (w * y2), 1 / y2))
    return w * y2 / 2, gx, gy


def _gradient_operators(xyz, faces):
    n = len(xyz)
    weights, dx, dy = _triangle_charts(xyz, faces)
    row = np.repeat(np.arange(len(faces)), 3)
    col = faces.ravel()
    gx = coo_matrix((dx.ravel(), (row, col)), shape=(len(faces), n)).tocsr()
    gy = coo_matrix((dy.ravel(), (row, col)), shape=(len(faces), n)).tocsr()
    lap = (gx.T @ diags(weights) @ gx + gy.T @ diags(weights) @ gy).tocsc()
    return gx, gy, weights, lap


def _initial_uv(xyz, previous, a, b, policy):
    chord = xyz[b] - xyz[a]
    distance = float(np.linalg.norm(chord))
    if not np.isfinite(distance) or distance < 1e-8:
        raise ValueError("two pins must be distinct in 3D")
    if policy == "lscm":
        shifted = previous - previous[a]
        delta = shifted[b]
        norm = float(np.linalg.norm(delta))
        if norm < 1e-8:
            raise ValueError("degenerate prior LSCM pin separation")
        rot = np.array([[delta[0], delta[1]], [-delta[1], delta[0]]]) / norm
        return (shifted @ rot.T) * (distance / norm), distance
    direction = chord / distance
    residual = xyz - xyz.mean(axis=0)
    residual -= (residual @ direction)[:, None] * direction
    _, singular, axes = np.linalg.svd(residual, full_matrices=False)
    if singular[0] < 1e-8:
        raise ValueError("3D panel points lie on a degenerate line")
    origin = xyz - xyz[a]
    return np.column_stack((origin @ direction, origin @ axes[0])), distance


def _nearest_rotations(gx, gy, uv):
    ux, vx = (gx @ uv).T
    uy, vy = (gy @ uv).T
    cosine = ux + vy
    sine = vx - uy
    length = np.hypot(cosine, sine)
    zero = length <= 1e-10
    cosine[zero] = 1
    sine[zero] = 0
    length[zero] = 1
    return cosine / length, sine / length


def _global_step(gx, gy, weights, lu, free, lap_free_fixed, pins, uv):
    cos, sin = _nearest_rotations(gx, gy, uv)
    u_rhs = gx.T @ (weights * cos) - gy.T @ (weights * sin)
    v_rhs = gx.T @ (weights * sin) + gy.T @ (weights * cos)
    nxt = uv.copy()
    nxt[free, 0] = lu.solve(u_rhs[free] - lap_free_fixed @ pins[:, 0])
    nxt[free, 1] = lu.solve(v_rhs[free] - lap_free_fixed @ pins[:, 1])
    return nxt


def solve_research_arap(disk, prior_uv, *, iterations=30, seed="pca"):
    """Two-pin area-weighted local/global ARAP; never guarantees injectivity."""
    if not 1 <= iterations <= MAX_ARAP_ITERATIONS or seed not in ("pca", "lscm"):
        raise ValueError("invalid bounded ARAP solver configuration")
    xyz = np.asarray(disk["points_xyz_mm"], dtype=np.float64)
    f = np.asarray(disk["faces"])
    old = np.asarray(prior_uv, dtype=np.float64)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or not np.isfinite(xyz).all():
        raise ValueError("invalid finite 3D millimetre points")
    if f.ndim != 2 or f.shape[1] != 3 or not np.issubdtype(f.dtype, np.integer):
        raise ValueError("invalid integer triangle face indices")
    if old.shape != (len(xyz), 2) or not np.isfinite(old).all():
        raise ValueError("missing finite source-linked LSCM initial coordinates")
    if np.any(f < 0) or np.any(f >= len(xyz)):
        raise ValueError("invalid triangle vertex IDs")
    first = int(disk["slit_pin_inner_id"])
    last = int(disk["slit_pin_outer_id"])
    if not 0 <= first < len(xyz) or not 0 <= last < len(xyz) or first == last:
        raise ValueError("invalid independent source pin identities")
    uv, chord = _initial_uv(xyz, old, first, last, seed)
    gx, gy, area, lap = _gradient_operators(xyz, f.astype(np.int64))
    fixed = np.zeros(len(xyz), dtype=bool)
    fixed[[first, last]] = True
    free = ~fixed
    lu = splu(lap[free][:, free].tocsc())
    coupled = lap[free][:, fixed]
    pin_uv = np.array([[0.0, 0.0], [chord, 0.0]])
    uv[fixed] = pin_uv
    max_move = None
    for _ in range(iterations):
        updated = _global_step(gx, gy, area, lu, free, coupled, pin_uv, uv)
        if not np.isfinite(updated).all():
            raise ValueError("nonfinite ARAP research solution")
        max_move = float(np.linalg.norm(updated - uv, axis=1).max())
        uv = updated
    return uv, {
        "method": "two_pin_area_weighted_local_global_ARAP_research",
        "seed": seed,
        "iterations_executed": iterations,
        "last_iteration_max_vertex_shift_mm": max_move,
        "pin_distance_policy": "3d_euclidean_chord_not_mesh_path_length",
        "source_pin_chord_3d_mm": chord,
        "original_3d_geometry_modified": False,
        "injectivity_or_material_feasibility_proved": False,
        "fabric_cutting_approved": False,
    }


def best_similarity_scale(points_xyz, faces, planar):
    """Diagnostic least-squares uniform UV scale from every unique mesh edge."""
    xyz = np.asarray(points_xyz, dtype=np.float64)
    tri = np.asarray(faces)
    uv = np.asarray(planar, dtype=np.float64)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or uv.shape != (len(xyz), 2):
        raise ValueError("incompatible 3D and 2D surface arrays")
    if tri.ndim != 2 or tri.shape[1] != 3 or not np.issubdtype(tri.dtype, np.integer):
        raise ValueError("expected integer source triangles")
    if not np.isfinite(xyz).all() or not np.isfinite(uv).all():
        raise ValueError("nonfinite source coordinates")
    if not len(tri) or np.any(tri < 0) or np.any(tri >= len(xyz)):
        raise ValueError("invalid triangle source topology")
    e = np.concatenate((tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]))
    edge = np.unique(np.sort(e, axis=1), axis=0)
    original = np.linalg.norm(xyz[edge[:, 0]] - xyz[edge[:, 1]], axis=1)
    flat = np.linalg.norm(uv[edge[:, 0]] - uv[edge[:, 1]], axis=1)
    if np.any(original <= 1e-10) or not np.any(flat > 1e-10):
        raise ValueError("degenerate original edge or entire UV candidate")
    scale = float(np.dot(original, flat) / np.dot(flat, flat))
    normalized = np.abs(scale * flat / original - 1)
    raw = np.abs(flat / original - 1)
    return {
        "unique_source_edges": len(edge),
        "best_fit_uniform_similarity_scale": scale,
        "unscaled_relative_edge_error_p95": float(np.quantile(raw, 0.95)),
        "rescaled_relative_edge_error_p95": float(np.quantile(normalized, 0.95)),
        "rescaled_relative_edge_error_mean": float(np.mean(normalized)),
        "scaling_does_not_resolve_2d_overlaps_or_folds": True,
        "approval_after_rescaling": False,
    }
