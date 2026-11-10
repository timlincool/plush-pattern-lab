"""True horizontal contours from original Stage6 *triangle/plane intersections*.

This uses source triangle edges and real millimetre interpolation. It does not
assume a single XY envelope loop and is not an approved fabric cutting line.
"""

from __future__ import annotations

import hashlib

import numpy as np
from shapely.geometry import Polygon

RESEARCH_Z_PLANES_MM = (60, 100, 115, 125, 130, 135, 140, 145, 155, 180, 205, 230, 245)


def _source_mesh(points, faces, z):
    xyz = np.asarray(points, dtype=np.float64)
    tri = np.asarray(faces)
    if (
        xyz.ndim != 2
        or xyz.shape[1] != 3
        or not 12 <= len(xyz) <= 300000
        or not np.isfinite(xyz).all()
    ):
        raise ValueError("true source surface must contain finite millimetre XYZ")
    if (
        tri.ndim != 2
        or tri.shape[1] != 3
        or not 4 <= len(tri) <= 600000
        or not np.issubdtype(tri.dtype, np.integer)
        or np.any(tri < 0)
        or np.any(tri >= len(xyz))
    ):
        raise ValueError("invalid original source triangle vertex IDs")
    if not np.isfinite(z) or not 0 < z < 1000:
        raise ValueError("invalid real section height in millimetres")
    if np.min(np.abs(xyz[:, 2] - z)) <= 1e-6:
        raise ValueError("horizontal plane runs through original vertex; choose another z")
    return xyz, tri.astype(np.int64)


def _true_intersection_graph(xyz, tri, z):
    above = xyz[:, 2] > z
    level = np.count_nonzero(above[tri], axis=1)
    triangles = tri[(level > 0) & (level < 3)]
    if not len(triangles):
        raise ValueError("source mesh has no triangle-plane intersection")
    crossed, owning_face = [], []
    for one, two in ((0, 1), (1, 2), (2, 0)):
        edges = triangles[:, (one, two)]
        mask = above[edges[:, 0]] != above[edges[:, 1]]
        crossed.append(np.sort(edges[mask], axis=1))
        owning_face.append(np.flatnonzero(mask))
    actual_edges, face_index = np.vstack(crossed), np.concatenate(owning_face)
    unique, inverse = np.unique(actual_edges, axis=0, return_inverse=True)
    ordered = np.argsort(face_index, kind="stable")
    sorted_faces, sorted_edges = face_index[ordered], inverse[ordered]
    if (
        len(sorted_faces) != 2 * len(triangles)
        or not np.array_equal(sorted_faces, np.repeat(np.arange(len(triangles)), 2))
    ):
        raise ValueError("degenerate source triangle-plane crossing")
    joined = sorted_edges.reshape(-1, 2)
    degree = np.bincount(joined.ravel(), minlength=len(unique))
    if np.any(degree != 2) or np.any(joined[:, 0] == joined[:, 1]):
        raise ValueError("open, branched or nonmanifold source plane contour")
    low, high = xyz[unique[:, 0]], xyz[unique[:, 1]]
    ratio = (z - low[:, 2]) / (high[:, 2] - low[:, 2])
    interpolated = low + (high - low) * ratio[:, None]
    return unique, interpolated[:, :2], joined


def _source_loops(source_edges, xy, pairs):
    adjacent = [[] for _ in range(len(source_edges))]
    for one, two in pairs:
        adjacent[one].append(int(two))
        adjacent[two].append(int(one))
    if any(len(row) != 2 for row in adjacent):
        raise ValueError("true section must contain only degree-2 loops")
    remaining = set(range(len(source_edges)))
    result = []
    while remaining:
        start, prior, current = min(remaining), -1, min(remaining)
        loop = []
        while current in remaining:
            remaining.remove(current)
            loop.append(current)
            neighbors = [item for item in adjacent[current] if item != prior]
            if prior != -1 and len(neighbors) != 1:
                raise ValueError("source intersection has an ambiguous vertex")
            prior, current = current, neighbors[0]
        if current != start:
            raise ValueError("source intersection did not close at original edge")
        vertices = xy[loop]
        poly = Polygon(vertices)
        if not poly.is_valid or poly.area <= 1e-8:
            raise ValueError("non-simple or zero-area real source contour")
        digest = hashlib.sha256(
            np.asarray(source_edges[loop], dtype="<i8").tobytes()
            + np.asarray(vertices, dtype="<f8").tobytes()
        ).hexdigest()
        result.append(
            {
                "crossed_original_mesh_vertex_id_edge_pairs": source_edges[loop].tolist(),
                "true_interpolated_contour_xy_mm": vertices.tolist(),
                "crossed_original_source_edges": len(loop),
                "closed_loop": True,
                "simple_polygon": True,
                "contour_perimeter_mm": float(poly.length),
                "enclosed_plane_area_mm2": float(poly.area),
                "contour_centroid_xy_mm": list(poly.centroid.coords[0]),
                "contour_bounds_xy_mm": [
                    vertices.min(axis=0).tolist(),
                    vertices.max(axis=0).tolist(),
                ],
                "original_source_edge_and_interpolated_xy_sha256": digest,
            }
        )
    return sorted(
        result,
        key=lambda item: (
            -item["contour_perimeter_mm"],
            item["contour_centroid_xy_mm"][0],
        ),
    )


def intersect_real_source_at_z(points, faces, z_mm):
    """Reconstruct every closed original-triangle intersection loop at z in mm."""
    xyz, tri = _source_mesh(points, faces, z_mm)
    original, xy, pairs = _true_intersection_graph(xyz, tri, z_mm)
    loops = _source_loops(original, xy, pairs)
    return {
        "plane_z_mm": z_mm,
        "true_source_plane_intersection_component_count": len(loops),
        "total_original_source_triangle_plane_segments": len(pairs),
        "source_contours": loops,
        "not_a_source_unwrapped_2d_fabric_stitch": True,
    }


def real_source_section_series(points, faces, z_levels=RESEARCH_Z_PLANES_MM):
    if len(z_levels) != len(set(z_levels)) or not z_levels:
        raise ValueError("source contour research planes must be unique")
    slices = [intersect_real_source_at_z(points, faces, z) for z in z_levels]
    return {
        "schema": "stage6-true-triangle-plane-component-loops-v1",
        "source_geometry_type": "actual_source_triangle_edges_intersected_exactly",
        "source_mesh_has_not_been_cut_or_modified": True,
        "single_rectangle_envelope_per_slice_not_assumed": True,
        "sections": slices,
        "not_an_original_3d_sculpt_fabric_pattern": True,
        "factory_cutting_approved": 0,
    }
