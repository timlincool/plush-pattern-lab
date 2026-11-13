"""Split real Stage6 high protrusion caps along original triangle mesh edges.

Only existing SciPy sparse shortest paths and face connected components. No UV
solver, triangulation re-meshing, physical stitch approval or fabric rest shape.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components, dijkstra

SCHEMA = "stage6-genuine-high-protrusion-source-edge-bisect-AB-v1"
SOURCE_SCHEMA = "stage6-genuine-source-z230-three-open-caps-v1"
ROUTES = ("Y_FRONT_BACK", "X_INNER_OUTER")
CAPS = ("left_high_protrusion", "right_high_protrusion")
EXPECTED_SOURCE_FACES = (1849, 1906)
EXPECTED_SOURCE_RIMS = (113, 112)


def _edges_by_faces(faces):
    indexed = defaultdict(list)
    for face_id, (a, b, c) in enumerate(faces):
        for u, v in ((a, b), (b, c), (c, a)):
            key = tuple(sorted((int(u), int(v))))
            indexed[key].append(face_id)
    if any(len(owners) not in (1, 2) for owners in indexed.values()):
        raise ValueError("non-manifold original source faces")
    return indexed


def _source(cap, name, expected_faces, expected_rim):
    if cap.get("id") != name or cap.get("source_topological_Euler") != 1:
        raise ValueError("only the two genuine Stage6 high protrusions are eligible")
    points = np.asarray(cap["vertices_xyz_mm"], dtype=np.float64)
    faces = np.asarray(cap["triangles_local_vertex_indices"], dtype=np.int64)
    rim = np.asarray(cap["original_rim_vertex_ids_in_cap_local_order"], dtype=np.int64)
    if (
        points.ndim != 2
        or points.shape[1] != 3
        or faces.shape != (expected_faces, 3)
        or rim.shape != (expected_rim,)
        or len(np.unique(rim)) != expected_rim
        or not np.isfinite(points).all()
        or np.any(faces < 0)
        or np.any(faces >= len(points))
        or np.any(rim < 0)
        or np.any(rim >= len(points))
    ):
        raise ValueError("original source cap faces or 230mm rim changed")
    owners = _edges_by_faces(faces)
    boundary = {edge for edge, fs in owners.items() if len(fs) == 1}
    expected = {tuple(sorted((int(a), int(b)))) for a, b in zip(rim, np.roll(rim, -1))}
    if boundary != expected:
        raise ValueError("source Z230 3D rim cannot be changed")
    return points, faces, rim, owners, expected


def _path(graph, start, target):
    distance, predecessor = dijkstra(
        graph, indices=int(start), directed=False, return_predecessors=True
    )
    if not np.isfinite(distance[target]):
        raise ValueError("no source-mesh meridian from rim to apex")
    route = [int(target)]
    while route[-1] != start:
        previous = int(predecessor[route[-1]])
        if previous < 0 or len(route) > graph.shape[0]:
            raise ValueError("source geodesic failed to reach its rim anchor")
        route.append(previous)
    return route[::-1]


def _source_meridian(xyz, rim, owners, axis):
    # Only original INTERNAL edges: original boundary shortcuts cannot cut disk.
    edges = np.asarray([key for key, fs in owners.items() if len(fs) == 2])
    length = np.linalg.norm(xyz[edges[:, 0]] - xyz[edges[:, 1]], axis=1)
    graph = csr_matrix(
        (
            np.r_[length, length],
            (np.r_[edges[:, 0], edges[:, 1]], np.r_[edges[:, 1], edges[:, 0]]),
        ),
        shape=(len(xyz), len(xyz)),
    )
    tip = int(np.argmax(xyz[:, 2]))
    first = int(rim[np.argmin(xyz[rim, axis])])
    last = int(rim[np.argmax(xyz[rim, axis])])
    forward = _path(graph, first, tip)
    backward = _path(graph, tip, last)
    route = forward + backward[1:]
    if (
        len(route) < 3
        or len(route) != len(set(route))
        or tip in set(rim)
        or set(route[1:-1]).intersection(set(rim))
    ):
        raise ValueError("source meridian is branched, degenerate or intersects rim")
    cut = {tuple(sorted(pair)) for pair in zip(route, route[1:])}
    if any(len(owners[edge]) != 2 for edge in cut):
        raise ValueError("meridian included an unpaired original source edge")
    return route, cut


def _panels(faces, owners, cut):
    first, second = [], []
    for edge, attached in owners.items():
        if len(attached) == 2 and edge not in cut:
            a, b = attached
            first.extend((a, b))
            second.extend((b, a))
    graph = csr_matrix(
        (np.ones(len(first), dtype=np.int8), (first, second)),
        shape=(len(faces), len(faces)),
    )
    count, labels = connected_components(graph, directed=False)
    if count != 2 or min(np.bincount(labels)) < 100:
        raise ValueError("real source meridian did not form two useful 3D panels")
    return [np.flatnonzero(labels == label) for label in (0, 1)]


def _ordered_boundary(boundary):
    neighbors = defaultdict(set)
    for u, v in boundary:
        neighbors[int(u)].add(int(v))
        neighbors[int(v)].add(int(u))
    if any(len(partners) != 2 for partners in neighbors.values()):
        raise ValueError("3D panel has an open, branched or non-simple rim")
    start = min(neighbors)
    previous, current, ring = -1, start, []
    while current not in ring:
        ring.append(current)
        choices = sorted(neighbors[current] - {previous})
        if previous >= 0 and len(choices) != 1:
            raise ValueError("panel rim changed direction within source edges")
        previous, current = current, choices[0]
    if current != start or len(ring) != len(neighbors):
        raise ValueError("panel has more than one boundary loop")
    return ring


def _panel_data(xyz, faces, face_ids, path, old_rim):
    originals, remapped = np.unique(faces[face_ids], return_inverse=True)
    triangles = remapped.reshape(-1, 3)
    points = xyz[originals]
    edges = _edges_by_faces(triangles)
    boundary = {edge for edge, fs in edges.items() if len(fs) == 1}
    ordered = _ordered_boundary(boundary)
    original_to_local = {int(p): i for i, p in enumerate(originals)}
    if not set(path).issubset(original_to_local):
        raise ValueError("entire 3D cut path must appear on both panels")
    local_path = [original_to_local[v] for v in path]
    original_rim = set(old_rim)
    rim_count = sum(
        1
        for u, v in boundary
        if originals[u] in original_rim and originals[v] in original_rim
    )
    euler = len(points) - len(edges) + len(triangles)
    if euler != 1 or rim_count < 2:
        raise ValueError("original source region not an open topological disk")
    return {
        "source_original_cap_vertex_id_per_panel_vertex": originals.tolist(),
        "vertices_xyz_mm": points.tolist(),
        "triangles_local_vertex_indices": triangles.tolist(),
        "boundary_panel_vertex_ids_in_order": ordered,
        "seam_original_cap_vertex_ids_in_order": path,
        "seam_panel_vertex_ids_in_order": local_path,
        "source_original_cap_face_ids": face_ids.tolist(),
        "source_original_z230_boundary_edges_on_panel": rim_count,
        "topological_Euler": euler,
        "physical_fabric_allowance_or_hidden_seam_verified": False,
    }


def _one_source(cap, name, nfaces, nborder, route):
    xyz, faces, rim, owners, source_rim = _source(cap, name, nfaces, nborder)
    meridian, cut = _source_meridian(
        xyz, rim, owners, axis=1 if route == ROUTES[0] else 0
    )
    groups = _panels(faces, owners, cut)
    panels = [_panel_data(xyz, faces, group, meridian, rim) for group in groups]
    all_ids = [fid for p in panels for fid in p["source_original_cap_face_ids"]]
    if len(set(all_ids)) != len(faces) or set(all_ids) != set(range(len(faces))):
        raise ValueError("source triangle coverage changed or faces duplicated")
    if sum(p["source_original_z230_boundary_edges_on_panel"] for p in panels) != len(
        source_rim
    ):
        raise ValueError("original Stage6 Z230 rim not preserved by source split")
    original_path_length = float(
        np.linalg.norm(np.diff(xyz[meridian], axis=0), axis=1).sum()
    )
    for panel in panels:
        ordered = panel["source_original_cap_vertex_id_per_panel_vertex"]
        if [ordered[i] for i in panel["seam_panel_vertex_ids_in_order"]] != meridian:
            raise ValueError("3D meridian identity lost during panel splitting")
        seam_xyz = np.asarray(panel["vertices_xyz_mm"])[
            panel["seam_panel_vertex_ids_in_order"]
        ]
        length = float(np.linalg.norm(np.diff(seam_xyz, axis=0), axis=1).sum())
        if abs(length - original_path_length) > 1e-8:
            raise ValueError("3D paired source seam lengths disagree")
    for index, panel in enumerate(panels):
        panel["id"] = f"{name}_{route}_panel_{index + 1}"
        panel["source_cap_id"] = name
    return {
        "name": name,
        "route": route,
        "original_z230_rim_edge_count": len(source_rim),
        "original_z230_source_witness_sha256": cap[
            "source_original_rim_edge_ids_sha256"
        ],
        "source_3d_meridian_length_mm": original_path_length,
        "original_cap_tip_vertex_id": int(np.argmax(xyz[:, 2])),
        "original_cap_meridian_vertex_ids": meridian,
        "source_face_count": len(faces),
        "panels": panels,
        "original_three_dimensional_source_seam_shared_twice": True,
    }


def build_real_protrusion_bisect_ab(original):
    if (
        original.get("schema") != SOURCE_SCHEMA
        or original.get("industrial_cutting_patterns_approved") != 0
        or original.get("P3_status") != "in_progress"
        or original.get("P4_status") != "not_started"
        or not original.get("upper_to_lower_source_netline_matched_at_1e_6_mm")
        or len(original.get("upper_caps", [])) != 3
    ):
        raise ValueError("requires previously source-verified Stage6 actual 3D caps")
    caps = original["upper_caps"]
    variants = []
    for route in ROUTES:
        variants.append(
            {
                "route": route,
                "side_protrusions": [
                    _one_source(cap, name, nfaces, nborder, route)
                    for cap, name, nfaces, nborder in zip(
                        caps[1:], CAPS, EXPECTED_SOURCE_FACES, EXPECTED_SOURCE_RIMS
                    )
                ],
                "single_central_real_source_crown_retained": True,
                "side_panel_count_total": 4,
                "source_Z230_meridian_start_end_not_factory_signed_off": True,
            }
        )
    return {
        "schema": SCHEMA,
        "source_original_three_caps_schema": SOURCE_SCHEMA,
        "original_stage6_blend_sha256": original["original_public_stage6_blend_sha256"],
        "original_source_25pct_proxy_sha256": original["source_proxy_ply_sha256"],
        "routes": list(ROUTES),
        "variants": variants,
        "source_three_dimensional_face_ids_and_Z230_rims_unchanged": True,
        "source_3d_shared_new_side_seams_matched": True,
        "source_cloud_ear_hidden_seams_not_designed_or_approved": True,
        "blender_abf_2d_not_yet_measured": True,
        "factory_cutting_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
    }
