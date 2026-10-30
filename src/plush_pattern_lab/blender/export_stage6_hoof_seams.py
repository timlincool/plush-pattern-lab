"""从校验后的 Stage 6 .blend 提取四蹄 2D 接缝参考，不修改模型。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy

from plush_pattern_lab.blender.audit_hoof_interfaces import (
    HOOFS,
    _source_objects,
    object_boundary_rings_mm,
    sha256_file,
)
from plush_pattern_lab.patterns.hoof_seam_reference import (
    build_reference,
    draw_reference_svg,
)


def extract_reference(source_hash):
    objects = _source_objects()
    body_rings, body_edges = object_boundary_rings_mm(objects[0])
    if len(body_rings) != 4 or body_edges != 2048:
        raise ValueError("Stage 6 主体必须恰好有四组 512 点开放环")
    hoofs = []
    for obj in objects[1:]:
        rings, edges = object_boundary_rings_mm(obj)
        if len(rings) != 1 or edges != 512:
            raise ValueError(f"Stage 6 蹄部开放环应为 512 边：{obj.name}")
        hoofs.append(rings[0])
    result = build_reference(body_rings, hoofs, HOOFS, source_hash)
    result["blender_version"] = bpy.app.version_string
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--svg", type=Path, required=True)
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    if bpy.app.version[:3] != (4, 3, 2):
        raise ValueError("研究证据必须固定 Blender 4.3.2")
    if not args.input.is_file() or args.input.suffix != ".blend":
        raise ValueError("指定 Stage 6 模型文件不存在或后缀错误")
    if args.output.suffix != ".json" or args.svg.suffix != ".svg":
        raise ValueError("报告需要 .json，二维参考图需要 .svg")
    if args.output.resolve() == args.svg.resolve():
        raise ValueError("报告和参考图不得为同一文件")
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError("拒绝覆盖已存在的 JSON 研究报告")
    if args.svg.exists() or args.svg.is_symlink():
        raise FileExistsError("拒绝覆盖已存在的 SVG 参考")
    digest = sha256_file(args.input)
    if digest != args.source_sha256:
        raise ValueError("Stage 6 模型 SHA-256 不符：禁止读取场景")
    bpy.ops.wm.open_mainfile(filepath=str(args.input.resolve()), load_ui=False)
    report = extract_reference(digest)
    svg = draw_reference_svg(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.svg.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    args.svg.write_text(svg, encoding="utf8")
    print(
        "STAGE6_HOOF_SEAM_REFERENCE_GENERATED",
        json.dumps(
            {
                "source_sha256": digest,
                "hoofs": len(report["hoofs"]),
                "perimeter_3d_mm": [
                    round(item["projection_diagnostics"]["perimeter_3d_mm"], 4)
                    for item in report["hoofs"]
                ],
                "max_projection_length_loss_mm": round(
                    max(
                        item["projection_diagnostics"]["projection_length_loss_mm"]
                        for item in report["hoofs"]
                    ),
                    4,
                ),
                "approved_cut_patterns": False,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
