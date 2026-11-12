"""True non-horizontal Stage6 ear-root 3D cut studies, never fabric patterns.

Both interfaces are source-edge piecewise-linear iso-surfaces, not horizontal
Z planes. Reuse the audited original-face cutter, then restore WORLD XYZ by
interpolating on the exact original source edge at normalized scalar t=0/1.
"""

from __future__ import annotations

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

from plush_pattern_lab.validation.stage6_true_ear_root_band_cut import (
    _component_info,
    _components,
    _ordered_original_seam_keys,
    _oriented_edges,
    _side_component,
    _source_band_geometry,
    _source_mesh,
    _surface_area,
    _unique_face_edges,
    clip_original_source_zone,
)

SCHEMA = "stage6-real-original-source-nonhorizontal-ear-root-paired-3d-v1"
STUDIES = (
    ("N15_sloped_source_band", 228.5, 243.5, 1.5),
    ("N17_sloped_source_band", 227.5, 244.5, 1.5),
)
SLOPE_Y_CENTER_MM = -45.0
SLOPE_Y_SPAN_MM = 15.0
CUT_LEVELS = (0.0, 1.0)
RESEARCH_ALLOWANCE_MM = 6.0


def _physical_cut_surfaces(xyz, base_lower, base_upper, slope):
    """Original vertex scalar values; cuts are linear per source triangle."""
    y_normal = np.clip((xyz[:, 1] - SLOPE_Y_CENTER_MM) / SLOPE_Y_SPAN_MM, -1.0, 1.0)
    lower = base_lower + slope * y_normal
    upper = base_upper + slope * y_normal
    if (
        np.any(upper - lower < 12)
        or not np.isfinite(xyz).all()
        or not np.isfinite(lower + upper).all()
    ):
        raise ValueError("nonfinite original source or proposed band is too narrow")
    scalar = (xyz[:, 2] - lower) / (upper - lower)
    if not np.isfinite(scalar).all():
        raise ValueError("original source implicit cut scalar is nonfinite")
    if np.min(np.abs(scalar)) <= 1e-6 or np.min(np.abs(scalar - 1)) <= 1e-6:
        raise ValueError(
            "non-horizontal original source cut passes through source vertex"
        )
    return scalar, lower, upper


def _restore_original_world_coordinates(zone, xyz, scalar):
    """Recover physical millimetre XYZ after clipping normalized scalar height."""
    points = []
    for key in zone["keys"]:
        if key[0] == "v":
            physical = xyz[key[1]]
        else:
            _, a, b, cut_level = key
            denominator = scalar[b] - scalar[a]
            if abs(denominator) <= 1e-12:
                raise ValueError("source edge does not cross specified iso-surface")
            ratio = (cut_level - scalar[a]) / denominator
            if not 0 < ratio < 1:
                raise ValueError("non-interior source-edge cut intersection")
            physical = xyz[a] + ratio * (xyz[b] - xyz[a])
        points.append(physical)
    zone["xyz"] = np.asarray(points, dtype=np.float64)
    return zone


def _split_original_source(xyz, faces, scalar):
    transformed = xyz.copy()
    transformed[:, 2] = scalar
    cuts = {
        "below": (None, CUT_LEVELS[0]),
        "root": CUT_LEVELS,
        "above": (CUT_LEVELS[1], None),
    }
    return {
        name: _restore_original_world_coordinates(
            clip_original_source_zone(transformed, faces, low, high), xyz, scalar
        )
        for name, (low, high) in cuts.items()
    }


def _iso_source_seam_edges(zone, component, iso_level):
    """Use canonical source-edge/iso labels, NEVER constant world Z."""
    chosen = {}
    for a, b in component["boundary"]:
        first, second = zone["keys"][a], zone["keys"][b]
        if first[0] == second[0] == "e" and first[3] == second[3] == iso_level:
            chosen[tuple(sorted((first, second)))] = (int(a), int(b))
    return chosen


def _iso_source_paired_seam(a, ca, b, cb, iso_level, subset=False):
    """Physically equal source 3D seam edges with opposite face winding."""
    first = _iso_source_seam_edges(a, ca, iso_level)
    second = _iso_source_seam_edges(b, cb, iso_level)
    if (not set(second).issubset(first)) if subset else (set(first) != set(second)):
        raise ValueError("non-horizontal original source 3D seams do not match")
    if len(second) < 3:
        raise ValueError("source iso-interface does not form a closed seam")
    orientation_a = _oriented_edges(a, ca, iso_level)
    orientation_b = _oriented_edges(b, cb, iso_level)
    if any(orientation_a[k] != tuple(reversed(orientation_b[k])) for k in second):
        raise ValueError("source paired iso-interface has wrong face winding")
    coords_a = {
        a["keys"][vertex]: a["xyz"][vertex]
        for segment in first.values()
        for vertex in segment
    }
    coords_b = {
        b["keys"][vertex]: b["xyz"][vertex]
        for segment in second.values()
        for vertex in segment
    }
    error = max(
        float(np.max(np.abs(coords_a[key] - physical)))
        for key, physical in coords_b.items()
    )
    if error > 1e-9:
        raise ValueError("source paired physical world coordinates disagree")
    ordered = _ordered_original_seam_keys(second)
    length = sum(
        float(np.linalg.norm(coords_a[start] - coords_a[end])) for start, end in second
    )
    return {
        "source_plane_z_mm": iso_level,
        "original_crossed_source_triangle_segment_count": len(second),
        "paired_3d_netline_length_each_side_mm": length,
        "max_source_3d_pair_position_error_mm": error,
        "matching_original_source_seam_edge_keys": [
            [list(start), list(end)] for start, end in sorted(second)
        ],
        "original_source_3d_ordered_ring_vertex_keys": [list(key) for key in ordered],
        "original_source_3d_ordered_ring_xyz_mm": [
            coords_a[key].tolist() for key in ordered
        ],
        "two_source_3d_sides_exactly_same_with_opposite_face_winding": True,
        "not_a_validated_two_sided_fabric_2d_netline": True,
    }


def _iso_source_surface_graph_width(zone, component, low, high):
    """Source-edge graph distance between two non-horizontal cut boundaries."""
    _, edges, _, _ = _unique_face_edges(component["faces"])
    xyz = zone["xyz"]
    distances = np.linalg.norm(xyz[edges[:, 0]] - xyz[edges[:, 1]], axis=1)
    a, b = edges[:, 0], edges[:, 1]
    first = _iso_source_seam_edges(zone, component, low)
    second = _iso_source_seam_edges(zone, component, high)
    lower = np.unique([v for pair in first.values() for v in pair])
    upper = np.unique([v for pair in second.values() for v in pair])
    origin = len(xyz)
    rows = np.r_[a, b, np.full(len(lower), origin), lower]
    cols = np.r_[b, a, lower, np.full(len(lower), origin)]
    weights = np.r_[distances, distances, np.full(2 * len(lower), 1e-12)]
    graph = coo_matrix((weights, (rows, cols)), shape=(origin + 1, origin + 1)).tocsr()
    result = dijkstra(graph, directed=False, indices=origin)[upper]
    if not np.isfinite(result).all():
        raise ValueError("source non-horizontal ear root graph is disconnected")
    return {
        "upper_seam_source_intersection_vertex_count": len(upper),
        "surface_graph_shortest_path_min_p05_median_p95_max_mm": np.quantile(
            result, (0, 0.05, 0.5, 0.95, 1)
        ).tolist(),
        "fraction_upper_source_seam_under_12mm_graph_width": float(
            np.mean(result < 2 * RESEARCH_ALLOWANCE_MM)
        ),
        "below_two_research_6mm_allowances_somewhere": bool(
            result.min() < 2 * RESEARCH_ALLOWANCE_MM
        ),
        "source_triangle_graph_distance_is_upper_bound_on_real_surface_geodesic": True,
        "this_is_not_2d_fabric_usable_allowance": True,
    }


def _annotated_source_netline(seam, normalized_cut_level):
    """Do not confuse iso-surface 0/1 with a world Z height in millimetres."""
    if seam.pop("source_plane_z_mm") != normalized_cut_level:
        raise ValueError("source interface is not the required scalar cut level")
    physical = np.asarray(seam["original_source_3d_ordered_ring_xyz_mm"])
    span = np.ptp(physical[:, :2], axis=0)
    seam.update(
        {
            "normalized_source_iso_surface_t": normalized_cut_level,
            "actual_original_world_z_minmax_mm": [
                float(physical[:, 2].min()),
                float(physical[:, 2].max()),
            ],
            "original_world_xy_bbox_width_depth_mm": span.tolist(),
            "original_world_xy_minor_extent_mm": float(span.min()),
            "original_world_xy_minor_extent_below_12mm_research_screen": bool(
                span.min() < 2 * RESEARCH_ALLOWANCE_MM
            ),
            "not_a_horizontal_plane_or_2d_fabric_seam": True,
        }
    )
    return seam


def _one_side(zones, parts, side):
    root = _side_component(parts["root"], side)
    cap = _side_component(parts["above"], side)
    body = parts["below"][0]
    if root["euler"] != 0 or len(root["boundary_loops"]) != 2:
        raise ValueError("original root is not a connected two-boundary annulus")
    if cap["euler"] != 1 or len(cap["boundary_loops"]) != 1:
        raise ValueError("original upper ear tip is not a one-boundary disk")
    lower = _annotated_source_netline(
        _iso_source_paired_seam(
            zones["below"], body, zones["root"], root, 0.0, subset=True
        ),
        0.0,
    )
    upper = _annotated_source_netline(
        _iso_source_paired_seam(zones["root"], root, zones["above"], cap, 1.0), 1.0
    )
    graph = _iso_source_surface_graph_width(zones["root"], root, 0.0, 1.0)
    return {
        "side": side,
        "actual_original_source_root_band": _component_info(zones["root"], root),
        "source_root_band_triangles_with_original_face_ids": _source_band_geometry(
            zones["root"], root
        ),
        "actual_upper_original_ear_tip": _component_info(zones["above"], cap),
        "body_to_root_paired_3d_source_netline": lower,
        "root_to_upper_ear_paired_3d_source_netline": upper,
        "surface_graph_between_3d_netlines": graph,
        "upper_original_ear_rim_xy_too_narrow_for_automatic_double_6mm_allowance": (
            upper["original_world_xy_minor_extent_below_12mm_research_screen"]
        ),
        "true_manufacturing_2d_pattern_generated": False,
        "fabric_and_assembly_approved": False,
    }


def _one_study(xyz, faces, choice):
    name, lower_base, upper_base, y_slope = choice
    scalar, lower, upper = _physical_cut_surfaces(xyz, lower_base, upper_base, y_slope)
    zones = _split_original_source(xyz, faces, scalar)
    parts = {name: _components(zone) for name, zone in zones.items()}
    if [len(parts[x]) for x in ("below", "root", "above")] != [1, 3, 2]:
        raise ValueError("original Stage6 non-horizontal band topology changed")
    original_area = _surface_area(xyz, faces)
    area = sum(_surface_area(zone["xyz"], zone["faces"]) for zone in zones.values())
    if abs(original_area - area) > 1e-4:
        raise ValueError("non-horizontal original source clipping lost area")
    patches = [_one_side(zones, parts, side) for side in ("left", "right")]
    return {
        "name": name,
        "nonhorizontal_source_vertex_cut_fields_mm": {
            "lower_z_at_y_center_mm": lower_base,
            "upper_z_at_y_center_mm": upper_base,
            "both_y_z_slope_amplitude_mm": y_slope,
            "y_center_mm": SLOPE_Y_CENTER_MM,
            "y_normalization_span_mm": SLOPE_Y_SPAN_MM,
            "lower_z_across_all_original_vertices_minmax_mm": [
                float(lower.min()),
                float(lower.max()),
            ],
            "upper_z_across_all_original_vertices_minmax_mm": [
                float(upper.min()),
                float(upper.max()),
            ],
            "piecewise_linear_source_vertex_scalar_not_analytic_fabric_seam": True,
        },
        "original_source_area_mm2": original_area,
        "all_3d_cut_zones_source_area_mm2": area,
        "source_area_reconstruction_error_mm2": abs(original_area - area),
        "true_3d_source_zone_component_counts": {
            key: len(components) for key, components in parts.items()
        },
        "original_ear_root_patches": patches,
        "source_original_triangles_never_modified": True,
        "3d_source_seams_not_2d_cloth_netlines": True,
        "double_6mm_sewing_allowance_not_verified": True,
        "manufacturing_seams_approved": False,
    }


def compare_nonhorizontal_original_source_roots(points, faces):
    """Two preregistered original-triangle source cuts, never factory patterns."""
    xyz, triangles = _source_mesh(points, faces, 230, 235)
    choices = [_one_study(xyz, triangles, choice) for choice in STUDIES]
    return {
        "schema": SCHEMA,
        "source_original_vertex_count": len(xyz),
        "source_original_triangle_count": len(triangles),
        "proposed_surface_designs": choices,
        "both_source_band_graph_widths_screened_against_12mm": True,
        "both_upper_ear_rims_still_narrow_and_not_material_qualified": True,
        "original_466k_high_density_source_not_directly_cut": True,
        "real_2d_fabric_rest_patterns_and_real_seam_allowance_not_generated": True,
        "signed_off_independent_ear_cloud_assembly_not_verified": True,
        "factory_cutting_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
    }
