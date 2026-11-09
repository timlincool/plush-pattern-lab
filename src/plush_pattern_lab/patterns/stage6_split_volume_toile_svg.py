"""100% A4 research pieces for independently stuffed vs internally joined head.

Each output is a paper seam-geometry experiment, never a real Stage6 unwrap.
"""

from __future__ import annotations

from html import escape

import numpy as np

A4 = (210.0, 297.0)


def _path(coords):
    p = np.asarray(coords, dtype=float)
    if p.ndim != 2 or p.shape[1] != 2 or len(p) < 3 or not np.isfinite(p).all():
        raise ValueError("source-inspired 2D paper outline is invalid")
    return "M " + " L ".join(f"{x:.4f},{y:.4f}" for x, y in p) + " Z"


def _page_shell(name, option, page):
    return [
        '<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" '
        'viewBox="0 0 210 297">',
        "<style>.cut{stroke:#1d3345;stroke-width:.4;fill:#eaf0f3;fill-rule:evenodd}"
        ".seam{stroke:#28618e;stroke-width:.35;fill:none;stroke-dasharray:2 1.5}"
        ".guide{stroke:#bb4f20;stroke-width:.45;fill:none;stroke-dasharray:1.1 1.2}"
        ".mark{fill:#b34c35} text{font:3.4px Arial,sans-serif;fill:#1d3345}"
        '</style><rect x="0" y="0" width="210" height="297" fill="white"/>',
        f'<text x="11" y="12">STAGE6 SPLIT VOLUMES {escape(option)} | PAGE {page}/11</text>',
        f'<text x="11" y="18">{escape(name)}</text>',
        '<text x="11" y="24">A4 100% / STUDY ONLY / NO FACTORY CUTTING APPROVAL</text>',
    ]


def _footer():
    return [
        '<rect x="11" y="276" width="10" height="10" stroke="#111" '
        'fill="none" stroke-width=".4"/>',
        '<text x="26" y="281">10 x 10 mm print check / NEVER fit-to-page</text>',
        '<text x="11" y="291">Original 3D Stage6 head and fabric not fitted</text>',
        "</svg>",
    ]


def _shift(cut):
    p = np.asarray(cut, dtype=float)
    bounds = np.vstack((p.min(axis=0), p.max(axis=0)))
    size = bounds[1] - bounds[0]
    if size[0] > 184 or size[1] > 236:
        raise ValueError(
            "large source-informed cut must be tiled, never silently scaled"
        )
    move = np.array([105, 148]) - bounds.mean(axis=0)
    result = p + move
    if (
        result[:, 0].min() < 10
        or result[:, 0].max() > 200
        or result[:, 1].min() < 27
        or result[:, 1].max() > 269
    ):
        raise ValueError("1-to-1 A4 mother piece would clip printer margins")
    return move


def _marks(coords, positions):
    p = np.asarray(coords, dtype=float)
    return [
        f'<circle class="mark" cx="{p[i, 0]:.4f}" cy="{p[i, 1]:.4f}" r=".8"/>'
        for i in positions
    ]


def _stitch(coords, *, guide=False):
    klass = "guide" if guide else "seam"
    return f'<path class="{klass}" d="{_path(coords)}"/>'


def _cut(coords, holes=()):
    lines = [_path(coords)]
    lines.extend(_path(h) for h in holes)
    return f'<path class="cut" d="{" ".join(lines)}"/>'


def _gore_page(row, option, page):
    cut = np.asarray(row["cut_polygon_xy_mm"], dtype=float)
    offset = _shift(cut)
    render = [
        _cut(cut),
        _stitch(row["stitch_polygon_xy_mm"]),
        _stitch(row["lower_stitch_xy_mm"]),
        _stitch(row["upper_stitch_xy_mm"]),
        *_marks(row["lower_stitch_xy_mm"], (0, 4, 8, 12, 16)),
        *_marks(row["upper_stitch_xy_mm"], (0, 4, 8, 12, 16)),
        *_marks(row["left_stitch_xy_mm"], range(len(row["left_stitch_xy_mm"]))),
        *_marks(row["right_stitch_xy_mm"], range(len(row["right_stitch_xy_mm"]))),
    ]
    content = [
        *_page_shell(row["id"], option, page),
        f'<g data-part="{escape(row["id"])}" '
        f'transform="translate({offset[0]:.5f} {offset[1]:.5f})">',
        *render,
        "</g>",
        *_footer(),
    ]
    return "\n".join(content) + "\n"


def _cap_page(row, option, page, *, guide=None):
    cut = np.asarray(row["cut_outer_xy_mm"], dtype=float)
    holes = row["cut_inner_holes_xy_mm"]
    offset = _shift(cut)
    marks = []
    ring = row["outer_stitch_xy_mm"]
    marks.extend(_marks(ring, (0, 16, 32, 48)))
    if guide is not None:
        marks.append(_stitch(guide, guide=True))
        marks.extend(_marks(guide, (0, 16, 32, 48)))
    for hole in row["upper_head_opening_stitch_xy_mm"]:
        marks.append(_stitch(hole, guide=True))
    content = [
        *_page_shell(row["id"], option, page),
        f'<g data-part="{escape(row["id"])}" '
        f'transform="translate({offset[0]:.5f} {offset[1]:.5f})">',
        _cut(cut, holes),
        _stitch(ring),
        *marks,
        "</g>",
        *_footer(),
    ]
    return "\n".join(content) + "\n"


def _collar_page(row, option, page):
    cut = np.asarray(row["cut_rectangle_xy_mm"], dtype=float)
    offset = _shift(cut)
    x = np.asarray(row["lower_and_upper_stitch_station_x_mm"], dtype=float)
    height = row["height_mm"]
    marks = []
    for i in (0, 16, 32, 48, 64):
        marks.append(f'<circle class="mark" cx="{x[i]:.4f}" cy="0" r=".8"/>')
        marks.append(f'<circle class="mark" cx="{x[i]:.4f}" cy="{height:.4f}" r=".8"/>')
    stitch = [
        f'<path class="seam" d="M0,0 L{x[-1]:.4f},0 '
        f'L{x[-1]:.4f},{height:.4f} L0,{height:.4f} Z"/>'
    ]
    content = [
        *_page_shell(row["id"], option, page),
        f'<g data-part="COLLAR-TRIAL" '
        f'transform="translate({offset[0]:.5f} {offset[1]:.5f})">',
        _cut(cut),
        *stitch,
        *marks,
        "</g>",
        *_footer(),
    ]
    return "\n".join(content) + "\n"


def render_split_volume_A4(study):
    if (
        study.get("schema") != "stage6-separated-torso-headneck-mother-trial-ab-v1"
        or study.get("factory_cutting_patterns_approved") != 0
    ):
        raise ValueError("only rejected split-anatomy toile candidates may be plotted")
    result = {}
    for trial in study["options"]:
        option = trial["name"]
        pages = []
        for item in trial["torso_gore_pieces"]:
            pages.append(_gore_page(item, option, len(pages) + 1))
        for item in trial["headneck_gore_pieces"]:
            pages.append(_gore_page(item, option, len(pages) + 1))
        shoulder = trial["shoulder_cap"]
        guide = trial["neck_source_inspired_guide"]["ring_xy_mm"]
        pages.append(
            _cap_page(
                shoulder,
                option,
                len(pages) + 1,
                guide=guide
                if trial["separate_head_is_stuffed_and_externally_attached"]
                else None,
            )
        )
        pages.append(_cap_page(trial["head_top_cap"], option, len(pages) + 1))
        if trial["head_bottom_cap_if_separate"] is not None:
            pages.append(
                _cap_page(trial["head_bottom_cap_if_separate"], option, len(pages) + 1)
            )
        else:
            pages.append(
                _collar_page(trial["neck_collar_if_integrated"], option, len(pages) + 1)
            )
        if len(pages) != 11:
            raise ValueError("A and B variants must each have exactly 11 study sheets")
        result[option] = {
            f"page-{i + 1:02d}.svg": sheet for i, sheet in enumerate(pages)
        }
    return result
