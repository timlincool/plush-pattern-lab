"""Independent intrinsic Gaussian-curvature screen for a slit fabric panel.

Triangle corner angles are invariant under rigid bending. Nonzero interior
angle deficit forbids an EXACT length-preserving flat net, but does not
specify a fabric tolerance, dart location, or production approval.
"""

from __future__ import annotations

import numpy as np


def _validated_disk(disk):
    points = np.asarray(disk["points_xyz_mm"], dtype=np.float64)
    faces = np.asarray(disk["faces"])
    boundary = np.asarray(disk["boundary_edges"])
    source = np.asarray(disk["source_vertex_ids"])
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
        raise ValueError("expected finite Nx3 millimetre points")
    if (
        faces.ndim != 2
        or faces.shape[1] != 3
        or not np.issubdtype(faces.dtype, np.integer)
    ):
        raise ValueError("expected integer Mx3 triangles")
    if (
        boundary.ndim != 2
        or boundary.shape[1] != 2
        or not np.issubdtype(boundary.dtype, np.integer)
    ):
        raise ValueError("expected integer Kx2 boundary edges")
    if len(faces) == 0 or len(boundary) == 0 or len(source) != len(points):
        raise ValueError("empty or inconsistent disk input")
    if not np.issubdtype(source.dtype, np.integer):
        raise ValueError("expected integer original source vertex IDs")
    if np.any(faces < 0) or np.any(faces >= len(points)):
        raise ValueError("triangle references an invalid vertex")
    if np.any(boundary < 0) or np.any(boundary >= len(points)):
        raise ValueError("boundary references an invalid vertex")
    if np.any(np.diff(np.sort(faces, axis=1), axis=1) == 0):
        raise ValueError("triangle has repeated vertex IDs")
    edges = np.sort(
        np.concatenate((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]])),
        axis=1,
    )
    unique, counts = np.unique(edges, axis=0, return_counts=True)
    supplied = np.unique(np.sort(boundary, axis=1), axis=0)
    if np.any(counts > 2) or len(supplied) != len(boundary):
        raise ValueError("nonmanifold or duplicated boundary")
    if not np.array_equal(unique[counts == 1], supplied):
        raise ValueError("disk boundary does not match triangle incidence")
    return points, faces.astype(np.int64), boundary.astype(np.int64), source


def _triangle_angles(points, faces):
    xyz = points[faces]
    angles = np.zeros((len(faces), 3), dtype=np.float64)
    for corner in range(3):
        first = xyz[:, (corner + 1) % 3] - xyz[:, corner]
        second = xyz[:, (corner + 2) % 3] - xyz[:, corner]
        numerator = np.linalg.norm(np.cross(first, second), axis=1)
        denominator = np.einsum("ij,ij->i", first, second)
        if np.any(numerator <= 1e-10):
            raise ValueError("collapsed source 3D triangle")
        angles[:, corner] = np.arctan2(numerator, denominator)
    return angles


def audit_intrinsic_curvature(disk, *, max_hotspots=12, threshold_degrees=3.0):
    """Report true interior angle deficits; ignore all cut/boundary vertices."""
    if not 1 <= max_hotspots <= 50 or not 0 < threshold_degrees <= 180:
        raise ValueError("invalid research curvature reporting limits")
    points, faces, border, sources = _validated_disk(disk)
    angles = _triangle_angles(points, faces)
    sums = np.zeros(len(points), dtype=np.float64)
    for corner in range(3):
        np.add.at(sums, faces[:, corner], angles[:, corner])
    is_boundary = np.zeros(len(points), dtype=bool)
    is_boundary[border.ravel()] = True
    interior = np.flatnonzero(~is_boundary)
    if not len(interior) or np.any(sums[interior] == 0):
        raise ValueError("no valid interior angle-deficit samples")
    defect = 2 * np.pi - sums[interior]
    degrees = np.degrees(defect)
    hottest = np.argsort(-np.abs(degrees), kind="stable")[:max_hotspots]
    witnesses = [
        {
            "source_vertex_id": int(sources[interior[index]]),
            "disk_vertex_id": int(interior[index]),
            "signed_defect_degrees": float(degrees[index]),
            "xyz_mm": points[interior[index]].round(4).tolist(),
        }
        for index in hottest
    ]
    return {
        "schema": "stage6-intrinsic-curvature-disk-screen-v1",
        "method": "signed_2pi_minus_sum_of_intrinsic_triangle_corner_angles",
        "source_mesh_vertices": len(points),
        "triangle_faces": len(faces),
        "excluded_cut_and_outer_boundary_vertices": int(is_boundary.sum()),
        "interior_vertex_count": len(interior),
        "abs_defect_degrees_p95": float(np.quantile(np.abs(degrees), 0.95)),
        "max_abs_defect_degrees": float(np.abs(degrees).max()),
        "positive_defect_over_threshold": int((degrees > threshold_degrees).sum()),
        "negative_defect_below_minus_threshold": int((degrees < -threshold_degrees).sum()),
        "screen_threshold_degrees": threshold_degrees,
        "positive_defect_total_radians": float(defect[defect > 0].sum()),
        "negative_defect_total_radians": float(defect[defect < 0].sum()),
        "top_abs_defect_hotspots": witnesses,
        "exact_isometry_possible_with_uncut_interior": bool(np.max(np.abs(degrees)) <= 1e-3),
        "not_a_proof_of_required_fabric_dart_count": True,
        "fabric_properties_or_manufacturing_approved": False,
    }
