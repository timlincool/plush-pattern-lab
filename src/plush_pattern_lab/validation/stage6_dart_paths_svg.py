"""Illustrate original-source speculative ear dart tip routes; not cutting CAD."""

from __future__ import annotations

from plush_pattern_lab.validation.stage6_dart_paths import SCHEMA


def render_dart_tip_comparison_svg(report):
    if (
        report.get("schema") != SCHEMA
        or len(report.get("candidates", [])) != 4
        or report.get("factory_cutting_patterns_approved") != 0
    ):
        raise ValueError("pinned original source dart-route comparison required")
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" '
        'viewBox="0 0 1200 800">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<text x="22" y="34" font-family="sans-serif" font-size="21">'
        'Stage6 SOURCE-MESH ear dart route hypotheses (original Y/Z)</text>',
        '<text x="22" y="57" font-family="sans-serif" font-size="13" '
        'fill="#aa3931">NOT 2D FABRIC PATTERNS | NOT SEWABLE SEAMS</text>',
    ]
    for i, item in enumerate(report["candidates"]):
        out.extend(_panel(item, i))
    out.append(
        '<text x="22" y="775" font-family="sans-serif" font-size="12" '
        'fill="#475569">Actual source mesh edges, 10px/mm Y/Z; '
        'disjoint paths must converge at one speculative tip. '
        'Original 3D X differences are not shown.</text>'
    )
    out.append("</svg>")
    return "\n".join(out) + "\n"


def _panel(item, index):
    left, top = 18 + (index % 2) * 591, 88 + (index // 2) * 338
    center_y, center_z = top + 157, left + 280
    result = [
        f'<rect x="{left}" y="{top}" width="573" height="318" rx="9" '
        'fill="white" stroke="#cbd5e1"/>',
        f'<text x="{left + 13}" y="{top + 25}" font-family="sans-serif" '
        f'font-size="15">{item["side"]} / target Z'
        f'{item["tip_target_z_mm"]:.0f}mm</text>',
    ]

    def loc(point):
        return center_z + 10 * (point[1] + 45), center_y - 10 * (point[2] - 223)

    section = item["original_source_section_arc_xyz_mm"]
    result.append(_polyline(section, loc, "#98a4b3", 3.0))
    for points, color in zip(
        item["disjoint_original_source_route_xyz_mm"], ("#2d79ad", "#b77428")
    ):
        result.append(_polyline(points, loc, color, 2.8))
    tx, ty = loc(item["chosen_source_tip_xyz_mm"])
    result.append(
        f'<circle cx="{tx:.2f}" cy="{ty:.2f}" r="4.6" '
        'fill="#bd3546" stroke="white"/>'
    )
    gap = item["min_original_vertex_to_vertex_gap_beyond_tip_4mm_mm"]
    result.append(
        f'<text x="{left + 12}" y="{top + 296}" font-family="sans-serif" '
        'font-size="12" fill="#334155">source vertex gap after tip +4mm: '
        f'{gap:.2f}mm; naive merge vertices: '
        f'{item["unconstrained_shortest_routes_meet_early_vertex_count"]}</text>'
    )
    return result


def _polyline(points, transform, color, weight):
    if len(points) < 2:
        raise ValueError("original source polyline is incomplete")
    xy = " ".join(f"{x:.3f},{y:.3f}" for x, y in map(transform, points))
    return (
        f'<polyline points="{xy}" fill="none" stroke="{color}" '
        f'stroke-width="{weight}" stroke-linejoin="round"/>'
    )
