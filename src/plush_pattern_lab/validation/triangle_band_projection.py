"""Baseline: quantify distortion of a 3D triangular ring projected to its seam plane.

A measurement-only negative control. It is NOT optimized surface flattening.
"""

from __future__ import annotations

import numpy as np


def _inputs(vertices_mm, faces, seam_ids):
    vertices = np.asarray(vertices_mm, dtype=np.float64)
    triangles = np.asarray(faces)
    seam = np.asarray(seam_ids)
    if (
        vertices.ndim != 2
        or vertices.shape[1] != 3
        or not 3 <= len(vertices) <= 20000
        or not np.isfinite(vertices).all()
    ):
        raise ValueError("finite Nx3 millimetre vertices required")
    if (
        triangles.ndim != 2
        or triangles.shape[1] != 3
        or not np.issubdtype(triangles.dtype, np.integer)
        or not 1 <= len(triangles) <= 40000
    ):
        raise ValueError("triangle indices required")
    if (
        seam.ndim != 1
        or not np.issubdtype(seam.dtype, np.integer)
        or not 4 <= len(seam) < len(vertices)
        or len(np.unique(seam)) != len(seam)
    ):
        raise ValueError("unrepeated seam index ring required")
    if (triangles < 0).any() or (triangles >= len(vertices)).any():
        raise ValueError("triangle out-of-range vertex indices")
    if (seam < 0).any() or (seam >= len(vertices)).any():
        raise ValueError("seam out-of-range vertex indices")
    if np.any(triangles[:, 0] == triangles[:, 1]):
        raise ValueError("degenerate repeated triangle vertex")
    if np.any(triangles[:, 1] == triangles[:, 2]):
        raise ValueError("degenerate repeated triangle vertex")
    if np.any(triangles[:, 0] == triangles[:, 2]):
        raise ValueError("degenerate repeated triangle vertex")
    return vertices, triangles.astype(np.int64), seam.astype(np.int64)


def _seam_basis(vertices, seam):
    ring = vertices[seam]
    center = ring.mean(axis=0)
    _, singular, directions = np.linalg.svd(ring - center, full_matrices=False)
    if singular[1] <= 1e-9:
        raise ValueError("seam cannot define a stable planar reference")
    normal = directions[-1]
    residual = (ring - center) @ normal
    return center, directions[:2].T, float(np.max(np.abs(residual)))


def _triangle_metrics(vertices, projected, faces):
    original = vertices[faces]
    flat = projected[faces]
    diff3 = original[:, [1, 2, 0]] - original
    diff2 = flat[:, [1, 2, 0]] - flat
    length3 = np.linalg.norm(diff3, axis=2)
    length2 = np.linalg.norm(diff2, axis=2)
    zero3 = int(np.count_nonzero(length3 <= 1e-10))
    valid = length3 > 1e-10
    fractions = np.zeros_like(length3)
    fractions[valid] = np.abs(1 - length2[valid] / length3[valid])
    area3 = 0.5 * np.linalg.norm(
        np.cross(original[:, 1] - original[:, 0],
                 original[:, 2] - original[:, 0]),
        axis=1,
    )
    signed2 = 0.5 * (
        (flat[:, 1, 0] - flat[:, 0, 0])
        * (flat[:, 2, 1] - flat[:, 0, 1])
        - (flat[:, 1, 1] - flat[:, 0, 1])
        * (flat[:, 2, 0] - flat[:, 0, 0])
    )
    return fractions, area3, signed2, zero3


def projection_screen(vertices_mm, faces, seam_ids):
    """Report actual edge/area losses without changing the underlying mesh."""
    vertices, triangles, seam = _inputs(vertices_mm, faces, seam_ids)
    center, axes, seam_residual = _seam_basis(vertices, seam)
    uv = (vertices - center) @ axes
    frac, area3, area2, zero3 = _triangle_metrics(vertices, uv, triangles)
    ratio = np.abs(area2) / np.maximum(area3, 1e-10)
    return {
        "status": "TRIANGLE_SEAM_PLANE_PROJECTION_BASELINE_NOT_FLATTENED",
        "vertex_count": len(vertices),
        "triangle_count": len(triangles),
        "seam_vertices": len(seam),
        "seam_plane_max_deviation_mm": seam_residual,
        "edge_relative_loss": {
            "mean": float(frac.mean()),
            "p95": float(np.quantile(frac, 0.95)),
            "max": float(frac.max()),
        },
        "degenerate_3d_edges": zero3,
        "degenerate_3d_triangles": int(np.count_nonzero(area3 <= 1e-10)),
        "collapsed_projected_triangles": int(
            np.count_nonzero(ratio <= 1e-4)
        ),
        "projected_area_ratio": {
            "median": float(np.median(ratio)),
            "p05": float(np.quantile(ratio, 0.05)),
        },
        "projected_triangle_area_signs": {
            "positive": int(np.count_nonzero(area2 > 1e-10)),
            "negative": int(np.count_nonzero(area2 < -1e-10)),
            "near_zero": int(np.count_nonzero(np.abs(area2) <= 1e-10)),
        },
        "piece_rest_shape_solved": False,
        "fit_method": "best_fit_seam_plane_projection_not_intrinsic_unfolding",
        "limitations": [
            "No mesh cut/seam split; all 3D face vertices simply projected",
            "Projection distortion is not an optimized 2D fabric rest shape",
            "No material anisotropy, fill, seam allowance or fabrication evidence",
        ],
    }
