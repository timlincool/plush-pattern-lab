"""Trace original triangle *surface* continuity between two Stage6 Z loops.

An open-slab triangle graph shares edges with positive height overlap.
Touching only at a source vertex is not connectivity. This is not a seam.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict

import numpy as np

SCHEMA = "stage6-true-source-slab-triangle-connectivity-v1"
SOURCE_SCHEMA = "stage6-true-triangle-plane-component-loops-v1"


def _inputs(points, faces, detail, lower, upper):
    xyz = np.asarray(points, dtype=np.float64)
    tri = np.asarray(faces)
    if (
        xyz.ndim != 2
        or xyz.shape[1] != 3
        or not np.isfinite(xyz).all()
        or tri.ndim != 2
        or tri.shape[1] != 3
        or not np.issubdtype(tri.dtype, np.integer)
        or len(tri) < 4
        or np.any(tri < 0)
        or np.any(tri >= len(xyz))
        or not 0 < lower < upper < 1000
    ):
        raise ValueError("invalid actual Stage6 triangle mesh or ordered Z band")
    if np.any(np.min(np.abs(xyz[:, 2, None] - [lower, upper]), axis=0) < 1e-6):
        raise ValueError("slab plane through original source vertex")
    if (
        detail.get("schema") != SOURCE_SCHEMA
        or detail.get("factory_cutting_approved") != 0
    ):
        raise ValueError("requires unapproved real Stage6 source section evidence")
    sections = detail.get("sections", [])
    lookup = {section["plane_z_mm"]: section for section in sections}
    if len(lookup) != len(sections) or lower not in lookup or upper not in lookup:
        raise ValueError("missing, duplicate or nonmatching source Z sections")
    return xyz, tri.astype(np.int64), lookup[lower], lookup[upper]


def _source_contour_edges(xyz, section):
    z = section["plane_z_mm"]
    loops = section["source_contours"]
    if section["true_source_plane_intersection_component_count"] != len(loops):
        raise ValueError("source contour count mismatch")
    for loop in loops:
        edges = np.asarray(loop["crossed_original_mesh_vertex_id_edge_pairs"])
        xy = np.asarray(loop["true_interpolated_contour_xy_mm"], dtype=np.float64)
        if (
            edges.ndim != 2
            or edges.shape[1] != 2
            or not np.issubdtype(edges.dtype, np.integer)
            or np.any(edges < 0)
            or np.any(edges >= len(xyz))
            or len(edges) < 3
            or xy.shape != (len(edges), 2)
            or not np.isfinite(xy).all()
            or not loop.get("closed_loop")
            or not loop.get("simple_polygon")
        ):
            raise ValueError("source contour original edge IDs missing or corrupt")
        a, b = xyz[edges[:, 0]], xyz[edges[:, 1]]
        if np.any((a[:, 2] > z) == (b[:, 2] > z)):
            raise ValueError("source original edge does not cross claimed section")
        ratios = (z - a[:, 2]) / (b[:, 2] - a[:, 2])
        actual = a[:, :2] + ratios[:, None] * (b[:, :2] - a[:, :2])
        if np.max(np.abs(actual - xy)) > 1e-6:
            raise ValueError("source contour interpolated XY differs from mesh")
        digest = hashlib.sha256(
            np.asarray(edges, dtype="<i8").tobytes()
            + np.asarray(xy, dtype="<f8").tobytes()
        ).hexdigest()
        if digest != loop["original_source_edge_and_interpolated_xy_sha256"]:
            raise ValueError("source contour original edge / XY SHA mismatch")
        yield edges


class _FaceUnionFind:
    """Deterministic face-component representative tracking without recursion."""

    def __init__(self, count):
        self.parent = np.arange(count, dtype=np.int64)
        self.rank = np.zeros(count, dtype=np.int8)

    def root(self, i):
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return int(i)

    def unite(self, i, j):
        a, b = self.root(i), self.root(j)
        if a == b:
            return
        if self.rank[a] < self.rank[b]:
            a, b = b, a
        self.parent[b] = a
        if self.rank[a] == self.rank[b]:
            self.rank[a] += 1


def _label_components(selected, owners, union_find):
    grouped = defaultdict(list)
    for local_id, global_id in enumerate(selected):
        grouped[union_find.root(local_id)].append(int(global_id))
    ordered = sorted(grouped.values(), key=lambda row: row[0])
    component = {}
    for label, face_ids in enumerate(ordered):
        for global_id in face_ids:
            component[global_id] = label
    edges_to_component = {
        edge: component[int(selected[local_id])]
        for edge, local_id in owners.items()
    }
    return ordered, edges_to_component, len(selected)


def _face_connectivity(xyz, tri, lower, upper):
    heights = xyz[:, 2]
    selected = np.flatnonzero(
        (np.max(heights[tri], axis=1) > lower)
        & (np.min(heights[tri], axis=1) < upper)
    )
    if len(selected) == 0:
        raise ValueError("no source triangles intersect open slab")
    face_groups = _FaceUnionFind(len(selected))
    edge_first = {}
    edge_count = defaultdict(int)
    for local_id, global_id in enumerate(selected):
        face = tri[global_id]
        for a, b in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            a, b = int(a), int(b)
            if max(heights[a], heights[b]) <= lower:
                continue
            if min(heights[a], heights[b]) >= upper:
                continue
            edge = (min(a, b), max(a, b))
            edge_count[edge] += 1
            if edge_count[edge] > 2:
                raise ValueError("nonmanifold source slab shared edge")
            if edge in edge_first:
                face_groups.unite(local_id, edge_first[edge])
            else:
                edge_first[edge] = local_id
    return _label_components(selected, edge_first, face_groups)


def _loop_component(xyz, section, edges_to_component):
    output = []
    for index, (loop, edges) in enumerate(
        zip(section["source_contours"], _source_contour_edges(xyz, section))
    ):
        groups = {
            edges_to_component.get(tuple(sorted(map(int, edge))))
            for edge in edges
        }
        if None in groups or len(groups) != 1:
            raise ValueError("a source loop jumps disconnected slab surfaces")
        output.append(
            {
                "loop_index_by_perimeter": index,
                "slab_component": groups.pop(),
                "source_edge_count": len(edges),
                "original_source_edge_and_xy_sha256": loop[
                    "original_source_edge_and_interpolated_xy_sha256"
                ],
                "perimeter_mm": loop["contour_perimeter_mm"],
                "centroid_xy_mm": loop["contour_centroid_xy_mm"],
            }
        )
    return output


def trace_true_source_slab(points, faces, detail, lower=230, upper=245):
    """Source-face components between original contour levels, fail closed."""
    xyz, tri, bottom, top = _inputs(points, faces, detail, lower, upper)
    groups, edges, face_count = _face_connectivity(xyz, tri, lower, upper)
    bottom_loops = _loop_component(xyz, bottom, edges)
    top_loops = _loop_component(xyz, top, edges)
    connections = []
    for label, group in enumerate(groups):
        entering = [
            loop["loop_index_by_perimeter"]
            for loop in bottom_loops
            if loop["slab_component"] == label
        ]
        exiting = [
            loop["loop_index_by_perimeter"]
            for loop in top_loops
            if loop["slab_component"] == label
        ]
        if not entering and not exiting:
            kind = "internal_island_not_on_either_plane"
        elif len(entering) == len(exiting) == 1:
            kind = "one_to_one_surface_continuation_not_seam"
        elif entering and not exiting:
            kind = "lower_loop_terminates_before_upper"
        elif exiting and not entering:
            kind = "upper_loop_appears_after_lower"
        else:
            kind = "branch_or_merge_requires_anatomical_review"
        connections.append(
            {
                "component": label,
                "original_triangle_count_in_slab": len(group),
                "lower_loop_indices": entering,
                "upper_loop_indices": exiting,
                "source_surface_relation": kind,
                "not_a_validated_sewing_join": True,
            }
        )
    return {
        "schema": SCHEMA,
        "lower_plane_z_mm": lower,
        "upper_plane_z_mm": upper,
        "source_triangle_count_in_open_slab": face_count,
        "source_surface_component_count_in_open_slab": len(groups),
        "lower_original_source_loops": bottom_loops,
        "upper_original_source_loops": top_loops,
        "surface_components": connections,
        "exact_original_mesh_source_vertex_id_provenance_validated": True,
        "vertex_only_contacts_are_not_connected": True,
        "independent_ear_and_cloud_mesh_ownership_not_inferred": True,
        "physical_attachment_and_design_not_verified": True,
        "approved_industrial_cutting_patterns": 0,
        "P3_structure_gate_passed": False,
        "P4_started": False,
    }
