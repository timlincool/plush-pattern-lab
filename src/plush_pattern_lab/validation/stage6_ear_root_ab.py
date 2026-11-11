"""Compare source-linked Stage6 ear-root rings, never certified fabric patterns.

Two true 25%-proxy triangle-plane cuts: A z230, B z235. A 1D source ring
is not a stationary 2D fabric edge, nor a demonstrated hidden seam.
"""

from __future__ import annotations

import numpy as np
from shapely.geometry import Polygon

from plush_pattern_lab.validation.stage6_ear_root_contract import SCHEMA
from plush_pattern_lab.validation.stage6_source_slab_continuity import (
    trace_true_source_slab,
)
from plush_pattern_lab.validation.stage6_true_source_contours import (
    real_source_section_series,
)

CHOICES = (("A_lower_root_ring", 230), ("B_higher_root_ring", 235))
SPLIT_PROBES = (225.90, 225.91)
RESEARCH_ALLOWANCE_MM = 6.0


def _sides(section):
    if section["true_source_plane_intersection_component_count"] != 3:
        raise ValueError("candidate plane must have central and two side source loops")
    result = {}
    for index, loop in enumerate(section["source_contours"]):
        x = loop["contour_centroid_xy_mm"][0]
        side = "left" if x < -15 else "right" if x > 15 else "center"
        if side in result:
            raise ValueError("ambiguous anatomical source loop ordering")
        xy = np.asarray(loop["true_interpolated_contour_xy_mm"], dtype=float)
        poly = Polygon(xy)
        if not poly.is_valid or poly.area <= 1e-7 or not np.isfinite(xy).all():
            raise ValueError("non-simple real source loop")
        result[side] = (index, loop, poly)
    if set(result) != {"center", "left", "right"}:
        raise ValueError("source anatomy missing one side or central loop")
    return result


def _notch_positions(loop, z):
    """Quarter-arc landmarks on source 3D ring, NOT sewing notches."""
    xy = np.asarray(loop["true_interpolated_contour_xy_mm"], dtype=float)
    edges = loop["crossed_original_mesh_vertex_id_edge_pairs"]
    if len(edges) != len(xy) or len(xy) < 8:
        raise ValueError("missing original source mesh edge ID provenance")
    start = int(np.argmax(xy[:, 1]))
    xy = np.roll(xy, -start, axis=0)
    edges = edges[start:] + edges[:start]
    segs = np.linalg.norm(np.roll(xy, -1, axis=0) - xy, axis=1)
    cumulative = np.r_[0.0, np.cumsum(segs)]
    total = float(cumulative[-1])
    if abs(total - loop["contour_perimeter_mm"]) > 1e-6:
        raise ValueError("source perimeter and indexed edge segments do not match")
    marks = []
    for quarter in range(4):
        arclen = total * quarter / 4
        index = int(np.searchsorted(cumulative, arclen, side="right") - 1)
        segment = min(index, len(xy) - 1)
        ratio = (arclen - cumulative[segment]) / segs[segment]
        at = xy[segment] + ratio * (xy[(segment + 1) % len(xy)] - xy[segment])
        marks.append(
            {
                "fraction_of_closed_ring": quarter / 4,
                "from_backmost_source_crossing_mm": float(arclen),
                "source_intersection_edge_before": edges[segment],
                "source_intersection_edge_after": edges[(segment + 1) % len(edges)],
                "true_source_xyz_mm": [float(at[0]), float(at[1]), float(z)],
                "not_a_manufacturing_notch": True,
            }
        )
    return marks


def _study_side(side, source, center, z):
    index, loop, shape = source
    bounds = shape.bounds
    return {
        "side": side,
        "source_loop_index_by_perimeter": index,
        "source_contour_sha256": loop[
            "original_source_edge_and_interpolated_xy_sha256"
        ],
        "original_proxy_crossed_edge_count": len(
            loop["crossed_original_mesh_vertex_id_edge_pairs"]
        ),
        "source_3d_ring_perimeter_mm": float(shape.length),
        "source_enclosed_xy_area_mm2": float(shape.area),
        "source_centroid_xy_mm": loop["contour_centroid_xy_mm"],
        "xy_bbox_width_mm": float(bounds[2] - bounds[0]),
        "xy_bbox_depth_mm": float(bounds[3] - bounds[1]),
        "source_xy_gap_to_central_loop_mm": float(shape.distance(center)),
        "xy_minor_bbox_under_two_research_6mm_allowances": (
            min(bounds[2] - bounds[0], bounds[3] - bounds[1])
            < 2 * RESEARCH_ALLOWANCE_MM
        ),
        "full_interpolated_original_source_xy_mm": loop[
            "true_interpolated_contour_xy_mm"
        ],
        "full_crossed_original_proxy_vertex_id_pairs": loop[
            "crossed_original_mesh_vertex_id_edge_pairs"
        ],
        "four_arclength_reference_marks": _notch_positions(loop, z),
        "source_polygon_is_not_an_unwrapped_fabric_pattern": True,
        "physical_ear_attachment_proven": False,
    }


def _verify_anchor(source_230, original):
    if original is None:
        return
    section = next(
        (s for s in original.get("sections", []) if s["plane_z_mm"] == 230),
        None,
    )
    expected = (
        []
        if section is None
        else [
            row["original_source_edge_and_interpolated_xy_sha256"]
            for row in section["source_contours"]
        ]
    )
    actual = [
        row["original_source_edge_and_interpolated_xy_sha256"]
        for row in source_230["source_contours"]
    ]
    if (
        original.get("schema") != "stage6-true-triangle-plane-component-loops-v1"
        or original.get("factory_cutting_approved") != 0
        or expected != actual
    ):
        raise ValueError(
            "existing trusted source z230 original edge / XY digest changed"
        )


def compare_real_ear_root_ab(points, faces, original_detail=None):
    """Compare two non-approved ring positions with exact source provenance."""
    levels = (*SPLIT_PROBES, *(z for _, z in CHOICES))
    series = real_source_section_series(points, faces, z_levels=levels)
    sections = {section["plane_z_mm"]: section for section in series["sections"]}
    counts = [
        sections[z]["true_source_plane_intersection_component_count"] for z in levels
    ]
    if counts != [1, 3, 3, 3]:
        raise ValueError("original source crown split topology has changed")
    _verify_anchor(sections[230], original_detail)
    track = trace_true_source_slab(points, faces, series, 230, 235)
    if track["source_surface_component_count_in_open_slab"] != 3 or any(
        item["source_surface_relation"] != "one_to_one_surface_continuation_not_seam"
        for item in track["surface_components"]
    ):
        raise ValueError("source side surfaces do not continue one-to-one")
    candidates = []
    for name, z in CHOICES:
        loopmap = _sides(sections[z])
        center = loopmap["center"][2]
        studies = [
            _study_side(side, loopmap[side], center, z) for side in ("left", "right")
        ]
        reflected = Polygon([(-x, y) for x, y in loopmap["left"][2].exterior.coords])
        gap = reflected.boundary.hausdorff_distance(loopmap["right"][2].boundary)
        candidates.append(
            {
                "name": name,
                "source_plane_z_mm": z,
                "height_above_split_upper_probe_mm": float(z - SPLIT_PROBES[1]),
                "original_source_closed_loop_count_including_crown": 3,
                "central_original_head_loop_perimeter_mm": float(center.length),
                "source_side_loops": studies,
                "left_right_reflected_boundary_hausdorff_mm": float(gap),
                "central_head_crown_not_merged_into_side_ear_rings": True,
                "source_height_not_validated_sewing_allowance": True,
                "ear_root_seam_or_dart_approved": False,
            }
        )
    return {
        "schema": SCHEMA,
        "method": "actual original 25pct Stage6 proxy triangle-plane contours",
        "split_event_bracket_mm": list(SPLIT_PROBES),
        "split_probe_loop_counts": [1, 3],
        "source_230_to_235_open_slab_triangles": track[
            "source_triangle_count_in_open_slab"
        ],
        "source_230_to_235_components": track["surface_components"],
        "candidate_options": candidates,
        "source_loop_3d_perimeter_is_not_a_2d_fabric_rest_length": True,
        "two_research_6mm_allowances_are_only_a_xy_screen": True,
        "actual_material_ear_root_seam_and_design_four_views_unverified": True,
        "manufacturing_cutting_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
    }
