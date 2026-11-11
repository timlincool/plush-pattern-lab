"""Screen fixed source ear-root quadrants against same-run Stage6 41Mesh data.

A projected original 3D arc is not a 2D fabric rest pattern or hidden seam.
All quadrants are reported; visibility does not decide which source edges to use.
"""

from __future__ import annotations

import hashlib
import struct
from collections import Counter
from math import hypot, isfinite

SCHEMA = "stage6-original-ear-root-quadrant-arc-41mesh-screen-v1"
SOURCE_SCHEMA = "stage6-original-source-ear-root-two-height-ring-ab-v1"
VIS_SCHEMA = "stage6-original-source-ear-root-ab-41mesh-five-view-v1"
ORIGINAL_SHA = "38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a"
PROXY_SHA = "5b52e3fd09c83b19c5b9d95d6d8d859a147ff4deef90f1518f868d2e82e3a2dd"
VIEWS = ("front", "back", "left", "right", "top")
QUADRANTS = ("medial", "lateral", "posterior", "anterior")
WINDOW = 12
SAMPLE_COUNT = 48
VISIBLE = "near_original_body_first_surface"
OTHER = "occluded_by_another_product_mesh"
SELF = "self_occluded_by_original_body"
UNCERTAIN = frozenset(
    {
        "no_authored_mesh_first_hit",
        "coincident_with_another_product_mesh_unresolved",
        "proxy_source_ahead_of_full_mesh_surface_unresolved",
    }
)


def _validate_heads(study, visibility):
    if (
        study.get("schema") != SOURCE_SCHEMA
        or visibility.get("schema") != VIS_SCHEMA
        or study.get("original_public_stage6_blend_sha256") != ORIGINAL_SHA
        or study.get("source_25pct_proxy_ply_sha256") != PROXY_SHA
        or visibility.get("original_public_blend_sha256") != ORIGINAL_SHA
        or visibility.get("raw_product_meshes_raycasted") != 41
        or visibility.get("original_fur_curves_not_tested") != 423
        or study.get("manufacturing_cutting_approved") != 0
        or visibility.get("manufacturing_seam_or_dart_approved") is not False
        or visibility.get("P4_started") is not False
        or len(study.get("candidate_options", [])) != 2
        or len(visibility.get("options", [])) != 2
    ):
        raise ValueError("unpinned or manufacturing-approved A/B input evidence")


def _validated_ring_geometry(ring, visibility):
    xy = ring["full_interpolated_original_source_xy_mm"]
    edges = ring["full_crossed_original_proxy_vertex_id_pairs"]
    samples = visibility["original_source_edge_samples"]
    if (
        ring["source_contour_sha256"] != visibility["source_contour_sha256"]
        or ring["original_proxy_crossed_edge_count"] != len(xy)
        or len(edges) != len(xy)
        or len(samples) != SAMPLE_COUNT
        or visibility["source_edge_samples_observed"] != SAMPLE_COUNT
        or visibility["original_source_crossed_edge_count"] != len(xy)
        or not ring["xy_minor_bbox_under_two_research_6mm_allowances"]
        or not visibility["surface_mesh_occlusion_not_a_hidden_sewing_seam"]
        or not visibility["physical_ear_root_not_approved"]
    ):
        raise ValueError("source ring or BVH sample dimensions changed")
    if any(
        len(point) != 2
        or len(pair) != 2
        or not all(isinstance(i, int) and i >= 0 for i in pair)
        or not all(isfinite(v) for v in point)
        for point, pair in zip(xy, edges)
    ):
        raise ValueError("invalid original source XY or triangle vertex IDs")
    digest = hashlib.sha256(
        b"".join(struct.pack("<qq", *pair) for pair in edges)
        + b"".join(struct.pack("<dd", *point) for point in xy)
    ).hexdigest()
    if digest != ring["source_contour_sha256"]:
        raise ValueError("original source crossed-edge and XY SHA mismatch")
    perimeter = sum(
        hypot(
            xy[(i + 1) % len(xy)][0] - point[0],
            xy[(i + 1) % len(xy)][1] - point[1],
        )
        for i, point in enumerate(xy)
    )
    if abs(perimeter - ring["source_3d_ring_perimeter_mm"]) > 1e-6:
        raise ValueError("source arc perimeter integrity mismatch")
    x_range = max(point[0] for point in xy) - min(point[0] for point in xy)
    y_range = max(point[1] for point in xy) - min(point[1] for point in xy)
    if min(x_range, y_range) >= 12:
        raise ValueError("source XY double-allowance risk flag changed")
    return xy, edges, samples


def _check_original_sample(sample, index, xy, edges, z):
    ordinal = index * len(xy) // SAMPLE_COUNT
    if (
        sample.get("source_edge_ordinal") != ordinal
        or sample.get("source_vertex_id_pair") != edges[ordinal]
        or sample.get("source_xyz_mm") != [*xy[ordinal], z]
        or set(sample.get("five_view_first_hit", {})) != set(VIEWS)
        or sample.get("physical_attachment_or_ear_identity_proven") is not False
    ):
        raise ValueError("altered Stage6 original source ID, XYZ or five views")
    observed_meshes = set()
    for row in sample["nearby_raw_meshes_within_6mm"]:
        if (
            row["mesh"] in observed_meshes
            or not isfinite(row["distance_mm"])
            or not 0 <= row["distance_mm"] <= 6.00001
        ):
            raise ValueError("untrusted independent product Mesh proximity")
        observed_meshes.add(row["mesh"])
    for view in VIEWS:
        if sample["five_view_first_hit"][view]["classification"] not in (
            {VISIBLE, OTHER, SELF} | UNCERTAIN
        ):
            raise ValueError("unrecognized 41-Mesh original first-hit category")


def _validated_samples(ring, visibility, z):
    xy, edges, samples = _validated_ring_geometry(ring, visibility)
    for index, sample in enumerate(samples):
        _check_original_sample(sample, index, xy, edges, z)
    return xy, samples


def _arc_length_mm(xy, start, stop):
    """Measure the original source-section polyline between sampled endpoints."""
    total = 0.0
    cursor = start
    while cursor != stop:
        nxt = (cursor + 1) % len(xy)
        total += hypot(
            xy[nxt][0] - xy[cursor][0],
            xy[nxt][1] - xy[cursor][1],
        )
        cursor = nxt
    return total


def _extremum_index(samples, side, quadrant):
    locations = [sample["source_xyz_mm"] for sample in samples]
    if quadrant == "medial":
        axis, sign = 0, 1 if side == "left" else -1
    elif quadrant == "lateral":
        axis, sign = 0, -1 if side == "left" else 1
    elif quadrant == "posterior":
        axis, sign = 1, 1
    else:
        axis, sign = 1, -1
    return max(range(len(samples)), key=lambda i: sign * locations[i][axis])


def _score_arc(samples):
    own_side = "left" if samples[0]["source_xyz_mm"][0] < 0 else "right"
    views = ("front", "back", own_side, "top")
    counts = {}
    for view in views:
        labels = Counter(
            sample["five_view_first_hit"][view]["classification"] for sample in samples
        )
        counts[view] = {
            "near_original_body_first_surface": labels[VISIBLE],
            "occluded_by_other_raw_product_mesh": labels[OTHER],
            "self_occluded_by_original_body": labels[SELF],
            "unresolved_or_no_hit": sum(labels[key] for key in UNCERTAIN),
        }
    contacts = Counter(
        mesh["mesh"]
        for sample in samples
        for mesh in sample["nearby_raw_meshes_within_6mm"]
        if mesh["distance_mm"] <= 3
    )
    return counts, dict(sorted(contacts.items())), own_side


def _quadrant_arc(ring, observed, z, name):
    xy, samples = _validated_samples(ring, observed, z)
    center = _extremum_index(samples, ring["side"], name)
    positions = [
        (center - WINDOW // 2 + index) % SAMPLE_COUNT for index in range(WINDOW)
    ]
    selected = [samples[index] for index in positions]
    first = selected[0]["source_edge_ordinal"]
    last = selected[-1]["source_edge_ordinal"]
    views, contacts, side = _score_arc(selected)
    if side != ring["side"]:
        raise ValueError("source arc crosses wrong original main-shell side")
    return {
        "hypothesis": name,
        "source_side": side,
        "source_height_mm": z,
        "source_contour_sha256": ring["source_contour_sha256"],
        "sample_count": WINDOW,
        "source_sample_indices_in_order": positions,
        "original_source_edge_ordinal_start": first,
        "original_source_edge_ordinal_end": last,
        "original_source_edge_id_pair_start": selected[0]["source_vertex_id_pair"],
        "original_source_edge_id_pair_end": selected[-1]["source_vertex_id_pair"],
        "source_xyz_start_mm": selected[0]["source_xyz_mm"],
        "source_xyz_end_mm": selected[-1]["source_xyz_mm"],
        "source_original_plane_arc_length_mm": _arc_length_mm(xy, first, last),
        "per_view_12point_first_hit": views,
        "independent_meshes_within_3mm_sample_counts": contacts,
        "original_arc_endpoints_unpaired": 2,
        "seam_allowance_or_material_tested": False,
        "approved_as_hidden_seam": False,
    }


def compare_source_quadrant_arcs(study, visibility):
    """Report all four predefined anatomical directions without optimization."""
    _validate_heads(study, visibility)
    options = []
    for option, observed in zip(study["candidate_options"], visibility["options"]):
        if (
            option["name"] != observed["name"]
            or option["source_plane_z_mm"] != observed["source_z_mm"]
            or [side["side"] for side in option["source_side_loops"]]
            != ["left", "right"]
            or [side["side"] for side in observed["sides"]] != ["left", "right"]
        ):
            raise ValueError("Stage6 source and 41-Mesh A/B identity mismatch")
        sides = []
        for ring, seen in zip(option["source_side_loops"], observed["sides"]):
            arcs = [
                _quadrant_arc(ring, seen, observed["source_z_mm"], quadrant)
                for quadrant in QUADRANTS
            ]
            sides.append({"side": ring["side"], "quadrant_arc_hypotheses": arcs})
        options.append(
            {
                "name": option["name"],
                "source_z_mm": observed["source_z_mm"],
                "sides": sides,
            }
        )
    return {
        "schema": SCHEMA,
        "comparison_method": "predeclared_12_of_48_contiguous_source_edge_quadrants",
        "studied_quadrants": list(QUADRANTS),
        "input_original_blend_sha256": ORIGINAL_SHA,
        "input_pinned_proxy_sha256": PROXY_SHA,
        "source_samples_each_full_loop": SAMPLE_COUNT,
        "arc_samples_each_quadrant": WINDOW,
        "option_results": options,
        "all_four_quadrants_reported_no_visibility_driven_cherry_pick": True,
        "original_41mesh_first_hit_not_final_fur_or_design": True,
        "fabric_seam_allowance_and_3d_to_2d_rest_shape_unverified": True,
        "unpaired_open_arc_endpoints_are_not_sewing_joins": True,
        "approved_factory_cutting_patterns": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
    }
