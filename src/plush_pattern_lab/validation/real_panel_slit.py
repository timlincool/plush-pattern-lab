"""Cut a real annular triangle shell along one shortest source-mesh edge path.

Preserve every original 3D face and 3D seam edge. The cut duplicates only
vertex identities in the unfolded topology. All geometry uses millimetres.
No factory-ready rest pattern, allowance, or fabric property is implied.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, dijkstra


def _edges(triangles, vertex_count):
    n = len(triangles)
    ordered = np.concatenate(
        (triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]])
    )
    unique, inverse, counts = np.unique(
        np.sort(ordered, axis=1), axis=0, return_inverse=True, return_counts=True
    )
    if np.any(counts > 2):
        raise ValueError("nonmanifold source or panel triangle edges")
    keys = unique[:, 0] * vertex_count + unique[:, 1]
    return unique, inverse, counts, keys, n


def _components(n, edges):
    if not len(edges):
        return n
    r = np.r_[edges[:, 0], edges[:, 1]]
    c = np.r_[edges[:, 1], edges[:, 0]]
    graph = coo_matrix(
        (np.ones(len(r), dtype=np.int8), (r, c)), shape=(n, n)
    ).tocsr()
    return connected_components(graph, directed=False, return_labels=False)


def _boundary_check(edges, vertex_count):
    if not len(edges):
        raise ValueError("empty panel boundary")
    ids = np.unique(edges)
    degree = np.bincount(edges.ravel(), minlength=vertex_count)
    if np.any(degree[ids] != 2):
        raise ValueError("a panel boundary is branched or has loose endpoints")
    graph = coo_matrix(
        (
            np.ones(2 * len(edges), dtype=np.int8),
            (
                np.r_[edges[:, 0], edges[:, 1]],
                np.r_[edges[:, 1], edges[:, 0]],
            ),
        ),
        shape=(vertex_count, vertex_count),
    ).tocsr()
    _, groups = connected_components(graph, directed=False)
    return len(np.unique(groups[ids]))


def _path_to_outer(coords, edge_ids, counts, cuff_ids, outer_ids):
    """Multi-source shortest path; original mesh boundary edges are excluded."""
    interiors = edge_ids[counts == 2]
    lengths = np.linalg.norm(
        coords[interiors[:, 0]] - coords[interiors[:, 1]], axis=1
    )
    if not len(interiors) or np.any(lengths <= 0):
        raise ValueError("invalid non-boundary edge lengths")
    n = len(coords)
    extra = np.column_stack((np.full(len(cuff_ids), n), cuff_ids))
    network = np.concatenate((interiors, extra))
    weights = np.r_[lengths, np.full(len(cuff_ids), 1e-10)]
    graph = coo_matrix(
        (
            np.r_[weights, weights],
            (
                np.r_[network[:, 0], network[:, 1]],
                np.r_[network[:, 1], network[:, 0]],
            ),
        ),
        shape=(n + 1, n + 1),
    ).tocsr()
    distances, predecessors = dijkstra(
        graph, directed=False, indices=n, return_predecessors=True
    )
    end = int(outer_ids[np.argmin(distances[outer_ids])])
    if not np.isfinite(distances[end]):
        raise ValueError("cuff and outer boundary cannot be joined")
    reversed_path = [end]
    while reversed_path[-1] != n:
        old = int(predecessors[reversed_path[-1]])
        if old < 0 or len(reversed_path) > n:
            raise ValueError("invalid shortest slit traceback")
        reversed_path.append(old)
    path = np.array(reversed_path[-2::-1], dtype=np.int64)
    if len(path) < 2 or len(np.unique(path)) != len(path):
        raise ValueError("cut path repeats vertices")
    if set(path) & set(cuff_ids) != {int(path[0])}:
        raise ValueError("cut crosses an additional hoof boundary vertex")
    if set(path) & set(outer_ids) != {int(path[-1])}:
        raise ValueError("cut crosses an additional outer boundary vertex")
    total = np.linalg.norm(coords[path[1:]] - coords[path[:-1]], axis=1)
    return path, float(total.sum())


def _cut_vertex_fans(triangles, edge_ids, inverse, counts, path):
    """Duplicate each slit vertex exactly once by its two incident face fans."""
    n = int(triangles.max()) + 1
    faces = triangles.copy()
    owners = np.tile(np.arange(len(faces)), 3)
    sort = np.argsort(inverse, kind="stable")
    starts = np.cumsum(counts) - counts
    edge_owners = np.full((len(edge_ids), 2), -1, dtype=np.int64)
    edge_owners[:, 0] = owners[sort[starts]]
    double = counts == 2
    edge_owners[double, 1] = owners[sort[starts[double] + 1]]
    cut_edges = {
        tuple(sorted((int(a), int(b)))) for a, b in zip(path[:-1], path[1:])
    }
    fan_links = defaultdict(list)
    slit_vertices = set(path.tolist())
    for ei, (a, b) in enumerate(edge_ids):
        if counts[ei] != 2 or (int(a), int(b)) in cut_edges:
            continue
        if a in slit_vertices:
            fan_links[int(a)].append(edge_owners[ei])
        if b in slit_vertices:
            fan_links[int(b)].append(edge_owners[ei])
    duplicates = []
    for point in path:
        point = int(point)
        incident = np.flatnonzero(np.any(triangles == point, axis=1))
        parent = {int(face): int(face) for face in incident}

        def find(index):
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        for first, second in fan_links[point]:
            parent[find(int(first))] = find(int(second))
        groups = defaultdict(list)
        for face in incident:
            groups[find(int(face))].append(int(face))
        if len(groups) != 2:
            raise ValueError("slit vertex does not have exactly two face fans")
        chosen = sorted(groups.values(), key=min)
        new_vertex = n + len(duplicates)
        duplicates.append(point)
        for face in chosen[1]:
            column = np.flatnonzero(faces[face] == point)
            if len(column) != 1:
                raise ValueError("slit face has ambiguous original vertex")
            faces[face, column[0]] = new_vertex
    return faces, np.asarray(duplicates, dtype=np.int64)


def _validate_cut_disk(faces, size, original_boundary, slit_edges):
    unique, inverse, counts, _, _ = _edges(faces, size)
    border = unique[counts == 1]
    expected = original_boundary + 2 * slit_edges
    if len(border) != expected or _boundary_check(border, size) != 1:
        raise ValueError("slit did not make a single closed outer boundary")
    if size - len(unique) + len(faces) != 1:
        raise ValueError("slit mesh is not an Euler-1 topological disk")
    owners = np.tile(np.arange(len(faces)), 3)
    order = np.argsort(inverse, kind="stable")
    starts = np.cumsum(counts) - counts
    linked = counts == 2
    pairs = np.column_stack(
        (owners[order[starts[linked]]], owners[order[starts[linked] + 1]])
    )
    if _components(len(faces), pairs) != 1:
        raise ValueError("slit triangle surface became disconnected")
    return border


def slit_real_panel(vertices_mm, whole_faces, face_ids, expected_cuff_edges=512):
    """Return a real full-panel disk and source-index map, not approved cut lines."""
    xyz = np.asarray(vertices_mm, dtype=np.float64)
    whole = np.asarray(whole_faces)
    selected = np.asarray(face_ids)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or not np.isfinite(xyz).all():
        raise ValueError("expected finite world-mm vertex coordinates")
    if whole.ndim != 2 or whole.shape[1] != 3:
        raise ValueError("expected a triangle source shell")
    if not np.issubdtype(whole.dtype, np.integer):
        raise ValueError("source face indices must be integers")
    if selected.ndim != 1 or len(selected) < 4:
        raise ValueError("expected selected source face indices")
    if not np.issubdtype(selected.dtype, np.integer):
        raise ValueError("selected face indices must be integral")
    if (selected < 0).any() or (selected >= len(whole)).any():
        raise ValueError("selected source faces out of range")
    if len(np.unique(selected)) != len(selected):
        raise ValueError("repeated source face index")
    if (whole < 0).any() or (whole >= len(xyz)).any():
        raise ValueError("invalid source shell face vertex")
    global_edges, _, global_counts, global_keys, _ = _edges(whole, len(xyz))
    region = whole[selected]
    vertices = np.unique(region.ravel())
    local_map = np.full(len(xyz), -1, dtype=np.int32)
    local_map[vertices] = np.arange(len(vertices))
    triangle = local_map[region].astype(np.int64)
    edges, inverse, counts, keys, _ = _edges(triangle, len(vertices))
    source_edge_lookup = np.searchsorted(
        global_keys,
        np.minimum(vertices[edges[:, 0]], vertices[edges[:, 1]]) * len(xyz)
        + np.maximum(vertices[edges[:, 0]], vertices[edges[:, 1]]),
    )
    if np.any(source_edge_lookup >= len(global_keys)):
        raise ValueError("selected edge absent from the original 3D shell")
    if not np.array_equal(
        global_keys[source_edge_lookup],
        np.minimum(vertices[edges[:, 0]], vertices[edges[:, 1]]) * len(xyz)
        + np.maximum(vertices[edges[:, 0]], vertices[edges[:, 1]]),
    ):
        raise ValueError("source and region triangle edges disagree")
    boundary = edges[counts == 1]
    in_source = global_counts[source_edge_lookup] == 1
    cuff = edges[(counts == 1) & in_source]
    outer = edges[(counts == 1) & ~in_source]
    if len(cuff) != expected_cuff_edges or not len(outer):
        raise ValueError("panel lacks one whole original hoof and outer seam")
    if _boundary_check(boundary, len(vertices)) != 2:
        raise ValueError("source panel must be exactly one two-boundary annulus")
    if _boundary_check(cuff, len(vertices)) != 1:
        raise ValueError("hoof source opening is not one directed ring")
    if _boundary_check(outer, len(vertices)) != 1:
        raise ValueError("outer source seam is not one directed ring")
    if len(vertices) - len(edges) + len(triangle) != 0:
        raise ValueError("original panel is not an Euler-zero annulus")
    coords = xyz[vertices]
    path, path_length = _path_to_outer(
        coords, edges, counts, np.unique(cuff), np.unique(outer)
    )
    cut_faces, duplicates = _cut_vertex_fans(
        triangle, edges, inverse, counts, path
    )
    if len(duplicates) != len(path):
        raise ValueError("every cut-path vertex must get one copy")
    cut_points = np.vstack((coords, coords[duplicates]))
    cut_source_ids = np.r_[vertices, vertices[duplicates]]
    disk_border = _validate_cut_disk(
        cut_faces, len(cut_points), len(boundary), len(path) - 1
    )
    return {
        "points_xyz_mm": cut_points,
        "faces": cut_faces,
        "source_vertex_ids": cut_source_ids,
        "source_face_ids": selected,
        "boundary_edges": disk_border,
        "slit_path_source_vertex_ids": vertices[path],
        "slit_path_length_3d_mm": path_length,
        "slit_pin_inner_id": int(path[0]),
        "slit_pin_outer_id": int(path[-1]),
        "source_cuff_edges": len(cuff),
        "source_outer_seam_edges": len(outer),
        "source_cuff_edge_global_ids": vertices[cuff].tolist(),
        "source_outer_edge_global_ids": vertices[outer].tolist(),
        "original_annulus_vertices": len(vertices),
        "original_annulus_faces": len(triangle),
        "cut_disk_vertices": len(cut_points),
        "cut_disk_faces": len(cut_faces),
        "cut_disk_boundary_edges": len(disk_border),
        "cut_disk_euler": 1,
        "fabric_cut_pattern_approved": False,
    }
