"""Four genuine Stage6 lower-shell disks from six original-source inter-rim slits.

Only a 3D topology experiment. Source faces and the seven original cut/hoof
interfaces are immutable. No planar fabric pattern or approved hidden seams.
"""

from __future__ import annotations

from collections import Counter

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, dijkstra

from plush_pattern_lab.validation.real_panel_slit import (
    _cut_vertex_fans,
    _edges,
    _validate_cut_disk,
)
from plush_pattern_lab.validation.stage6_lower_seven_port_graph import (
    _check_locked_source,
    _clip_original_lower,
)
from plush_pattern_lab.validation.stage6_real_protrusion_bisect import (
    _ordered_boundary,
)
from plush_pattern_lab.validation.whole_shell_partition import NAMES

SCHEMA = "stage6-seven-original-ports-six-source-interrim-disk-cuts-v1"
QA_SCHEMA = "stage6-real-lower-seven-3d-rims-four-zone-interface-audit-v1"
SOURCE_RIM_COUNT = (113, 112)
EXPECTED_FACES = (34579, 21703, 34260, 21436)
EXPECTED_BORDERS = (3, 2, 3, 2)


def _boundary(mesh):
    edges, inverse, counts, _, _ = _edges(mesh["faces"], len(mesh["xyz"]))
    border = edges[counts == 1]
    if len(border) < 8:
        raise ValueError("source-zone boundary is missing")
    n = len(mesh["xyz"])
    graph = coo_matrix(
        (
            np.ones(len(border) * 2, dtype=np.int8),
            (
                np.r_[border[:, 0], border[:, 1]],
                np.r_[border[:, 1], border[:, 0]],
            ),
        ),
        shape=(n, n),
    ).tocsr()
    _, labels = connected_components(graph, directed=False)
    grouped = []
    for group in np.unique(labels[border[:, 0]]):
        selection = border[labels[border[:, 0]] == group]
        ids = np.unique(selection)
        degrees = np.bincount(selection.ravel(), minlength=n)
        if len(ids) < 3 or np.any(degrees[ids] != 2):
            raise ValueError("source boundary contains an open or branched loop")
        grouped.append({"vertices": ids, "edges": selection})
    return grouped, edges, inverse, counts


def _find_rims(mesh, expected_count, front, side):
    loops, _, _, _ = _boundary(mesh)
    if len(loops) != expected_count:
        raise ValueError("original lower four-zone open rim count drift")
    z = mesh["xyz"][:, 2]
    hoof = [row for row in loops if len(row["edges"]) == 512]
    ear = [row for row in loops if len(row["edges"]) == SOURCE_RIM_COUNT[side]]
    if len(hoof) != 1 or (front and len(ear) != 1):
        raise ValueError("original one-hoof and side-head boundary missing")
    if np.max(np.abs(z[hoof[0]["vertices"]] - 20)) > 0.001:
        raise ValueError("original Stage6 hoof source Z changed")
    outer = [row for row in loops if row not in hoof + ear]
    if len(outer) != 1:
        raise ValueError("main upper seam rim changed")
    return hoof[0], outer[0], ear[0] if front else None


def _shortest(mesh, source, target, forbidden=()):
    loops, edges, _, counts = _boundary(mesh)
    xyz = mesh["xyz"]
    border_vertices = set(
        np.concatenate([loop["vertices"] for loop in loops]).tolist()
    )
    src, dest = set(map(int, source)), set(map(int, target))
    if not src or not dest or src & dest:
        raise ValueError("shortest inter-rim source/target must be disjoint")
    blocked = (border_vertices - src - dest) | set(map(int, forbidden))
    eligible = (counts == 2) & ~np.isin(edges, list(blocked)).any(axis=1)
    inside = edges[eligible]
    if not len(inside):
        raise ValueError("no surviving real internal source edges")
    n = len(xyz)
    root = np.array(sorted(src), dtype=np.int64)
    extra = np.column_stack((np.full(len(root), n), root))
    network = np.vstack((inside, extra))
    length = np.linalg.norm(xyz[inside[:, 0]] - xyz[inside[:, 1]], axis=1)
    weight = np.r_[length, np.full(len(root), 1e-12)]
    graph = coo_matrix(
        (
            np.r_[weight, weight],
            (
                np.r_[network[:, 0], network[:, 1]],
                np.r_[network[:, 1], network[:, 0]],
            ),
        ),
        shape=(n + 1, n + 1),
    ).tocsr()
    dist, previous = dijkstra(graph, indices=n, return_predecessors=True)
    end = min(dest, key=lambda point: dist[point])
    if not np.isfinite(dist[end]):
        raise ValueError("the real original source rims cannot be connected")
    backwards = [end]
    while backwards[-1] != n:
        before = int(previous[backwards[-1]])
        if before < 0 or len(backwards) > n + 1:
            raise ValueError("source shortest inter-rim traceback failed")
        backwards.append(before)
    path = np.asarray(backwards[-2::-1], dtype=np.int64)
    if (
        len(path) < 2
        or len(np.unique(path)) != len(path)
        or path[0] not in src
        or path[-1] not in dest
        or set(map(int, path[1:-1])) & border_vertices
        or set(map(int, path)) & blocked
    ):
        raise ValueError("source path contacts the wrong original opening")
    distance = float(np.linalg.norm(np.diff(xyz[path], axis=0), axis=1).sum())
    if not 0 < distance < 1000:
        raise ValueError("degenerate actual Stage6 source seam length")
    return path, distance


def _cut(mesh, path, old_rim_count):
    loops, edges, inverse, counts = _boundary(mesh)
    new_faces, duplicates = _cut_vertex_fans(
        mesh["faces"], edges, inverse, counts, path
    )
    if not np.array_equal(path, duplicates):
        raise ValueError("source cut duplicated a different vertex chain")
    data = {
        "xyz": np.vstack((mesh["xyz"], mesh["xyz"][path])),
        "faces": new_faces,
        "source_id": np.r_[mesh["source_id"], mesh["source_id"][path]],
    }
    now, updated_edges, _, _ = _boundary(data)
    if len(now) != len(loops) - 1:
        raise ValueError("inter-rim source cut did not merge exactly two holes")
    if len(now) == 1:
        _validate_cut_disk(
            data["faces"],
            len(data["xyz"]),
            sum(len(loop["edges"]) for loop in loops),
            len(path) - 1,
        )
    elif len(data["xyz"]) - len(updated_edges) + len(new_faces) != 0:
        raise ValueError("first original source cut is not a two-loop annulus")
    if len(loops) != old_rim_count:
        raise ValueError("input original Stage6 number of open rims was changed")
    return data


def _zone_mesh(xyz, faces, zone):
    centers = xyz[faces].mean(axis=1)
    labels = (centers[:, 0] >= 0).astype(np.int8) * 2
    labels += (centers[:, 1] >= 20).astype(np.int8)
    selected = np.flatnonzero(labels == zone)
    original_ids, inverse = np.unique(faces[selected], return_inverse=True)
    if len(selected) != EXPECTED_FACES[zone]:
        raise ValueError("true Y20 source face counts changed")
    return {
        "xyz": xyz[original_ids],
        "faces": inverse.reshape(-1, 3),
        "source_id": original_ids,
    }, selected


def _make_cut(mesh, src, dst, forbidden, role):
    path, length = _shortest(mesh, src, dst, forbidden)
    original = mesh["source_id"][path]
    evidence = {
        "seam_role": role,
        "original_3d_clipped_lower_source_vertex_ids": original.tolist(),
        "original_3d_netline_mm": length,
        "original_source_seam_edge_count": len(path) - 1,
        "source_3d_exact_edges_not_2d_stitches": True,
    }
    return path, evidence


def _one_zone(xyz, faces, zone):
    original, face_ids = _zone_mesh(xyz, faces, zone)
    front = zone in (0, 2)
    side = zone // 2
    hoof, outer, ear = _find_rims(
        original, EXPECTED_BORDERS[zone], front, side
    )
    seams = []
    if front:
        first, proof = _make_cut(
            original,
            ear["vertices"],
            outer["vertices"],
            (),
            "high_protrusion_to_main_upper_boundary",
        )
        seams.append(proof)
        middle = _cut(original, first, 3)
        after, _, _, _ = _boundary(middle)
        foot = next(row for row in after if len(row["edges"]) == 512)
        other = next(row for row in after if row is not foot)
        source_hoof = set(map(int, original["source_id"][hoof["vertices"]]))
        original_outer = set(map(int, original["source_id"][outer["vertices"]]))
        used = set(map(int, original["source_id"][first]))
        source = [
            k for k in foot["vertices"]
            if int(middle["source_id"][k]) in source_hoof
        ]
        target = [
            k for k in other["vertices"]
            if int(middle["source_id"][k]) in original_outer - used
        ]
        forbidden = [
            k for k, value in enumerate(middle["source_id"])
            if int(value) in used
        ]
        second, proof = _make_cut(
            middle, source, target, forbidden, "hoof_to_main_upper_boundary"
        )
        seams.append(proof)
        disk = _cut(middle, second, 2)
    else:
        first, proof = _make_cut(
            original,
            hoof["vertices"],
            outer["vertices"],
            (),
            "hoof_to_main_upper_boundary",
        )
        seams.append(proof)
        disk = _cut(original, first, 2)
    final, edges, _, _ = _boundary(disk)
    if (
        len(final) != 1
        or len(disk["xyz"]) - len(edges) + len(disk["faces"]) != 1
        or not np.array_equal(
            disk["source_id"][disk["faces"]], faces[face_ids]
        )
        or len(seams) != EXPECTED_BORDERS[zone] - 1
    ):
        raise ValueError("real Stage6 original faces or disk identity changed")
    return disk, face_ids, seams, final[0]


def _paired_source_edges(disk, seams, border):
    identity = np.asarray(disk["source_id"])
    oriented = np.concatenate(
        (
            disk["faces"][:, [0, 1]],
            disk["faces"][:, [1, 2]],
            disk["faces"][:, [2, 0]],
        )
    )
    _, inverse, counts = np.unique(
        np.sort(oriented, axis=1),
        axis=0,
        return_inverse=True,
        return_counts=True,
    )
    perimeter = oriented[counts[inverse] == 1]
    copies = Counter(
        tuple(sorted((int(identity[u]), int(identity[v]))))
        for u, v in perimeter
    )
    for seam in seams:
        source = seam["original_3d_clipped_lower_source_vertex_ids"]
        for a, b in zip(source, source[1:]):
            if copies[tuple(sorted((a, b)))] != 2:
                raise ValueError("a real original source seam lacks two disk copies")
    if len(perimeter) != len(border["edges"]):
        raise ValueError("source boundary index differs from face boundary")
    return True


def build_lower_six_cut_disks(source, faces, caps, full, seven, trimesh_module):
    """Turn seven original 3D openings into four source-linked research disks."""
    _check_locked_source(source, faces, caps, full)
    if (
        seven.get("schema") != QA_SCHEMA
        or seven.get("source_original_3D_boundary_edges") != 2462
        or seven.get("factory_cutting_patterns_approved") != 0
        or seven.get("P3_status") != "in_progress"
        or seven.get("P4_status") != "not_started"
        or seven["source_four_zone_comparisons"][0]["split_y_mm"] != 20
        or seven["source_four_zone_comparisons"][0][
            "minimum_additional_topological_opening_cuts_to_four_disks"
        ] != 6
    ):
        raise ValueError("requires verified seven-real-port lower Stage6 contract")
    xyz, lower_faces = _clip_original_lower(
        source, faces, trimesh_module
    )
    zones = []
    all_source_face_ids = []
    for zone in range(4):
        disk, face_ids, seams, ring = _one_zone(xyz, lower_faces, zone)
        _paired_source_edges(disk, seams, ring)
        all_source_face_ids.extend(face_ids.tolist())
        zones.append(
            {
                "id": NAMES[zone],
                "real_original_clipped_source_face_count": len(face_ids),
                "original_lower_mesh_source_face_ids": face_ids.tolist(),
                "source_3d_xyz_mm": disk["xyz"].tolist(),
                "triangles_local_vertex_indices": disk["faces"].tolist(),
                "original_lower_mesh_vertex_id_per_disk_vertex": (
                    disk["source_id"].tolist()
                ),
                "final_original_source_disk_rim_vertex_ids_in_order": (
                    _ordered_boundary(set(map(tuple, ring["edges"])))
                ),
                "topological_Euler": 1,
                "original_source_3d_disk_seam_paths": seams,
                "source_faces_and_7_original_open_ports_preserved": True,
                "approved_factory_pattern": False,
            }
        )
    if (
        len(all_source_face_ids) != len(lower_faces)
        or set(all_source_face_ids) != set(range(len(lower_faces)))
        or [len(x["original_source_3d_disk_seam_paths"]) for x in zones]
        != [2, 1, 2, 1]
    ):
        raise ValueError("some original lower Stage6 source triangles are missing")
    return {
        "schema": SCHEMA,
        "original_stage6_blend_sha256": caps["original_public_stage6_blend_sha256"],
        "original_source_proxy_sha256": caps["source_proxy_ply_sha256"],
        "source_y_split_mm": 20.0,
        "source_3d_six_interrim_paths": sum(
            len(x["original_source_3d_disk_seam_paths"]) for x in zones
        ),
        "source_3d_total_original_lower_face_count": len(lower_faces),
        "source_topological_disks": zones,
        "source_3d_paths_and_faces_not_fabric_patterns": True,
        "factory_cutting_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
    }
