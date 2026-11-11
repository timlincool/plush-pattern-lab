"""Visualize measured Stage6 original source-surface level-set events only."""

from __future__ import annotations

from plush_pattern_lab.validation.stage6_source_slab_continuity import SCHEMA


def render_source_slab_timeline(reports):
    """Display loop continuity; drawing is not a seam, cloth, or CAD pattern."""
    if len(reports) != 5 or any(report.get("schema") != SCHEMA for report in reports):
        raise ValueError("pinned five source slab reports required for topology atlas")
    width, height = 1580, 400
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fbfaf7"/>',
        '<text x="30" y="36" font-family="sans-serif" font-size="19" '
        'fill="#17283b">STAGE6 SOURCE SURFACE / REAL TRIANGLE Z-SLAB TOPOLOGY</text>',
        '<text x="30" y="58" font-family="sans-serif" font-size="12" '
        'fill="#a33">NOT CUT PATTERNS | NOT EAR ROOT SEAM PROOF</text>',
    ]
    for i, report in enumerate(reports):
        out.extend(_panel(report, 26 + i * 309))
    out.append(
        '<text x="30" y="385" font-family="sans-serif" font-size="12" '
        'fill="#334155">Blue: persists | Amber: branch/merge | '
        'Red: ends | Source 25% proxy, not fabric pattern</text>'
    )
    out.append("</svg>")
    return "\n".join(out) + "\n"


def _panel(report, left):
    zlo = report["lower_plane_z_mm"]
    zhi = report["upper_plane_z_mm"]
    lower = report["lower_original_source_loops"]
    upper = report["upper_original_source_loops"]
    top_x = {
        loop["loop_index_by_perimeter"]: left + 55 + i * 74
        for i, loop in enumerate(lower)
    }
    end_x = {
        loop["loop_index_by_perimeter"]: left + 55 + i * 74
        for i, loop in enumerate(upper)
    }
    out = [
        f'<rect x="{left}" y="80" width="294" height="277" rx="9" '
        'fill="white" stroke="#d6dee5"/>',
        f'<text x="{left + 14}" y="103" font-family="sans-serif" '
        f'font-size="14" fill="#102a43">Z{zlo} - Z{zhi} mm</text>',
        f'<text x="{left + 14}" y="122" font-family="sans-serif" '
        f'font-size="10" fill="#475569">'
        f'{report["source_triangle_count_in_open_slab"]} original triangles</text>',
    ]
    for slab in report["surface_components"]:
        a, b = slab["lower_loop_indices"], slab["upper_loop_indices"]
        color = (
            "#9b3c35" if not b and a else "#bc7a22"
            if len(a) != 1 or len(b) != 1 else "#206a9e"
        )
        for lo in a:
            for hi in b:
                out.append(
                    f'<path d="M {top_x[lo]} 168 Q {left + 147} 220 '
                    f'{end_x[hi]} 279" fill="none" stroke="{color}" '
                    'stroke-width="2.8"/>'
                )
        if a and not b:
            for lo in a:
                out.append(
                    f'<path d="M {top_x[lo]} 168 L {top_x[lo]} 212" '
                    'stroke="#9b3c35" stroke-width="2.8" '
                    'stroke-dasharray="4,3"/>'
                )
    for k, positions, yy in (
        ("L", top_x, 168),
        ("U", end_x, 279),
    ):
        for order, x in positions.items():
            out.append(
                f'<circle cx="{x}" cy="{yy}" r="18" '
                'fill="#f3f7fb" stroke="#31506b"/>'
            )
            out.append(
                f'<text x="{x}" y="{yy + 4}" font-family="sans-serif" '
                f'text-anchor="middle" font-size="12" fill="#152739">'
                f'{k}{order}</text>'
            )
    out.append(
        f'<text x="{left + 14}" y="338" font-family="sans-serif" '
        f'font-size="10" fill="#475569">'
        f'{len(lower)} lower / {len(upper)} upper closed loops</text>'
    )
    return out
