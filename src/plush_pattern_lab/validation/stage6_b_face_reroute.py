"""Source-edge B-high2 reroute experiments avoiding historic facial area.

C exits on a lower anterior boundary. D runs to a lateral high boundary.
Neither cut line is a design-approved hidden seam or a fabric rest pattern.
"""

from __future__ import annotations

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

from plush_pattern_lab.validation.multi_radial_panels import (
    _dual_labels,
    _make_panels,
    _source_pairs,
)
from plush_pattern_lab.validation.real_panel_slit import (
    _region_topology,
    _validated_source_inputs,
)

RESEARCH_ROUTES = (
    ("C_low_neck_boundary", 150.0, -78.0, -65.0),
    ("D_lateral_high_boundary", 190.0, -55.0, -5.0),
)
EXPECTED_REGION_FACES = 36833
EXPECTED_OLD_B_PANEL_FACES = (20915, 6904, 9014)
EXCLUDED_FACE_REGION = {
    "abs_x_max_mm": 20.0,
    "front_y_below_mm": -70.0,
    "face_z_above_mm": 155.0,
}


def _old_source_paths(region_ids, xyz, original):
    if len(original) != 3:
        raise ValueError("must preserve the original B three source-edge paths")
    paths = []
    for item in original:
        ids = np.asarray(item["original_source_vertex_ids"], dtype=np.int64)
        if ids.ndim != 1 or len(ids) < 2 or np.any(ids < 0):
            raise ValueError("invalid trusted original radial source path")
        local = np.searchsorted(region_ids, ids)
        if np.any(local >= len(region_ids)):
            raise ValueError("source cut edge references a foreign region vertex")
        if not np.array_equal(region_ids[local], ids):
            raise ValueError("source cut path vertex IDs differ from real region")
        length = np.linalg.norm(np.diff(xyz[ids], axis=0), axis=1).sum()
        if abs(length - item["source_3d_length_mm"]) > 1e-3:
            raise ValueError("original fixed 3D source path length changed")
        paths.append(local)
    return paths


def _candidate_targets(coords, boundary_ids, mode):
    _, z_min, y_min, y_max = mode
    near_boundary = coords[boundary_ids]
    mask = (
        (near_boundary[:, 2] >= z_min)
        & (near_boundary[:, 1] >= y_min)
        & (near_boundary[:, 1] <= y_max)
        & (near_boundary[:, 0] >= -2.0)
    )
    selected = boundary_ids[mask]
    if not len(selected):
        raise ValueError("no reachable upper boundary in chosen anatomical zone")
    return selected


def _allowed_mesh_edges(coords, interior, cuff, outer, preserved, targets, anchor):
    forbidden = np.zeros(len(coords), dtype=bool)
    forbidden[np.unique(cuff)] = True
    forbidden[np.unique(outer)] = True
    forbidden[targets] = False
    forbidden[list(set(np.concatenate(preserved).tolist()))] = True
    face = EXCLUDED_FACE_REGION
    forbidden |= (
        (np.abs(coords[:, 0]) <= face["abs_x_max_mm"])
        & (coords[:, 1] < face["front_y_below_mm"])
        & (coords[:, 2] >= face["face_z_above_mm"])
    )
    forbidden[anchor] = False
    safe_targets = targets[~forbidden[targets]]
    if not len(safe_targets):
        raise ValueError("all candidate endpoints intersect a protected source region")
    valid_edges = interior[~(forbidden[interior[:, 0]] | forbidden[interior[:, 1]])]
    return valid_edges, safe_targets


def _source_edge_shortest(coords, allowed, anchor, targets):
    lengths = np.linalg.norm(coords[allowed[:, 0]] - coords[allowed[:, 1]], axis=1)
    row = np.r_[allowed[:, 0], allowed[:, 1]]
    col = np.r_[allowed[:, 1], allowed[:, 0]]
    graph = coo_matrix(
        (np.r_[lengths, lengths], (row, col)), shape=(len(coords), len(coords))
    )
    distance, prev = dijkstra(
        graph.tocsr(), indices=anchor, return_predecessors=True, directed=False
    )
    target = int(targets[np.argmin(distance[targets])])
    if not np.isfinite(distance[target]):
        raise ValueError("no source-edge route reaches anatomically filtered boundary")
    backward = [target]
    while backward[-1] != anchor:
        nxt = int(prev[backward[-1]])
        if nxt < 0 or len(backward) > len(coords):
            raise ValueError("broken bounded shortest path in original source mesh")
        backward.append(nxt)
    return np.asarray(backward[::-1], dtype=np.int64)


def _route_candidate(coords, edges, counts, cuff, outer, paths, mode):
    anchor = int(paths[2][0])
    boundary = np.unique(outer)
    targets = _candidate_targets(coords, boundary, mode)
    allowed, safe_targets = _allowed_mesh_edges(
        coords, edges[counts == 2], cuff, outer, paths[:2], targets, anchor
    )
    return _source_edge_shortest(coords, allowed, anchor, safe_targets)


def _build_source_pieces(
    coords,
    region_ids,
    region_faces,
    selected,
    edges,
    inverse,
    counts,
    cuff,
    outer,
    paths,
):
    labels = _dual_labels(region_faces, edges, inverse, counts, paths)
    source_paths = [region_ids[p] for p in paths]
    roles = {
        "hoof": {tuple(sorted(pair)) for pair in region_ids[cuff]},
        "outer": {tuple(sorted(pair)) for pair in region_ids[outer]},
        "radial": set().union(*(_source_pairs(p) for p in source_paths)),
    }
    panels = _make_panels(
        region_faces, region_ids, selected, roles, paths, coords, labels
    )
    lengths = [
        float(np.linalg.norm(np.diff(coords[p], axis=0), axis=1).sum()) for p in paths
    ]
    return panels, source_paths, lengths


def reroute_original_b_high2(xyz, all_faces, selected, original_B_paths):
    """Same original B path0/path1 and cuff anchor; only the third path changes."""
    points, triangles, selected = _validated_source_inputs(xyz, all_faces, selected)
    if len(selected) != EXPECTED_REGION_FACES:
        raise ValueError("not the 36833-face immutable Stage6 left-front source")
    region_ids, region_faces, edges, inverse, counts, _, cuff, outer = _region_topology(
        points, triangles, selected, 512
    )
    old = _old_source_paths(region_ids, points, original_B_paths)
    coords = points[region_ids]
    result = []
    for mode in RESEARCH_ROUTES:
        new_path = _route_candidate(coords, edges, counts, cuff, outer, old, mode)
        paths = [old[0], old[1], new_path]
        panels, source_paths, lengths = _build_source_pieces(
            coords,
            region_ids,
            region_faces,
            selected,
            edges,
            inverse,
            counts,
            cuff,
            outer,
            paths,
        )
        result.append(
            {
                "candidate": mode[0],
                "target_research_constraints": {
                    "min_z_mm": mode[1],
                    "min_y_mm": mode[2],
                    "max_y_mm": mode[3],
                    "min_x_mm": -2.0,
                    "historic_face_exclusion": EXCLUDED_FACE_REGION.copy(),
                },
                "panels": panels,
                "source_paths": source_paths,
                "path_lengths_3d_mm": lengths,
                "source_face_count": sum(p["face_count"] for p in panels),
                "source_original_B_prefix_paths_exact": True,
                "source_3d_radial_seam_edges_exactly_paired": True,
                "materials_and_visible_seam_approval": False,
                "approved_for_cutting": False,
            }
        )
    return result
