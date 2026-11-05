"""Top projection of actual 3D seam edges: NEVER a 2D fabric cutting template."""

from __future__ import annotations

import numpy as np

PALETTE = {"0:1": "#CB6E2D", "0:2": "#2584A0", "1:3": "#2584A0", "2:3": "#CB6E2D"}


def render_four_zone_seam_map(vertices_mm, report):
    """View from +Z; use true 3D seam edge x/y, not flattened rest lengths."""
    points = np.asarray(vertices_mm, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("expected real 3D millimetre positions")
    if not np.isfinite(points).all():
        raise ValueError("invalid 3D seam diagram coordinates")
    if not report["all_regions_single_connected_annuli_with_one_complete_hoof"]:
        raise ValueError("must not visualize a rejected full-shell panel candidate")
    x0, y0 = points[:, :2].min(axis=0)
    x1, y1 = points[:, :2].max(axis=0)
    margin = 12
    width, height = float(x1 - x0 + 2 * margin), float(y1 - y0 + 2 * margin)

    def point(vertex_id):
        x, y = points[int(vertex_id), :2]
        return float(x - x0 + margin), float(y1 - y + margin)

    strokes = []
    for edge in report["seam_edges"]:
        a, b = (point(idx) for idx in edge["vertex_ids"])
        color = PALETTE[edge["region_pair"]]
        strokes.append(
            f'<line x1="{a[0]:.3f}" y1="{a[1]:.3f}" '
            f'x2="{b[0]:.3f}" y2="{b[1]:.3f}" stroke="{color}"/>'
        )
    circles = []
    for region in report["regions"]:
        x, y, z = region["source_hoof_centroid_mm"]
        sx, sy = float(x - x0 + margin), float(y1 - y + margin)
        circles.append(
            f'<circle cx="{sx:.3f}" cy="{sy:.3f}" r="2.0" '
            f'fill="#f6efe1" stroke="#394e5a" stroke-width="0.25"/>'
        )
    title = "STAGE6 MAIN SHELL / TOP-PROJECTED 3D SEAM DRAFT"
    warning = "NOT FABRIC CUT LINES / NOT 2D REST SHAPE"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.3f}mm" '
        f'height="{height:.3f}mm" viewBox="0 0 {width:.3f} {height:.3f}">
'
        '<rect width="100%" height="100%" fill="#ffffff"/>
'
        f'<text x="3" y="6" font-size="3" fill="#223746">{title}</text>
'
        f'<g stroke-width="0.55" stroke-linecap="round">
'
        + "
".join(strokes)
        + "
</g>
"
        + "
".join(circles)
        + f'
<text x="3" y="{height - 3:.3f}" font-size="3" fill="#bf4c2d">'
        + warning
        + "</text>
</svg>
"
    )
