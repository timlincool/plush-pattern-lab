"""Trusted Stage6 old hoof ring -> two independently joined anatomy A/B trials.

Original 3D source is not modified. All SVGs are explicitly non-factory
research assets, including the seam guide / integrated collar alternatives.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from build_stage6_upper_mother_toile import _verified_real_lower_spec
from propose_stage6_shell_panels import PROXY_SHA256, load_pinned_proxy

from plush_pattern_lab.patterns.stage6_split_volume_mother import (
    build_split_volume_mother_ab,
)
from plush_pattern_lab.patterns.stage6_split_volume_panel_interface import (
    build_split_24piece_assembly_graphs,
)
from plush_pattern_lab.patterns.stage6_split_volume_toile_svg import (
    render_split_volume_A4,
)
from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256
from plush_pattern_lab.validation.stage6_split_volume_toile_qc import (
    audit_separated_stage6_toile,
)


def _assembly_guide(study, qa):
    results = [
        "# Stage6 25cm原始四蹄 → 后躯与前头颈两个独立体积：A/B研究装配",
        "",
        "**只供研究试缝与讨论，不是原雕塑原始纸样、量产技术包或正式厂商文件。**",
        "旧下半身13片及原四蹄4×512条真源缝保持不变。每个候选再添加11个试验片，",
        "因此每个候选是24片组合研究，旧4张A4+新11张A4共15张。",
        "A和B是两组**替代实验**，不要把两组纸样混在同一成品试布。",
        "",
        "## A：后躯与头颈独立封闭、填充后外部缝合",
        "",
        "1. 依旧样纸缝4只LEG、4块平面SOLE（仅测试闭合）及下腹四孔YOKE；",
        "   按源编号合并4条BAND，保留BAND-3的研究返口。",
        "2. 4块TORSO-i的下沿逐16段与BAND-i上沿配对，再按顺序合四条TORSO纵缝；",
        "   上口接SHOULDER-CAP-TRIAL的四组16段顶缝，肩片中心的橙色椭圆",
        "   是**表面缝接引导线，不剪孔**。",
        "3. 头颈由4块HEADNECK-i沿四条侧缝成筒，顶部接HEAD-TOP-CAP-TRIAL。",
        "   从下缘填入少量试验棉后，用CLOSED-NECK-BASE-TRIAL封闭头颈底边。",
        "4. 身体从旧BAND-3返口作试验填充，再沿研究肩片椭圆导引用手缝",
        "   把已独立封闭的头颈底面连接到肩片外表面。",
        "   **两块已封闭的软体的表面梯形/锁边缝并非机器净缝对合验证**；",
        "   颈根下方可能留10mm高度/偏位，必须实体模型与设计验证。",
        "",
        "## B：在肩片开颈孔，通过10mm连接圈与头颈内部相通",
        "",
        "1. 旧4蹄13片不变，四块TORSO-i与BAND-i按同一原16段配对。",
        "2. 肩片的颈孔采用真正内孔裁切线（向孔中心内缩6mm缝份），",
        "   与原肩片外周净缝留出足够双缝份桥宽。",
        "3. 新COLLAR-TRIAL沿10mm左右侧缝先车成筒，64段下口接肩孔、",
        "   64段上口接四个HEADNECK-i的底圈，各自按0/16/32/48编号缝合。",
        "4. 合四条HEADNECK侧缝并加HEAD-TOP-CAP，上沿封闭；",
        "   通过旧BAND-3研究返口尝试翻面/填棉。",
        "   **42.49mm试验返口是否足以翻出实际毛绒头颈尚未实物测试**。",
        "",
        "## 必须先得到人工确认的风险",
    ]
    for variant in study["options"]:
        observation = variant["source_neck_port_modification"]
        results.extend(
            [
                f"- {variant['name']}: 颈根相对源Stage6 Z145截面XY缩小为 "
                f"{observation['explicit_source_head_root_xy_scale']:.0%}；"
                f"源点到新纸样根部轮廓最大平面差 "
                f"{observation['max_source_head_root_to_2d_port_vertex_xy_shift_mm']:.2f}mm；"
                f"肩片开孔/导引线到外围最短净缝间距 "
                f"{observation['minimum_body_cap_boundary_to_port_mm']:.2f}mm。",
            ]
        )
    results.extend(
        [
            f"- 原Z135→145主壳与头颈源截面中心XY偏移 "
            f"{study['real_source_135_to145_center_shift_xy_mm']:.2f}mm；"
            "此处新结构并非源雕塑中真实的可直接对接缝线。",
            f"- 研究头顶在Z230，原公开源顶Z≈"
            f"{study['reference_only_source_top_z_mm']:.2f}mm，"
            f"仍留{study['source_3d_top_height_not_represented_mm']:.2f}mm高度造型未解释。",
            "- 真正耳朵、七云团、眼鼻嘴、尾根、10雨滴、长短绒及原鼓起蹄底均未配置。",
            "- 原真实Stage6连续主壳未有已获批的厂家DXF展开；两个实验只是",
            "  数字净缝配对对照，不允许据此宣称布料无褶皱、同原设计或可量产。",
            "- 原Z130→155跨体积中心跳71mm应在独立体积与肩/颈工艺中",
            "  通过3D比对与实际样片消化，不能伪造能拉伸71mm的面料。",
            "",
        ]
    )
    return "\n".join(results)


def _outputs(study, qc, lower_sha, lower):
    source_json = json.dumps(study, ensure_ascii=False, indent=2)
    audit_json = json.dumps(qc, ensure_ascii=False, indent=2)
    assets = {
        "two_volume_source_envelope_ab.json": source_json + "\n",
        "two_volume_seam_and_port_qc.json": audit_json + "\n",
        "assembly_A_B.md": _assembly_guide(study, qc),
    }
    graphs = build_split_24piece_assembly_graphs(lower, study)
    for name, graph in graphs.items():
        assets[f"{name}/panel_interface_research_graph.json"] = (
            json.dumps(graph, ensure_ascii=False, indent=2) + "\n"
        )
    pages = render_split_volume_A4(study)
    for variant, sheets in pages.items():
        for name, data in sheets.items():
            assets[f"{variant}/{name}"] = data
    hashes = {
        name: hashlib.sha256(data.encode("utf8")).hexdigest()
        for name, data in assets.items()
    }
    manifest = {
        "schema": "stage6-two-anatomical-volumes-source-mother-trial-manifest-v1",
        "original_public_blend_sha256": SOURCE_SHA256,
        "original_proxy_25pct_sha256": PROXY_SHA256,
        "same_run_original_source_lower_toile_sha256": lower_sha,
        "variants": list(pages),
        "pieces_in_each_complete_lower_plus_option": 24,
        "lower_A4_pages_per_variant": 4,
        "new_A4_pages_per_variant": 11,
        "total_A4_pages_per_independent_variant": 15,
        "new_variant_A_B_svg_total": 22,
        "full_24piece_interface_graphs": {
            name: {
                "pieces": graph["total_research_pieces"],
                "numeric_interface_pairs": graph["numerically_paired_interface_count"],
                "unproven_manual_joins": graph[
                    "manual_unverified_surface_attachment_count"
                ],
            }
            for name, graph in graphs.items()
        },
        "documented_material_and_original_shape_failures": True,
        "approved_industrial_patterns": 0,
        "files_sha256": hashes,
    }
    assets["manifest.json"] = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    return assets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proxy", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--lower-source", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.source_sha256 != SOURCE_SHA256:
        raise ValueError("only pinned public Stage6 source hash supported")
    if args.out_dir.exists() or args.out_dir.is_symlink():
        raise FileExistsError("cannot overwrite earlier source-linked results")
    if (
        not args.lower_source.is_file()
        or args.lower_source.is_symlink()
        or args.lower_source.suffix != ".json"
    ):
        raise ValueError("same-run lower hoof-anchored trial missing")
    lower_bytes = args.lower_source.read_bytes()
    lower = json.loads(lower_bytes)
    xyz, faces = load_pinned_proxy(args.proxy)
    _verified_real_lower_spec(xyz, faces, lower)
    split = build_split_volume_mother_ab(lower, xyz)
    audit = audit_separated_stage6_toile(lower, split)
    assets = _outputs(split, audit, hashlib.sha256(lower_bytes).hexdigest(), lower)
    args.out_dir.mkdir(parents=True, exist_ok=False)
    for name, data in assets.items():
        target = args.out_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(data, encoding="utf8")
    print(
        "STAGE6_SEPARATE_TORSO_HEAD_A_B_REAL_SOURCE_TRIALS",
        json.dumps(
            {
                "options": [
                    {
                        "name": row["name"],
                        "source_neck_scale": row["source_neck_port_modification"][
                            "explicit_source_head_root_xy_scale"
                        ],
                        "neck_port_clearance_mm": row["source_neck_port_modification"][
                            "minimum_body_cap_boundary_to_port_mm"
                        ],
                    }
                    for row in split["options"]
                ],
                "new_sheets": 22,
                "pieces_each_variant": 24,
                "all_new_seams_paired_in_2d": all(
                    row["all_new_mathematical_seam_lengths_paired"]
                    for row in audit["two_distinct_manufacturing_trial_variants"]
                ),
                "factory_approved": False,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
