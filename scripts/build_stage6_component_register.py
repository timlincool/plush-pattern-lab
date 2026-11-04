"""Generate a draft factory component and assembly registry from public Stage6 proof.

This is planning data, NOT a set of cut patterns, part counts or approved BOM.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from plush_pattern_lab.validation.manufacturing_registry import (
    build_draft_register,
)

MAX_INPUT_BYTES = 1_000_000


def _read_json(path):
    if not path.is_file() or path.is_symlink():
        raise ValueError("source evidence must be an existing regular JSON")
    if path.suffix != ".json" or path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("unexpected evidence file size or extension")
    return json.loads(path.read_text(encoding="utf-8"))


def generate(scene_path, seams_path):
    return build_draft_register(_read_json(scene_path), _read_json(seams_path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--seams", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.suffix != ".json":
        raise ValueError("only JSON manufacturing-registry drafts are supported")
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError("refuse to overwrite a previous component registry")
    report = generate(args.scene, args.seams)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        "STAGE6_DRAFT_COMPONENT_REGISTER",
        json.dumps(
            {
                "mesh_candidates": report["model_mesh_count"],
                "assembly_intents": len(report["assembly_intents"]),
                "geometry_only": report["joins_with_measured_3d_boundary_only"],
                "unknown_anchors": report["unresolved_attachment_target_count"],
                "approved_patterns": report["approved_cut_patterns"],
            }
        ),
    )


if __name__ == "__main__":
    main()
