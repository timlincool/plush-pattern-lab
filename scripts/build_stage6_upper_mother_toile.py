"""Turn trusted lower-mother trial into an 18-piece joined research assembly.

Build upper four gores and a cap from Stage6 observed source slices. Neither
the upper envelope proxy nor its 2D seam lengths certify 3D body shape.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from propose_stage6_shell_panels import PROXY_SHA256, load_pinned_proxy

from plush_pattern_lab.patterns.stage6_lower_mother_toile import (
    extract_original_hoof_rings,
)
from plush_pattern_lab.patterns.stage6_upper_mother_toile import (
    build_upper_mother_from_lower,
)
from plush_pattern_lab.patterns.stage6_upper_mother_toile_svg import (
    render_stage6_upper_mother_a4,
)
from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256
from plush_pattern_lab.validation.stage6_lower_mother_toile_qc import (
    inspect_source_lower_toile,
)
from plush_pattern_lab.validation.stage6_upper_mother_toile_qc import (
    audit_source_profile_upper_mother,
)


def _verified_real_lower_spec(xyz, faces, lower):
    inspect_source_lower_toile(lower)
    real_rings = extract_original_hoof_rings(xyz, faces)
    for name in ("FL", "FR", "RL", "RR"):
        actual = real_rings[name]
        recorded = lower["original_source_hoofs"][name]
        if not np.array_equal(
            actual["original_vertex_ids"],
            recorded["source_vertex_ids"],
        ):
            raise ValueError("a lower hoop source vertex ID changed since original PLY")
        if not np.allclose(
            actual["original_xy_mm"],
            recorded["source_stitch_ring_xy_mm"],
            atol=1e-10,
            rtol=0,
        ):
            raise ValueError("lower hoop XY ring does not equal trusted Stage6 PLY")


def _guide(upper, audit):
    pairs = audit["four_real_lower_band_to_upper_source_stitch_relations"]
    side = audit["four_independent_new_upper_side_seam_relations"]
    top = audit["four_top_cap_indexed_16_edge_stitch_relations"]
    result = [
        "# Stage6 原始四蹄下腹母版 → 四片胸颈头身母版试缝顺序",
        "",
        "**研究性纸上试缝闭合，不是原始羊驼最终纸样、工业DXF或工厂验收。**",
        "前一版13片四蹄下腹A4四页不变；本包只新增四片上身试验布片和一块顶部试验盖片。",
        "本地13片与新增5片合计18片，研究净缝数字关系完整；",
        "**真正头颈在Z=130～155处的轮廓跳变尚未解决，材料/填棉也未验证。**",
        "",
        "## 新增下缘接合（旧 BAND 仍不修改）",
    ]
    for item in pairs:
        result.append(
            f'- {item["sewing_pair"]}: {item["paired_net_stitch_mm"]:.3f} mm，'
            "按旧母版16个原外围分段及编号缝，禁止拉伸到统一长度。"
        )
    result.extend(["", "## 新上身四条纵向缝"])
    for item in side:
        result.append(
            f'- {item["sewing_pair"]}: '
            f'{item["shared_side_stitch_mm"]:.3f} mm，'
            "按6层截面站位标记连接。"
        )
    result.extend(["", "## 上端盖片"])
    for item in top:
        result.append(
            f'- {item["sewing_pair"]}: {item["stitch_mm"]:.3f} mm。'
        )
    result.extend(
        [
            "",
            "## 缝制／翻面研究顺序（未进行实际试布）",
            "1. 用旧4张下腹A4按原4个蹄口身份做净缝，对位；四块平面SOLE不是原真鼓蹄。",
            "2. 四块UPPER新片分别对接旧BAND-1～4的开放上沿；",
            "   保留旧BAND-3低接缝研究返口，切勿在新上身另开未知洞。",
            "3. 自下往上合UPPER-1.right→UPPER-2.left等四条侧缝，",
            "   UPPER-4.right→UPPER-1.left封合时检查两端三线接点是否堆叠。",
            "4. 以每组16条分段净缝把TOP-CAP-TRIAL接到UPPER-1～4。",
            "   新盖片没有耳根、尾巴、眼鼻绣花连接线。",
            "5. 理论上可通过旧BAND-3返口翻出，但实体毛绒厚度、能否通过及",
            "   填棉支撑均**未测试**；填充或工厂打样前先作廉价样布试缝。",
            "",
            "## 自动检查发现的结构性否决",
            f'- 原真实截面中心最大相邻偏移 {upper["max_source_observed_profile_center_step_mm"]:.2f} mm；'
            "此跳变暗示原颈、后部身壳需拆分而非一片连续笼罩。",
            f'- 新母版设计二维纵向缝与其3D拟合包络纵向弦长最大差 '
            f'{audit["original_source_surrogate_meridian_length_mismatch_mm"]:.2f} mm；'
            "这不是测得的布料伸长，而是新试验母版不能保真还原原雕塑的证据。",
            '- 原Stage6顶部最高点高于本试验盖片Z=230mm；耳、云团、'
            "尾根、10水滴、真实绒向、材料/绣花/实际站姿均未签核。",
            "- 4条旧BAND上沿在新研究装配里已数字配缝，"
            "但不意味着完整原Stage6造型、真实缝份和两处四线交汇均已经通过。",
            "- 5张新A4（与旧4张合计9张）必须100%打印并实际量10×10mm校准框。",
            "- 布料与实样、供应商设备、绣花机和公差必须重新验证；"
            "严禁将18片研究母版冒充正式工厂裁切纸样。",
            "",
        ]
    )
    return "\n".join(result)


def _payloads(upper, qa, lower_sha):
    files = {
        "upper_mother_source_profile.json": json.dumps(
            upper, ensure_ascii=False, indent=2
        ) + "\n",
        "upper_mother_seam_audit.json": json.dumps(
            qa, ensure_ascii=False, indent=2
        ) + "\n",
        "assembly_sequence.md": _guide(upper, qa),
        **render_stage6_upper_mother_a4(upper),
    }
    hashes = {
        name: hashlib.sha256(text.encode("utf8")).hexdigest()
        for name, text in files.items()
    }
    manifest = {
        "schema": "stage6-upper-source-envelope-mother-trial-manifest-v1",
        "status": "RESEARCH_MATCHED_SEAMS_BUT_ORIGINAL_STAGE6_SHAPE_UNPROVEN",
        "source_original_blend_sha256": SOURCE_SHA256,
        "source_proxy_25pct_ply_sha256": PROXY_SHA256,
        "same_run_lower_mother_source_json_sha256": lower_sha,
        "upper_trial_piece_count": 5,
        "combined_lower_plus_upper_research_piece_count": 18,
        "new_A4_svg_pages": 5,
        "combined_research_A4_pages": 9,
        "printed_scale": "100_percent_actual_A4_210x297mm",
        "original_stage6_3d_sculpt_fitted": False,
        "neck_split_still_required": True,
        "factory_cuts_approved": 0,
        "research_file_sha256": hashes,
    }
    files["manifest.json"] = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    return files


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--proxy", type=Path, required=True)
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--lower-source", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    if args.source_sha256 != SOURCE_SHA256:
        raise ValueError("original public Stage6 Blender source is not verified")
    if args.out_dir.exists() or args.out_dir.is_symlink():
        raise FileExistsError("do not overwrite existing real Stage6 trial outputs")
    if not args.lower_source.is_file() or args.lower_source.is_symlink():
        raise ValueError("the same-run lower source geometry is missing")
    lower_bytes = args.lower_source.read_bytes()
    lower = json.loads(lower_bytes)
    xyz, faces = load_pinned_proxy(args.proxy)
    _verified_real_lower_spec(xyz, faces, lower)
    upper = build_upper_mother_from_lower(lower, xyz)
    qa = audit_source_profile_upper_mother(upper, lower)
    files = _payloads(upper, qa, hashlib.sha256(lower_bytes).hexdigest())
    args.out_dir.mkdir(parents=True, exist_ok=False)
    for name, value in files.items():
        (args.out_dir / name).write_text(value, encoding="utf8")
    print(
        "STAGE6_UPPER_MOTHER_4_BAND_PAIRED_SOURCE_NECK_RISK_REJECT",
        json.dumps(
            {
                "new_upper_parts": 5,
                "combined_research_parts": 18,
                "all_new_sewing_relations_matched_in_2d": qa[
                    "all_12_new_sewing_relations_matched_in_2d"
                ],
                "max_source_center_jump_mm": qa[
                    "original_stage6_source_cross_section_center_jump_mm"
                ],
                "synthetic_3d_vs_2d_meridian_mismatch_mm": qa[
                    "original_source_surrogate_meridian_length_mismatch_mm"
                ],
                "P4_factory_approved": False,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
