"""Five Stage6 body-proxy orthographic projections with historic face X/Z marks.

The image is NOT an aligned reference photo or a factory cutting template.
"""

from __future__ import annotations

from html import escape

import numpy as np

VIEWS = (
    ("front", (0, 2), (1, 1)),
    ("back", (0, 2), (-1, 1)),
    ("left", (1, 2), (1, 1)),
    ("right", (1, 2), (-1, 1)),
    ("top", (0, 1), (1, 1)),
)
ROUTE_STROKES = ("#b94436", "#b17a20", "#235ca8")


def _screen(view, raw, left, top, width, height):
    axes, signs = view
    uv = raw[:, axes] * np.asarray(signs)
    minimum = uv.min(axis=0)
    maximum = uv.max(axis=0)
    extent = np.maximum(maximum - minimum, 1e-6)
    scale = min((width - 34) / extent[0], (height - 55) / extent[1])

    def convert(points):
        coord = np.asarray(points)[:, axes] * np.asarray(signs)
        return np.column_stack(
            (
                left + 17 + (coord[:, 0] - minimum[0]) * scale,
                top + height - 20 - (coord[:, 1] - minimum[1]) * scale,
            )
        )

    return convert, scale


def _polyline(points, width=1.4, *, stroke="#344353", dashed=False):
    path = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    dash = ' stroke-dasharray="3 2"' if dashed else ""
    return (
        f'<polyline points="{path}" fill="none" stroke="{stroke}" '
        f'stroke-width="{width:.2f}" stroke-linejoin="round"{dash}/>'
    )


def _face_features(convert, face):
    out = []
    for eye in face["eyes"]:
        x, z = eye["center_xz"]
        radius = eye["ellipse_radii_xz"]
        center = convert(np.array([[x, 0, z]]))[0]
        origin = convert(np.array([[x + radius[0], 0, z]]))[0]
        vertical = convert(np.array([[x, 0, z + radius[1]]]))[0]
        out.append(
            f'<ellipse cx="{center[0]:.2f}" cy="{center[1]:.2f}" '
            f'rx="{abs(origin[0] - center[0]):.2f}" '
            f'ry="{abs(vertical[1] - center[1]):.2f}" '
            'fill="none" stroke="#c4457a" stroke-width="1.1" '
            'stroke-dasharray="3 2"/>'
        )
    for name in ("y_nose_xz", "mouth_stem_xz", "mouth_left_xz", "mouth_right_xz"):
        vertices = np.asarray(face[name], dtype=float)
        coords = np.column_stack(
            (vertices[:, 0], np.zeros(len(vertices)), vertices[:, 1])
        )
        out.append(_polyline(convert(coords), 1.4, stroke="#c4457a", dashed=True))
    return out


def _draw_routes(convert, routes, name):
    """Preserve route draw order while separating renderer complexity."""
    strokes = []
    for k, route in enumerate(routes):
        source = np.asarray(route["source_points_xyz_mm"])
        projected = convert(source)
        flags = route["front_main_shell_near_side_flags"]
        for j in range(len(projected) - 1):
            visible = name == "front" and flags[j] and flags[j + 1]
            strokes.append(
                _polyline(
                    projected[j : j + 2],
                    1.45,
                    stroke=ROUTE_STROKES[k],
                    dashed=name == "front" and not visible,
                )
            )
        if name == "front":
            for witness in route["historic_face_proximity_witnesses"]:
                x, y = convert(np.asarray([witness["xyz_mm"]]))[0]
                strokes.append(
                    f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.6" '
                    'fill="none" stroke="#d7191c" stroke-width="1"/>'
                )
    return strokes


def render_source_seam_orthoview_svg(source_points, report, face_reference):
    """Body proxy; front solid=near shell, dashed=self-hidden; other views projected."""
    points = np.asarray(source_points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
        raise ValueError("finite source PLY needed for geometric projections")
    if report.get("schema") != "stage6-pinned-source-front-shell-historical-face-v14-review-v1":
        raise ValueError("wrong verified seam review schema")
    if len(report.get("routes", [])) != 3:
        raise ValueError("exactly three original B radial paths required")
    width, height = 490, 430
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="945" '
        'viewBox="0 0 1500 945">',
        '<rect x="0" y="0" width="1500" height="945" fill="#fcfcfc"/>',
        '<text x="18" y="22" font-size="16" font-family="sans-serif">'
        'REAL STAGE6 B THREE-DISK SOURCE SEAMS | NOT A CUTTING PATTERN</text>',
        '<text x="18" y="42" font-size="11" font-family="sans-serif">'
        'Source body proxy only; pink marks = historical surface14 face X/Z, '
        'NOT registered final design. Front depth-tested; other views projection-only.'
        '</text>',
    ]
    for i, (name, axes, signs) in enumerate(VIEWS):
        left = (i % 3) * 500 + 5
        top = (i // 3) * 435 + 56
        svg.append(
            f'<rect x="{left}" y="{top}" width="{width}" height="{height}" '
            'fill="white" stroke="#9da5aa" stroke-width="0.7"/>'
        )
        svg.append(
            f'<text x="{left + 13}" y="{top + 18}" font-size="14" '
            f'font-family="sans-serif">{escape(name.upper())}</text>'
        )
        convert, scale = _screen((axes, signs), points, left, top, width, height)
        subsample = points[:: max(1, len(points) // 4500)]
        for x, y in convert(subsample):
            svg.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="0.55" '
                'fill="#646b70" opacity="0.18"/>'
            )
        if name == "front":
            svg.extend(_face_features(convert, face_reference))
        svg.extend(_draw_routes(convert, report["routes"], name))
        svg.append(
            f'<text x="{left + 11}" y="{top + height - 7}" '
            'font-family="sans-serif" font-size="10">'
            f'Body-proxy mm (not final design; scale {scale:.2f}px/mm)</text>'
        )
    svg.extend(
        [
            '<text x="1018" y="515" font-family="sans-serif" font-size="13">'
            'Legend: red=old slit, ochre=high route 1, blue=high route 2</text>',
            '<text x="1018" y="540" font-family="sans-serif" font-size="12">'
            'Front red circles = proximity to historic nose/mouth</text>',
            '<text x="1018" y="562" font-family="sans-serif" font-size="12">'
            'Clouds, fleece, eye meshes, tail and factory sewing NOT checked</text>',
            '</svg>',
        ]
    )
    return "\n".join(svg) + "\n"
