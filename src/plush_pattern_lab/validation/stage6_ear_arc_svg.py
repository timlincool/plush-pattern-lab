"""Display fixed original Stage6 quadrant arcs, not sewable cutting lines."""

from __future__ import annotations

from plush_pattern_lab.validation.stage6_ear_arc_screen import SCHEMA

COLORS = {
    "medial": "#2563a6",
    "posterior": "#ab711e",
    "lateral": "#c74a46",
    "anterior": "#687b8c",
}


def render_stage6_arc_screen_svg(report, study):
    """Compare 16 original-source partial arcs at equal local XY scale."""
    if (
        report.get("schema") != SCHEMA
        or len(report.get("option_results", [])) != 2
        or report.get("approved_factory_cutting_patterns") != 0
    ):
        raise ValueError("unverified Stage6 source arc screen report")
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1180" height="770" '
        'viewBox="0 0 1180 770">',
        '<rect width="1180" height="770" fill="#fafaf8"/>',
        '<text x="20" y="38" font-family="sans-serif" font-size="21" '
        'fill="#1a334a">Stage6 source ear-root: fixed quadrant arc screens</text>',
        '<text x="20" y="61" font-family="sans-serif" font-size="12" '
        'fill="#b1322d">NOT CUTTING PATTERNS / NOT HIDDEN SEAM APPROVAL</text>',
    ]
    for i, option in enumerate(report["option_results"]):
        source = study["candidate_options"][i]
        if source["name"] != option["name"]:
            raise ValueError("source study and rendered option differ")
        for j, side in enumerate(option["sides"]):
            contour = source["source_side_loops"][j]
            if side["side"] != contour["side"]:
                raise ValueError("original source side mismatch")
            out.extend(_panel(option, side, contour, i, j))
    out.append(
        '<text x="24" y="750" font-family="sans-serif" font-size="12" '
        'fill="#455366">Blue: medial / ochre: posterior / red: lateral / '
        'grey: anterior. 10 px/mm; recentered; open unpaired endpoints.</text>'
    )
    out.append("</svg>")
    return "\n".join(out) + "\n"


def _panel(option, side, contour, column, row):
    left, top = 18 + column * 579, 88 + row * 326
    center_x, center_y = left + 285, top + 138
    xy = contour["full_interpolated_original_source_xy_mm"]
    z = option["source_z_mm"]
    cx, cy = contour["source_centroid_xy_mm"]

    def position(point):
        return center_x + 10 * (point[0] - cx), center_y - 10 * (point[1] - cy)

    outline = " ".join(
        f"{px:.2f},{py:.2f}" for px, py in map(position, xy)
    )
    result = [
        f'<rect x="{left}" y="{top}" width="559" height="313" rx="10" '
        'fill="white" stroke="#d3dbe3"/>',
        f'<text x="{left + 14}" y="{top + 25}" font-family="sans-serif" '
        f'font-size="15" fill="#1e3448">{option["name"]} | '
        f'{side["side"]} | Z={z}mm</text>',
        f'<polygon points="{outline}" fill="none" stroke="#c9d3df" '
        'stroke-width="2.0"/>',
    ]
    for arc in side["quadrant_arc_hypotheses"]:
        start = arc["original_source_edge_ordinal_start"]
        stop = arc["original_source_edge_ordinal_end"]
        count = (stop - start) % len(xy) + 1
        segment = [xy[(start + k) % len(xy)] for k in range(count)]
        pts = " ".join(
            f"{px:.2f},{py:.2f}" for px, py in map(position, segment)
        )
        color = COLORS[arc["hypothesis"]]
        result.append(
            f'<polyline points="{pts}" fill="none" stroke="{color}" '
            'stroke-width="3.2" stroke-linecap="round"/>'
        )
        for endpoint in (segment[0], segment[-1]):
            px, py = position(endpoint)
            result.append(
                f'<circle cx="{px:.2f}" cy="{py:.2f}" r="3.6" '
                f'fill="white" stroke="{color}" stroke-width="1.7"/>'
            )
    medial = side["quadrant_arc_hypotheses"][0]
    views = medial["per_view_12point_first_hit"]
    exposed = sum(
        result["near_original_body_first_surface"] for result in views.values()
    )
    result.extend(
        [
            f'<text x="{left + 15}" y="{top + 271}" font-family="sans-serif" '
            'font-size="12" fill="#304557">Medial source arc: '
            f'{medial["source_original_plane_arc_length_mm"]:.2f}mm; '
            f'near-body first-hits {exposed}/48 in 4 views</text>',
            f'<text x="{left + 15}" y="{top + 292}" font-family="sans-serif" '
            'font-size="11" fill="#7f3433">Raw 41Mesh only; '
            '12 source samples; no paired sewing edge</text>',
        ]
    )
    return result
