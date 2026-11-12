"""Package existing 13+5 source-anchored surrogate sheets as a traceable toile.

NO new 3D flattening or 'factory-ready' geometries are created. Existing
lower and upper asset manifests must be SHA-verifiable and from one source run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from plush_pattern_lab.patterns.stage6_research_assembly_svg import (
    render_research_assembly_svg,
)
from plush_pattern_lab.patterns.stage6_research_panel_interface import (
    SCHEMA,
    SOURCE_SHA,
    build_stage6_research_assembly,
)

LOWER = ("sheet-01.svg", "sheet-02.svg", "sheet-03.svg", "sheet-04.svg")
UPPER = tuple(f"upper-sheet-0{i}.svg" for i in range(1, 6))
SHEETS = LOWER + UPPER
PROXY_SHA = "5b52e3fd09c83b19c5b9d95d6d8d859a147ff4deef90f1518f868d2e82e3a2dd"


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _inputs(path, *, required):
    if not path.is_dir() or path.is_symlink():
        raise ValueError("expected verified lower/upper research assets directory")
    manifest = path / "manifest.json"
    if not manifest.is_file() or manifest.is_symlink():
        raise ValueError("research manifest is absent")
    index = json.loads(manifest.read_text(encoding="utf8"))
    hashed = index.get("files_sha256", index.get("research_file_sha256"))
    if (
        not isinstance(hashed, dict)
        or not set(required).issubset(hashed)
        or index.get("source_original_blend_sha256") != SOURCE_SHA
        or index.get("source_proxy_25pct_ply_sha256") != PROXY_SHA
    ):
        raise ValueError("research assets manifest did not match Stage6 pinned source")
    for filename, expected in hashed.items():
        if Path(filename).name != filename:
            raise ValueError("unexpected untrusted research asset path")
        asset = path / filename
        if not asset.is_file() or asset.is_symlink() or _sha(asset.read_bytes()) != expected:
            raise ValueError("original lower/upper research asset SHA256 mismatch")
    return index


def _original_sheets(lower_dir, upper_dir):
    assets = {}
    for i, filename in enumerate(SHEETS):
        root = lower_dir if i < 4 else upper_dir
        path = root / filename
        data = path.read_bytes()
        document = ET.fromstring(data)
        attrs = document.attrib
        if (
            document.tag != "{http://www.w3.org/2000/svg}svg"
            or attrs.get("width") != "210mm"
            or attrs.get("height") != "297mm"
            or attrs.get("viewBox") != "0 0 210 297"
        ):
            raise ValueError("paper sheet must be exactly A4 at 1:1 scale")
        if b'width="10" height="10"' not in data or b"calibration" not in data.lower():
            raise ValueError("original research sheet lacks 10x10mm calibration")
        if b"<script" in data.lower() or b"foreignobject" in data.lower():
            raise ValueError("untrusted active content inside original print page")
        assets[f"print/sheet-{i + 1:02d}.svg"] = data
    return assets


def _guide(graph):
    lines = [
        "# Stage6 18片研究套件：原始纸样＋逐条缝合关系",
        "",
        "**仅用于低成本试布，不是原设计可生产纸样。还没有做过实体试缝。**",
        "",
        "## 打印",
        "",
        "全部9张A4 SVG按100%实际尺寸打印。量测每页10×10mm校准框。",
        "黑线裁切、虚线净缝。6mm缝份未经布料/厂商确认。",
        "",
        f"研究裁片：{graph['total_research_pieces']}件（不是41个视觉Mesh）"
        f"；数值配缝：{graph['paired_interface_count']}组。",
        "",
        "## 工艺先后顺序（研究方案）",
        "",
    ]
    for item in graph["assembly_stages"]:
        lines.append(f"{item['step']}. {item['operation']}")
        if "warning" in item:
            lines.append(f"   - 注意：{item['warning']}")
    lines.extend(["", "## 逐组二维净缝线（不是实际缝纫通过）", ""])
    for relation in graph["paired_stitch_interfaces"]:
        lines.append(
            f"- {relation['id']}：{relation['first']} ↔ "
            f"{relation['second']}；{relation['segment_count']}段、"
            f"净缝{relation['first_2d_netline_mm']:.3f}mm，"
            f"最大逐段差{relation['max_segment_disagreement_mm']:.6f}mm"
        )
    lines.extend(
        [
            "",
            "## 尚未解决，禁止作为正式工厂文件",
            "",
            "- 真实头颈轮廓仍有约71mm的原源截面中心跳变，"
            "上身四片是人工包络代理而非真实原Stage6制版。",
            "- 头身新二维纵缝与其3D拟合包络纵边最大失配约89mm；"
            "不是材料弹性可自动修复的误差。",
            "- 四个SOLE仅为平面试样，不是原模型鼓起蹄底的真2D裁片。",
            "- 内外耳、七云覆层、尾巴、五官、十水滴及十连接带均"
            "没有真实布片/安装缝线。",
            "- 返口只是BAND-3上的拟议留口；真实布料翻面、"
            "填充、站立与外形对照均未验证。",
            "- 原4×512源蹄口身份未改变；其余新纸样与原雕塑"
            "外形还未签核。P3进行中，P4未开始，批准纸样0。",
            "",
        ]
    )
    return "\n".join(lines)


def build_research_assembly_pack(lower_dir, upper_dir, destination):
    """Repackage the actual nine verified A4 sheets + a 32-interface guide."""
    if destination.exists() or destination.is_symlink():
        raise ValueError("do not overwrite existing original research assets")
    lower_manifest = _inputs(
        lower_dir,
        required=(
            "lower_toile_source_geometry.json",
            "lower_toile_seam_audit.json",
            *LOWER,
        ),
    )
    upper_manifest = _inputs(
        upper_dir,
        required=(
            "upper_mother_source_profile.json",
            "upper_mother_seam_audit.json",
            *UPPER,
        ),
    )
    lower_bytes = (lower_dir / "lower_toile_source_geometry.json").read_bytes()
    upper_bytes = (upper_dir / "upper_mother_source_profile.json").read_bytes()
    if (
        upper_manifest.get("same_run_lower_mother_source_json_sha256")
        != _sha(lower_bytes)
        or lower_manifest.get("piece_count") != 13
        or upper_manifest.get("combined_lower_plus_upper_research_piece_count") != 18
    ):
        raise ValueError("lower/upper source data not created in one trusted run")
    low = json.loads(lower_bytes)
    high = json.loads(upper_bytes)
    graph = build_stage6_research_assembly(low, high)
    content = {
        "panel_interface_research_graph.json": (
            json.dumps(graph, ensure_ascii=False, indent=2) + "\n"
        ).encode("utf8"),
        "sewing_sequence_RESEARCH_ONLY.md": _guide(graph).encode("utf8"),
        "assembly_map_RESEARCH_ONLY.svg": render_research_assembly_svg(
            graph
        ).encode("utf8"),
        **_original_sheets(lower_dir, upper_dir),
    }
    manifest = {
        "schema": "stage6-eighteen-existing-toile-paper-assembly-v1",
        "source_original_blend_sha256": SOURCE_SHA,
        "source_proxy_25pct_ply_sha256": PROXY_SHA,
        "lower_original_research_source_json_sha256": _sha(lower_bytes),
        "upper_original_research_source_json_sha256": _sha(upper_bytes),
        "source_lower_manifest_sha256": _sha((lower_dir / "manifest.json").read_bytes()),
        "source_upper_manifest_sha256": _sha((upper_dir / "manifest.json").read_bytes()),
        "total_research_paper_parts": graph["total_research_pieces"],
        "stitched_2d_interface_pairs": graph["paired_interface_count"],
        "printed_A4_page_count": graph["print_sheet_count"],
        "all_4x512_true_hoof_source_edge_IDs_unchanged": True,
        "real_Stage6_sculpt_silhouette_verified": False,
        "factory_sewn_or_approved": False,
        "P3_status": "in_progress",
        "P4_status": "not_started",
        "each_asset_SHA256": {name: _sha(data) for name, data in content.items()},
    }
    content["manifest.json"] = (
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    ).encode("utf8")
    destination.mkdir(parents=True, exist_ok=False)
    for filename, data in content.items():
        target = destination / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lower-dir", type=Path, required=True)
    parser.add_argument("--upper-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    result = build_research_assembly_pack(
        args.lower_dir, args.upper_dir, args.out_dir
    )
    print(
        "STAGE6_18_PIECE_SEWING_GRAPH_AND_NINE_EXISTING_A4_PAGES_NOT_FACTORY",
        json.dumps(
            {
                "parts": result["total_research_paper_parts"],
                "pairs": result["stitched_2d_interface_pairs"],
                "pages": result["printed_A4_page_count"],
                "approved": False,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
