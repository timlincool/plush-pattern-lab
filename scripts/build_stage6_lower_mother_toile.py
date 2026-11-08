"""Build four 1:1 A4 lower-hoof test-toile sheets from the pinned Stage6 PLY.

The 13 pieces are a new *underbody manufacturing hypothesis*. The source hoof
rings are original, but the body yoke/leg sleeves/flat soles/upper bands are
not derived flattenings of the full Stage6 sculpt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from propose_stage6_shell_panels import PROXY_SHA256, load_pinned_proxy

from plush_pattern_lab.patterns.stage6_lower_mother_toile import (
    build_source_hoof_lower_toile,
    extract_original_hoof_rings,
)
from plush_pattern_lab.patterns.stage6_lower_mother_toile_svg import (
    render_lower_mother_toile_a4,
)
from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256
from plush_pattern_lab.validation.stage6_lower_mother_toile_qc import (
    inspect_source_lower_toile,
)

SOURCE_HOOF_REFERENCE = "original public Stage6 4x512 boundary loops at Z=20mm"
WARNING = "RESEARCH LOWER-TOILE ONLY, NOT ORIGINAL STAGE6 CUTTING PATTERNS"


def _guide(spec, qa):
    rows = [
        "# Stage6 原始四蹄锚定：下腹连接母版低成本试缝指南",
        "",
        "**研究试布，禁止当作整只羊驼的真实纸样或正式工厂生产文件。**",
        "原蹄口源点Z=20mm是可信几何；**新下腹YOKE假定位于Z=60mm**，",
        "其位置与真实Stage6连续主壳**尚未有设计/布料/填棉验收**。",
        "源网格中的Rounded hoof base有约20mm高度；这里的平面试验端片",
        "仅用于验证布筒接口，不是原始3D蹄底模型的真实展开。",
        "",
        "## 1. 打印与部件身份",
        "",
        "- 4张A4 SVG，打印**100% / Actual Size**，每页先量10×10mm方框。",
        "- 裁 YOKE-01 一片（四个小孔）、LEG-FL/FR/RL/RR 各一片、",
        "  SOLE-FL/FR/RL/RR 平面临时试样各一片、BAND-1～4 各一片：**13片**。",
        "- 黑线裁切、蓝色虚线净缝线，暂定**6mm缝份**，没有真实布料样卡确认。",
        "- 每个蹄口原始512条边保留数值对应，只将4组四分之一原源边序",
        "  转描为橙色定位点；**不要求工厂按512个微小顶点逐个手工打缺口**。",
        "- 平台投影形状尺寸和斜口位置来自Stage6真实蹄口；"
        "  试验布筒长度40mm、下腹外围与上围条是新设计假设。",
        "",
        "## 2. 实际源蹄口长度（数字缝线）",
        "",
        "| 位置 | 原始512边实际周长 | 本试样布筒顶端/底端数字长度 |",
        "| --- | ---: | ---: |",
    ]
    for item in qa["source_hoofs"]:
        value = item["source_3d_ring_perimeter_mm"]
        rows.append(
            f"| {item['hoof']} | {value:.4f} mm | {value:.4f} / {value:.4f} mm |"
        )
    rows.extend(
        [
            "",
            "这是数值逐段配缝（与源蹄口投影一致），**不证明真实毛绒布筒会缝成相同3D形状**。",
            "",
            "## 3. 小样试缝顺序（尚未完成整个头身）",
            "",
            "1. 从纸样上转移 YOKE 四个原始蹄口的编号和4个源顶点四分之一标记。",
            "   YOKE 内孔裁切线**比净缝孔更小**，留出向孔内折叠的缝份。",
            "2. 逐件把四条 LEG 直布条的左右边合成布筒，标记里外面；"
            "   布筒上缘的顶点源ID顺序与对应YOKE孔的数值边序对应。",
            "3. 将各LEG顶缘与同名YOKE内孔缝在净缝线上；再用相同源环边长对应的",
            "   临时平面SOLE端片封底，检查周长匹配和接缝是否打皱。"
            "   SOLE是平面试片，不是原始圆鼓的Stage6蹄底正式制版。",
            "4. 先缝 BAND-1.right ↔ BAND-2.left，依次围成四围条，最后",
            "   BAND-4.right ↔ BAND-1.left；每条围带的下边按源外缘64段序号",
            "   与YOKE外围四等分段对位，再按实际布料疏缝。",
            "5. BAND-3与YOKE缝纫线约35%～65%的紫色段暂留作**研究返口**，"
            "   开口约"
            f" {qa['proposed_return_gap_mm']:.1f}mm；**上围条目前仍是整圈开放**，"
            "   因此这只是将来全身闭合后的预留位置，而非已经实测的翻面路径。",
            "6. 当前试缝件可检查四蹄及下腹相对站位，却**不能直接安装眼鼻嘴、"
            "   耳、七云团、尾、十雨滴或填充为目标成品**。禁止把开放上围",
            "   缝当作已经配对的头身接口。",
            "",
            "## 4. 本轮不会自动通过的制造检查",
            "",
            "- 需先与原始设计正面/侧面/背面/顶部对照真正腹部轮廓、"
            "  原四足站位/足底方向，验证是否必须重画YOKE外缘和腿根。",
            "- 需完成接到真实胸颈/主壳的上沿配缝、省道、返口，"
            "  两处四线交汇的工业接法和眼鼻耳尾云团安装。",
            "- 需给厂家所用合成面料样本实测经纬伸长、厚度、绒向、"
            "  缝份/缝线设备、填充重量及实体首样。",
            "- 当前仅为**能打印的局部接口试缝套件**，"
            "  不代表 P3整体完成，更不是P4正式工业1:1裁布包。",
            "",
        ]
    )
    return "\n".join(rows)


def _source_profile_check(xyz, spec):
    slab = xyz[np.abs(xyz[:, 2] - 60) <= 3]
    if len(slab) < 30:
        raise ValueError("missing real Stage6 source shell reference at Z=60mm")
    q = np.quantile(slab[:, :2], [0.01, 0.99], axis=0)
    yoke = np.asarray(spec["yoke"]["outer_stitch_xy_mm"])
    bounds = np.vstack((yoke.min(axis=0), yoke.max(axis=0)))
    return {
        "source_Z60_mm_slab_vertex_count": len(slab),
        "source_1st_99th_percentile_xy_bounds_mm": q.tolist(),
        "new_yoke_outer_xy_bounds_mm": bounds.tolist(),
        "signed_new_minus_source_envelope_limits_mm": (bounds - q).tolist(),
        "source_3d_body_silhouette_matched": False,
    }


def _files(spec, qa, profile):
    sheets = render_lower_mother_toile_a4(spec)
    spec["original_stage6_body_at_z60_geometry_comparison"] = profile
    spec_data = json.dumps(spec, ensure_ascii=False, indent=2)
    qa_data = json.dumps(qa, ensure_ascii=False, indent=2)
    output = {
        "lower_toile_source_geometry.json": spec_data + "\n",
        "lower_toile_seam_audit.json": qa_data + "\n",
        "sewing_guide.md": _guide(spec, qa),
        **sheets,
    }
    hashes = {
        name: hashlib.sha256(body.encode("utf8")).hexdigest()
        for name, body in output.items()
    }
    manifest = {
        "schema": "stage6-hoof-anchored-lower-toile-asset-manifest-v1",
        "status": WARNING,
        "source_original_blend_sha256": SOURCE_SHA256,
        "source_proxy_25pct_ply_sha256": PROXY_SHA256,
        "source_hoof_reference": SOURCE_HOOF_REFERENCE,
        "original_source_hoof_edges_retained": 2048,
        "research_new_ventral_z_mm": 60,
        "stitch_units": "mm",
        "printing": {"paper": "A4", "scale": "100_percent", "pages": 4},
        "piece_count": 13,
        "geometry": "new yoke + synthetic tubes/soles + open upper bands",
        "not_entire_stage6_character_pattern": True,
        "future_torso_neck_head_and_cloud_links_missing": True,
        "approved_industrial_paper_patterns": 0,
        "files_sha256": hashes,
    }
    output["manifest.json"] = json.dumps(
        manifest, indent=2, ensure_ascii=False
    ) + "\n"
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proxy", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.source_sha256 != SOURCE_SHA256:
        raise ValueError("wrong public Stage6 source model sha256")
    if args.out_dir.is_symlink() or args.out_dir.exists():
        raise FileExistsError("source evidence directory must not pre-exist")
    xyz, faces = load_pinned_proxy(args.proxy)
    rings = extract_original_hoof_rings(xyz, faces)
    spec = build_source_hoof_lower_toile(rings)
    qa = inspect_source_lower_toile(spec)
    profile = _source_profile_check(xyz, spec)
    files = _files(spec, qa, profile)
    args.out_dir.mkdir(parents=True, exist_ok=False)
    for name, content in files.items():
        (args.out_dir / name).write_text(content, encoding="utf8")
    print(
        "STAGE6_TRUE_HOOF_LOWER_MOTHER_TOILE_NOT_PRODUCTION",
        json.dumps(
            {
                "hoof_perimeters_mm": {
                    r["hoof"]: r["source_3d_ring_perimeter_mm"]
                    for r in qa["source_hoofs"]
                },
                "mother_components": spec["piece_count"],
                "a4_pages": 4,
                "yoke_outer_seam_mm": spec["yoke"]["outer_stitch_perimeter_mm"],
                "fabric_or_factory_approved": False,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
