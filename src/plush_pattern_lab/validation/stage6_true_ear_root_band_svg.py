"""Research-only source 3D ear-root strip atlas, never a cloth paper pattern."""

from __future__ import annotations

from plush_pattern_lab.validation.stage6_true_ear_root_band_cut import SCHEMA


def render_real_root_band_svg(report):
    """Original XY view of two true 3D matched seams with width-risk notes."""
    if (
        report.get("schema") != SCHEMA
        or len(report.get("original_source_ear_root_band_patches", [])) != 2
        or report.get("approved_factory_cutting_patterns") != 0
    ):
        raise ValueError("only source-verified unapproved real root patches")
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1260" height="670" '
        'viewBox="0 0 1260 670">',
        '<rect width="100%" height="100%" fill="#fafbf9"/>',
        '<text x="24" y="39" font-family="sans-serif" font-size="22" '
        'fill="#1f3347">STAGE6 REAL TRIANGLE SOURCE CUT | TWO EAR ROOT BANDS</text>',
        '<text x="24" y="67" font-family="sans-serif" font-size="14" '
        'fill="#a73834">3D PAIRED GEOMETRY ONLY - NOT 2D FABRIC REST PATTERNS</text>',
    ]
    for index, patch in enumerate(report["original_source_ear_root_band_patches"]):
        out.extend(_draw_panel(patch, 20 + 630 * index))
    out.extend(
        [
            '<text x="24" y="622" font-family="sans-serif" font-size="16" '
            'fill="#9c3434">6mm + 6mm RESEARCH ALLOWANCE: '
            'source triangle surface graph spacing is insufficient</text>',
            '<text x="24" y="649" font-family="sans-serif" font-size="12" '
            'fill="#475569">Cut coordinates derive from immutable PLY original edge IDs '
            'and two exact Z intersections. Fabric thickness, hair and production '
            'turnover have NOT been tested.</text>',
            "</svg>",
        ]
    )
    return "\n".join(out) + "\n"


def _draw_panel(patch, left):
    side = patch["side"]
    bottom = patch["body_to_root_3d_paired_netline"]
    top = patch["root_to_upper_ear_3d_paired_netline"]
    xyz0 = bottom["original_source_3d_ordered_ring_xyz_mm"]
    xyz1 = top["original_source_3d_ordered_ring_xyz_mm"]
    combined = xyz0 + xyz1
    center_x = sum(p[0] for p in combined) / len(combined)
    center_y = sum(p[1] for p in combined) / len(combined)
    def point(p):
        return left + 310 + 16 * (p[0] - center_x), 306 - 16 * (p[1] - center_y)
    def polygon(xyz):
        return " ".join(f"{u:.2f},{v:.2f}" for u, v in map(point, xyz))
    gap = patch["between_two_3d_seams_source_surface_graph"]
    lower_len = bottom["paired_3d_netline_length_each_side_mm"]
    upper_len = top["paired_3d_netline_length_each_side_mm"]
    return [
        f'<rect x="{left}" y="93" width="610" height="495" rx="10" '
        'fill="#fff" stroke="#cbd5e1"/>',
        f'<text x="{left + 18}" y="127" font-family="sans-serif" '
        f'font-size="20" fill="#203449">{side.upper()} / source root band</text>',
        f'<polygon points="{polygon(xyz0)}" fill="none" '
        'stroke="#215f94" stroke-width="2.8"/>',
        f'<polygon points="{polygon(xyz1)}" fill="none" '
        'stroke="#bd7a28" stroke-width="2.8"/>',
        f'<text x="{left + 20}" y="506" font-family="sans-serif" '
        'font-size="14" fill="#215f94">'
        f'Z230 paired seam: {lower_len:.3f}mm / '
        f'{bottom["original_crossed_source_triangle_segment_count"]} source segments</text>',
        f'<text x="{left + 20}" y="532" font-family="sans-serif" '
        'font-size="14" fill="#a36623">'
        f'Z235 paired seam: {upper_len:.3f}mm / '
        f'{top["original_crossed_source_triangle_segment_count"]} source segments</text>',
        f'<text x="{left + 20}" y="558" font-family="sans-serif" '
        'font-size="13" fill="#943b34">'
        'Smallest source graph gap: '
        f'{gap["surface_graph_shortest_path_min_p05_median_p95_max_mm"][0]:.2f}mm'
        '</text>',
    ]
