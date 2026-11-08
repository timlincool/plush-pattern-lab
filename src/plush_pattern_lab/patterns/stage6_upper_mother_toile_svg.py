"""Five 1:1 A4 research sheets for upper surrogate gores and top closure.

Only stitch arc lengths are controlled. Textile mechanical and silhouette
validity remain unresolved, especially around the observed neck transition.
"""

from __future__ import annotations

from html import escape

import numpy as np

A4_WIDTH_MM = 210
A4_HEIGHT_MM = 297


def _path(vertices):
    p = np.asarray(vertices, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 2 or len(p) < 3:
        raise ValueError("invalid upper research stitch/cut polyline")
    if not np.isfinite(p).all():
        raise ValueError("nonfinite mother toile plot coordinates")
    return (
        f"M {p[0, 0]:.4f},{p[0, 1]:.4f} "
        + " ".join(f"L{x:.4f},{y:.4f}" for x, y in p[1:])
        + " Z"
    )


def _start_page(label, number):
    return [
        '<svg xmlns="http://www.w3.org/2000/svg" width="210mm" '
        'height="297mm" viewBox="0 0 210 297">',
        "<style>.cut{stroke:#28333b;stroke-width:.45;fill:#f0f4f5}"
        ".seam{stroke:#286c95;stroke-width:.35;fill:none;stroke-dasharray:2 1}"
        ".notch{fill:#b9472c}.grain{stroke:#34835a;fill:none;stroke-width:.45}"
        "text{font:3.4px Arial,sans-serif;fill:#28333b}</style>",
        '<rect width="210" height="297" fill="white"/>',
        f'<text x="12" y="12">UPPER MOTHER - SOURCE-ENVELOPE TRIAL {number}/5</text>',
        f'<text x="12" y="18">{escape(label)}</text>',
        '<text x="12" y="24">A4 100% scale / RESEARCH ONLY / '
        "NOT ORIGINAL STAGE6 CUTTING PATTERN</text>",
    ]


def _footer():
    return [
        '<rect x="12" y="275" width="10" height="10" fill="none" '
        'stroke="#111" stroke-width=".4"/>',
        '<text x="26" y="279">Calibration 10 x 10 mm - measure before any toile</text>',
        '<text x="26" y="283">Black cut / blue stitch / red source ring marks</text>',
        '<text x="12" y="291">No material, fur, 3D fit or factory approval</text>',
        "</svg>",
    ]


def _placement(cut):
    p = np.asarray(cut, dtype=np.float64)
    minimum, maximum = p.min(axis=0), p.max(axis=0)
    size = maximum - minimum
    if size[0] > 178 or size[1] > 234:
        raise ValueError("1:1 upper torso study piece does not fit one A4 page")
    center = (minimum + maximum) / 2
    shift = np.array([105, 148]) - center
    placed = p + shift
    if (
        placed[:, 0].min() < 12
        or placed[:, 0].max() > 198
        or placed[:, 1].min() < 28
        or placed[:, 1].max() > 268
    ):
        raise ValueError("real-size upper mother print would clip paper frame")
    return shift


def _notches(points, rows):
    xy = np.asarray(points, dtype=np.float64)
    return [
        f'<circle class="notch" cx="{xy[i, 0]:.4f}" cy="{xy[i, 1]:.4f}" r=".8"/>'
        for i in rows
    ]


def _seam(points):
    return f'<path class="seam" d="{_path(points)}"/>'


def _gore_page(part, index):
    cut = np.asarray(part["cut_outline_xy_mm"])
    offset = _placement(cut)
    content = [
        f'<g transform="translate({offset[0]:.5f} {offset[1]:.5f})" '
        f'data-part="{escape(part["id"])}">',
        f'<path class="cut" d="{_path(cut)}"/>',
        _seam(part["stitch_outline_xy_mm"]),
        _seam(part["bottom_stitch_xy_mm"]),
        _seam(part["upper_stitch_xy_mm"]),
        *_notches(part["bottom_stitch_xy_mm"], (0, 4, 8, 12, 16)),
        *_notches(part["upper_stitch_xy_mm"], (0, 4, 8, 12, 16)),
    ]
    middle = np.asarray(part["stitch_outline_xy_mm"]).mean(axis=0)
    content.append(
        f'<text x="{middle[0]:.3f}" y="{middle[1]:.3f}">'
        f"{escape(part['id'])} / {escape(part['paired_lower_band'])}</text>"
    )
    content.append("</g>")
    lines = [
        *_start_page(
            f"{part['id']} lower -> {part['paired_lower_band']} top / 16 shared edges",
            index + 1,
        ),
        *content,
        *_footer(),
    ]
    return "\n".join(lines) + "\n"


def _cap_page(cap):
    stitch = np.asarray(cap["stitch_ring_xy_mm"])
    cut = np.asarray(cap["cut_outline_xy_mm"])
    shift = _placement(cut)
    content = [
        f'<g data-part="{escape(cap["id"])}" '
        f'transform="translate({shift[0]:.5f} {shift[1]:.5f})">',
        f'<path class="cut" d="{_path(cut)}"/>',
        _seam(stitch),
        *_notches(stitch, (0, 16, 32, 48)),
        "</g>",
        '<text x="12" y="38">Cap stitches 64 edges = '
        "4 x 16 indexed upper-gore seams</text>",
        '<text x="12" y="44">This cap is synthetic, not the Stage6 ear/head sculpt.</text>',
    ]
    lines = [*_start_page("Top cap surrogate at Z=230mm", 5), *content, *_footer()]
    return "\n".join(lines) + "\n"


def render_stage6_upper_mother_a4(upper):
    if (
        upper.get("schema") != "stage6-source-profile-informed-upper-mother-toile-v1"
        or upper.get("industrial_cut_patterns_approved") != 0
        or len(upper.get("upper_gore_pieces", [])) != 4
    ):
        raise ValueError("upper source-envelope trial is not verified research")
    pages = {
        f"upper-sheet-{i + 1:02d}.svg": _gore_page(row, i)
        for i, row in enumerate(upper["upper_gore_pieces"])
    }
    pages["upper-sheet-05.svg"] = _cap_page(upper["research_top_cap"])
    return pages
