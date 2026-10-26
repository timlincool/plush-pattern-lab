"""Independent geometry-quality audit for a sewn cloth trial (numerical evidence only).

Checks something seam-gap-only tests miss: global target mismatch, local
stretch/compression, and triangle-normal reversals. Units are metres in arrays;
reported lengths are mm. Never a material or manufacturability certificate.
"""

from __future__ import annotations

import numpy as np


def _points(data, width, name):
    a = np.asarray(data, dtype=np.float64)
    if a.ndim != 2 or a.shape[1] != width or not np.all(np.isfinite(a)):
        raise ValueError(f"{name}: expected finite Nx{width} array")
    return a


def _indexes(data, width, count, name):
    a = np.asarray(data)
    if a.ndim != 2 or a.shape[1] != width or not np.issubdtype(a.dtype, np.integer):
        raise ValueError(f"{name}: expected integer Nx{width}")
    if a.size == 0 or (a < 0).any() or (a >= count).any():
        raise ValueError(f"{name}: empty or out-of-range indices")
    return a.astype(np.int64, copy=False)


def rigid_alignment(points, reference):
    """Proper rigid Kabsch alignment, no scale/shear; row-vector convention."""
    if len(points) != len(reference) or len(points) < 4:
        raise ValueError("Correspondence count mismatch")
    x = points - points.mean(axis=0)
    y = reference - reference.mean(axis=0)
    u, _, vt = np.linalg.svd(x.T @ y)
    sign = np.sign(np.linalg.det(u @ vt))
    rot = u @ np.diag([1.0, 1.0, sign]) @ vt
    return x @ rot + reference.mean(axis=0)


def nearest_vertex_distances(points, target, block=128):
    """Memory-bounded exact vertex-to-vertex nearest distances, NumPy only.

    O(N*M) work is intentional for small (<=5000) research meshes. Raise
    before accidental million-fibre use; use a spatial index for large meshes.
    """
    if len(points) > 5000 or len(target) > 5000 or len(points) == 0 or len(target) == 0:
        raise ValueError("Nearest-distance research input must be <=5000 vertices")
    norms = np.einsum("ij,ij->i", target, target)
    answer = np.empty(len(points), dtype=np.float64)
    for start in range(0, len(points), block):
        part = points[start : start + block]
        dist2 = (
            np.einsum("ij,ij->i", part, part)[:, None]
            + norms[None, :]
            - 2.0 * (part @ target.T)
        )
        # Rounding can make exact-zero squared distances slightly negative.
        np.maximum(dist2, 0.0, out=dist2)
        answer[start : start + len(part)] = np.sqrt(dist2.min(axis=1))
    return answer


def evaluate(vertices, flat_rest, faces, sewing_pairs, target, initial_vertices):
    """All arrays share stable vertex identities, including duplicated seam vertices.

    flat_rest: 2D *natural* coordinates, not pre-draped 3D positions.
    target: synthetic per-vertex reference. A user-supplied real shape would
    require registration and target sampling; do not claim this score for one.
    """
    xyz = _points(vertices, 3, "vertices")
    rest = _points(flat_rest, 2, "rest")
    goal = _points(target, 3, "target")
    initial = _points(initial_vertices, 3, "initial")
    n = len(xyz)
    if n < 8 or len(rest) != n or len(goal) != n or len(initial) != n:
        raise ValueError("Vertex identity/count mismatch")
    quad = _indexes(faces, 4, n, "faces")
    pairs = _indexes(sewing_pairs, 2, n, "sewing_pairs")
    if np.any(pairs[:, 0] == pairs[:, 1]):
        raise ValueError("Sewing pair connects a vertex to itself")
    tri = np.concatenate((quad[:, (0, 1, 2)], quad[:, (0, 2, 3)]), axis=0)
    flat_edges = np.stack(
        (rest[tri[:, 1]] - rest[tri[:, 0]], rest[tri[:, 2]] - rest[tri[:, 0]]), axis=-1
    )
    det = np.linalg.det(flat_edges)
    if np.any(np.abs(det) < 1e-13):
        raise ValueError("Degenerate/zero-area 2D rest triangle")
    geom_edges = np.stack(
        (xyz[tri[:, 1]] - xyz[tri[:, 0]], xyz[tri[:, 2]] - xyz[tri[:, 0]]), axis=-1
    )
    deformation = geom_edges @ np.linalg.inv(flat_edges)
    singular = np.linalg.svd(deformation, compute_uv=False)
    if not np.all(np.isfinite(singular)):
        raise ValueError("Non-finite deformation gradient")
    abs_strain = np.abs(singular - 1.0).ravel()
    rest_area = np.sum(np.abs(det) * 0.5)
    normals = np.cross(geom_edges[:, :, 0], geom_edges[:, :, 1])
    original_normals = np.cross(
        initial[tri[:, 1]] - initial[tri[:, 0]], initial[tri[:, 2]] - initial[tri[:, 0]]
    )
    oriented = np.einsum("ij,ij->i", normals, original_normals)
    face_area = np.linalg.norm(normals, axis=1) * 0.5
    if not np.all(np.isfinite(face_area)):
        raise ValueError("Non-finite 3D face area")
    # Reversal relative to original orientation is a fold warning, NOT a proof
    # of self-intersection. A zero-area triangle is tracked separately.
    reverse_indices = np.flatnonzero(oriented < -1e-15)
    reverse_count = int(len(reverse_indices))
    collapsed_count = int(np.count_nonzero(face_area < 1e-12))
    # Actionable evidence: identify where the fold warnings occur rather than
    # presenting a bare count. Indices use the two-triangle-per-quad layout.
    # Identify a separate failure mode at each tip of a gore. A singular
    # point where many panels meet needs explicit cap design; do not erase
    # these failures from the overall count or call the shell watertight.
    longitudinal = rest[tri[:, (0, 1, 2)], 1].mean(axis=1)
    span = float(np.ptp(rest[:, 1]))
    if span <= 1e-8:
        raise ValueError("Flat rest longitudinal span collapsed")
    frac = (longitudinal - rest[:, 1].min()) / span
    end_flips = int(
        np.count_nonzero((oriented < -1e-15) & ((frac < 0.05) | (frac > 0.95)))
    )
    reverse_samples = [
        {
            "quad_face_index": int(t % len(quad)),
            "triangle_of_quad": int(t // len(quad)),
            "rest_longitudinal_center_mm": float(longitudinal[t] * 1000),
            "at_first_or_last_5pct": bool(frac[t] < 0.05 or frac[t] > 0.95),
        }
        for t in reverse_indices[:40]
    ]
    aligned = rigid_alignment(xyz, goal)
    correspondence = np.linalg.norm(aligned - goal, axis=1)
    unaligned = np.linalg.norm(xyz - goal, axis=1)
    # Symmetric *vertex-sampled* nearest-neighbour distance (not a true
    # continuous-surface Chamfer/Hausdorff bound; mesh density can bias it).
    d1 = nearest_vertex_distances(aligned, goal)
    d2 = nearest_vertex_distances(goal, aligned)
    gap = np.linalg.norm(xyz[pairs[:, 0]] - xyz[pairs[:, 1]], axis=1)
    return {
        "status": "NUMERICAL_DIAGNOSTICS_NOT_MANUFACTURING_APPROVAL",
        "seam": {
            "pair_count": len(pairs),
            "mean_gap_mm": float(gap.mean() * 1000),
            "p95_gap_mm": float(np.quantile(gap, 0.95) * 1000),
            "max_gap_mm": float(gap.max() * 1000),
        },
        "target_shape": {
            "reference_kind": "explicit_corresponding_synthetic_vertices",
            "rigid_aligned_correspondence_rms_mm": float(
                np.sqrt(np.mean(correspondence**2)) * 1000
            ),
            "rigid_aligned_correspondence_p95_mm": float(
                np.quantile(correspondence, 0.95) * 1000
            ),
            "unaligned_correspondence_rms_mm": float(
                np.sqrt(np.mean(unaligned**2)) * 1000
            ),
            "symmetric_vertex_chamfer_mean_mm": float((d1.mean() + d2.mean()) * 500),
        },
        "strain": {
            "triangle_count": len(tri),
            "max_abs_principal_strain": float(abs_strain.max()),
            "p95_abs_principal_strain": float(np.quantile(abs_strain, 0.95)),
            "area_3d_over_flat_rest": float(face_area.sum() / rest_area),
            "orientation_reversed_vs_initial": reverse_count,
            "endpoint_region_flips": end_flips,
            "interior_region_flips": reverse_count - end_flips,
            "endpoint_region_definition": "first/last 5% of 2D rest longitudinal extent",
            "orientation_reversal_samples": reverse_samples,
            "near_zero_area_triangles": collapsed_count,
        },
        "limitations": [
            "Shape reference is analytic with known vertex correspondence",
            "Rigid alignment removes translation and rotation, not nonrigid errors",
            "Vertex Chamfer is sampling-sensitive, not a surface distance bound",
            "Normal reversal does not certify or rule out face intersections",
            "No physical material calibration, shell welding, collision or stuffing",
        ],
    }
