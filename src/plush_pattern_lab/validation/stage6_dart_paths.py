"""Trace speculative ear-dart tip closures on original Stage6 triangle edges.

Two source-edge branches may share only a predeclared candidate tip vertex.
Original mesh remains intact; 3D routes are not paired 2D sewing netlines.
"""

from __future__ import annotations

import hashlib
import struct

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial.distance import cdist

SCHEMA = "stage6-source-ear-medial-arc-dart-tip-routes-v1"
TIP_TARGETS_Z_MM = (225.0, 219.0)
PLANE_Z_MM = 230
ROOT_SIDE_RADIUS_X_MM = 12.0
ROOT_SIDE_RADIUS_Y_MM = 15.0
TIP_CLEARANCE_SCREEN_MM = 4.0
NARROW_GAP_RESEARCH_MM = 2.0


def original_edges(points, faces):
    """Construct immutable original triangle vertex edge IDs and 3D lengths."""
    xyz = np.asarray(points, dtype=np.float64)
    triangles = np.asarray(faces)
    if (
        xyz.ndim != 2
        or xyz.shape[1] != 3
        or not np.isfinite(xyz).all()
        or triangles.ndim != 2
        or triangles.shape[1] != 3
        or not np.issubdtype(triangles.dtype, np.integer)
        or np.any(triangles < 0)
        or np.any(triangles >= len(xyz))
    ):
        raise ValueError("invalid original source triangle Vertex ID graph")
    edges = np.concatenate(
        (triangles[:, (0, 1)], triangles[:, (1, 2)], triangles[:, (2, 0)])
    )
    edges = np.unique(np.sort(edges, axis=1), axis=0)
    if np.any(edges[:, 0] == edges[:, 1]):
        raise ValueError("degenerate source mesh self-edge")
    length = np.linalg.norm(xyz[edges[:, 0]] - xyz[edges[:, 1]], axis=1)
    if np.any(length <= 1e-9):
        raise ValueError("source mesh contains zero-length triangle edge")
    return xyz, edges, length


def _validated_anchor_endpoint(xyz, all_edges, pair, position):
    """Interpolated Z230 endpoint must lie on claimed original PLY edge."""
    if (
        len(pair) != 2
        or any(not isinstance(i, int) or i < 0 or i >= len(xyz) for i in pair)
        or len(position) != 3
        or not np.isfinite(position).all()
        or abs(position[2] - PLANE_Z_MM) > 1e-7
    ):
        raise ValueError("invalid source arc endpoint ID or source XYZ")
    key = tuple(sorted(pair))
    row = np.searchsorted(all_edges[:, 0], key[0], side="left")
    if not np.any(np.all(all_edges[row:, :] == key, axis=1)):
        raise ValueError("source crossed edge missing from actual triangle graph")
    a, b = xyz[pair[0]], xyz[pair[1]]
    if (a[2] < PLANE_Z_MM) == (b[2] < PLANE_Z_MM):
        raise ValueError("source endpoint edge does not cross root plane")
    ratio = (PLANE_Z_MM - a[2]) / (b[2] - a[2])
    true_xyz = a + ratio * (b - a)
    if np.max(np.abs(true_xyz - position)) > 1e-5:
        raise ValueError("source original edge / interpolated XYZ mismatch")
    lower = pair[0] if a[2] < PLANE_Z_MM else pair[1]
    return int(lower), float(np.linalg.norm(xyz[lower] - true_xyz))


def _validate_medial_arc(xyz, edges, side, arc):
    if (
        side not in ("left", "right")
        or arc.get("hypothesis") != "medial"
        or arc.get("source_side") != side
        or arc.get("source_height_mm") != PLANE_Z_MM
        or arc.get("sample_count") != 12
        or arc.get("original_arc_endpoints_unpaired") != 2
        or arc.get("approved_as_hidden_seam") is not False
    ):
        raise ValueError("not an original unapproved A medial source arc")
    ends = (
        (arc["original_source_edge_id_pair_start"], arc["source_xyz_start_mm"]),
        (arc["original_source_edge_id_pair_end"], arc["source_xyz_end_mm"]),
    )
    verified = [
        _validated_anchor_endpoint(xyz, edges, pair, position)
        for pair, position in ends
    ]
    if verified[0][0] == verified[1][0]:
        raise ValueError("both source arc ends collapse to one mesh vertex")
    return verified


def _route_graph(xyz, edges, lengths, center, target_z, blocked=()):
    valid = (
        (xyz[:, 2] >= target_z - 3.0)
        & (xyz[:, 2] < PLANE_Z_MM - 1e-5)
        & (abs(xyz[:, 0] - center[0]) < ROOT_SIDE_RADIUS_X_MM)
        & (abs(xyz[:, 1] - center[1]) < ROOT_SIDE_RADIUS_Y_MM)
    )
    if blocked:
        valid[np.asarray(sorted(blocked), dtype=np.int64)] = False
    mask = valid[edges[:, 0]] & valid[edges[:, 1]]
    active, weight = edges[mask], lengths[mask]
    graph = coo_matrix(
        (
            np.r_[weight, weight],
            (np.r_[active[:, 0], active[:, 1]], np.r_[active[:, 1], active[:, 0]]),
        ),
        shape=(len(xyz), len(xyz)),
    ).tocsr()
    return valid, graph


def _route_to_tip(predecessor, tip, start, count):
    route = [int(start)]
    while route[-1] != tip:
        following = int(predecessor[route[-1]])
        if following < 0 or len(route) > count:
            raise ValueError("disconnected original source edge route")
        route.append(following)
    return route


def _root_tip(xyz, valid, center, target_z):
    candidates = np.flatnonzero(valid)
    if not len(candidates):
        raise ValueError("no original source face vertices near proposed tip")
    target = np.array([center[0], center[1], target_z])
    distance = np.linalg.norm(xyz[candidates] - target, axis=1)
    return int(candidates[int(np.argmin(distance))])


def _point_gap_after_tip(xyz, first, second, tip):
    filtered = []
    for route in (first, second):
        inner = [
            point
            for point in route[:-1]
            if np.linalg.norm(xyz[point] - xyz[tip]) > TIP_CLEARANCE_SCREEN_MM
        ]
        filtered.append(inner)
    if not all(filtered):
        return None
    return float(cdist(xyz[filtered[0]], xyz[filtered[1]]).min())


def _candidate(xyz, edges, lengths, side, arc, target_z):
    endpoints = _validate_medial_arc(xyz, edges, side, arc)
    positions = np.asarray(
        (arc["source_xyz_start_mm"], arc["source_xyz_end_mm"]), dtype=np.float64
    )
    center = positions.mean(axis=0)[:2]
    valid, graph = _route_graph(xyz, edges, lengths, center, target_z)
    if not all(valid[item[0]] for item in endpoints):
        raise ValueError("source arc endpoint outside fixed 3D route research band")
    tip = _root_tip(xyz, valid, center, target_z)
    distance, parent = dijkstra(graph, indices=tip, return_predecessors=True)
    original = [_route_to_tip(parent, tip, pair[0], len(xyz)) for pair in endpoints]
    early_join = len(set(original[0][:-1]) & set(original[1][:-1]))
    _, detour = _route_graph(
        xyz, edges, lengths, center, target_z, set(original[0][:-1])
    )
    other_dist, other_parent = dijkstra(detour, indices=tip, return_predecessors=True)
    second = _route_to_tip(other_parent, tip, endpoints[1][0], len(xyz))
    first = original[0]
    if set(first[:-1]) & set(second[:-1]):
        raise ValueError("source dart branches share vertices before their tip")
    gap = _point_gap_after_tip(xyz, first, second, tip)
    return {
        "side": side,
        "tip_target_z_mm": target_z,
        "chosen_original_source_tip_vertex_id": tip,
        "chosen_source_tip_xyz_mm": xyz[tip].tolist(),
        "original_source_arc_start_end_vertex_edge_ids": [
            arc["original_source_edge_id_pair_start"],
            arc["original_source_edge_id_pair_end"],
        ],
        "original_source_arc_length_mm": arc["source_original_plane_arc_length_mm"],
        "unconstrained_shortest_routes_meet_early_vertex_count": early_join,
        "disjoint_original_source_route_ids": [first, second],
        "disjoint_original_source_route_xyz_mm": [
            xyz[first].tolist(),
            xyz[second].tolist(),
        ],
        "source_3d_dart_route_identity_sha256": hashlib.sha256(
            np.asarray(first + second, dtype="<i8").tobytes()
            + np.asarray(xyz[first + second], dtype="<f8").tobytes()
        ).hexdigest(),
        "3d_route_to_tip_mm": [
            float(distance[endpoints[0][0]] + endpoints[0][1]),
            float(other_dist[endpoints[1][0]] + endpoints[1][1]),
        ],
        "extra_3d_route_2_due_to_disjoint_routing_mm": float(
            other_dist[endpoints[1][0]] - distance[endpoints[1][0]]
        ),
        "min_original_vertex_to_vertex_gap_beyond_tip_4mm_mm": gap,
        "branch_gap_under_2mm_research_screen": (
            gap is None or gap < NARROW_GAP_RESEARCH_MM
        ),
        "source_original_triangles_not_cut": True,
        "source_mesh_edge_routes_not_surface_intersection_or_fabrication": True,
        "minimum_gap_is_vertex_sampling_screen_not_continuous_segment_distance": True,
        "not_a_validated_two_sided_sewing_netline": True,
        "not_actual_material_allowance_or_hidden_seam": True,
    }


def _validated_original_section_arc(arc, ring):
    """Verify every original Z230 contour ID, not only two endpoints."""
    xy = ring["full_interpolated_original_source_xy_mm"]
    edge_pairs = ring["full_crossed_original_proxy_vertex_id_pairs"]
    if len(xy) != len(edge_pairs) or len(xy) < 16:
        raise ValueError("original Z230 full contour geometry missing")
    digest = hashlib.sha256(
        b"".join(struct.pack("<qq", *pair) for pair in edge_pairs)
        + b"".join(struct.pack("<dd", *point) for point in xy)
    ).hexdigest()
    if (
        digest != ring["source_contour_sha256"]
        or digest != arc["source_contour_sha256"]
    ):
        raise ValueError("original section arc source edge / XY SHA mismatch")
    start = arc["original_source_edge_ordinal_start"]
    stop = arc["original_source_edge_ordinal_end"]
    if (
        not all(isinstance(v, int) and 0 <= v < len(xy) for v in (start, stop))
        or edge_pairs[start] != arc["original_source_edge_id_pair_start"]
        or edge_pairs[stop] != arc["original_source_edge_id_pair_end"]
        or [*xy[start], PLANE_Z_MM] != arc["source_xyz_start_mm"]
        or [*xy[stop], PLANE_Z_MM] != arc["source_xyz_end_mm"]
    ):
        raise ValueError("original source arc endpoints changed")
    indices = [start]
    while indices[-1] != stop:
        if len(indices) > len(xy):
            raise ValueError("source arc skipped around original full contour")
        indices.append((indices[-1] + 1) % len(xy))
    actual = sum(
        np.linalg.norm(np.asarray(xy[a]) - np.asarray(xy[b]))
        for a, b in zip(indices, indices[1:])
    )
    if abs(actual - arc["source_original_plane_arc_length_mm"]) > 1e-5:
        raise ValueError("true original source arc length mismatch")
    return [[*xy[i], PLANE_Z_MM] for i in indices]


def explore_source_ear_dart_endings(points, faces, review, source):
    """Compare both ear sides and two fixed original source tip depths."""
    xyz, edges, lengths = original_edges(points, faces)
    if (
        review.get("schema") != "stage6-original-ear-root-quadrant-arc-41mesh-screen-v1"
        or review.get("approved_factory_cutting_patterns") != 0
        or review.get("P4_status") != "not_started"
        or review.get("input_pinned_proxy_sha256")
        != "5b52e3fd09c83b19c5b9d95d6d8d859a147ff4deef90f1518f868d2e82e3a2dd"
    ):
        raise ValueError("not original Stage6 25%-proxy source arc research")
    a = review["option_results"][0]
    if a["name"] != "A_lower_root_ring" or a["source_z_mm"] != PLANE_Z_MM:
        raise ValueError("source A root ring Z230 is missing")
    original = source["candidate_options"][0]
    if (
        source.get("schema") != "stage6-original-source-ear-root-two-height-ring-ab-v1"
        or original["name"] != a["name"]
        or original["source_plane_z_mm"] != PLANE_Z_MM
    ):
        raise ValueError("source-only A ear ring detail missing")
    results = []
    for side, ring in zip(a["sides"], original["source_side_loops"]):
        if side["side"] not in ("left", "right") or side["side"] != ring["side"]:
            raise ValueError("unrecognized original source side")
        arcs = side["quadrant_arc_hypotheses"]
        if not arcs or arcs[0]["hypothesis"] != "medial":
            raise ValueError("original predefined medial source arc is missing")
        section_arc = _validated_original_section_arc(arcs[0], ring)
        for target in TIP_TARGETS_Z_MM:
            item = _candidate(xyz, edges, lengths, side["side"], arcs[0], target)
            item["original_source_section_arc_xyz_mm"] = section_arc
            item["source_full_contour_sha256"] = ring["source_contour_sha256"]
            results.append(item)
    if len(results) != 4:
        raise ValueError("must check two sides and two predefined apex depths")
    return {
        "schema": SCHEMA,
        "original_source_proxy_vertex_count": len(xyz),
        "original_source_proxy_triangle_count": len(faces),
        "original_source_proxy_unique_mesh_edge_count": len(edges),
        "open_medial_source_ring_height_mm": PLANE_Z_MM,
        "candidates": results,
        "source_arc_not_cut_or_flattened": True,
        "disjoint_3d_routes_are_not_two_sided_2d_fabric_netlines": True,
        "seam_allowance_and_real_material_not_tested": True,
        "factory_cutting_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
    }
