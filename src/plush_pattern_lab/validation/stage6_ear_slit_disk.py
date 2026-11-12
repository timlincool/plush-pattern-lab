"""Open a real Stage6 root annulus at three predeclared source-edge routes.

The cut duplicates ONLY topological vertex identities. Every triangle keeps
its immutable source Face ID and physical XYZ. No industrial cutting authority.
"""

from __future__ import annotations

import json
from hashlib import sha256

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

from plush_pattern_lab.validation.real_panel_slit import (
    _cut_vertex_fans,
    _edges,
    _validate_cut_disk,
)

SCHEMA = "stage6-original-ear-root-source-annulus-side-slit-v1"
SOURCE_SCHEMA = "stage6-real-original-source-nonhorizontal-ear-root-paired-3d-v1"
ROUTES = ("medial", "posterior", "lateral")
STUDIES = ("N15_sloped_source_band", "N17_sloped_source_band")
ALLOWANCE_MM = 6.0


def _canonical_sha(data):
    return sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        .encode("utf8")
    ).hexdigest()


def _paired_ring(source, keys, xyz):
    ordered = source["original_source_3d_ordered_ring_vertex_keys"]
    world = source["original_source_3d_ordered_ring_xyz_mm"]
    mapping = {key: index for index, key in enumerate(keys)}
    if len(mapping) != len(keys) or len(ordered) != len(world):
        raise ValueError("duplicate source root keys or mismatched seam vertices")
    try:
        indices = np.array([mapping[tuple(key)] for key in ordered], dtype=np.int64)
    except KeyError as e:
        raise ValueError("original 3D paired source edge missing from root patch") from e
    if (
        len(indices) < 12
        or len(np.unique(indices)) != len(indices)
        or np.max(np.abs(xyz[indices] - np.asarray(world))) > 1e-8
        or source["max_source_3d_pair_position_error_mm"] != 0
        or not source["two_source_3d_sides_exactly_same_with_opposite_face_winding"]
    ):
        raise ValueError("original source 3D seam identity/physical XYZ mismatch")
    return indices


def validate_original_root_patch(study, patch, reference):
    """Verify full derived original-triangle geometry against permanent SHA."""
    if (
        study["name"] not in STUDIES
        or patch["side"] not in ("left", "right")
        or study.get("true_3d_source_zone_component_counts")
        != {"below": 1, "root": 3, "above": 2}
        or patch["actual_original_source_root_band"]["euler_characteristic"] != 0
        or patch["actual_original_source_root_band"]["closed_boundary_loop_count"] != 2
        or patch["true_manufacturing_2d_pattern_generated"]
        or patch["fabric_and_assembly_approved"]
    ):
        raise ValueError("unapproved true source annulus research required")
    derived = patch["source_root_band_triangles_with_original_face_ids"]
    if _canonical_sha(derived) != reference["source_patch_canonical_sha256"]:
        raise ValueError("pinned original source 3D patch content SHA mismatch")
    xyz = np.asarray(derived["source_3d_xyz_mm"], dtype=np.float64)
    faces = np.asarray(derived["derived_triangle_local_vertex_ids"])
    source_faces = np.asarray(derived["each_derived_face_original_triangle_id"])
    if (
        xyz.ndim != 2
        or xyz.shape[1] != 3
        or not np.isfinite(xyz).all()
        or faces.ndim != 2
        or faces.shape[1] != 3
        or not np.issubdtype(faces.dtype, np.integer)
        or np.any(faces < 0)
        or np.any(faces >= len(xyz))
        or np.any(source_faces < 0)
        or np.any(source_faces >= 116568)
        or len(source_faces) != len(faces)
        or len(faces) != reference["source_patch_derived_triangles"]
    ):
        raise ValueError("invalid original-source derived triangle or Face ID")
    keys = [tuple(key) for key in derived["original_source_vertex_or_edge_plane_keys"]]
    if len(keys) != len(xyz):
        raise ValueError("original source vertex/edge provenance length changed")
    low = _paired_ring(patch["body_to_root_paired_3d_source_netline"], keys, xyz)
    high = _paired_ring(patch["root_to_upper_ear_paired_3d_source_netline"], keys, xyz)
    edges, inverse, counts, _, _ = _edges(faces, len(xyz))
    boundary = edges[counts == 1]
    if (
        np.any(counts > 2)
        or len(boundary) != len(low) + len(high)
        or len(xyz) - len(edges) + len(faces) != 0
        or len(np.unique(faces)) != len(xyz)
    ):
        raise ValueError("original source root is not exactly one closed annulus")
    if set(low) & set(high):
        raise ValueError("source upper and lower rings share vertices")
    return xyz, faces.astype(np.int64), keys, source_faces, low, high, edges, inverse, counts


def _source_route_anchors(xyz, low, high, side, direction):
    if direction not in ROUTES:
        raise ValueError("route was not preregistered")
    sign = 1 if side == "left" else -1
    if direction == "medial":
        loc, polarity = 0, sign
    elif direction == "lateral":
        loc, polarity = 0, -sign
    else:
        loc, polarity = 1, 1
    start = int(low[np.argmax(polarity * xyz[low, loc])])
    stop = int(high[np.argmax(polarity * xyz[high, loc])])
    if start == stop:
        raise ValueError("original upper and lower slit anchors coincide")
    return start, stop


def _shortest_source_side_route(xyz, edge_ids, counts, low, high, anchors):
    """Stay inside original annulus except one vertex on each boundary."""
    start, stop = anchors
    boundary = set(np.r_[low, high].tolist())
    allowed = np.ones(len(xyz), dtype=bool)
    allowed[list(boundary)] = False
    allowed[[start, stop]] = True
    inner = edge_ids[(counts == 2) & allowed[edge_ids].all(axis=1)]
    lengths = np.linalg.norm(xyz[inner[:, 1]] - xyz[inner[:, 0]], axis=1)
    graph = coo_matrix(
        (
            np.r_[lengths, lengths],
            (np.r_[inner[:, 0], inner[:, 1]], np.r_[inner[:, 1], inner[:, 0]]),
        ),
        shape=(len(xyz), len(xyz)),
    ).tocsr()
    distance, parent = dijkstra(graph, indices=start, return_predecessors=True)
    if not np.isfinite(distance[stop]):
        raise ValueError("original inner mesh cannot connect selected seam anchors")
    backwards = [stop]
    while backwards[-1] != start:
        before = int(parent[backwards[-1]])
        if before < 0 or len(backwards) > len(xyz):
            raise ValueError("broken source-mesh seam traceback")
        backwards.append(before)
    path = np.array(backwards[::-1], dtype=np.int64)
    if len(set(path.tolist())) != len(path) or set(path[1:-1]) & boundary:
        raise ValueError("source slit touches another original boundary vertex")
    return path, float(distance[stop])


def _triangle_area(xyz, faces):
    tri = xyz[faces]
    return float(
        (0.5 * np.linalg.norm(
            np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1
        )).sum()
    )


def create_source_slit_disk(study, patch, reference, direction):
    """Return a genuine topological disk with the original source Face IDs."""
    xyz, faces, keys, source_faces, low, high, edges, inverse, counts = (
        validate_original_root_patch(study, patch, reference)
    )
    start, stop = _source_route_anchors(xyz, low, high, patch["side"], direction)
    path, source_length = _shortest_source_side_route(
        xyz, edges, counts, low, high, (start, stop)
    )
    cut_faces, duplicates = _cut_vertex_fans(faces, edges, inverse, counts, path)
    if not np.array_equal(duplicates, path):
        raise ValueError("original-source seam duplication was not one-to-one")
    points = np.vstack((xyz, xyz[path]))
    source_ids = np.r_[np.arange(len(xyz)), path]
    original_boundary = int(np.count_nonzero(counts == 1))
    disk_border = _validate_cut_disk(
        cut_faces, len(points), original_boundary, len(path) - 1
    )
    original_area = _triangle_area(xyz, faces)
    disk_area = _triangle_area(points, cut_faces)
    if abs(original_area - disk_area) > 1e-7:
        raise ValueError("source 3D face area was lost during topological slit")
    if len(cut_faces) != len(source_faces):
        raise ValueError("original source triangle Face IDs not retained")
    return {
        "source_side": patch["side"],
        "source_study": study["name"],
        "slit_direction": direction,
        "source_patch_sha256": reference["source_patch_canonical_sha256"],
        "real_source_3d_slit_length_mm": source_length,
        "slit_original_local_vertex_ids": path.tolist(),
        "slit_original_vertex_or_edge_plane_keys": [list(keys[i]) for i in path],
        "source_xyz_mm": points,
        "disk_triangle_vertex_ids": cut_faces,
        "original_patch_vertex_id_per_disk_vertex": source_ids,
        "derived_source_face_id_per_disk_triangle": source_faces,
        "disk_boundary_edges": disk_border,
        "original_source_lower_boundary_vertex_ids": low,
        "original_source_upper_boundary_vertex_ids": high,
        "original_source_patch_area_mm2": original_area,
        "source_disk_area_mm2": disk_area,
        "original_source_face_count": len(faces),
        "slit_disk_face_count": len(cut_faces),
        "slit_disk_euler_characteristic": 1,
        "slit_disk_single_boundary": True,
        "original_source_3d_triangle_geometry_unmodified": True,
        "sewable_or_cutting_approved": False,
    }
