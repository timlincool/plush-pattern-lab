"""A4 millimetre top projection of the original seven genuine Stage6 3D rims.

Not an unwrapped two-dimensional fabric cutting line or approved pattern.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import numpy as np

from plush_pattern_lab.validation.stage6_lower_seven_port_graph import (
    SCHEMA,
    _clip_original_lower,
)
from plush_pattern_lab.validation.whole_shell_partition import (
    _edge_ownership,
    _interfaces,
)

HEAD_COLORS = ("#b75a47", "#ba7b2c", "#ba7b2c")
ZONE_COLORS = {
    "0:1": "#387f93",
    "0:2": "#5877a3",
    "1:3": "#387f93",
    "2:3": "#5877a3",
}


def _line(a, b, color, width):
    left = np.asarray([a[0] + 105, 197 - a[1]], dtype=float)
    right = np.asarray([b[0] + 105, 197 - b[1]], dtype=float)
    if (
        np.any(left < 0)
        or np.any(right < 0)
        or left[0] > 210
        or right[0] > 210
        or left[1] > 297
        or right[1] > 297
    ):
        raise ValueError("true original XY projection falls outside A4 millimetres")
    return (
        f'<line x1="{left[0]:.4f}" y1="{left[1]:.4f}" '
        f'x2="{right[0]:.4f}" y2="{right[1]:.4f}" '
        f'stroke="{color}" stroke-width="{width}" />'
    )


def render_seven_real_rims_a4(source, faces, caps, report, y_split, trimesh_module):
    """Project physical-source X/Y 1:1; never pretend this is fabric rest shape."""
    if (
        report.get("schema") != SCHEMA
        or report.get("factory_cutting_patterns_approved") != 0
        or y_split not in (20.0, 25.0)
        or y_split
        not in [
            row["split_y_mm"] for row in report.get("source_four_zone_comparisons", [])
        ]
    ):
        raise ValueError("original seven-rim study required before source drawing")
    xyz, triangles = _clip_original_lower(source, faces, trimesh_module)
    centers = xyz[triangles].mean(axis=1)
    labels = (centers[:, 0] >= 0).astype(np.int8) * 2
    labels += (centers[:, 1] >= y_split).astype(np.int8)
    topology = _edge_ownership(triangles)
    boundaries = topology[0][topology[1] == 1]
    upper = np.all(np.abs(xyz[boundaries, 2] - 230) < 1e-7, axis=1)
    _, matched, paired, _ = _interfaces(labels, xyz, topology)
    if not paired or len(boundaries) != 2462 or int(upper.sum()) != 414:
        raise ValueError("actual source boundary or zone seam count changed")
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="210mm" '
        'height="297mm" viewBox="0 0 210 297">',
        '<rect width="210" height="297" fill="#ffffff" />',
        '<text x="10" y="10" font-family="sans-serif" font-size="5">'
        "ORIGINAL STAGE6 - 7 PORTS / 4 ZONES</text>",
        f'<text x="10" y="16" font-family="sans-serif" font-size="3.3">'
        f"XY top projection 1:1 mm, partition Y={y_split:.0f} mm</text>",
        '<text x="10" y="22" font-family="sans-serif" font-size="3.3" '
        'fill="#b75a47">NOT FABRIC REST SHAPE / NOT INDUSTRIAL PATTERN</text>',
        '<g stroke-linecap="round" fill="none">',
    ]
    for a, b in boundaries[~upper]:
        out.append(_line(xyz[a], xyz[b], "#282e33", "0.48"))
    for seam in matched:
        a, b = seam["vertex_ids"]
        out.append(_line(xyz[a], xyz[b], ZONE_COLORS[seam["region_pair"]], "0.55"))
    for cap, color in zip(caps["upper_caps"], HEAD_COLORS):
        points = np.asarray(cap["vertices_xyz_mm"], dtype=float)
        ring = points[cap["original_rim_vertex_ids_in_cap_local_order"]]
        for a, b in zip(ring, np.roll(ring, -1, axis=0)):
            out.append(_line(a, b, color, "0.65"))
    out.extend(
        [
            "</g>",
            '<rect x="170" y="34" width="34" height="42" '
            'fill="#fff" stroke="#d5dce1" stroke-width=".25"/>',
            '<text x="172" y="39" font-size="3.0" '
            'font-family="sans-serif">3D source boundaries</text>',
        ]
    )
    legend = (
        ("#282e33", "4 hoof rims", 44),
        ("#b75a47", "central cap", 50),
        ("#ba7b2c", "side ports", 56),
        ("#5877a3", "4-zone seams", 62),
    )
    for color, label, height in legend:
        out.append(
            f'<line x1="172" y1="{height}" x2="178" y2="{height}" '
            f'stroke="{color}" stroke-width=".8"/>'
        )
        out.append(
            f'<text x="179" y="{height + 1}" font-size="2.8" '
            f'font-family="sans-serif">{label}</text>'
        )
    out.extend(
        [
            '<rect x="181" y="275" width="10" height="10" '
            'stroke="#111" stroke-width=".45" fill="none"/>',
            '<text x="176" y="291" font-size="2.8" '
            'font-family="sans-serif">10x10 mm gauge</text>',
            '<text x="10" y="292" font-size="3.0" '
            'font-family="sans-serif" fill="#b75a47">'
            "Research top projection only - never cut cloth from this drawing.</text>",
            "</svg>",
        ]
    )
    svg = "\n".join(out) + "\n"
    ET.fromstring(svg)
    return svg
