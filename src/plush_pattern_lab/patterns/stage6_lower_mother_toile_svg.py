"""Four A4 research-toile SVG sheets at true millimetre scale.

Real four hoof *seam rings* are projected from pinned source triangles. All
surrounding mother-shell pieces are newly designed, not fitted Stage6 panels.
"""

from __future__ import annotations

from html import escape

import numpy as np

PAGE_W, PAGE_H = 210.0, 297.0
ORDER = ("FL", "FR", "RL", "RR")
SHEET_LABELS = (
    "Yoke with 4 original hoof seam holes",
    "Four straight research leg sleeves",
    "Four FLAT SYNTHETIC test soles",
    "Four quarter upper outer bands (top OPEN)",
)


def _pts(points):
    return " ".join(f"{x:.4f},{y:.4f}" for x, y in points)


def _path(points):
    xy = np.asarray(points, dtype=float)
    if xy.ndim != 2 or xy.shape[1] != 2 or len(xy) < 3:
        raise ValueError("invalid research cutting/stitching polygon")
    return f"M {xy[0, 0]:.4f},{xy[0, 1]:.4f} " + " ".join(
        f"L {x:.4f},{y:.4f}" for x, y in xy[1:]
    ) + " Z"


def _frame(index):
    name = escape(SHEET_LABELS[index])
    return [
        '<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" '
        'viewBox="0 0 210 297">',
        "<style>"
        ".cut{stroke:#172e40;stroke-width:.45;fill:#eef3f5;fill-rule:evenodd}"
        ".stitch{stroke:#176fa3;stroke-width:.32;fill:none;stroke-dasharray:2 1.3}"
        ".mark{fill:#bd4e1d}.gap{stroke:#9d4d9f;stroke-width:.6;fill:none}"
        "text{font-family:Arial,sans-serif;fill:#172e40}"
        ".id{font-weight:bold;font-size:3.9px}.small{font-size:2.8px}"
        "</style>",
        '<rect width="210" height="297" fill="white"/>',
        f'<text x="13" y="12" class="id">STAGE6 LOWER MOTHER - RESEARCH SHEET {index + 1}/4</text>',
        f'<text x="13" y="18" class="small">{name}</text>',
        '<text x="13" y="23" class="small">PRINT 100% / A4 / mm / '
        'SOURCE RINGS + NEW MOTHER SURROGATE / NOT FACTORY APPROVED</text>',
    ]


def _footer():
    return [
        '<rect x="13" y="275" width="10" height="10" fill="none" '
        'stroke="#111" stroke-width=".4"/>',
        '<text x="27" y="279" class="small">10 x 10 mm calibration square</text>',
        '<text x="27" y="283" class="small">Black CUT / dashed blue STITCH '
        '/ orange NOTCH / purple TURNING GAP</text>',
        '<text x="13" y="290" class="small">Do not fit-to-page. '
        'Real fabric, stuffing, whole-character shape NOT validated.</text>',
        "</svg>",
    ]


def _translated_group(content, dx, dy, *, identity):
    label = escape(identity)
    return [
        f'<g data-part="{label}" transform="translate({dx:.5f} {dy:.5f})">',
        *content,
        "</g>",
    ]


def _stitch(points):
    return f'<path class="stitch" d="{_path(points)}"/>'


def _notches(points, indices, *, radius=0.85):
    xy = np.asarray(points, dtype=np.float64)
    return [
        f'<circle class="mark" cx="{xy[i, 0]:.4f}" '
        f'cy="{xy[i, 1]:.4f}" r="{radius:.2f}"/>'
        for i in indices
    ]


def _place_yoke(spec):
    yoke = spec["yoke"]
    outer = np.asarray(yoke["outer_cut_xy_mm"])
    minimum = outer.min(axis=0)
    maximum = outer.max(axis=0)
    extent = maximum - minimum
    if extent[0] > 182 or extent[1] > 242:
        raise ValueError("research source yoke cannot fit exact A4 print space")
    translation = np.array(
        [105 - (minimum[0] + maximum[0]) / 2, 149 - (minimum[1] + maximum[1]) / 2]
    )
    transformed = outer + translation
    if (
        transformed[:, 0].min() < 12
        or transformed[:, 0].max() > 198
        or transformed[:, 1].min() < 27
        or transformed[:, 1].max() > 269
    ):
        raise ValueError("actual-mm yoke cut is clipped by A4 print borders")
    cut = [_path(yoke["outer_cut_xy_mm"])]
    cut.extend(_path(item) for item in yoke["inner_cut_holes_xy_mm"])
    parts = [f'<path class="cut" d="{" ".join(cut)}"/>']
    parts.append(_stitch(yoke["outer_stitch_xy_mm"]))
    for identity in ORDER:
        ring = np.asarray(yoke["source_hoof_holes_stitch_xy_mm"][identity])
        parts.append(_stitch(ring))
        parts.extend(_notches(ring, [0, 128, 256, 384]))
        center = ring.mean(axis=0)
        parts.append(
            f'<text x="{center[0] - 4:.3f}" y="{center[1] + 1:.3f}" '
            f'class="id">{identity}</text>'
        )
    return _translated_group(parts, *translation, identity="VENTRAL-YOKE")


def _draw_straight_band(
    length, height, allowance, notch_stations, *, opening=False
):
    half = float(allowance)
    parts = [
        f'<rect class="cut" x="{-half:.4f}" y="{-half:.4f}" '
        f'width="{length + 2 * half:.4f}" height="{height + 2 * half:.4f}"/>',
        f'<path class="stitch" d="M0,0 L0,{height:.4f} '
        f'L{length:.4f},{height:.4f} L{length:.4f},0"/>',
    ]
    if opening:
        first, last = length * 0.35, length * 0.65
        parts.extend(
            [
                f'<path class="stitch" d="M0,0 L{first:.4f},0 '
                f'M{last:.4f},0 L{length:.4f},0"/>',
                f'<path class="gap" d="M{first:.4f},0 L{last:.4f},0" '
                'stroke-dasharray="1 1"/>',
                f'<circle class="mark" cx="{first:.4f}" cy="0" r=".8"/>',
                f'<circle class="mark" cx="{last:.4f}" cy="0" r=".8"/>',
            ]
        )
    else:
        parts.append(f'<path class="stitch" d="M0,0 L{length:.4f},0"/>')
    for position in notch_stations:
        if not 0 < position < length:
            raise ValueError("source-linked notch not inside original stitch line")
        parts.append(
            f'<circle class="mark" cx="{position:.4f}" cy="0" r=".75"/>'
        )
    return parts


def _place_four_strips(spec, *, kind):
    allowance = float(spec["material_seam_allowance_is_unverified_mm"])
    parts = []
    for index in range(4):
        top = 35 + index * 58
        if kind == "sleeve":
            identity = ORDER[index]
            row = spec["original_source_hoofs"][identity]
            length = row["source_original_hoof_perimeter_mm"]
            height = float(row["sleeve_height_mm"])
            label = f"LEG-{identity}"
            opening = False
            stitch_stations = row["sleeve_stitch_station_x_mm"]
            notch_stations = [stitch_stations[j] for j in (128, 256, 384)]
        else:
            row = spec["outer_quarter_bands"][index]
            length = row["yoke_outer_section_stitch_mm"]
            height = float(row["stitch_rectangle_xy_mm"][2][1])
            label = row["id"]
            opening = label == spec["turning_gap_research"]["band_id"]
            stitch_stations = row["stitch_bottom_station_x_mm"]
            notch_stations = [stitch_stations[j] for j in (4, 8, 12)]
        if length + 2 * allowance > 183 or height + 2 * allowance > 55:
            raise ValueError("trial band/sleeve violates unscaled A4 page geometry")
        if top + height + allowance > 269:
            raise ValueError("four trial pieces do not fit 1:1 A4 page")
        shapes = _draw_straight_band(
            length, height, allowance, notch_stations, opening=opening
        )
        shapes.append(
            f'<text x="1" y="{height * 0.50:.3f}" class="id">{label}</text>'
        )
        shapes.append(
            f'<text x="1" y="{height * 0.72:.3f}" class="small">'
            f'Stitch {length:.2f} mm / H {height:.1f} mm</text>'
        )
        parts.extend(_translated_group(shapes, 22, top, identity=label))
    return parts


def _place_sole_copies(spec):
    allowance = float(spec["material_seam_allowance_is_unverified_mm"])
    parts = []
    for index, identity in enumerate(ORDER):
        row = spec["original_source_hoofs"][identity]
        ring = np.asarray(row["source_stitch_ring_xy_mm"])
        if len(ring) != 512:
            raise ValueError("not the original 512-edge source hoop ring")
        from shapely.geometry import Polygon

        cut = np.asarray(
            Polygon(ring).buffer(allowance, quad_segs=12).exterior.coords
        )
        minimum = cut.min(axis=0)
        size = cut.max(axis=0) - minimum
        if size[0] > 75 or size[1] > 72:
            raise ValueError("synthetic sole outline violates A4 research layout")
        x = 35 if index % 2 == 0 else 126
        y = 54 if index < 2 else 159
        xy_shift = np.array([x, y]) - minimum
        pieces = [
            f'<path class="cut" d="{_path(cut)}"/>',
            _stitch(ring),
        ]
        pieces.extend(_notches(ring, [0, 128, 256, 384]))
        midpoint = ring.mean(axis=0)
        pieces.append(
            f'<text x="{midpoint[0] - 9:.3f}" y="{midpoint[1] + 1:.3f}" '
            f'class="id">SOLE-{identity}</text>'
        )
        parts.extend(
            _translated_group(pieces, *xy_shift, identity=f"TEST-SOLE-{identity}")
        )
    return parts


def render_lower_mother_toile_a4(spec):
    """Exactly four 100%-scale research sheets, never a factory tech pack."""
    if spec.get("approved_industrial_paper_patterns") != 0:
        raise ValueError("research-only lower shell cannot carry fabrication approval")
    renderers = (
        lambda: _place_yoke(spec),
        lambda: _place_four_strips(spec, kind="sleeve"),
        lambda: _place_sole_copies(spec),
        lambda: _place_four_strips(spec, kind="band"),
    )
    result = {}
    for index, renderer in enumerate(renderers):
        pieces = [*_frame(index), *renderer(), *_footer()]
        result[f"sheet-{index + 1:02d}.svg"] = "\n".join(pieces) + "\n"
    return result
