"""Side-by-side actual source non-horizontal cut rings, not fabric paper."""

from __future__ import annotations

from plush_pattern_lab.validation.stage6_nonhorizontal_ear_root_cut import SCHEMA


def render_nonhorizontal_ear_root_svg(report):
    """Four source-XYZ review panels, equal XY scale; NO cloth cutting lines."""
    if (
        report.get("schema") != SCHEMA
        or len(report.get("proposed_surface_designs", [])) != 2
        or report.get("factory_cutting_patterns_approved") != 0
    ):
        raise ValueError("only original non-approved source cut studies can be drawn")
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1300" height="790" '
        'viewBox="0 0 1300 790">',
        '<rect width="100%" height="100%" fill="#f9fafb"/>',
        '<text x="24" y="36" font-family="sans-serif" font-size="22" '
        'fill="#1d3448">Original Stage6 non-horizontal 3D ear-root band studies</text>',
        '<text x="24" y="61" font-family="sans-serif" font-size="13" '
        'fill="#ac3531">ACTUAL SOURCE TRIANGLES / NOT 2D FABRIC PATTERNS</text>',
    ]
    for i, option in enumerate(report["proposed_surface_designs"]):
        for j, patch in enumerate(option["original_ear_root_patches"]):
            out.extend(_one_panel(option, patch, 12 + i * 644, 91 + j * 328))
    out.extend(
        [
            '<text x="24" y="770" font-family="sans-serif" font-size="12" '
            'fill="#475569">Same 16 px/mm XY scale | Original source mesh '
            'edge coordinates and Z variation | No validated fabric allowance '
            'or sewing assembly</text>',
            "</svg>",
        ]
    )
    return "\n".join(out) + "\n"


def _one_panel(option, patch, left, top):
    lower = patch["body_to_root_paired_3d_source_netline"]
    upper = patch["root_to_upper_ear_paired_3d_source_netline"]
    low_xyz = lower["original_source_3d_ordered_ring_xyz_mm"]
    hi_xyz = upper["original_source_3d_ordered_ring_xyz_mm"]
    both = low_xyz + hi_xyz
    cx = sum(p[0] for p in both) / len(both)
    cy = sum(p[1] for p in both) / len(both)

    def project(p):
        return left + 310 + 16 * (p[0] - cx), top + 148 - 16 * (p[1] - cy)

    def path(points):
        return " ".join(f"{x:.2f},{y:.2f}" for x, y in map(project, points))

    graph = patch["surface_graph_between_3d_netlines"]
    width = graph["surface_graph_shortest_path_min_p05_median_p95_max_mm"][0]
    min_rim = upper["original_world_xy_minor_extent_mm"]
    return [
        f'<rect x="{left}" y="{top}" width="632" height="318" rx="9" '
        'fill="white" stroke="#d5dde3"/>',
        f'<text x="{left + 14}" y="{top + 25}" font-family="sans-serif" '
        f'font-size="17" fill="#17334b">{option["name"]} / {patch["side"]}</text>',
        f'<polygon points="{path(low_xyz)}" fill="none" stroke="#236995" '
        'stroke-width="3.0"/>',
        f'<polygon points="{path(hi_xyz)}" fill="none" stroke="#b4742c" '
        'stroke-width="3.0"/>',
        f'<text x="{left + 17}" y="{top + 258}" font-family="sans-serif" '
        'font-size="12" fill="#2e4b61">3D source graph gap '
        f'{width:.2f}mm; upper rim XY minor {min_rim:.2f}mm</text>',
        f'<text x="{left + 17}" y="{top + 282}" font-family="sans-serif" '
        'font-size="12" fill="#ad3532">Upper seam still too narrow '
        'for assumed 2 x 6mm allowances; no 2D pattern</text>',
    ]
