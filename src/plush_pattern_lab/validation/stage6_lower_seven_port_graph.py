"""Source-locked Stage6 lower seven-rim shell joined to its four real 3D zones.

Proves original 3D cap/hoof edge and zone topology, NOT cloth rest patterns.
Uses existing four-zone incidence/graph tools and MIT trimesh 4.11.1 clipping.
"""

from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree

from plush_pattern_lab.validation.whole_shell_partition import (
    NAMES,
    _boundary_stats,
    _components,
    _edge_ownership,
    _face_components,
    _interfaces,
)

SCHEMA = "stage6-real-lower-seven-3d-rims-four-zone-interface-audit-v1"
CAPS_SCHEMA = "stage6-genuine-source-z230-three-open-caps-v1"
SOURCE_SHA = "38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a"
PROXY_SHA = "5b52e3fd09c83b19c5b9d95d6d8d859a147ff4deef90f1518f868d2e82e3a2dd"
CAP_IDS = ("central_crown", "left_high_protrusion", "right_high_protrusion")
RIM_COUNTS = (189, 113, 112)
SPLITS = (20.0, 25.0)
EXPECTED_Y20 = ((-1, 3, 34579), (0, 2, 21703), (-1, 3, 34260), (0, 2, 21436))
EXPECTED_PORTS = (
    {"left_front": 95, "right_front": 94},
    {"left_front": 113},
    {"right_front": 112},
)


def _check_locked_source(source, faces, caps, full):
    if (
        len(source) != 59306
        or len(faces) != 116568
        or caps.get("schema") != CAPS_SCHEMA
        or caps.get("original_public_stage6_blend_sha256") != SOURCE_SHA
        or caps.get("source_proxy_ply_sha256") != PROXY_SHA
        or caps.get("industrial_cutting_patterns_approved") != 0
        or caps.get("P3_status") != "in_progress"
        or caps.get("P4_status") != "not_started"
        or not caps.get("upper_to_lower_source_netline_matched_at_1e_6_mm")
        or [c["id"] for c in caps.get("upper_caps", [])] != list(CAP_IDS)
        or [c["source_boundary_edges"] for c in caps["upper_caps"]] != list(RIM_COUNTS)
        or caps.get("lower_single_original_surface", {}).get(
            "source_Euler_characteristic"
        )
        != -5
        or not caps["lower_single_original_surface"].get(
            "original_four_hoof_rings_exactly_512_edges_each"
        )
        or full.get("schema") != "stage6-source-pinned-whole-shell-seam-plan-v1"
        or full.get("source_original_model_sha256") != SOURCE_SHA
        or full.get("proxy_ply_sha256") != PROXY_SHA
        or full.get("shorter_3d_seam_graph_study_y_mm") != 20.0
        or [r["split_y_mm"] for r in full.get("scenarios", [])] != list(SPLITS)
        or any(r.get("source_triangles") != 116568 for r in full["scenarios"])
    ):
        raise ValueError("requires unchanged genuine seven-port Stage6 source data")


def _clip_original_lower(source, faces, trimesh_module):
    if trimesh_module.__version__ != "4.11.1":
        raise ValueError("only audited MIT trimesh==4.11.1 supported")
    mesh = trimesh_module.Trimesh(vertices=source, faces=faces, process=False)
    lower = trimesh_module.intersections.slice_mesh_plane(
        mesh, plane_normal=[0, 0, -1], plane_origin=[0, 0, 230], cap=False
    )
    lower.merge_vertices(digits_vertex=12)
    xyz = np.asarray(lower.vertices, dtype=np.float64)
    faces = np.asarray(lower.faces, dtype=np.int64)
    if len(faces) != 111978 or len(xyz) != 57215:
        raise ValueError("actual original lower source clip changed")
    return xyz, faces


def _seven_source_rims(xyz, topology):
    edges, counts, _, _, _ = topology
    boundary = edges[counts == 1]
    upper = np.all(np.abs(xyz[boundary, 2] - 230) < 1e-7, axis=1)
    if (
        len(boundary) != 2462
        or int(upper.sum()) != sum(RIM_COUNTS)
        or _boundary_stats(boundary, len(xyz)) != {"loops": 7, "degree_failures": 0}
    ):
        raise ValueError("lower source no longer contains exactly seven closed rims")
    hoof = boundary[~upper]
    if len(hoof) != 2048 or _boundary_stats(hoof, len(xyz)) != {
        "loops": 4,
        "degree_failures": 0,
    }:
        raise ValueError("original four hoof rims lost")
    _, components = _components(len(xyz), hoof)
    sizes = sorted(
        int(np.count_nonzero(components[hoof[:, 0]] == group))
        for group in np.unique(components[hoof[:, 0]])
    )
    if sizes != [512] * 4:
        raise ValueError("one of four original 512-edge source hoof rims changed")
    return boundary, upper


def _cap_source_port(xyz, original, owner):
    points = np.asarray(original["vertices_xyz_mm"], dtype=np.float64)
    rim_ids = np.asarray(original["original_rim_vertex_ids_in_cap_local_order"])
    physical = points[rim_ids]
    candidates = np.unique(np.asarray(list(owner), dtype=int))
    distance, nearest = cKDTree(xyz[candidates]).query(physical)
    mapped = candidates[nearest]
    if (
        len(np.unique(mapped)) != len(rim_ids)
        or not np.isfinite(physical).all()
        or float(np.max(distance)) > 1e-6
        or np.max(np.abs(physical[:, 2] - 230)) > 1e-7
    ):
        raise ValueError("original upper 3D cap rim no longer matches lower source")
    edges = [
        tuple(sorted((int(a), int(b)))) for a, b in zip(mapped, np.roll(mapped, -1))
    ]
    if len(set(edges)) != len(edges) or any(e not in owner for e in edges):
        raise ValueError("same-source 3D lower rim edge missing")
    lengths = np.linalg.norm(physical - np.roll(physical, -1, axis=0), axis=1)
    if abs(float(lengths.sum()) - original["source_3d_rim_perimeter_mm"]) > 1e-6:
        raise ValueError("original two-sided 3D cap rim lengths not identical")
    zone_ids = np.asarray([owner[e] for e in edges], dtype=int)
    if np.any(zone_ids < 0) or np.any(zone_ids >= len(NAMES)):
        raise ValueError("unknown source lower 3D attachment zone")
    mapping = {
        NAMES[int(k)]: int(np.count_nonzero(zone_ids == k)) for k in np.unique(zone_ids)
    }
    span = {
        NAMES[int(k)]: float(lengths[zone_ids == k].sum()) for k in np.unique(zone_ids)
    }
    transitions = np.flatnonzero(zone_ids != np.roll(zone_ids, 1))
    return {
        "source_cap": original["id"],
        "original_source_3D_rim_edges": len(edges),
        "original_source_3D_perimeter_mm": original["source_3d_rim_perimeter_mm"],
        "lower_zone_edges": mapping,
        "lower_zone_arcs_mm": span,
        "cross_zone_transition_count": len(transitions),
        "transition_original_3D_xyz_mm": xyz[mapped[transitions]].tolist(),
        "original_3D_join_not_paired_2D_fabric_netline": True,
    }


def _region(zone, labels, xyz, faces, topology):
    edges, counts, first, second, face_edges = topology
    selected = np.flatnonzero(labels == zone)
    used, visits = np.unique(face_edges[selected].ravel(), return_counts=True)
    boundary = edges[used[visits == 1]]
    stats = _boundary_stats(boundary, len(xyz))
    internal = (counts == 2) & (labels[first] == zone)
    internal &= labels[np.maximum(second, 0)] == zone
    links = np.column_stack((first[internal], second[internal]))
    components = _face_components(selected, links, len(faces))
    euler = int(len(np.unique(faces[selected])) - len(used) + len(selected))
    if components != 1 or stats["degree_failures"] != 0 or euler != 2 - stats["loops"]:
        raise ValueError(
            "four-zone original 3D source patch topology not disk-with-holes"
        )
    return {
        "zone": NAMES[zone],
        "source_3D_triangles": int(len(selected)),
        "source_3D_connected_components": components,
        "source_3D_boundary_loops": stats["loops"],
        "source_Euler": euler,
        "minimum_additional_topological_rim_to_rim_cuts_to_make_disk": (
            stats["loops"] - 1
        ),
        "real_fabric_2D_rest_shape_validated": False,
    }


def _partition(xyz, faces, caps, scenario):
    height = float(scenario["split_y_mm"])
    centers = xyz[faces].mean(axis=1)
    labels = (centers[:, 0] >= 0).astype(np.int8) * 2
    labels += (centers[:, 1] >= height).astype(np.int8)
    topology = _edge_ownership(faces)
    boundary, upper = _seven_source_rims(xyz, topology)
    edges, counts, first, second, _ = topology
    paired = np.column_stack((first[counts == 2], second[counts == 2]))
    if (
        len(xyz) - len(edges) + len(faces) != -5
        or _face_components(np.arange(len(faces)), paired, len(faces)) != 1
    ):
        raise ValueError("lower original 7-hole surface is disconnected")
    owners = {
        tuple(map(int, edge)): int(labels[first[index]])
        for index, edge in enumerate(edges)
        if counts[index] == 1 and abs(xyz[edge[0], 2] - 230) < 1e-7
    }
    if len(owners) != sum(RIM_COUNTS):
        raise ValueError("source head rim original lower triangles incomplete")
    ports = [_cap_source_port(xyz, cap, owners) for cap in caps["upper_caps"]]
    if [p["lower_zone_edges"] for p in ports] != list(EXPECTED_PORTS) or [
        p["cross_zone_transition_count"] for p in ports
    ] != [2, 0, 0]:
        raise ValueError("real central 95/94 plus side 113/112 source join changed")
    regions = [_region(i, labels, xyz, faces, topology) for i in range(4)]
    interfaces, _, complete, _ = _interfaces(labels, xyz, topology)
    if not complete or len(interfaces) != 4:
        raise ValueError("real four-zone 3D source seam pairing incomplete")
    if height == 20:
        measured = [
            (p["source_Euler"], p["source_3D_boundary_loops"], p["source_3D_triangles"])
            for p in regions
        ]
        if measured != list(EXPECTED_Y20):
            raise ValueError("old original source region topology changed")
    cuts = sum(
        p["minimum_additional_topological_rim_to_rim_cuts_to_make_disk"]
        for p in regions
    )
    return {
        "split_y_mm": height,
        "seven_original_3D_open_rim_edge_count": len(boundary),
        "source_3D_three_head_rim_edge_count": int(upper.sum()),
        "source_3D_four_hoof_rim_edge_count": int((~upper).sum()),
        "source_3D_lower_shell_triangles": len(faces),
        "head_crown_to_lower_zone_source_3D_interfaces": ports,
        "lower_four_zone_source_patches": regions,
        "source_3D_four_zone_shared_seams": interfaces,
        "minimum_additional_topological_opening_cuts_to_four_disks": cuts,
        "exact_3D_zone_seams_not_a_2D_cloth_pattern": True,
    }


def audit_original_seven_port_shell(source, faces, caps, original_four, trimesh_module):
    _check_locked_source(source, faces, caps, original_four)
    xyz, triangles = _clip_original_lower(source, faces, trimesh_module)
    measured = [
        _partition(xyz, triangles, caps, row) for row in original_four["scenarios"]
    ]
    if [
        row["minimum_additional_topological_opening_cuts_to_four_disks"]
        for row in measured
    ] != [6, 6]:
        raise ValueError("source 7-port/4-zone minimum opening topology changed")
    return {
        "schema": SCHEMA,
        "original_public_stage6_blend_sha256": SOURCE_SHA,
        "original_proxy_25pct_sha256": PROXY_SHA,
        "source_original_z230_head_rims": 3,
        "source_original_hoof_rims": 4,
        "source_original_3D_boundary_edges": 2462,
        "source_four_zone_comparisons": measured,
        "central_source_cap_joins_two_distinct_lower_front_regions": True,
        "side_caps_join_left_and_right_lower_front_regions": True,
        "six_additional_cuts_are_topological_lower_bound_not_manufacturing_seams": True,
        "original_source_3D_port_graph_not_2D_rest_shape": True,
        "fabric_material_and_physical_sample_not_verified": True,
        "factory_cutting_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
    }
