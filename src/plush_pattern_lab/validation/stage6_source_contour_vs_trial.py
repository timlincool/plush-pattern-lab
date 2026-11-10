"""Compare actual source contour loops against two unapproved 2D trial rings."""

from __future__ import annotations

import numpy as np
from shapely.geometry import Polygon

SOURCE_REVIEW_Z_MM = (135, 145, 155, 180, 205, 230)


def _trial_ring_at_z(option, height):
    if height == 135:
        heights, key = option["body_rings_z_mm"], "body_synthetic_rings_xy_mm"
    else:
        heights, key = option["head_rings_z_mm"], "head_synthetic_rings_xy_mm"
    if height not in heights:
        raise ValueError("trial does not contain requested source slice height")
    coords = np.asarray(option[key][heights.index(height)], dtype=np.float64)
    poly = Polygon(coords)
    if not poly.is_valid or poly.area <= 10:
        raise ValueError("untrusted source-envelope surrogate ring polygon")
    return poly


def compare_true_contours_to_split_study(real, study):
    if (
        real.get("schema") != "stage6-true-triangle-plane-component-loops-v1"
        or study.get("schema") != "stage6-separated-torso-headneck-mother-trial-ab-v1"
        or study.get("factory_cutting_patterns_approved") != 0
        or len(study.get("options", [])) != 2
    ):
        raise ValueError("not the current source-linked research contour and A/B trial")
    reference = {row["plane_z_mm"]: row for row in real["sections"]}
    if not set(SOURCE_REVIEW_Z_MM).issubset(reference):
        raise ValueError("source exact neck and head triangle-plane contours missing")
    candidates = []
    for option in study["options"]:
        comparisons = []
        for height in SOURCE_REVIEW_Z_MM:
            section = reference[height]
            contours = section["source_contours"]
            source = Polygon(contours[0]["true_interpolated_contour_xy_mm"])
            trial = _trial_ring_at_z(option, height)
            comparisons.append(
                {
                    "source_z_mm": height,
                    "true_source_section_component_count": len(contours),
                    "true_source_largest_closed_contour_edges": contours[0][
                        "crossed_original_source_edges"
                    ],
                    "true_source_dominant_loop_perimeter_mm": float(source.length),
                    "new_research_trial_ring_perimeter_mm": float(trial.length),
                    "net_perimeter_difference_mm": float(trial.length - source.length),
                    "true_vs_trial_boundary_hausdorff_distance_mm": float(
                        source.boundary.hausdorff_distance(trial.boundary)
                    ),
                    "true_source_other_loops_ignored_by_trial": len(contours) - 1,
                    "source_sculpt_aligned_and_factory_approved": False,
                }
            )
        candidates.append(
            {
                "name": option["name"],
                "compared_slice_heights_mm": list(SOURCE_REVIEW_Z_MM),
                "source_true_loop_to_trial_ring": comparisons,
                "max_2d_true_source_contour_boundary_hausdorff_mm": max(
                    row["true_vs_trial_boundary_hausdorff_distance_mm"]
                    for row in comparisons
                ),
                "single_head_top_cap_fails_true_z230_component_structure": (
                    reference[230]["true_source_plane_intersection_component_count"] > 1
                ),
                "approved_for_cutting": False,
            }
        )
    return {
        "schema": "stage6-real-sculpt-contour-vs-split-A-B-trial-qa-v1",
        "reference_type": "true_original_triangles_intersected_with_horizontal_plane",
        "metric": "XY plane boundary Hausdorff distance at identical source Z",
        "actual_closed_component_count_125": reference[125][
            "true_source_plane_intersection_component_count"
        ]
        if 125 in reference
        else None,
        "actual_closed_component_count_230": reference[230][
            "true_source_plane_intersection_component_count"
        ],
        "actual_closed_component_count_245": reference[245][
            "true_source_plane_intersection_component_count"
        ]
        if 245 in reference
        else None,
        "candidates": candidates,
        "true_source_slice_is_not_fabric_rest_shape": True,
        "source_to_trial_sewing_not_proven": True,
        "factory_cutting_approved": 0,
    }


def render_true_source_contours_svg(report):
    """Draw all original exact contours at shared XY scale, not a paper pattern."""
    if report.get("schema") != "stage6-true-triangle-plane-component-loops-v1":
        raise ValueError("actual source contour audit required before rendering")
    slices = report["sections"]
    if not 2 <= len(slices) <= 16:
        raise ValueError("research contour atlas supports 2–16 source planes")
    width, height = 1200, ((len(slices) + 3) // 4) * 235 + 40
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="white"/>',
        '<text x="13" y="20" font-family="sans-serif" font-size="15">'
        "REAL STAGE6 original triangle-plane contours | NOT FABRIC CUTTING</text>",
    ]
    for i, section in enumerate(slices):
        out.extend(_draw_source_section_panel(section, i))
    out.append("</svg>")
    return "\n".join(out) + "\n"


def _draw_source_section_panel(section, index):
    left, top = 4 + (index % 4) * 300, 36 + (index // 4) * 235
    scale = 0.74
    result = [
        f'<rect x="{left}" y="{top}" width="292" height="227" '
        'fill="#fafafa" stroke="#cdd2d5" stroke-width=".8"/>',
        f'<text x="{left + 10}" y="{top + 17}" font-family="sans-serif" '
        f'font-size="12">Z={section["plane_z_mm"]}mm | '
        f"{section['true_source_plane_intersection_component_count']} source loops</text>",
    ]
    for order, contour in enumerate(section["source_contours"]):
        points = np.asarray(contour["true_interpolated_contour_xy_mm"], dtype=float)
        x = left + 146 + scale * points[:, 0]
        y = top + 110 - scale * (points[:, 1] - 24)
        coords = " ".join(f"{a:.2f},{b:.2f}" for a, b in zip(x, y))
        stroke = "#27699c" if order == 0 else "#b95723"
        result.append(
            f'<polygon points="{coords}" fill="none" stroke="{stroke}" '
            'stroke-width="1.2" stroke-linejoin="round"/>'
        )
    result.append(
        f'<text x="{left + 10}" y="{top + 217}" '
        'font-family="sans-serif" font-size="9">'
        "True 3D mesh intersections; common 0.74 px/mm XY scale</text>"
    )
    return result
