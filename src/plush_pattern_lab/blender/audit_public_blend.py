"""检查准备公开的 H-compact Blender 资产是否携带内嵌脚本或隐私路径。
只读；以 --disable-autoexec 启动；报告不包含脚本/路径原文。
"""

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

import bpy

FLAGGED = re.compile(
    r"(?:gh[pousr]_[a-zA-Z0-9]{24,}|github_pat_[a-zA-Z0-9_]{24,}|sk-(?:proj-)?[a-zA-Z0-9_-]{30,}|-----BEGIN [^-]*PRIVATE KEY-----|\b(?:password|passwd)\s*[:=])"
)
PATH_PRIVATE = re.compile(
    r"(?:[A-Za-z]:[\\/](?:Users|Desktop|Documents)[\\/]|/(?:home|Users)/[^/\s]{2,}/|libfile_[a-zA-Z0-9]{12,})"
)
SENSITIVE_PROPS = (
    "token",
    "password",
    "apikey",
    "api_key",
    "secret",
    "credential",
    "authorization",
)


def file_hash(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _scan_objects(inspected, findings, flag):
    for obj in bpy.data.objects:
        inspected["objects"] += 1
        for k, v in obj.items():
            inspected["custom_properties"] += 1
            if any(x in k.lower() for x in SENSITIVE_PROPS):
                findings.append(
                    {
                        "level": "review",
                        "category": "sensitive_prop_name",
                        "location": obj.name + ":" + k,
                    }
                )
            if isinstance(v, (str, int, float)):
                flag("object_property", obj.name + ":" + k, v)
        animation = obj.animation_data
        if animation is not None:
            for driver in animation.drivers:
                inspected["drivers"] += 1
                flag(
                    "driver_expression",
                    obj.name + ":" + str(driver.data_path),
                    driver.driver.expression,
                )


def _scan_scenes(inspected, findings, flag):
    for scene in bpy.data.scenes:
        for k, v in scene.items():
            inspected["custom_properties"] += 1
            if any(x in k.lower() for x in SENSITIVE_PROPS):
                findings.append(
                    {
                        "level": "review",
                        "category": "sensitive_prop_name",
                        "location": "scene:" + k,
                    }
                )
            if isinstance(v, (str, int, float)):
                flag("scene_property", k, v)


def _scan_worlds(inspected, flag):
    for world in bpy.data.worlds:
        for k, v in world.items():
            inspected["custom_properties"] += 1
            if isinstance(v, (str, int, float)):
                flag("world_property", k, v)


def _scan_properties(inspected, findings, flag):
    _scan_objects(inspected, findings, flag)
    _scan_scenes(inspected, findings, flag)
    _scan_worlds(inspected, flag)


def _make_flag(findings):
def flag(category, loc, value):
    s = str(value)
    if FLAGGED.search(s):
        findings.append(
            {
                "level": "block",
                "category": category + ":possible_secret",
                "location": loc,
            }
        )
    if PATH_PRIVATE.search(s):
        findings.append(
            {
                "level": "review",
                "category": category + ":private_path",
                "location": loc,
            }
        )

    return flag


def _scan_asset_refs(inspected, flag):
    for text in bpy.data.texts:
        inspected["texts"] += 1
        raw = text.as_string()
        if raw.strip():
            inspected["scripts"] += 1
        flag("embedded_text", text.name, raw)
    for image in bpy.data.images:
        inspected["images"] += 1
        if image.packed_file:
            inspected["packed_files"] += 1
        flag("image_filepath", image.name, image.filepath)
        flag("image_name", image.name, image.name)
    for library in bpy.data.libraries:
        inspected["libraries"] += 1
        flag("library_path", library.name, library.filepath)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--source-sha256", required=True)
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    if not a.input.is_file() or a.output.exists():
        raise RuntimeError("Input/report invalid")
    digest = file_hash(a.input)
    if digest != a.source_sha256:
        raise RuntimeError("Frozen input SHA does not match")
    bpy.ops.wm.open_mainfile(filepath=str(a.input.resolve()), load_ui=False)
    findings = []
    inspected = {
        "texts": 0,
        "scripts": 0,
        "images": 0,
        "libraries": 0,
        "objects": 0,
        "custom_properties": 0,
        "drivers": 0,
        "packed_files": 0,
    }

    flag = _make_flag(findings)
    _scan_asset_refs(inspected, flag)
    _scan_properties(inspected, findings, flag)
    # 保存和报告只包含统计信息 + 位置，避免把可疑 token 再复制到 CI 日志。
    level = Counter(x["level"] for x in findings)
    report = {
        "status": "BLOCK"
        if level["block"]
        else "REVIEW"
        if level["review"]
        else "PASS_SCOPE_LIMITED",
        "input_sha256": digest,
        "blender": bpy.app.version_string,
        "objects_in_scene": len(bpy.context.scene.objects),
        "inspected": inspected,
        "findings": findings,
        "limitations": [
            "Not a forensic scan of all Blender binary datablocks or geometry string attributes",
            "Does not establish intellectual property ownership",
            "Text/image external file paths may be intentionally present and need normalization",
            "Disabled auto-exec only prevents built-in automatic execution, not every possible Blender CVE",
        ],
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8"
    )
    print(
        "PUBLIC_MODEL_PREFLIGHT",
        json.dumps(
            {k: v for k, v in report.items() if k != "findings"}, ensure_ascii=False
        ),
        flush=True,
    )
    if level["block"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
