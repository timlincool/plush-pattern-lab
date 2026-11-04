"""Read-only surface-topology evidence before decimating the Stage6 main shell.

This does not construct, approve or export a fabric cutting pattern.
"""

from __future__ import annotations


def _counts(face_sizes, edge_incidence):
    if not isinstance(face_sizes, dict) or not isinstance(edge_incidence, dict):
        raise ValueError("face and edge categories must be explicit dictionaries")
    if set(edge_incidence) != {"0", "1", "2", ">2"}:
        raise ValueError("edge incidence categories must include loose/complex cases")
    if any(not isinstance(value, int) or value < 0 for value in face_sizes.values()):
        raise ValueError("invalid face polygon counts")
    if any(
        not isinstance(value, int) or value < 0 for value in edge_incidence.values()
    ):
        raise ValueError("invalid edge incidence counts")


def summarize_core_shell_topology(
    vertices,
    edges,
    faces,
    face_sizes,
    edge_incidence,
    face_components,
    boundary_loop_sizes,
):
    """Quantify exact face/edge counts without assuming cloth manufacturability."""
    _counts(face_sizes, edge_incidence)
    if not all(
        isinstance(value, int) and value > 0 for value in (vertices, edges, faces)
    ):
        raise ValueError("positive integral mesh sizes are required")
    if sum(face_sizes.values()) != faces or sum(edge_incidence.values()) != edges:
        raise ValueError("polygon and edge incidence tallies must match mesh")
    if not isinstance(face_components, int) or not 1 <= face_components <= faces:
        raise ValueError("invalid face-connected component count")
    if not isinstance(boundary_loop_sizes, list):
        raise ValueError("ordered boundary loop counts required")
    if any(not isinstance(value, int) or value < 3 for value in boundary_loop_sizes):
        raise ValueError("invalid open boundary loop sizes")
    if sum(boundary_loop_sizes) != edge_incidence["1"]:
        raise ValueError("unmatched boundary edges; not a closed directed ring set")
    euler = vertices - edges + faces
    full_boundary = sorted(boundary_loop_sizes) == [512, 512, 512, 512]
    manifold = edge_incidence["0"] == 0 and edge_incidence[">2"] == 0
    candidate = face_components == 1 and manifold and full_boundary
    genus_numerator = 2 - len(boundary_loop_sizes) - euler
    genus = (
        genus_numerator // 2
        if candidate and genus_numerator >= 0 and genus_numerator % 2 == 0
        else None
    )
    return {
        "schema": "stage6-core-shell-mesh-topology-v1",
        "status": "MAIN_SHELL_RETOPOLOGY_INPUT_AUDIT_ONLY",
        "vertices": vertices,
        "edges": edges,
        "faces": faces,
        "face_sizes": dict(sorted(face_sizes.items())),
        "edge_incidence": edge_incidence,
        "face_components_by_shared_edge": face_components,
        "boundary_loop_vertex_counts": sorted(boundary_loop_sizes),
        "euler_characteristic": euler,
        "manifold_edges_only": manifold,
        "four_512_edge_openings_verified": full_boundary,
        "single_face_connected_component": face_components == 1,
        "genus_candidate_if_orientable": genus,
        "candidate_for_non_destructive_proxy_experiment": candidate,
        "low_poly_proxy_created": False,
        "cutting_patterns_approved": False,
        "limitations": [
            "A topological shell is not a manufacturable sewn panel set",
            "Orientability and genus need independent face-winding confirmation",
            "Proxy decimation must retain the original four hoof seam identities",
            "No fabric, actual sewing, seam allowance or physical sample evidence",
        ],
    }
