"""A static SVG of slit triangle-band UVs: diagnostic, not a cutting stencil."""

from __future__ import annotations

from html import escape

import numpy as np


def _layout(results, layouts):
    spans = []
    for corners in layouts:
        pts = np.asarray(corners, dtype=np.float64).reshape(-1, 2)
        if not np.isfinite(pts).all() or len(pts) < 3:
            raise ValueError("invalid UV triangles")
        spans.append((pts.min(axis=0), np.ptp(pts, axis=0)))
    cell_w = max(float(span[1][0]) for span in spans) + 32
    cell_h = max(float(span[1][1]) for span in spans) + 28
    return spans, cell_w, cell_h


def draw_slit_unroll_svg(results, layouts):
    """Research visualization at real mm scale; no allowances or cut boundaries."""
    if len(results) != 8 or len(layouts) != 8:
        raise ValueError("expected eight actual Stage 6 triangular patches")
    spans, cell_w, cell_h = _layout(results, layouts)
    width, height = 2 * cell_w, 4 * cell_h + 8
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.3f}mm" '
        f'height="{height:.3f}mm" viewBox="0 0 {width:.3f} {height:.3f}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<g fill="#f5f6f4" stroke="#71838b" stroke-width="0.09">',
    ]
    for i, (record, corners) in enumerate(zip(results, layouts)):
        minimum, _ = spans[i]
        origin = np.array([cell_w * (i % 2) + 12, cell_h * (i // 2) + 15])
        coords = np.asarray(corners) - minimum + origin
        for face in coords:
            points = " ".join(f"{x:.3f},{y:.3f}" for x, y in face)
            parts.append(f'<polygon points="{points}"/>')
        quality = record["optimized"]
        label = escape(str(record["object"]))[:52]
        parts.extend(
            [
                '</g><g fill="#273c49" font-size="3.4">',
                f'<text x="{origin[0]:.2f}" y="{origin[1] - 6:.2f}">'
                f"{label} / ring {record['ring_index']}</text>",
                f'<text x="{origin[0]:.2f}" y="{origin[1] - 2:.2f}">'
                f"p95 {quality['p95_abs_edge_relative_error']:.1%}; "
                f"flips {quality['mixed_winding_or_collapsed_triangles']}; "
                f"overlap {record['overlap']['overlapping_triangle_pairs']}</text>",
                '</g><g fill="#f5f6f4" stroke="#71838b" stroke-width="0.09">',
            ]
        )
    parts.extend(
        [
            "</g>",
            f'<text x="8" y="{height - 4:.2f}" font-size="3.2">'
            "RESEARCH ONLY: PERIODIC SEAM SLIT - NOT A CUT PATTERN"
            "</text>",
            "</svg>",
        ]
    )
    return "\n".join(parts) + "\n"
