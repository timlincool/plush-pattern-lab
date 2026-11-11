"""Exact original Stage6 3D source ear-root band cuts, not cloth cutting patterns.

Clip the immutable 25% original source triangles at Z230/Z235. Derived
triangle corners retain original Vertex IDs or original edge+plane identities.
Prove opposing 3D netlines match; this does NOT prove 2D fabric netlines.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, dijkstra

SCHEMA = "stage6-true-ear-root-3d-split-and-matched-seams-v1"
LOWER_Z_MM = 230
UPPER_Z_MM = 235
RESEARCH_ALLOWANCE_MM = 6.0


def _source_mesh(points, triangles, lower, upper):
    xyz = np.asarray(points, dtype=np.float64)
    tri = np.asarray(triangles)
    if (
        xyz.ndim != 2
        or xyz.shape[1] != 3
        or len(xyz) < 4
        or not np.isfinite(xyz).all()
        or tri.ndim != 2
        or tri.shape[1] != 3
        or len(tri) < 4
        or not np.issubdtype(tri.dtype, np.integer)
        or np.any(tri < 0)
        or np.any(tri >= len(xyz))
        or not 0 < lower < upper < 1000
    ):
        raise ValueError("invalid immutable original source triangle mesh")
    if min(np.min(np.abs(xyz[:, 2] - z)) for z in (lower, upper)) <= 1e-6:
        raise ValueError("source cut plane passes through original vertex")
    return xyz, tri.astype(np.int64)


def _source_position(xyz, key):
    if key[0] == "v":
        return xyz[key[1]]
    _, a, b, z = key
    u, v = xyz[a], xyz[b]
    return u + (v - u) * ((z - u[2]) / (v[2] - u[2]))


def _original_intersection_key(a, b, z):
    owners = set(a[1:3] if a[0] == "e" else a[1:])
    owners.update(b[1:3] if b[0] == "e" else b[1:])
    if len(owners) != 2:
        raise ValueError("clipped point does not lie on an original triangle edge")
    return ("e", *sorted(owners), z)


def _halfspace_clip(polygon, xyz, z, above):
    if not polygon:
        return []
    output = []
    prior = polygon[-1]
    prior_inside = (_source_position(xyz, prior)[2] >= z) if above else (
        _source_position(xyz, prior)[2] <= z
    )
    for current in polygon:
        current_inside = (_source_position(xyz, current)[2] >= z) if above else (
            _source_position(xyz, current)[2] <= z
        )
        if current_inside != prior_inside:
            output.append(_original_intersection_key(prior, current, z))
        if current_inside:
            output.append(current)
        prior, prior_inside = current, current_inside
    return output


def _face_cycle(xyz, face, low, high):
    corners = [("v", int(i)) for i in face]
    if low is not None:
        corners = _halfspace_clip(corners, xyz, low, True)
    if high is not None:
        corners = _halfspace_clip(corners, xyz, high, False)
    unique = []
    for key in corners:
        if not unique or key != unique[-1]:
            unique.append(key)
    if len(unique) > 1 and unique[0] == unique[-1]:
        unique.pop()
    return unique


def _insert_source_polygon(xyz, polygon, face_id, index, faces, source_ids):
    if len(polygon) < 3:
        return
    points = np.asarray([_source_position(xyz, key) for key in polygon])
    if np.linalg.norm(np.cross(points[1] - points[0], points[2] - points[0])) < 1e-10:
        return
    local = []
    for key in polygon:
        if key not in index:
            index[key] = len(index)
        local.append(index[key])
    for i in range(1, len(local) - 1):
        area2 = np.linalg.norm(
            np.cross(points[i] - points[0], points[i + 1] - points[0])
        )
        if area2 > 1e-10:
            faces.append((local[0], local[i], local[i + 1]))
            source_ids.append(face_id)


def clip_original_source_zone(xyz, triangles, low=None, high=None):
    """Keep original source face IDs and canonical cut-edge/height identities."""
    verts = {}
    result, parents = [], []
    for face_id, face in enumerate(triangles):
        heights = xyz[face, 2]
        if (low is not None and heights.max() < low) or (
            high is not None and heights.min() > high
        ):
            continue
        polygon = _face_cycle(xyz, face, low, high)
        _insert_source_polygon(xyz, polygon, face_id, verts, result, parents)
    keys = list(verts)
    return {
        "xyz": np.asarray([_source_position(xyz, key) for key in keys]),
        "faces": np.asarray(result, dtype=np.int64),
        "keys": keys,
        "source_face_ids": np.asarray(parents, dtype=np.int64),
    }


def _unique_face_edges(faces):
    raw = np.concatenate((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]))
    unique, inverse, counts = np.unique(
        np.sort(raw, axis=1), axis=0, return_inverse=True, return_counts=True
    )
    if np.any(counts > 2):
        raise ValueError("derived original source split contains nonmanifold edge")
    return raw, unique, inverse, counts


def _face_groups(zone):
    _, _, inverse, counts = _unique_face_edges(zone["faces"])
    ranked = np.argsort(inverse, kind="stable")
    starts = np.cumsum(counts) - counts
    shared = np.flatnonzero(counts == 2)
    owners = np.tile(np.arange(len(zone["faces"])), 3)
    pairs = np.column_stack(
        (owners[ranked[starts[shared]]], owners[ranked[starts[shared] + 1]])
    )
    graph = coo_matrix(
        (
            np.ones(2 * len(pairs), dtype=np.int8),
            (np.r_[pairs[:, 0], pairs[:, 1]], np.r_[pairs[:, 1], pairs[:, 0]]),
        ),
        shape=(len(zone["faces"]), len(zone["faces"])),
    ).tocsr()
    count, ids = connected_components(graph, directed=False)
    return [np.flatnonzero(ids == k) for k in range(count)]


def _source_border(faces):
    _, edges, _, counts = _unique_face_edges(faces)
    boundary = edges[counts == 1]
    euler = len(np.unique(faces)) - len(edges) + len(faces)
    neighbors = defaultdict(list)
    for a, b in boundary:
        neighbors[int(a)].append(int(b))
        neighbors[int(b)].append(int(a))
    if any(len(group) != 2 for group in neighbors.values()):
        raise ValueError("derived source patch boundary is open or branched")
    remaining = set(neighbors)
    loops = []
    while remaining:
        start = min(remaining)
        old, current = -1, start
        loop = []
        while current in remaining:
            remaining.remove(current)
            loop.append(current)
            onward = next(i for i in sorted(neighbors[current]) if i != old)
            old, current = current, onward
        if current != start:
            raise ValueError("derived source boundary did not close")
        loops.append(loop)
    return boundary, euler, loops


def _components(zone):
    output = []
    for face_ids in _face_groups(zone):
        faces = zone["faces"][face_ids]
        border, euler, loops = _source_border(faces)
        vertices = np.unique(faces)
        output.append(
            {
                "faces": faces,
                "face_ids": face_ids,
                "vertices": vertices,
                "boundary": border,
                "boundary_loops": loops,
                "euler": euler,
                "centroid": zone["xyz"][vertices].mean(axis=0),
            }
        )
    return output


def _side_component(components, side):
    parts = [
        row
        for row in components
        if (row["centroid"][0] < -35 if side == "left" else row["centroid"][0] > 35)
    ]
    if len(parts) != 1:
        raise ValueError("original ear region does not have exactly one side component")
    return parts[0]


def _seam_edges(zone, component, height):
    xyz = zone["xyz"]
    border = component["boundary"]
    chosen = border[np.all(np.abs(xyz[border, 2] - height) < 1e-7, axis=1)]
    result = {}
    for a, b in chosen:
        first, second = zone["keys"][a], zone["keys"][b]
        if first[0] != "e" or second[0] != "e":
            raise ValueError("seam is not tied to actual original crossed source edges")
        result[tuple(sorted((first, second)))] = (int(a), int(b))
    return result


def _oriented_edges(zone, component, height):
    faces = component["faces"]
    raw, _, inverse, counts = _unique_face_edges(faces)
    boundary_ids = set(np.flatnonzero(counts == 1).tolist())
    oriented = {}
    for idx, (a, b) in enumerate(raw):
        if inverse[idx] not in boundary_ids:
            continue
        first, second = zone["keys"][a], zone["keys"][b]
        if first[0] == second[0] == "e" and first[3] == second[3] == height:
            oriented[tuple(sorted((first, second)))] = (first, second)
    return oriented


def _ordered_original_seam_keys(segments):
    """Return one simple original crossed-edge loop, with stable start/direction."""
    neighbors = defaultdict(list)
    for a, b in segments:
        neighbors[a].append(b)
        neighbors[b].append(a)
    if any(len(item) != 2 for item in neighbors.values()):
        raise ValueError("original source cut is not a simple two-degree ring")
    start = min(neighbors)
    loop = [start]
    previous = None
    current = start
    while True:
        other = min(i for i in neighbors[current] if i != previous)
        if other == start:
            break
        if other in loop or len(loop) > len(segments):
            raise ValueError("source seam double-backed or failed to close")
        loop.append(other)
        previous, current = current, other
    if len(loop) != len(segments):
        raise ValueError("source cut has untraced or nested extra segments")
    return loop


def _paired_seam(a, ca, b, cb, height, subset=False):
    first = _seam_edges(a, ca, height)
    second = _seam_edges(b, cb, height)
    if (not set(second).issubset(first)) if subset else (set(first) != set(second)):
        raise ValueError("two real source 3D seam boundaries do not match")
    if len(second) < 3:
        raise ValueError("original source seam has too few segments")
    winding_a, winding_b = (
        _oriented_edges(a, ca, height),
        _oriented_edges(b, cb, height),
    )
    if any(winding_a[key] != tuple(reversed(value)) for key, value in winding_b.items()):
        raise ValueError("original paired surface seams do not have opposite winding")
    coords_a = {a["keys"][idx]: a["xyz"][idx] for item in first.values() for idx in item}
    coords_b = {b["keys"][idx]: b["xyz"][idx] for item in second.values() for idx in item}
    if max(float(np.max(np.abs(coords_a[k] - p))) for k, p in coords_b.items()) > 1e-9:
        raise ValueError("original paired source seam XYZ locations do not agree")
    perimeter = sum(
        float(np.linalg.norm(coords_a[start] - coords_a[end]))
        for start, end in second
    )
    ordered = _ordered_original_seam_keys(second)
    return {
        "source_plane_z_mm": height,
        "original_crossed_source_triangle_segment_count": len(second),
        "paired_3d_netline_length_each_side_mm": perimeter,
        "max_source_3d_pair_position_error_mm": 0.0,
        "matching_original_source_seam_edge_keys": [
            [list(a), list(b)] for a, b in sorted(second)
        ],
        "original_source_3d_ordered_ring_vertex_keys": [
            list(key) for key in ordered
        ],
        "original_source_3d_ordered_ring_xyz_mm": [
            coords_a[key].tolist() for key in ordered
        ],
        "two_source_3d_sides_exactly_same_with_opposite_face_winding": True,
        "not_a_validated_two_sided_fabric_2d_netline": True,
    }


def _surface_graph_width(zone, component, low, high):
    _, edges, _, _ = _unique_face_edges(component["faces"])
    xyz = zone["xyz"]
    length = np.linalg.norm(xyz[edges[:, 0]] - xyz[edges[:, 1]], axis=1)
    a, b = edges[:, 0], edges[:, 1]
    lower = np.unique([v for pair in _seam_edges(zone, component, low).values() for v in pair])
    upper = np.unique([v for pair in _seam_edges(zone, component, high).values() for v in pair])
    origin = len(xyz)
    rows = np.r_[a, b, np.full(len(lower), origin), lower]
    cols = np.r_[b, a, lower, np.full(len(lower), origin)]
    weights = np.r_[length, length, np.full(2 * len(lower), 1e-12)]
    graph = coo_matrix((weights, (rows, cols)), shape=(origin + 1, origin + 1))
    distance = dijkstra(graph.tocsr(), directed=False, indices=origin)[upper]
    if not np.isfinite(distance).all():
        raise ValueError("original ear root has disconnected top seam")
    return {
        "upper_seam_source_intersection_vertex_count": len(upper),
        "surface_graph_shortest_path_min_p05_median_p95_max_mm": np.quantile(
            distance, (0, 0.05, 0.5, 0.95, 1)
        ).tolist(),
        "fraction_upper_source_seam_under_12mm_graph_width": float(
            np.mean(distance < 2 * RESEARCH_ALLOWANCE_MM)
        ),
        "below_two_research_6mm_allowances_somewhere": bool(
            distance.min() < 2 * RESEARCH_ALLOWANCE_MM
        ),
        "source_triangle_graph_distance_is_upper_bound_on_real_surface_geodesic": True,
        "this_is_not_2d_fabric_usable_allowance": True,
    }


def _surface_area(points, faces):
    xyz = points[faces]
    return float(
        (0.5 * np.linalg.norm(
            np.cross(xyz[:, 1] - xyz[:, 0], xyz[:, 2] - xyz[:, 0]), axis=1
        )).sum()
    )


def _component_info(zone, component):
    return {
        "derived_source_triangle_count": len(component["faces"]),
        "original_source_face_count": len(np.unique(
            zone["source_face_ids"][component["face_ids"]]
        )),
        "derived_source_vertex_count": len(component["vertices"]),
        "source_surface_area_mm2": _surface_area(zone["xyz"], component["faces"]),
        "euler_characteristic": component["euler"],
        "closed_boundary_loop_count": len(component["boundary_loops"]),
    }


def _source_band_geometry(zone, component):
    """Derived patch triangle faces plus their immutable original source IDs."""
    source = component["vertices"]
    local_faces = np.searchsorted(source, component["faces"])
    return {
        "source_3d_xyz_mm": zone["xyz"][source].tolist(),
        "original_source_vertex_or_edge_plane_keys": [
            list(zone["keys"][int(i)]) for i in source
        ],
        "derived_triangle_local_vertex_ids": local_faces.tolist(),
        "each_derived_face_original_triangle_id": zone["source_face_ids"][
            component["face_ids"]
        ].tolist(),
        "not_industrial_2d_paper_pattern": True,
    }


def _ear_components(zones, parts, side, low, high):
    root = _side_component(parts["root"], side)
    cap = _side_component(parts["above"], side)
    body = parts["below"][0]
    if root["euler"] != 0 or len(root["boundary_loops"]) != 2 or cap["euler"] != 1:
        raise ValueError("root annulus or ear tip cap source topology invalid")
    if (
        len(_seam_edges(zones["root"], root, low))
        + len(_seam_edges(zones["root"], root, high))
        != len(root["boundary"])
    ):
        raise ValueError("derived ear root contains an additional unpaired border")
    return {
        "side": side,
        "actual_3d_root_band": _component_info(zones["root"], root),
        "derived_3d_root_band_mesh_research_only": _source_band_geometry(
            zones["root"], root
        ),
        "actual_3d_ear_upper_tip": _component_info(zones["above"], cap),
        "body_to_root_3d_paired_netline": _paired_seam(
            zones["below"], body, zones["root"], root, low, subset=True
        ),
        "root_to_upper_ear_3d_paired_netline": _paired_seam(
            zones["root"], root, zones["above"], cap, high
        ),
        "between_two_3d_seams_source_surface_graph": _surface_graph_width(
            zones["root"], root, low, high
        ),
        "real_source_2d_paper_pattern_generated": False,
        "material_and_turning_test_passed": False,
    }


def analyze_real_source_ear_root_bands(points, triangles, lower=LOWER_Z_MM, upper=UPPER_Z_MM):
    """Cut actual source triangles in memory; pair body↔root↔ear tip seams."""
    xyz, faces = _source_mesh(points, triangles, lower, upper)
    zones = {
        "below": clip_original_source_zone(xyz, faces, None, lower),
        "root": clip_original_source_zone(xyz, faces, lower, upper),
        "above": clip_original_source_zone(xyz, faces, upper, None),
    }
    parts = {name: _components(zone) for name, zone in zones.items()}
    if [len(parts[x]) for x in ("below", "root", "above")] != [1, 3, 3]:
        raise ValueError("not the locked Stage6 1/3/3 source 3D zone topology")
    original_area = _surface_area(xyz, faces)
    reconstructed = sum(
        _surface_area(zone["xyz"], zone["faces"]) for zone in zones.values()
    )
    if abs(original_area - reconstructed) > 1e-4:
        raise ValueError("original source 3D triangle area was lost during cut")
    return {
        "schema": SCHEMA,
        "original_source_vertex_count": len(xyz),
        "original_source_triangle_count": len(faces),
        "research_z_levels_mm": [lower, upper],
        "original_source_area_mm2": original_area,
        "area_after_exact_triangle_clipping_mm2": reconstructed,
        "source_area_absolute_reconstruction_error_mm2": abs(original_area - reconstructed),
        "source_cut_zone_component_counts": {
            key: len(value) for key, value in parts.items()
        },
        "original_source_ear_root_band_patches": [
            _ear_components(zones, parts, side, lower, upper)
            for side in ("left", "right")
        ],
        "original_sculpt_mesh_unchanged": True,
        "seam_3d_pairing_not_2d_material_rest_shape": True,
        "original_center_head_kept_not_manufacturer_cut_line": True,
        "approved_factory_cutting_patterns": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
    }
