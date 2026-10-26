"""Printable 1:1 paper kit for a *synthetic* capped plush toile, not production.

Convert audited stitch/cut geometry into individually labeled sheets, matched
seam marks and an explicit turning/stuffing opening. SVG units are real mm.
No raster scaling, code evaluation, Blender dependency or output overwrites.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
from shapely.geometry import Polygon

PAPER_MM = {"A4": (210.0, 297.0), "Letter": (215.9, 279.4)}
MARGIN_MM = 12.0
LABEL_MM = 7.0
GUTTER_MM = 8.0
OPENING = (0.40, 0.60)
STATUS = "PRINTABLE_SYNTHETIC_TOILE_NOT_A_PRODUCTION_PATTERN"


def _array(values, name: str) -> np.ndarray:
    try:
        array = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name}: invalid numeric coordinates") from exc
    if array.ndim != 2 or array.shape[1] != 2 or not 3 <= len(array) <= 1500:
        raise ValueError(f"{name}: expected finite Nx2 with 3..1500 points")
    if not np.isfinite(array).all() or np.max(np.abs(array)) > 10000:
        raise ValueError(f"{name}: non-finite or unbounded coordinates")
    return array


def _piece(name: str, cut, stitch, kind: str) -> dict:
    outside = _array(cut, f"{name} cut")
    inside = _array(stitch, f"{name} stitch")
    outer = Polygon(outside)
    seam = Polygon(inside)
    if not outer.is_valid or not seam.is_valid or outer.area <= 1 or seam.area <= 1:
        raise ValueError(f"{name}: collapsed or self-intersecting paper piece")
    if not outer.buffer(0.01).covers(seam):
        raise ValueError(f"{name}: seam line must be inside cut outline")
    minimum = outside.min(axis=0)
    maximum = outside.max(axis=0)
    return {
        "id": name,
        "kind": kind,
        "cut": outside,
        "stitch": inside,
        "minimum": minimum,
        "size": maximum - minimum,
        "cut_area_mm2": float(outer.area),
    }


def _verified_cap(
    spec: dict, end: str, index: int, n: int, left: np.ndarray, right: np.ndarray
) -> dict:
    cap = spec["caps"][end]
    ring = _array(cap["stitch_ring_2d_mm"], end + " ring")
    if len(ring) != 2 * n:
        raise ValueError("Cap ring must have 2 vertices for each panel")
    length = np.linalg.norm(np.roll(ring, -1, axis=0) - ring, axis=1)
    width = float(right[index, 0] - left[index, 0])
    if np.max(abs(length - width / 2)) > 1e-5:
        raise ValueError("Cap-to-gore transverse stitch segments do not match")
    return _piece(end.upper(), cap["cut_outline_2d_mm"], ring, "cap")


def _spec_pieces(spec: dict) -> tuple[list[dict], int, float, float]:
    if (
        not isinstance(spec, dict)
        or spec.get("schema") != "synthetic-capped-plush-pattern-v1"
    ):
        raise ValueError("Expected the audited synthetic capped pattern schema")
    if (
        spec.get("status")
        != "NET_PATTERN_GEOMETRY_ONLY_NO_SEWING_OR_STUFFING_CERTIFICATION"
    ):
        raise ValueError("Unrecognized input research geometry status")
    params = spec.get("parameters", {})
    n = params.get("panels")
    allowance = params.get("allowance_mm")
    if isinstance(n, bool) or not isinstance(n, int) or not 6 <= n <= 24:
        raise ValueError("Panel count must be an integer between 6 and 24")
    if not isinstance(allowance, (int, float)) or not 3 <= allowance <= 12:
        raise ValueError(
            "Prototype needs an explicit 3..12 mm tentative seam allowance"
        )
    left = _array(spec["gore"]["left_stitch_2d_mm"], "left stitch")
    right = _array(spec["gore"]["right_stitch_2d_mm"], "right stitch")
    if left.shape != right.shape or not np.all(np.diff(left[:, 1]) > 0):
        raise ValueError("Side seam indexing/order must match top to bottom")
    if not np.allclose(left[:, 1], right[:, 1], atol=1e-7):
        raise ValueError("Left and right stitch rows do not match")
    left_steps = np.linalg.norm(np.diff(left, axis=0), axis=1)
    right_steps = np.linalg.norm(np.diff(right, axis=0), axis=1)
    if np.max(abs(left_steps - right_steps)) > 1e-6:
        raise ValueError("Side seams must match at every stitch-row segment")
    seam_length = float(left_steps.sum())
    stitch = np.vstack((left, right[::-1]))
    pieces = [
        _piece(f"P{i:02d}", spec["gore"]["cut_outline_2d_mm"], stitch, "gore")
        for i in range(1, n + 1)
    ]
    for end, index in (("upper", 0), ("lower", -1)):
        pieces.append(_verified_cap(spec, end, index, n, left, right))
    return pieces, n, float(allowance), seam_length


def _placed_piece(piece: dict, left: float, cut_top: float) -> dict:
    pw, ph = map(float, piece["size"])
    return {
        "id": piece["id"],
        "cut_bounds_mm": [
            round(z, 5) for z in (left, cut_top, left + pw, cut_top + ph)
        ],
        "translation_mm": [
            round(left - float(piece["minimum"][0]), 6),
            round(cut_top - float(piece["minimum"][1]), 6),
        ],
    }


def _placement(pieces: list[dict], paper: str) -> tuple[list[list[dict]], tuple]:
    if paper not in PAPER_MM:
        raise ValueError("Only A4 and Letter are supported")
    width, height = PAPER_MM[paper]
    top = MARGIN_MM + 20
    bottom = height - MARGIN_MM - 18
    x, y, row_end = MARGIN_MM, top, top
    pages: list[list[dict]] = [[]]
    for piece in pieces:
        pw, ph = map(float, piece["size"])
        slot_width, slot_height = pw + GUTTER_MM, ph + LABEL_MM
        if slot_width > width - 2 * MARGIN_MM or slot_height > bottom - top:
            raise ValueError("Piece exceeds one physical page: refusing to scale it")
        if piece["id"] == "LOWER" and pages[-1] and pages[-1][-1]["id"] == "UPPER":
            previous = pages[-1][-1]["cut_bounds_mm"]
            beside_x = previous[0]
            below_y = previous[3] + GUTTER_MM + LABEL_MM
            if beside_x + pw <= width - MARGIN_MM and below_y + ph <= bottom:
                pages[-1].append(_placed_piece(piece, beside_x, below_y))
                row_end = max(row_end, below_y + ph)
                continue
        if x + slot_width > width - MARGIN_MM + 1e-8:
            x, y = MARGIN_MM, row_end + GUTTER_MM
        if y + slot_height > bottom + 1e-8:
            pages.append([])
            x, y, row_end = MARGIN_MM, top, top
        placement = _placed_piece(piece, x, y + LABEL_MM)
        pages[-1].append(placement)
        x += slot_width
        row_end = max(row_end, y + slot_height)
    return pages, (width, height)


def _seam_at_fraction(rows: np.ndarray, fraction: float) -> tuple[float, float]:
    segments = np.linalg.norm(np.diff(rows, axis=0), axis=1)
    travel = np.r_[0.0, np.cumsum(segments)]
    target = float(travel[-1]) * fraction
    return (
        float(np.interp(target, travel, rows[:, 0])),
        float(np.interp(target, travel, rows[:, 1])),
    )


def _polygon_points(values: np.ndarray) -> str:
    return " ".join(f"{x:.5f},{y:.5f}" for x, y in values)


def _piece_svg(piece: dict, placement: dict, spec: dict, n: int) -> list[str]:
    dx, dy = placement["translation_mm"]
    label = escape(piece["id"])
    parts = [
        f'<text x="{placement["cut_bounds_mm"][0]:.3f}" '
        f'y="{placement["cut_bounds_mm"][1] - 1.5:.3f}" class="piece-label">{label} / CUT ONE</text>',
        f'<g data-piece="{label}" transform="translate({dx:.6f} {dy:.6f})">',
        f'<polygon class="cut" points="{_polygon_points(piece["cut"])}"/>',
        f'<polygon class="stitch" points="{_polygon_points(piece["stitch"])}"/>',
    ]
    if piece["kind"] == "gore":
        parts.extend(_gore_marks(piece["id"], spec, n))
    else:
        for idx, (xx, yy) in enumerate(piece["stitch"]):
            if idx % 2:
                parts.append(
                    f'<circle class="notch" cx="{xx:.4f}" cy="{yy:.4f}" r="0.75"/>'
                )
        xx, yy = piece["stitch"][0]
        parts.append(f'<circle class="cap-start" cx="{xx:.4f}" cy="{yy:.4f}" r="1.2"/>')
    parts.append("</g>")
    return parts


def _gore_marks(identifier: str, spec: dict, count: int) -> list[str]:
    left = _array(spec["gore"]["left_stitch_2d_mm"], "left stitch")
    right = _array(spec["gore"]["right_stitch_2d_mm"], "right stitch")
    marks = []
    for row in (left, right):
        for at in (0.25, 0.5, 0.75):
            xx, yy = _seam_at_fraction(row, at)
            marks.append(f'<circle class="notch" cx="{xx:.4f}" cy="{yy:.4f}" r="0.8"/>')
    if identifier in ("P01", f"P{count:02d}"):
        row = left if identifier == "P01" else right
        for at in OPENING:
            xx, yy = _seam_at_fraction(row, at)
            marks.append(
                f'<circle class="opening" cx="{xx:.4f}" cy="{yy:.4f}" r="1.15"/>'
            )
    center = 0.5 * (left[len(left) // 2, 0] + right[len(right) // 2, 0])
    y1 = float(left[len(left) // 3, 1])
    y2 = float(left[2 * len(left) // 3, 1])
    marks.extend(
        [
            f'<line class="nap" x1="{center:.4f}" y1="{y1:.4f}" x2="{center:.4f}" y2="{y2:.4f}"/>',
            f'<path class="nap" d="M{center - 1.3:.4f},{y2 - 2:.4f} '
            f'L{center:.4f},{y2:.4f} L{center + 1.3:.4f},{y2 - 2:.4f}"/>',
        ]
    )
    return marks


def _page_svg(
    page: list[dict],
    pieces: dict,
    paper_mm: tuple,
    number: int,
    total: int,
    spec: dict,
    panel_count: int,
    paper: str,
) -> str:
    width, height = paper_mm
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:g}mm" '
        f'height="{height:g}mm" viewBox="0 0 {width:g} {height:g}">',
        "<style>"
        ".cut{stroke:#232323;stroke-width:.35;fill:#f1f4f3}"
        ".stitch{stroke:#26769a;stroke-width:.28;fill:none;stroke-dasharray:2 1}"
        ".notch{fill:#b4472d}.opening{fill:none;stroke:#952f99;stroke-width:.55}.cap-start{fill:#3458aa}"
        ".nap{stroke:#297647;fill:none;stroke-width:.4}"
        "text{font-family:Arial,sans-serif;fill:#222}"
        ".piece-label{font-size:3.1px;font-weight:bold}</style>",
        f'<rect width="{width:g}" height="{height:g}" fill="white"/>',
        f'<text x="{MARGIN_MM:g}" y="13" font-size="4">SYNTHETIC TOILE / STUDY ONLY / NOT APPROVED</text>',
        f'<text x="{MARGIN_MM:g}" y="20" font-size="3.2">'
        f"{paper} {number}/{total} / print 100% / seam blue dashed / cut black</text>",
    ]
    for item in page:
        lines.extend(_piece_svg(pieces[item["id"]], item, spec, panel_count))
    footer_y = height - 13
    lines.extend(
        [
            f'<rect x="{MARGIN_MM:g}" y="{footer_y:g}" width="10" height="10" '
            'fill="none" stroke="black" stroke-width=".3"/>',
            f'<text x="{MARGIN_MM + 14:g}" y="{footer_y + 4:g}" font-size="3">'
            "10 x 10 mm calibration - verify printed dimension</text>",
            f'<text x="{MARGIN_MM + 14:g}" y="{footer_y + 8:g}" font-size="2.8">'
            "red seam dot | purple gap | green nap | blue cap P01 start</text>",
            "</svg>",
        ]
    )
    return "\n".join(lines) + "\n"


def _guide(n: int, allowance: float, seam_length: float, paper: str) -> str:
    opening = seam_length * (OPENING[1] - OPENING[0])
    return f"""# 合成椭球毛绒玩偶：第一次实体试缝指南

**只用于廉价试布打样，不是原始角色造型、已验证生产纸样或儿童玩具安全认证。**
请勿直接以此加工批量产品；当前 Blender 模型仍检出布壳面片穿插。

## 打印与裁剪

1. 打印 sheet-*.svg，纸张设为 {paper}，**实际尺寸/100%**，禁止“适应页面”；先用尺测量每张纸上的 10 × 10 mm 方框。若不准确，停止。
2. 剪黑色实线：侧片 P01…P{n:02d} 各 1 件、UPPER/LOWER 各 1 件，总计 {n + 2} 片。蓝色虚线是缝纫线，外圈临时缝份 {allowance:g} mm；使用前确认试布是否适配。
3. 将红色圆点转描到布料缝线两侧作对位标记，**不能剪到蓝色缝线**。绿色箭头是待实物验证的毛向假设；所有侧片统一朝向，不是自动实测的材料经纬方向。
4. 保留镜像/正反面标记；帽片蓝色起点对应 P01 上/下边的第一个拼接顶点，往后每两段对应下一侧片。P 编号只是裁片身份，不是贴在外表面的装饰。

## 试缝顺序

1. 按顺序缝 P01.right ↔ P02.left，一直到 P{n - 1:02d}.right ↔ P{n:02d}.left；匹配侧边三组红色标记。
2. P{n:02d}.right ↔ P01.left 的中段留作返口：从顶部沿缝线弧长 40% 到 60% 的两枚紫色标记之间暂不缝合（约 {opening:.1f} mm）。这不是额外裁开洞口。
3. UPPER 帽片按编号依次缝合每个 P 的上端两个半段；LOWER 缝合下端。先用疏缝/大头针核对对位，不要强拉导致帽片或小角起皱。
4. 经返口翻到正面，分次放入**少量试验填充物**并观察轮廓；记录真实填充重量、接缝开裂或起皱位置，最后用藏针法封返口。若面料/尺寸与纸样不适配，停止并修改假设。

## 必须记录的实体数据（未测量不得填“通过”）

- 纸张实际 10mm 校准值、用料及批次、经纬/毛向、缝线宽度。
- 完成品高度、宽度、前/侧/顶三视图照片；各截面褶皱和帽片隆起；填充克重与手工耗时。
- 裁片间红点是否对齐、临时返口尺寸是否足够、缝线崩裂/扭转/翻面问题。
- 结果与原来的合成目标及 Blender A/B 的误差，不仅比较外观渲染。

该几何参考来自可重复的合成椭球，而非真实羊驼/原始私人模型。模型的剩余自交、真实布料伸缩、纤维棉回复、工艺强度均**未通过验证**，应迭代后再考虑角色外形与生产。
"""


def build(
    spec: dict, paper: str = "A4", source_sha256: str | None = None
) -> tuple[dict, list[str], str]:
    pieces, n, allowance, seam_length = _spec_pieces(spec)
    pages, size = _placement(pieces, paper)
    by_id = {piece["id"]: piece for piece in pieces}
    output_pages = [
        _page_svg(page, by_id, size, i, len(pages), spec, n, paper)
        for i, page in enumerate(pages, 1)
    ]
    if source_sha256 is not None and (
        len(source_sha256) != 64
        or any(c not in "0123456789abcdef" for c in source_sha256)
    ):
        raise ValueError("Expected lowercase SHA-256 provenance")
    manifest = {
        "schema": "plush-synthetic-prototype-kit-v1",
        "status": STATUS,
        "source_sha256": source_sha256,
        "paper": paper,
        "paper_size_mm": list(size),
        "print_scale": 1.0,
        "calibration_square_mm": 10,
        "assumed_seam_allowance_mm": allowance,
        "piece_count": n + 2,
        "gore_count": n,
        "top_cap_count": 1,
        "bottom_cap_count": 1,
        "total_cut_area_cm2": round(
            sum(piece["cut_area_mm2"] for piece in pieces) / 100, 3
        ),
        "turning_opening": {
            "seam": f"P{n:02d}.right <-> P01.left",
            "from_top_fraction": OPENING[0],
            "to_top_fraction": OPENING[1],
            "nominal_length_mm": round(seam_length * (OPENING[1] - OPENING[0]), 3),
        },
        "notches": "registration dots on STITCH line only; do not clip through thread",
        "sheets": [
            {"file": f"sheet-{i:02d}.svg", "pieces": sheet}
            for i, sheet in enumerate(pages, 1)
        ],
        "limitations": [
            "Not a validated production, material or child-safety pattern",
            "No fabric/nap calibration; 6mm nominal allowance is an assumption",
            "The Blender sewn shell still has nonadjacent triangle intersections",
            "Paper/toile prototype measurements must be collected before promotion",
        ],
    }
    return manifest, output_pages, _guide(n, allowance, seam_length, paper)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--paper", choices=tuple(PAPER_MM), default="A4")
    args = parser.parse_args()
    if (
        not args.input.is_file()
        or args.output_dir.exists()
        or args.output_dir.is_symlink()
    ):
        raise RuntimeError("Input absent or output directory already exists")
    data = args.input.read_bytes()
    manifest, pages, guide = build(
        json.loads(data.decode("utf-8")), args.paper, hashlib.sha256(data).hexdigest()
    )
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (args.output_dir / "sewing-guide.md").write_text(guide, encoding="utf-8")
    for page, entry in zip(pages, manifest["sheets"]):
        (args.output_dir / entry["file"]).write_text(page, encoding="utf-8")
    print(
        "PROTOTYPE_KIT_PREPARED",
        json.dumps(
            {
                "paper": args.paper,
                "pieces": manifest["piece_count"],
                "sheets": len(pages),
                "status": STATUS,
            }
        ),
    )


if __name__ == "__main__":
    main()
