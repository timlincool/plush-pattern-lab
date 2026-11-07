"""Front source-shell depth versus historical surface14 facial marks.

Only pinned main-body PLY is tested. No clouds, fur, separate face meshes, or
factory stitch approval. World coordinates are millimetres.
"""

from __future__ import annotations

import numpy as np


def _source_arrays(points, faces):
    xyz = np.asarray(points, dtype=np.float64)
    tri = np.asarray(faces)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or not np.isfinite(xyz).all():
        raise ValueError("expected finite original Stage6 3D millimetre source")
    if tri.ndim != 2 or tri.shape[1] != 3 or not np.issubdtype(tri.dtype, np.integer):
        raise ValueError("expected original triangle vertex IDs")
    if np.any(tri < 0) or np.any(tri >= len(xyz)):
        raise ValueError("source face references invalid vertex")
    return xyz, tri.astype(np.int64)


def front_first_hit_y(source_tris, point):
    """Intersect orthographic -Y ray at X/Z with source triangles."""
    x, z = point[0], point[2]
    projected = source_tris[:, :, [0, 2]]
    bbox_min = projected.min(axis=1)
    bbox_max = projected.max(axis=1)
    valid_bbox = (
        (bbox_min[:, 0] <= x + 1e-7)
        & (bbox_max[:, 0] >= x - 1e-7)
        & (bbox_min[:, 1] <= z + 1e-7)
        & (bbox_max[:, 1] >= z - 1e-7)
    )
    triangles = source_tris[valid_bbox]
    if not len(triangles):
        return None
    a, b, c = [triangles[:, j, :][:, [0, 2]] for j in range(3)]
    denom = (b[:, 1] - c[:, 1]) * (a[:, 0] - c[:, 0]) + (
        c[:, 0] - b[:, 0]
    ) * (a[:, 1] - c[:, 1])
    nondegenerate = np.abs(denom) > 1e-10
    if not np.any(nondegenerate):
        return None
    a, b, c = a[nondegenerate], b[nondegenerate], c[nondegenerate]
    triangles, denom = triangles[nondegenerate], denom[nondegenerate]
    u = (
        (b[:, 1] - c[:, 1]) * (x - c[:, 0])
        + (c[:, 0] - b[:, 0]) * (z - c[:, 1])
    ) / denom
    v = (
        (c[:, 1] - a[:, 1]) * (x - c[:, 0])
        + (a[:, 0] - c[:, 0]) * (z - c[:, 1])
    ) / denom
    w = 1 - u - v
    inside = np.minimum(np.minimum(u, v), w) >= -1e-5
    if not np.any(inside):
        return None
    y = (
        u * triangles[:, 0, 1]
        + v * triangles[:, 1, 1]
        + w * triangles[:, 2, 1]
    )[inside]
    return float(y.min())


def _polyline_distance_xz(point_xz, polyline):
    path = np.asarray(polyline, dtype=float)
    if path.ndim != 2 or path.shape[1] != 2 or len(path) < 2:
        raise ValueError("invalid historical facial stroke polyline")
    edges = path[1:] - path[:-1]
    len2 = np.sum(edges * edges, axis=1)
    if np.any(len2 <= 0):
        raise ValueError("duplicate historic facial stroke points")
    t = np.clip(np.sum((point_xz - path[:-1]) * edges, axis=1) / len2, 0, 1)
    nearest = path[:-1] + t[:, None] * edges
    return float(np.linalg.norm(nearest - point_xz, axis=1).min())


def _historic_features_distance(point_xz, reference):
    names = ("y_nose_xz", "mouth_stem_xz", "mouth_left_xz", "mouth_right_xz")
    strokes = {
        name: _polyline_distance_xz(point_xz, reference[name]) for name in names
    }
    name = min(strokes, key=strokes.get)
    eyes = []
    for eye in reference["eyes"]:
        center = np.asarray(eye["center_xz"], dtype=float)
        radius = np.asarray(eye["ellipse_radii_xz"], dtype=float)
        if np.any(radius <= 0):
            raise ValueError("invalid historical eye radius")
        if np.linalg.norm((point_xz - center) / radius) <= 1:
            eyes.append(eye["name"])
    return name, strokes[name], eyes


def audit_front_paths(
    points, faces, path_rows, face_reference, *, near_mm=0.7, alert_mm=3.0
):
    """Report main-shell front-side path samples near historic nose/eyes/mouth."""
    xyz, tri = _source_arrays(points, faces)
    if face_reference.get("revision") != "surface14" or face_reference.get("units") != "mm":
        raise ValueError("historical front-face registration format mismatch")
    if not 0 < near_mm <= 2 or not 0 < alert_mm <= 10:
        raise ValueError("unbounded preliminary geometric screening distance")
    surface = xyz[tri]
    reports = []
    for seam in path_rows:
        ids = np.asarray(seam["original_source_vertex_ids"])
        if ids.ndim != 1 or len(ids) < 2 or not np.issubdtype(ids.dtype, np.integer):
            raise ValueError("invalid source-linked radial seam path IDs")
        if np.any(ids < 0) or np.any(ids >= len(xyz)) or len(np.unique(ids)) != len(ids):
            raise ValueError("source radial seam contains invalid or repeated vertices")
        pts = xyz[ids]
        measured = np.linalg.norm(np.diff(pts, axis=0), axis=1).sum()
        if abs(measured - seam["source_3d_length_mm"]) > 1e-3:
            raise ValueError("original radial seam 3D arc length drifted")
        visible, unknown, witnesses, gaps = [], 0, [], []
        for idx, p in zip(ids, pts):
            first = front_first_hit_y(surface, p)
            if first is None:
                unknown += 1
            gap = None if first is None else float(p[1] - first)
            gaps.append(gap)
            near = gap is not None and gap <= near_mm
            visible.append(near)
            name, distance, eyes = _historic_features_distance(p[[0, 2]], face_reference)
            if near and (distance <= alert_mm or eyes):
                witnesses.append(
                    {
                        "source_vertex_id": int(idx),
                        "xyz_mm": np.round(p, 4).tolist(),
                        "nearest_historic_stroke": name,
                        "projected_distance_mm": round(distance, 4),
                        "overlapping_historic_eye_ellipse": eyes,
                        "front_main_shell_depth_gap_mm": round(gap, 4),
                    }
                )
        reports.append(
            {
                "path_id": seam["path_id"],
                "source_vertex_ids": ids.tolist(),
                "source_points_xyz_mm": np.round(pts, 5).tolist(),
                "source_3d_seam_length_mm": float(measured),
                "front_main_shell_near_side_flags": visible,
                "front_main_shell_depth_gap_mm": gaps,
                "source_front_near_side_vertex_count": int(sum(visible)),
                "source_body_occluded_vertex_count": int(
                    len(ids) - sum(visible) - unknown
                ),
                "front_raycast_missing_hits": unknown,
                "historical_front_face_feature_alert_vertex_count": len(witnesses),
                "historic_face_proximity_witnesses": witnesses[:24],
                "design_revision_or_human_review_required": bool(witnesses),
            }
        )
    return {
        "schema": "stage6-pinned-source-front-shell-historical-face-v14-review-v1",
        "historic_registration_is_not_verified_stage6_facial_geometry": True,
        "view": "orthographic front from negative Y",
        "main_shell_front_ray_margin_mm": near_mm,
        "historic_face_proximity_buffer_mm": alert_mm,
        "cloud_fur_eye_mesh_occlusion_not_tested": True,
        "not_a_visibility_or_cutting_approval": True,
        "routes": reports,
        "factory_approved_cut_patterns": 0,
    }
