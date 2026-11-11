"""Draw Stage6 true source ring locations; never emit cutting paper patterns."""

from __future__ import annotations

from plush_pattern_lab.validation.stage6_ear_root_ab import SCHEMA


def render_root_ab_svg(report):
    if (
        report.get("schema") != SCHEMA
        or report.get("manufacturing_cutting_approved") != 0
        or len(report.get("candidate_options", [])) != 2
    ):
        raise ValueError("verified source-only ear-root A/B study required")
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="480" '
        'viewBox="0 0 1100 480">',
        '<rect width="100%" height="100%" fill="#fbfaf7"/>',
        '<text x="20" y="34" font-family="sans-serif" font-size="21" '
        'fill="#1f3345">Stage6 source ear-root ring A/B | original mesh</text>',
        '<text x="20" y="57" font-family="sans-serif" font-size="13" '
        'fill="#ac3b31">RESEARCH ONLY - NOT PATTERNS OR SEWING NOTCHES</text>',
    ]
    for order, candidate in enumerate(report["candidate_options"]):
        out.extend(_panel(candidate, 12 + order * 545))
    out.append(
        '<text x="20" y="463" font-family="sans-serif" font-size="12" '
        'fill="#52657b">Common 3 px/mm XY scale. XY gap and 6mm allowance '
        'are only research screens, not seam feasibility.</text>'
    )
    out.append("</svg>")
    return "\n".join(out) + "\n"


def _panel(candidate, left):
    z = candidate["source_plane_z_mm"]
    result = [
        f'<rect x="{left}" y="78" width="530" height="355" rx="8" '
        'fill="white" stroke="#d6dce3"/>',
        f'<text x="{left + 14}" y="106" font-family="sans-serif" '
        f'font-size="16" fill="#243749">{candidate["name"]} | Z={z} mm</text>',
    ]
    for side in candidate["source_side_loops"]:
        x0, y0 = left + 265, 248
        xy = side["full_interpolated_original_source_xy_mm"]
        points = " ".join(
            f"{x0 + 3 * x:.2f},{y0 - 3 * (y + 47):.2f}" for x, y in xy
        )
        color = "#216f9c" if side["side"] == "left" else "#aa6824"
        result.append(
            f'<polygon points="{points}" fill="none" stroke="{color}" '
            'stroke-width="2.1"/>'
        )
        for mark in side["four_arclength_reference_marks"]:
            x, y, _ = mark["true_source_xyz_mm"]
            result.append(
                f'<circle cx="{x0 + 3 * x:.2f}" cy="{y0 - 3 * (y + 47):.2f}" '
                'r="3" fill="#df4456"/>'
            )
        label_x = left + (20 if side["side"] == "left" else 290)
        minor = min(side["xy_bbox_width_mm"], side["xy_bbox_depth_mm"])
        result.append(
            f'<text x="{label_x}" y="375" font-family="sans-serif" '
            f'font-size="12" fill="{color}">{side["side"]}: '
            f'{side["source_3d_ring_perimeter_mm"]:.2f} mm, '
            f'XY minor {minor:.2f} mm</text>'
        )
    return result
