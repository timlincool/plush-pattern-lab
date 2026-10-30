"""Validate a local triangular seam band as a connected two-boundary annulus.

This is pure topology, NOT a 2D flattening, rest shape, or cut approval.
"""

from __future__ import annotations

from collections import Counter, defaultdict


def _edges_of_face(face):
    return [tuple(sorted((a, b))) for a, b in zip(face, face[1:] + face[:1])]


def _components(nodes, adjacency):
    remaining = set(nodes)
    count = 0
    while remaining:
        count += 1
        pending = [remaining.pop()]
        while pending:
            current = pending.pop()
            for neighbor in adjacency[current] & remaining:
                remaining.remove(neighbor)
                pending.append(neighbor)
    return count


def _boundary_loops(edges):
    graph = defaultdict(set)
    for a, b in edges:
        graph[a].add(b)
        graph[b].add(a)
    if not graph or any(len(neighbors) != 2 for neighbors in graph.values()):
        return 0
    return _components(graph, graph)


def analyze_triangle_patch(seam, faces):
    """Screen all faces incident to the seam vertices, with no coordinate guesses."""
    ring = [int(v) for v in seam]
    if len(ring) < 4 or len(set(ring)) != len(ring):
        raise ValueError("invalid seam ring")
    triangles = [tuple(int(v) for v in face) for face in faces]
    if not triangles or any(len(t) != 3 or len(set(t)) != 3 for t in triangles):
        raise ValueError("nontriangular/degenerate one-vertex-ring face patch")
    seam_set = set(ring)
    edges_to_faces = defaultdict(list)
    face_seam_count = Counter()
    vertices = set()
    for i, triangle in enumerate(triangles):
        vertices.update(triangle)
        face_seam_count[len(set(triangle) & seam_set)] += 1
        for edge in _edges_of_face(triangle):
            edges_to_faces[edge].append(i)
    return _summarize(ring, triangles, vertices, edges_to_faces, face_seam_count)


def _summarize(ring, triangles, vertices, edges_to_faces, face_seam_count):
    boundary_edges = {
        edge for edge, owners in edges_to_faces.items() if len(owners) == 1
    }
    seam_edges = set(_edges_of_face(ring))
    nonmanifold = sum(len(owners) > 2 for owners in edges_to_faces.values())
    face_adjacency = defaultdict(set)
    for owners in edges_to_faces.values():
        if len(owners) == 2:
            a, b = owners
            face_adjacency[a].add(b)
            face_adjacency[b].add(a)
    components = _components(range(len(triangles)), face_adjacency)
    outer_edges = boundary_edges - seam_edges
    boundary_loops = _boundary_loops(boundary_edges)
    outer_vertices = set(vertices) - set(ring)
    seam_exposed = len(seam_edges & boundary_edges)
    euler = len(vertices) - len(edges_to_faces) + len(triangles)
    return {
        "seam_vertices": len(ring),
        "triangles": len(triangles),
        "total_vertices": len(vertices),
        "outer_vertices": len(outer_vertices),
        "edges": len(edges_to_faces),
        "seam_boundary_edges_exposed": seam_exposed,
        "outer_boundary_edges": len(outer_edges),
        "face_components": components,
        "boundary_loops": boundary_loops,
        "nonmanifold_edges": nonmanifold,
        "euler_characteristic": euler,
        "triangles_by_seam_vertex_count": {
            str(k): v for k, v in sorted(face_seam_count.items())
        },
        "candidate_triangular_annulus": (
            components == 1
            and boundary_loops == 2
            and seam_exposed == len(ring)
            and nonmanifold == 0
            and euler == 0
            and len(outer_vertices) >= 3
        ),
        "limitations": "mesh topology screen; no surface flattening or strain proof",
    }
