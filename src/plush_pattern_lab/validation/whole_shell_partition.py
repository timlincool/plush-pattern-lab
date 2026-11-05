"""Draft a four-region 3D manufacturing seam graph on the REAL Stage6 main shell.

This is a full-shell face/edge partition with exactly matched shared 3D edges.
It is NOT a 2D rest-shape or an industrial sewing/cutting pattern.
"""

from __future__ import annotations

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

NAMES = ("left_front", "left_rear", "right_front", "right_rear")
REQUIRED_PAIRS = {"0:1", "0:2", "1:3", "2:3"}


def _validated_mesh(points, faces):
    vertices = np.asarray(points, dtype=np.float64)
    triangles = np.asarray(faces)
    if vertices.ndim != 2 or vertices.shape[1] != 3:
        raise ValueError("expected Nx3 millimetre vertices")
    if not 12 <= len(vertices) <= 300000 or not np.isfinite(vertices).all():
        raise ValueError("invalid finite Stage6 shell coordinates")
    if triangles.ndim != 2 or triangles.shape[1] != 3:
        raise ValueError("expected triangular faces")
    if not 4 <= len(triangles) <= 600000:
        raise ValueError("invalid triangle count")
    if not np.issubdtype(triangles.dtype, np.integer):
        raise ValueError("triangle indices must be integral")
    if (triangles < 0).any() or (triangles >= len(vertices)).any():
        raise ValueError("triangle index outside vertex array")
    if any((triangles[:, k] == triangles[:, (k + 1) % 3]).any() for k in range(3)):
        raise ValueError("repeated triangle vertex indices")
    return vertices, triangles.astype(np.int64)


def _edge_ownership(triangles):
    face_count = len(triangles)
    edges = np.sort(
        np.concatenate(
            (
                triangles[:, [0, 1]],
                triangles[:, [1, 2]],
                triangles[:, [2, 0]],
            )
        ),
        axis=1,
    )
    unique, inverse, counts = np.unique(
        edges, axis=0, return_inverse=True, return_counts=True
    )
    if (counts > 2).any() or (counts == 0).any():
        raise ValueError("nonmanifold/invalid input shell edge incidence")
    ordered = np.argsort(inverse, kind="stable")
    face_owners = np.tile(np.arange(face_count), 3)[ordered]
    starts = np.cumsum(counts) - counts
    first = face_owners[starts]
    second = np.full(len(unique), -1, dtype=np.int64)
    dual = counts == 2
    second[dual] = face_owners[starts[dual] + 1]
    return unique, counts, first, second, inverse.reshape(3, face_count).T


def _components(n, edges):
    if n < 1:
        return 0, np.empty(0, dtype=int)
    if len(edges) == 0:
        return n, np.arange(n)
    rows = np.r_[edges[:, 0], edges[:, 1]]
    cols = np.r_[edges[:, 1], edges[:, 0]]
    graph = csr_matrix((np.ones(len(rows), dtype=np.int8), (rows, cols)), shape=(n, n))
    return connected_components(graph, directed=False)


def _boundary_stats(edges, vertex_count):
    if not len(edges):
        return {"loops": 0, "degree_failures": 0}
    used = np.unique(edges.ravel())
    degrees = np.bincount(edges.ravel(), minlength=vertex_count)
    count, labels = _components(vertex_count, edges)
    return {
        "loops": int(len(np.unique(labels[used]))),
        "degree_failures": int(np.count_nonzero(degrees[used] != 2)),
    }


def _face_components(region_face_ids, internal, total_faces):
    index = np.full(total_faces, -1, dtype=np.int64)
    index[region_face_ids] = np.arange(len(region_face_ids))
    mapped = index[internal]
    if (mapped < 0).any():
        raise ValueError("component graph has cross-region face")
    count, _ = _components(len(region_face_ids), mapped)
    return int(count)


def _region_report(region, labels, vertices, triangles, topology, cuff_size):
    edges, counts, first, second, face_edge_ids = topology
    selected = np.flatnonzero(labels == region)
    chosen, used_counts = np.unique(face_edge_ids[selected].ravel(), return_counts=True)
    border = edges[chosen[used_counts == 1]]
    boundary = _boundary_stats(border, len(vertices))
    verts = np.unique(triangles[selected].ravel())
    internal = (counts == 2) & (labels[first] == region)
    internal &= labels[np.maximum(second, 0)] == region
    linked = np.column_stack((first[internal], second[internal]))
    source = (counts == 1) & (labels[first] == region)
    cuffs = edges[source]
    cuff_graph = _boundary_stats(cuffs, len(vertices))
    cuff_vertices = np.unique(cuffs.ravel()) if len(cuffs) else np.array([], int)
    return {
        "region_id": region,
        "name": NAMES[region],
        "face_count": int(len(selected)),
        "vertex_count": int(len(verts)),
        "edge_count": int(len(chosen)),
        "face_components_by_shared_edge": _face_components(
            selected, linked, len(triangles)
        ),
        "euler_characteristic": int(len(verts) - len(chosen) + len(selected)),
        "boundary_edge_count": int(len(border)),
        "boundary_loop_count": boundary["loops"],
        "boundary_degree_failures": boundary["degree_failures"],
        "source_hoof_boundary_edges": int(len(cuffs)),
        "source_hoof_boundary_loops": cuff_graph["loops"],
        "source_hoof_centroid_mm": (
            [round(float(v), 4) for v in vertices[cuff_vertices].mean(axis=0)]
            if len(cuff_vertices)
            else None
        ),
        "contains_one_complete_expected_hoof_opening": (
            len(cuffs) == cuff_size
            and cuff_graph["loops"] == 1
            and cuff_graph["degree_failures"] == 0
        ),
        "fabric_piece_approved": False,
        "requires_radial_slit_to_flatten": True,
    }


def _seam_path(pair_edges, vertex_count):
    active = np.unique(pair_edges.ravel())
    degrees = np.bincount(pair_edges.ravel(), minlength=vertex_count)
    components, labels = _components(vertex_count, pair_edges)
    return {
        "path_components": int(len(np.unique(labels[active]))),
        "endpoints_degree_one": int(np.count_nonzero(degrees[active] == 1)),
        "branch_vertices_over_two": int(np.count_nonzero(degrees[active] > 2)),
    }


def _interfaces(labels, vertices, topology):
    edges, counts, first, second, _ = topology
    between = counts == 2
    between &= labels[first] != labels[np.maximum(second, 0)]
    edge_ids = np.flatnonzero(between)
    a = np.minimum(labels[first[between]], labels[second[between]])
    b = np.maximum(labels[first[between]], labels[second[between]])
    codes = [f"{int(x)}:{int(y)}" for x, y in zip(a, b)]
    reports, seam_edges = [], []
    for key in sorted(set(codes)):
        subset = edge_ids[[value == key for value in codes]]
        selected = edges[subset]
        lengths = np.linalg.norm(
            vertices[selected[:, 1]] - vertices[selected[:, 0]], axis=1
        )
        route = _seam_path(selected, len(vertices))
        reports.append(
            {
                "region_pair": key,
                "edge_count": int(len(selected)),
                "total_3d_length_mm": float(lengths.sum()),
                "max_edge_length_mm": float(lengths.max()),
                **route,
                "both_sides_use_identical_proxy_edges": True,
                "production_net_seam_approved": False,
            }
        )
        for edge_id, edge in zip(subset, selected):
            seam_edges.append(
                {
                    "edge_id": int(edge_id),
                    "vertex_ids": [int(edge[0]), int(edge[1])],
                    "region_pair": key,
                }
            )
    complete = len(seam_edges) == len(edge_ids)
    return reports, seam_edges, complete, edges[edge_ids]


def _run_length_encoding(labels):
    edges = np.r_[0, np.flatnonzero(labels[1:] != labels[:-1]) + 1, len(labels)]
    return [
        [int(start), int(end), int(labels[start])]
        for start, end in zip(edges[:-1], edges[1:])
    ]


def draft_four_zone_shell(vertices_mm, faces, split_y_mm=20, cuff_size=512):
    """True 3D face partitions; no cloth allowances, UV unroll or signoff."""
    vertices, triangles = _validated_mesh(vertices_mm, faces)
    if not np.isfinite(split_y_mm) or not 1 <= cuff_size <= 4096:
        raise ValueError("invalid split plane or expected hoof ring size")
    centers = vertices[triangles].mean(axis=1)
    labels = (centers[:, 0] >= 0).astype(np.int8) * 2
    labels += (centers[:, 1] >= split_y_mm).astype(np.int8)
    topology = _edge_ownership(triangles)
    regions = [
        _region_report(i, labels, vertices, triangles, topology, cuff_size)
        for i in range(4)
    ]
    interfaces, seam_edges, paired, network_edges = _interfaces(
        labels, vertices, topology
    )
    junctions = np.bincount(network_edges.ravel(), minlength=len(vertices))
    joints = np.flatnonzero(junctions > 2)
    valid = (
        all(row["face_components_by_shared_edge"] == 1 for row in regions)
        and all(row["boundary_loop_count"] == 2 for row in regions)
        and all(row["boundary_degree_failures"] == 0 for row in regions)
        and all(row["euler_characteristic"] == 0 for row in regions)
        and all(row["contains_one_complete_expected_hoof_opening"] for row in regions)
        and {row["region_pair"] for row in interfaces} == REQUIRED_PAIRS
        and all(
            row["path_components"] == 1
            and row["endpoints_degree_one"] == 2
            and row["branch_vertices_over_two"] == 0
            for row in interfaces
        )
        and paired
    )
    return {
        "schema": "stage6-actual-shell-four-zone-seam-graph-v1",
        "status": "FOUR_REGION_3D_TOPOLOGY_DRAFT_NOT_CUT_PATTERN",
        "coordinate_system": "X left/right, Y front/back, world millimetres",
        "split_x_mm": 0.0,
        "split_y_mm": float(split_y_mm),
        "source_vertices": len(vertices),
        "source_triangles": len(triangles),
        "source_original_open_boundary_edges": int((topology[1] == 1).sum()),
        "regions": regions,
        "seam_interfaces": interfaces,
        "seam_edges": seam_edges,
        "face_region_label_rle": _run_length_encoding(labels),
        "total_shared_3d_seam_edges": len(seam_edges),
        "total_shared_3d_seam_length_mm": float(
            sum(row["total_3d_length_mm"] for row in interfaces)
        ),
        "shared_seam_junction_vertices_over_two": len(joints),
        "shared_seam_junction_xyz_mm": [
            [round(float(v), 4) for v in vertices[index]] for index in joints
        ],
        "all_regions_single_connected_annuli_with_one_complete_hoof": bool(valid),
        "manufacturing_panel_count_approved": 0,
        "real_2d_fabric_rest_shapes_generated": False,
        "manufacturing_approved": False,
        "limitations": [
            "Four quadrants from 3D centroid split planes are provisional design routes",
            "Each region is an annulus and still requires a suitable slit/dart to flatten",
            "Cross-junctions require manufacturing-grade seam end construction",
            "3D interface length matches do not prove equal sewable 2D resting lengths",
            "No seam allowances, grain lines, filling paths, materials or real samples",
        ],
    }
