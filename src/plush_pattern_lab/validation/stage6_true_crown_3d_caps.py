"""Research-only genuine Stage6 upper crown 3D source caps, using MIT trimesh.

A horizontal source cut is a 3D geometric seam candidate, not a fabric rest
pattern, source-approved hidden seam, or a manufacturable assembly.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict

import numpy as np
from scipy.spatial import cKDTree

from plush_pattern_lab.validation.stage6_true_source_contours import (
    intersect_real_source_at_z,
)

SCHEMA = "stage6-genuine-source-z230-three-open-caps-v1"
CUT_Z_MM = 230.0
SOURCE_PLY_SHA256 = "5b52e3fd09c83b19c5b9d95d6d8d859a147ff4deef90f1518f868d2e82e3a2dd"
SOURCE_BLEND_SHA256 = "38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a"
WITNESS_SHA256 = "b561770a6cfeaea33abedc11bfb3992b2fe80b4bf83d10a66459682938af6571"
WITNESS_SCHEMA = "stage6-original-source-z230-crown-three-contour-review-witness-v1"
COMPONENTS = ("central_crown", "left_high_protrusion", "right_high_protrusion")
EXPECTED_BORDERS = (189, 113, 112)
EXPECTED_TOP_FACES = (1663, 1849, 1906)
EXPECTED_LOWER_FACES = 111978
EXPECTED_SOURCE_VERTEX_COUNT = 59306
EXPECTED_SOURCE_TRIANGLE_COUNT = 116568


def validate_witness(source_points, source_faces, witness, witness_raw):
    """Match complete original-edge IDs against the real triangle cut at 230 mm."""
    if (
        hashlib.sha256(witness_raw).hexdigest() != WITNESS_SHA256
        or witness.get("schema") != WITNESS_SCHEMA
        or witness.get("original_public_blend_sha256") != SOURCE_BLEND_SHA256
        or witness.get("source_section_z_mm") != CUT_Z_MM
        or witness.get("source_component_count") != 3
        or witness.get("factory_patterns_approved") != 0
    ):
        raise ValueError("untrusted source-locked original crown witness")
    actual = intersect_real_source_at_z(source_points, source_faces, CUT_Z_MM)
    original = actual["source_contours"]
    supplied = witness["source_contours"]
    if len(original) != 3 or len(supplied) != 3:
        raise ValueError("original crown must contain exactly three loops")
    for row, old, count in zip(original, supplied, EXPECTED_BORDERS):
        if (
            row["crossed_original_source_edges"] != count
            or row["original_source_edge_and_interpolated_xy_sha256"]
            != old.get("original_source_edge_and_interpolated_xy_sha256")
            or row["crossed_original_mesh_vertex_id_edge_pairs"]
            != old.get("crossed_original_mesh_vertex_id_edge_pairs")
        ):
            raise ValueError("crown source witness and triangle crossing changed")
    return original


def boundary_edges(mesh):
    all_edges, occurrences = np.unique(mesh.edges_sorted, axis=0, return_counts=True)
    if np.any(occurrences > 2):
        raise ValueError("source-clipped surface contains nonmanifold edges")
    boundary = all_edges[occurrences == 1]
    if not len(boundary):
        raise ValueError("clipped source surface has no cut seam")
    return boundary, all_edges


def _closed_ring_sizes(edges):
    adjacency = defaultdict(set)
    for u, v in edges:
        a, b = int(u), int(v)
        adjacency[a].add(b)
        adjacency[b].add(a)
    if any(len(near) != 2 for near in adjacency.values()):
        raise ValueError("source clip boundary is open, branched or degenerate")
    remaining = set(adjacency)
    lengths = []
    while remaining:
        stack = [min(remaining)]
        visited = set()
        while stack:
            here = stack.pop()
            if here in visited:
                continue
            visited.add(here)
            stack.extend(adjacency[here] - visited)
        if len(visited) < 3:
            raise ValueError("source boundary ring too short")
        remaining.difference_update(visited)
        lengths.append(len(visited))
    return sorted(lengths)


def _match_rim_to_original(vertices, rim, original):
    """Each cut node must uniquely match one real source edge interpolation."""
    source = np.asarray(original["true_interpolated_contour_xy_mm"], dtype=float)
    candidates = np.unique(rim)
    if len(candidates) != len(source):
        raise ValueError("source ring vertex count differs after external slicing")
    xy = vertices[candidates, :2]
    dist, correspondence = cKDTree(source).query(xy)
    if max(dist) > 1e-6 or len(set(correspondence.tolist())) != len(source):
        raise ValueError("source original-edge XY identities lost in clipped mesh")
    original_order = np.empty(len(source), dtype=np.int64)
    original_order[correspondence] = candidates
    actual_edges = {tuple(sorted((int(a), int(b)))) for a, b in rim}
    expected_edges = {
        tuple(sorted((int(original_order[i]), int(original_order[(i + 1) % len(source)]))))
        for i in range(len(source))
    }
    if actual_edges != expected_edges:
        raise ValueError("original-cut rim is not a single source-ordered closed ring")
    ordered_xyz = vertices[original_order]
    length = np.linalg.norm(
        ordered_xyz - np.roll(ordered_xyz, -1, axis=0), axis=1
    ).sum()
    if abs(length - original["contour_perimeter_mm"]) > 1e-6:
        raise ValueError("real Stage6 three-dimensional seam length changed")
    return original_order.tolist(), float(length)


def _audit_lower_half(lower, originals):
    rim, unique_edges = boundary_edges(lower)
    on_plane = np.all(np.abs(lower.vertices[rim, 2] - CUT_Z_MM) < 1e-7, axis=1)
    if (
        len(rim) != 2462
        or int(on_plane.sum()) != sum(EXPECTED_BORDERS)
        or len(lower.faces) != EXPECTED_LOWER_FACES
        or len(lower.split(only_watertight=False)) != 1
        or len(lower.vertices) - len(unique_edges) + len(lower.faces) != -5
        or _closed_ring_sizes(rim[~on_plane]) != [512] * 4
        or _closed_ring_sizes(rim[on_plane]) != sorted(EXPECTED_BORDERS)
    ):
        raise ValueError("lower core lost four hoof openings or head cut identity")
    lower_rims = []
    for original in originals:
        subset = rim[on_plane]
        xy = lower.vertices[subset[:, 0], :2]
        reference = np.asarray(original["true_interpolated_contour_xy_mm"])
        neighbors = cKDTree(reference).query(xy)[0] < 1e-6
        matched = subset[neighbors]
        ordered, length = _match_rim_to_original(lower.vertices, matched, original)
        lower_rims.append(
            {
                "source_witness_order_local_vertex_ids": ordered,
                "real_3d_stitch_perimeter_mm": length,
            }
        )
    return {
        "source_triangle_count_after_cut": len(lower.faces),
        "connected_surface_components": 1,
        "source_Euler_characteristic": -5,
        "boundary_ring_lengths_edges_sorted": _closed_ring_sizes(rim),
        "original_four_hoof_rings_exactly_512_edges_each": True,
        "lower_head_cut_rims": lower_rims,
        "not_a_flattened_or_sewable_lower_gore": True,
    }


def build_three_real_source_caps(
    source, source_faces, witness, witness_raw, trimesh_module
):
    """Use third-party mesh plane clip, not a new UV or surface solver."""
    if (
        len(source) != EXPECTED_SOURCE_VERTEX_COUNT
        or len(source_faces) != EXPECTED_SOURCE_TRIANGLE_COUNT
        or trimesh_module.__version__ != "4.11.1"
    ):
        raise ValueError("only original Stage6 proxy and pinned trimesh supported")
    original = validate_witness(source, source_faces, witness, witness_raw)
    mesh = trimesh_module.Trimesh(vertices=source, faces=source_faces, process=False)
    upper = trimesh_module.intersections.slice_mesh_plane(
        mesh, plane_normal=[0, 0, 1], plane_origin=[0, 0, CUT_Z_MM], cap=False
    )
    lower = trimesh_module.intersections.slice_mesh_plane(
        mesh, plane_normal=[0, 0, -1], plane_origin=[0, 0, CUT_Z_MM], cap=False
    )
    # Third-party slicing emits duplicated corners per intersected source triangle.
    # Weld identical interpolated coordinates; do not remesh original source.
    upper.merge_vertices(digits_vertex=12)
    lower.merge_vertices(digits_vertex=12)
    regions = upper.split(only_watertight=False)
    if len(regions) != 3 or sum(len(r.faces) for r in regions) != len(upper.faces):
        raise ValueError("source Stage6 above 230 is not exactly three caps")
    caps = []
    for original_row, label, n_faces in zip(original, COMPONENTS, EXPECTED_TOP_FACES):
        centers = np.asarray(original_row["true_interpolated_contour_xy_mm"])
        want = centers.mean(axis=0)
        region = min(
            regions,
            key=lambda x: np.linalg.norm(x.vertices[:, :2].mean(axis=0) - want),
        )
        regions.remove(region)
        rim, unique = boundary_edges(region)
        if (
            len(rim) != original_row["crossed_original_source_edges"]
            or len(region.faces) != n_faces
            or len(region.vertices) - len(unique) + len(region.faces) != 1
            or not region.is_winding_consistent
            or _closed_ring_sizes(rim) != [len(rim)]
            or np.max(np.abs(region.vertices[rim, 2] - CUT_Z_MM)) > 1e-7
        ):
            raise ValueError("top cap not an original source-connected open disk")
        ordered, rim_length = _match_rim_to_original(region.vertices, rim, original_row)
        caps.append(
            {
                "id": label,
                "source_original_rim_edge_ids_sha256": original_row[
                    "original_source_edge_and_interpolated_xy_sha256"
                ],
                "source_original_rim_edge_vertex_pairs": original_row[
                    "crossed_original_mesh_vertex_id_edge_pairs"
                ],
                "original_rim_vertex_ids_in_cap_local_order": ordered,
                "source_3d_rim_perimeter_mm": rim_length,
                "source_topological_Euler": 1,
                "source_boundary_edges": len(rim),
                "vertices_xyz_mm": region.vertices.tolist(),
                "triangles_local_vertex_indices": region.faces.tolist(),
                "upper_real_source_3d_mesh_not_original_flat_fabric": True,
            }
        )
    bottom = _audit_lower_half(lower, original)
    for cap, paired in zip(caps, bottom["lower_head_cut_rims"]):
        if abs(
            cap["source_3d_rim_perimeter_mm"]
            - paired["real_3d_stitch_perimeter_mm"]
        ) > 1e-6:
            raise ValueError("source 3D upper/lower netline length mismatch")
    return {
        "schema": SCHEMA,
        "original_public_stage6_blend_sha256": SOURCE_BLEND_SHA256,
        "source_proxy_ply_sha256": SOURCE_PLY_SHA256,
        "source_witness_file_sha256": WITNESS_SHA256,
        "open_source_clipper": "trimesh 4.11.1 MIT slice_mesh_plane",
        "source_height_mm": CUT_Z_MM,
        "upper_exact_original_source_crown_components": len(caps),
        "source_original_stitch_edge_ids_preserved": True,
        "upper_to_lower_source_netline_matched_at_1e_6_mm": True,
        "upper_caps": caps,
        "lower_single_original_surface": bottom,
        "source_proxy_not_full_high_density_466278_face_mesh": True,
        "geometry_source_cut_not_2d_flattening": True,
        "visual_seam_hidden_by_cloud_or_ear_not_verified": True,
        "industrial_cutting_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
    }
