"""Scale-aware visual counterexample of a real CUT but not sewable full panel.

The underlying UV solution may self-overlap and is explicitly not a cutting line.
The exact 3D source edge and local 2D vertex IDs remain in the companion JSON.
"""

from __future__ import annotations

import numpy as np

COLORS = {"hoof": "#376C9A", "outer": "#D08C35", "slit": "#C04F50"}


def render_full_panel_research_svg(disk, uv, results):
    """Every boundary line is actual UV(mm), even if the solution is rejected."""
    xy = np.asarray(uv, dtype=np.float64)
    if xy.ndim != 2 or xy.shape[1] != 2 or not np.isfinite(xy).all():
        raise ValueError("expected finite cut-panel 2D millimetre coordinates")
    minimum, maximum = xy.min(axis=0), xy.max(axis=0)
    bbox = maximum - minimum
    if np.any(bbox <= 0):
        raise ValueError("collapsed UV net drawing")
    margin = 16
    width, height = (bbox + 2 * margin).tolist()
    edge_ids = np.asarray(disk["boundary_edges"], dtype=np.int64)
    source_ids = np.asarray(disk["source_vertex_ids"])
    hoof = {tuple(sorted(edge)) for edge in disk["source_cuff_edge_global_ids"]}
    outer = {tuple(sorted(edge)) for edge in disk["source_outer_edge_global_ids"]}
    slit = {
        tuple(sorted(edge))
        for edge in zip(
            disk["slit_path_source_vertex_ids"][:-1],
            disk["slit_path_source_vertex_ids"][1:],
        )
    }
    strokes = []
    for a, b in edge_ids:
        pair = tuple(sorted((int(source_ids[a]), int(source_ids[b]))))
        kind = "hoof" if pair in hoof else "outer" if pair in outer else "slit"
        if kind == "slit" and pair not in slit:
            raise ValueError("invalid boundary classification for research SVG")
        x1, y1 = xy[a] - minimum + margin
        x2, y2 = xy[b] - minimum + margin
        strokes.append(
            f'<line x1="{x1:.4f}" y1="{y1:.4f}" '
            f'x2="{x2:.4f}" y2="{y2:.4f}" '
            f'stroke="{COLORS[kind]}" stroke-width="0.18"/>'
        )
    quality = results["strain_screen"]
    label = results["status"]
    p95 = quality["triangle_edge_relative_error"]["p95"]
    collisions = results["global_2d_overlap"]["overlapping_nonzero_area_triangle_pairs"]
    xscale, yscale = margin, height - 8
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.3f}mm" '
        f'height="{height:.3f}mm" viewBox="0 0 {width:.3f} {height:.3f}">',
        '<rect width="100%" height="100%" fill="white"/>',
        *strokes,
        f'<text x="4" y="4" font-size="2.6" fill="#a52c20">{label}</text>',
        f'<text x="4" y="8" font-size="2.3">EDGE P95 {p95:.1%}; '
        f'OVERLAP PAIRS {collisions}</text>',
        '<text x="4" y="12" font-size="2.3">NOT A CUTTING TEMPLATE</text>',
        f'<line x1="{xscale:.2f}" y1="{yscale:.2f}" '
        f'x2="{xscale + 10:.2f}" y2="{yscale:.2f}" '
        'stroke="black" stroke-width="0.35"/>',
        f'<text x="{xscale:.2f}" y="{yscale - 1:.2f}" font-size="2.3">'
        '10 mm reference</text>',
        "</svg>",
    ]
    return "\n".join(parts) + "\n"
