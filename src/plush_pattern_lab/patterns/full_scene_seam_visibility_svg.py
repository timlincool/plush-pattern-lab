"""Source-linked five-view design screen: original product Mesh occlusion layers.

The drawing is a projected research overlay, not a render, photograph,
continuous segment-visibility proof, sewing template or aligned design image.
"""

from __future__ import annotations

import numpy as np

from plush_pattern_lab.patterns.source_seam_view_svg import (
    ROUTE_STROKES,
    VIEWS,
    _face_features,
    _polyline,
    _screen,
)

REPORT_SCHEMA = "stage6-original-full-41-product-mesh-source-seam-occlusion-v1"
PANEL_WIDTH = 492
PANEL_HEIGHT = 434
CANVAS_WIDTH = 1500
CANVAS_HEIGHT = 950


def _view_body_dots(convert, source):
    dots = source[:: max(1, len(source) // 3200)]
    result = []
    for x, y in convert(dots):
        result.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="0.5" fill="#79848c" opacity="0.19"/>'
        )
    return result


def _is_near_body(sample):
    return sample["classification"] == "near_original_body_first_surface"


def _route_lines(convert, view, report):
    result = []
    for index, path in enumerate(report["paths"]):
        samples = path["samples"]
        points = np.asarray([s["original_source_xyz_mm"] for s in samples])
        uv = convert(points)
        for j in range(len(uv) - 1):
            one, two = samples[j : j + 2]
            near = _is_near_body(one) and _is_near_body(two)
            color = ROUTE_STROKES[index] if near else "#9b9b9b"
            result.append(
                _polyline(
                    uv[j : j + 2],
                    1.55,
                    stroke=color,
                    dashed=not near,
                )
            )
        if view == "front":
            result.extend(_face_warning_dots(convert, samples))
    return result


def _face_warning_dots(convert, samples):
    result = []
    for sample in samples:
        if not sample["historic_face_v14_alert"]:
            continue
        x, y = convert(np.asarray([sample["original_source_xyz_mm"]]))[0]
        color = "#e53525" if _is_near_body(sample) else "#de8700"
        result.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.1" '
            f'fill="none" stroke="{color}" stroke-width="1.4"/>'
        )
    return result


def _view_panel(points, report, historic, view, index):
    name, axes, signs = view
    left = 5 + (index % 3) * 500
    top = 63 + (index // 3) * 440
    convert, _ = _screen((axes, signs), points, left, top, PANEL_WIDTH, PANEL_HEIGHT)
    parts = [
        f'<rect x="{left}" y="{top}" width="{PANEL_WIDTH}" height="{PANEL_HEIGHT}" '
        'fill="#fff" stroke="#b1b9be" stroke-width="0.8"/>',
        f'<text x="{left + 15}" y="{top + 20}" font-family="sans-serif" '
        f'font-size="13">{name.upper()} | PRODUCT RAW MESH FIRST-HIT</text>',
    ]
    parts.extend(_view_body_dots(convert, points))
    if name == "front":
        parts.extend(_face_features(convert, historic))
    parts.extend(_route_lines(convert, name, report))
    target = report["paths"][2]
    counts = target["classifications"]
    near = counts.get("near_original_body_first_surface", 0)
    overlay = target["other_mesh_occluded_count"]
    unknown = target["unresolved_or_no_hit_count"]
    parts.append(
        f'<text x="{left + 11}" y="{top + PANEL_HEIGHT - 8}" '
        'font-family="sans-serif" font-size="10">'
        f"B2: near body {near} | other Mesh occluded {overlay} | unresolved {unknown}"
        "</text>"
    )
    return parts


def render_product_mesh_five_view_svg(source_points, report, historic_face):
    """Only five projection panels; real 3D first-hit classifications supplied."""
    raw = np.asarray(source_points, dtype=np.float64)
    if raw.ndim != 2 or raw.shape[1] != 3 or not np.isfinite(raw).all():
        raise ValueError("valid pinned source proxy XYZ required")
    if report.get("schema") != REPORT_SCHEMA:
        raise ValueError("not real Stage6 full product Mesh visibility")
    if report.get("product_meshes_raytested") != 41:
        raise ValueError("full product Mesh coverage missing")
    if [v["view"] for v in report["view_results"]] != [v[0] for v in VIEWS]:
        raise ValueError("missing actual five-view original scene evidence")
    if historic_face.get("revision") != "surface14":
        raise ValueError("historical nose/eye placement contract changed")
    result = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_WIDTH}" '
        f'height="{CANVAS_HEIGHT}" viewBox="0 0 {CANVAS_WIDTH} {CANVAS_HEIGHT}">',
        '<rect width="1500" height="950" fill="#fbfbfb"/>',
        '<text x="15" y="22" font-family="sans-serif" font-size="17">'
        "STAGE6 B THREE RADIAL SEAMS | 41 PRODUCT MESH FIRST-HIT, 5 VIEWS</text>",
        '<text x="15" y="43" font-family="sans-serif" font-size="11">'
        "Historical face v14 shown only as a warning;"
        " original body proxy is not final face embroidery.</text>",
    ]
    for index, view in enumerate(VIEWS):
        result.extend(
            _view_panel(raw, report["view_results"][index], historic_face, view, index)
        )
    result.extend(
        [
            '<text x="1015" y="535" font-family="sans-serif" font-size="13">'
            "Source path colors: red old, amber high-1, blue high-2.</text>",
            '<text x="1015" y="559" font-family="sans-serif" font-size="12">'
            "Solid = source near first body mesh; gray dashed = otherwise.</text>",
            '<text x="1015" y="582" font-family="sans-serif" font-size="12">'
            "Front orange/red circles = historic eye/nose/mouth alert vertices.</text>",
            '<text x="1015" y="605" font-family="sans-serif" font-size="12">'
            "Other Mesh occlusion is NOT a verified hidden manufacturing stitch.</text>",
            '<text x="1015" y="628" font-family="sans-serif" font-size="12">'
            "No curves/fur, modifiers, material response or design alignment.</text>",
            '<text x="1015" y="651" font-family="sans-serif" font-size="12">'
            "NO APPROVED FABRIC CUTTING PATTERNS.</text>",
            "</svg>",
        ]
    )
    return "\n".join(result) + "\n"
