"""Stage6 original contour-to-Mesh evidence, never anatomical ownership.

Exact source-section geometry comes from the same-run pinned 25% proxy.
Independent raw Mesh proximity and orthographic first-hit are observations,
not a seam, a sewing instruction, or proof that a protrusion is an ear.
"""

from __future__ import annotations

from collections import Counter
from math import isfinite

from plush_pattern_lab.validation.full_scene_seam_visibility import VALID_GROUPS, VIEWS

SOURCE_SCHEMA = "stage6-true-triangle-plane-component-loops-v1"
AUDIT_SCHEMA = "stage6-original-section-41-product-mesh-proximity-5view-v1"
TARGET_COUNTS = {125: 2, 230: 3, 245: 2}
SAMPLES_PER_LOOP = 48
CONTACT_CUTOFF_MM = 3.0
SEARCH_RADIUS_MM = 6.0


def _source_loop_samples(section, loop, order):
    points = loop["true_interpolated_contour_xy_mm"]
    edges = loop["crossed_original_mesh_vertex_id_edge_pairs"]
    if (
        not loop.get("closed_loop")
        or not loop.get("simple_polygon")
        or len(points) != len(edges)
        or len(points) < 3
        or not isfinite(loop["contour_perimeter_mm"])
        or loop["contour_perimeter_mm"] <= 0
    ):
        raise ValueError("unverified original source closed-loop geometry")
    for xy, edge in zip(points, edges):
        if (
            len(xy) != 2
            or not all(isfinite(v) for v in xy)
            or len(edge) != 2
            or any(not isinstance(v, int) or v < 0 for v in edge)
            or edge[0] == edge[1]
        ):
            raise ValueError("invalid original source interpolated edge evidence")
    count = min(len(points), SAMPLES_PER_LOOP)
    samples = []
    for k in range(count):
        idx = (k * len(points)) // count
        samples.append(
            {
                "source_edge_ordinal": idx,
                "source_vertex_id_pair": edges[idx],
                "source_xyz_mm": [*points[idx], section["plane_z_mm"]],
            }
        )
    return {
        "z_mm": section["plane_z_mm"],
        "source_loop_index_by_perimeter": order,
        "original_source_contour_sha256": loop[
            "original_source_edge_and_interpolated_xy_sha256"
        ],
        "total_original_crossed_source_edges": len(points),
        "source_centroid_xy_mm": loop["contour_centroid_xy_mm"],
        "source_perimeter_mm": loop["contour_perimeter_mm"],
        "sampled_source_edges": samples,
    }


def plan_original_contour_samples(detail):
    """Fail closed on missing/mutated Stage6 multi-ring source sections."""
    if (
        detail.get("schema") != SOURCE_SCHEMA
        or detail.get("source_geometry_type")
        != "actual_source_triangle_edges_intersected_exactly"
        or detail.get("factory_cutting_approved") != 0
    ):
        raise ValueError("not the locked original-triangle source study")
    sections = detail.get("sections")
    if not isinstance(sections, list):
        raise ValueError("missing original source sections")
    mapped = {s["plane_z_mm"]: s for s in sections}
    if len(mapped) != len(sections) or not set(TARGET_COUNTS).issubset(mapped):
        raise ValueError("duplicate or missing source planes")
    result = []
    for z, count in TARGET_COUNTS.items():
        section = mapped[z]
        if (
            section.get("true_source_plane_intersection_component_count") != count
            or len(section.get("source_contours", [])) != count
        ):
            raise ValueError("locked Stage6 z125/z230/z245 component count changed")
        result.append(
            {
                "z_mm": z,
                "loops": [
                    _source_loop_samples(section, loop, idx)
                    for idx, loop in enumerate(section["source_contours"])
                ],
            }
        )
    return result


def classify_independent_mesh_neighbors(hits):
    """Nearest *independent* raw Mesh contacts; never infer ear/cloud seams."""
    if not isinstance(hits, list):
        raise ValueError("missing BVH neighbor observations")
    seen = set()
    for hit in hits:
        name, role, dist = hit["mesh"], hit["group"], hit["distance_mm"]
        if (
            not isinstance(name, str)
            or not name
            or name in seen
            or role not in VALID_GROUPS - {"core_body_mesh"}
            or not isinstance(dist, (int, float))
            or not isfinite(dist)
            or not 0 <= dist <= SEARCH_RADIUS_MM + 1e-6
        ):
            raise ValueError("invalid independent source Mesh proximity")
        seen.add(name)
    ordered = sorted(hits, key=lambda h: (h["distance_mm"], h["mesh"]))
    close = [h for h in ordered if h["distance_mm"] <= CONTACT_CUTOFF_MM]
    if len(close) == 0:
        label = "no_independent_mesh_within_3mm"
    elif len(close) == 1:
        label = "one_independent_mesh_within_3mm_not_ownership"
    else:
        label = "multiple_independent_meshes_within_3mm_ambiguous"
    return {
        "proximity_classification": label,
        "nearest_independent_raw_mesh": ordered[0] if ordered else None,
        "close_independent_mesh_count": len(close),
        "nearby_raw_meshes_within_6mm": ordered,
        "physical_attachment_or_ear_identity_proven": False,
    }


def summarize_loop_observations(loop, samples):
    """Summarize same-run BVH observations without upgrading fabrication."""
    expected = loop["sampled_source_edges"]
    if len(samples) != len(expected):
        raise ValueError("lost original source contour sample in Mesh audit")
    for source, observed in zip(expected, samples):
        if (
            observed.get("source_edge_ordinal") != source["source_edge_ordinal"]
            or observed.get("source_vertex_id_pair") != source["source_vertex_id_pair"]
            or observed.get("source_xyz_mm") != source["source_xyz_mm"]
            or set(observed.get("five_view_first_hit", {}))
            != {view[0] for view in VIEWS}
        ):
            raise ValueError("source ID/XYZ or required five-view observations changed")
    contacts = Counter(row["proximity_classification"] for row in samples)
    view_summary = {}
    for view, *_ in VIEWS:
        view_summary[view] = {
            "first_hit_product_mesh_counts": dict(
                sorted(
                    Counter(
                        row["five_view_first_hit"][view]["mesh"] for row in samples
                    ).items(),
                    key=lambda pair: str(pair[0]),
                )
            ),
            "classification_counts": dict(
                sorted(
                    Counter(
                        row["five_view_first_hit"][view]["classification"]
                        for row in samples
                    ).items()
                )
            ),
        }
    return {
        "source_loop_index_by_perimeter": loop["source_loop_index_by_perimeter"],
        "source_loop_sha256": loop["original_source_contour_sha256"],
        "original_source_crossed_edges": loop["total_original_crossed_source_edges"],
        "observed_edge_sample_count": len(samples),
        "source_centroid_xy_mm": loop["source_centroid_xy_mm"],
        "source_perimeter_mm": loop["source_perimeter_mm"],
        "independent_mesh_proximity_counts": dict(sorted(contacts.items())),
        "five_view_first_hit_summary": view_summary,
        "raw_source_edge_samples": samples,
        "anatomical_protrusion_owner_confirmed": False,
        "hidden_manufacturing_seam_confirmed": False,
        "design_four_view_signoff_pending": True,
    }
