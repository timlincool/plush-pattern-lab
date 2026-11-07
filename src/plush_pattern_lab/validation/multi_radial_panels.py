"""Split a source-linked annulus using disjoint original 3D mesh-edge arcs.

Every face belongs to exactly one topological disk. Original XYZ, source
face IDs, hoof ring and cross-zone seams are unchanged. RESEARCH ONLY.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, dijkstra

from plush_pattern_lab.validation.real_panel_slit import (
    _region_topology,
    _validated_source_inputs,
)


def _unique_edges(faces):
    f = np.asarray(faces, dtype=np.int64)
    pairs = np.concatenate((f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]))
    return np.unique(
        np.sort(pairs, axis=1),
        axis=0,
        return_inverse=True,
        return_counts=True,
    )


def _boundary_components(edges, vertex_count):
    ids = np.unique(edges)
    degree = np.bincount(edges.ravel(), minlength=vertex_count)
    if not len(ids) or np.any(degree[ids] != 2):
        raise ValueError("open or branched manufactured panel boundary")
    a = np.r_[edges[:, 0], edges[:, 1]]
    b = np.r_[edges[:, 1], edges[:, 0]]
    graph = coo_matrix((np.ones(len(a)), (a, b)), shape=(vertex_count, vertex_count))
    _, labels = connected_components(graph.tocsr(), directed=False)
    return len(np.unique(labels[ids]))


def _ordered_cuff(cuff, initial_vertex):
    adjacent = defaultdict(list)
    for a, b in cuff:
        adjacent[int(a)].append(int(b))
        adjacent[int(b)].append(int(a))
    if len(adjacent) != len(cuff) or any(len(v) != 2 for v in adjacent.values()):
        raise ValueError("non-simple source cuff ring")
    if initial_vertex not in adjacent:
        raise ValueError("source slit did not originate at a cuff vertex")
    order = [int(initial_vertex)]
    for _ in range(len(cuff) - 1):
        prev = order[-2] if len(order) > 1 else None
        nxt = sorted(n for n in adjacent[order[-1]] if n != prev)
        if not nxt or nxt[0] in order:
            raise ValueError("cuff ring is not a simple closed loop")
        order.append(nxt[0])
    if order[0] not in adjacent[order[-1]]:
        raise ValueError("cuff ring did not close")
    return np.asarray(order, dtype=np.int64)


def _route_high(coords, edges, counts, cuff, outer, anchor, forbidden, minimum_z):
    if not np.isfinite(minimum_z):
        raise ValueError("invalid outer seam target height")
    n = len(coords)
    cuff_ids = np.unique(cuff)
    outer_ids = np.unique(outer)
    allowed = outer_ids[coords[outer_ids, 2] >= minimum_z]
    if not len(allowed):
        raise ValueError("no outer boundary endpoint above requested height")
    blocked = np.zeros(n, dtype=bool)
    blocked[cuff_ids] = True
    blocked[anchor] = False
    blocked[outer_ids] = True
    blocked[allowed] = False
    blocked[list(forbidden)] = True
    if blocked[anchor]:
        raise ValueError("two slit paths share the same cuff source vertex")
    interior = edges[counts == 2]
    keep = ~(blocked[interior[:, 0]] | blocked[interior[:, 1]])
    valid = interior[keep]
    weight = np.linalg.norm(coords[valid[:, 0]] - coords[valid[:, 1]], axis=1)
    pairs = np.r_[valid[:, 0], valid[:, 1]]
    other = np.r_[valid[:, 1], valid[:, 0]]
    graph = coo_matrix((np.r_[weight, weight], (pairs, other)), shape=(n, n))
    distance, parent = dijkstra(
        graph.tocsr(), directed=False, indices=anchor, return_predecessors=True
    )
    endpoint = int(allowed[np.argmin(distance[allowed])])
    if not np.isfinite(distance[endpoint]):
        raise ValueError("no disjoint source-edge path reaches requested outer seam")
    backward = [endpoint]
    while backward[-1] != anchor:
        step = int(parent[backward[-1]])
        if step < 0 or len(backward) > n:
            raise ValueError("broken source-edge slit traceback")
        backward.append(step)
    return np.asarray(backward[::-1], dtype=np.int64)


def _dual_labels(faces, source_edges, inverse, counts, paths):
    cut = {
        tuple(sorted((int(a), int(b))))
        for path in paths
        for a, b in zip(path[:-1], path[1:])
    }
    if len(cut) != sum(len(path) - 1 for path in paths):
        raise ValueError("cut paths share a source edge")
    owners = np.tile(np.arange(len(faces)), 3)
    order = np.argsort(inverse, kind="stable")
    begins = np.cumsum(counts) - counts
    ids = np.flatnonzero(counts == 2)
    endpoints = np.column_stack(
        (owners[order[begins[ids]]], owners[order[begins[ids] + 1]])
    )
    keep = np.fromiter(
        (tuple(edge) not in cut for edge in source_edges[ids]),
        dtype=bool,
        count=len(ids),
    )
    attached = endpoints[keep]
    row = np.r_[attached[:, 0], attached[:, 1]]
    col = np.r_[attached[:, 1], attached[:, 0]]
    graph = coo_matrix((np.ones(len(row)), (row, col)), shape=(len(faces), len(faces)))
    parts, labels = connected_components(graph.tocsr(), directed=False)
    if parts != len(paths):
        raise ValueError("radial seams did not split into expected number of disks")
    return labels


def _source_pairs(path):
    return {tuple(sorted((int(a), int(b)))) for a, b in zip(path[:-1], path[1:])}


def _panel(face_ids, region_faces, source_vertices, source_face_ids, roles, paths, xyz):
    original_faces = region_faces[face_ids]
    used = np.unique(original_faces)
    new_faces = np.searchsorted(used, original_faces)
    edges, _, counts = _unique_edges(new_faces)
    border = edges[counts == 1]
    euler = len(used) - len(edges) + len(face_ids)
    if euler != 1 or _boundary_components(border, len(used)) != 1:
        raise ValueError("one manufacturing panel is not a topological disk")
    global_vertices = source_vertices[used]
    classified = defaultdict(list)
    for a, b in global_vertices[border]:
        pair = tuple(sorted((int(a), int(b))))
        matches = [key for key, ids in roles.items() if pair in ids]
        if len(matches) != 1:
            raise ValueError("unpaired or multiply classified 3D boundary edge")
        classified[matches[0]].append([int(a), int(b)])
    for key in ("hoof", "outer", "radial"):
        if not classified[key]:
            raise ValueError("panel missing cuff, outer or radial source boundary")
    first = next((p for p in paths if np.all(np.isin(p, used))), None)
    if first is None:
        raise ValueError("panel has no full radial arc for UV pins")
    start = int(np.searchsorted(used, first[0]))
    end = int(np.searchsorted(used, first[-1]))
    arc_length = float(np.linalg.norm(np.diff(xyz[first], axis=0), axis=1).sum())
    return {
        "face_count": len(face_ids),
        "vertex_count": len(used),
        "boundary_edge_count": len(border),
        "disk_euler": euler,
        "source_face_ids": source_face_ids[face_ids],
        "source_vertex_ids": global_vertices,
        "faces": new_faces,
        "boundary_edges": border,
        "points_xyz_mm": xyz[used],
        "source_cuff_edges": len(classified["hoof"]),
        "source_outer_seam_edges": len(classified["outer"]),
        "source_cuff_edge_global_ids": classified["hoof"],
        "source_outer_edge_global_ids": classified["outer"],
        "source_slit_edge_global_ids": classified["radial"],
        "slit_pin_inner_id": start,
        "slit_pin_outer_id": end,
        "slit_path_length_3d_mm": arc_length,
        "cutting_approved": False,
    }


def _assert_source_edge_pairing(panels, roles):
    counted = defaultdict(int)
    for panel in panels:
        for key in (
            "source_cuff_edge_global_ids",
            "source_outer_edge_global_ids",
            "source_slit_edge_global_ids",
        ):
            for pair in panel[key]:
                counted[tuple(sorted(pair))] += 1
    for label, pairs in roles.items():
        required = 2 if label == "radial" else 1
        if any(counted[pair] != required for pair in pairs):
            raise ValueError("source seam edges lack exact two-sided pairing")
    if set(counted) != set().union(*roles.values()):
        raise ValueError("unexpected source boundary edge")


def _make_panels(region_faces, region_vertices, selected, roles, paths, xyz, labels):
    panels = [
        _panel(
            np.flatnonzero(labels == i),
            region_faces,
            region_vertices,
            selected,
            roles,
            paths,
            xyz,
        )
        for i in range(len(paths))
    ]
    _assert_source_edge_pairing(panels, roles)
    if sum(row["face_count"] for row in panels) != len(selected):
        raise ValueError("source faces lost or duplicated by radial cutting")
    return panels


def split_annulus_by_radial_paths(
    xyz,
    all_faces,
    selected,
    base_source_path,
    extra_specs,
    expected_cuff_edges=512,
):
    """Return source-verified 2/3 disk candidates from one real annulus.

    extra_specs: (fraction of ordered original cuff, minimum outer Z in mm).
    The fraction is NOT an anatomically approved seam orientation.
    """
    points, all_faces, selected = _validated_source_inputs(xyz, all_faces, selected)
    region_vertices, region_faces, edges, inverse, counts, _, cuff, outer = (
        _region_topology(points, all_faces, selected, expected_cuff_edges)
    )
    source_base = np.asarray(base_source_path, dtype=np.int64)
    local_base = np.searchsorted(region_vertices, source_base)
    if np.any(local_base >= len(region_vertices)) or not np.array_equal(
        region_vertices[local_base], source_base
    ):
        raise ValueError("baseline slit source vertex identities changed")
    if not 1 <= len(extra_specs) <= 2:
        raise ValueError("only one or two extra radial cuts are supported")
    cuff_order = _ordered_cuff(cuff, int(local_base[0]))
    paths = [local_base]
    used = set(local_base.tolist())
    coords = points[region_vertices]
    for fraction, min_z in extra_specs:
        if not 0 < fraction < 1:
            raise ValueError("invalid cuff arc fraction")
        anchor = int(cuff_order[round(fraction * len(cuff_order)) % len(cuff_order)])
        path = _route_high(coords, edges, counts, cuff, outer, anchor, used, min_z)
        paths.append(path)
        used.update(path.tolist())
    interiors = {tuple(edge) for edge in edges[counts == 2]}
    if any(
        tuple(sorted((int(a), int(b)))) not in interiors
        for path in paths
        for a, b in zip(path[:-1], path[1:])
    ):
        raise ValueError("radial route is not an original interior triangle edge")
    labels = _dual_labels(region_faces, edges, inverse, counts, paths)
    source_paths = [region_vertices[path] for path in paths]
    roles = {
        "hoof": {tuple(sorted(pair)) for pair in region_vertices[cuff]},
        "outer": {tuple(sorted(pair)) for pair in region_vertices[outer]},
        "radial": set().union(*(_source_pairs(p) for p in source_paths)),
    }
    panels = _make_panels(
        region_faces, region_vertices, selected, roles, paths, coords, labels
    )
    return {
        "panels": panels,
        "source_paths": source_paths,
        "path_lengths_3d_mm": [
            float(np.linalg.norm(np.diff(coords[path], axis=0), axis=1).sum())
            for path in paths
        ],
        "research_extra_specs": [
            [float(fraction), float(height)] for fraction, height in extra_specs
        ],
        "source_faces_unmodified": True,
        "source_3d_seams_exactly_paired": True,
        "approved_for_cutting": False,
    }
