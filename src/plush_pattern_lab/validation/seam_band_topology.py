"""Closed-boundary one-face-ring topology check before attempting 3D->2D flattening.

Pure integer topology. Never guesses stitching by nearest 3D positions.
"""

from __future__ import annotations

from collections import Counter


def _quad_partner_pairs(face, a, b, seam_set):
    """Resolve radial partners from cyclic face order, never from distances."""
    nodes = tuple(int(v) for v in face)
    if len(nodes) != 4 or len(set(nodes)) != 4:
        raise ValueError("boundary-adjacent face is not a nondegenerate quad")
    if set(nodes) & seam_set != {a, b}:
        raise ValueError("face has unexpected boundary vertices")
    ia, ib = nodes.index(a), nodes.index(b)
    if (ia + 1) % 4 == ib:
        return ((a, nodes[(ia - 1) % 4]), (b, nodes[(ib + 1) % 4]))
    if (ib + 1) % 4 == ia:
        return ((a, nodes[(ia + 1) % 4]), (b, nodes[(ib - 1) % 4]))
    raise ValueError("seam vertices are not neighbors on the quad")


def outer_ring_for_quads(boundary, adjacent_faces):
    """Find one stable outer partner for each seam vertex, or fail closed."""
    seam = [int(v) for v in boundary]
    if len(seam) < 4 or len(seam) != len(set(seam)):
        raise ValueError("boundary vertices are missing or repeated")
    if len(adjacent_faces) != len(seam):
        raise ValueError("one adjacent face per boundary edge is required")
    seam_set = set(seam)
    radial = {}
    face_keys = set()
    for index, (a, b) in enumerate(zip(seam, seam[1:] + seam[:1])):
        face = tuple(int(v) for v in adjacent_faces[index])
        if frozenset(face) in face_keys:
            raise ValueError("a face is used by multiple boundary edges")
        face_keys.add(frozenset(face))
        for vertex, partner in _quad_partner_pairs(face, a, b, seam_set):
            if vertex in radial and radial[vertex] != partner:
                raise ValueError("inconsistent radial vertex across adjacent faces")
            radial[vertex] = partner
    outer = [radial[vertex] for vertex in seam]
    if len(set(outer)) != len(outer):
        raise ValueError("outer ring merges vertices, not a regular quad strip")
    return outer

def face_profile(boundary, adjacent_faces):
    """Bounded classification of the first face band without exporting geometry."""
    faces = [tuple(int(v) for v in face) for face in adjacent_faces]
    kinds = Counter(len(face) for face in faces)
    used = set()
    unique_faces = set()
    for face in faces:
        used.update(face)
        unique_faces.add(frozenset(face))
    data = {
        "boundary_vertices": len(boundary),
        "adjacent_faces": len(faces),
        "unique_adjacent_faces": len(unique_faces),
        "polygon_vertex_counts": {str(k): v for k, v in sorted(kinds.items())},
        "unique_vertex_count_in_band": len(used),
        "regular_quad_strip": False,
        "limitation": "not yet a surface flattening or cut pattern",
    }
    try:
        outer = outer_ring_for_quads(boundary, faces)
    except ValueError as exc:
        data["quad_strip_failure_reason"] = str(exc)
    else:
        data["regular_quad_strip"] = True
        data["outer_ring_vertices"] = len(outer)
    return data
