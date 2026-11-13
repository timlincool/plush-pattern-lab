# SPDX-License-Identifier: GPL-2.0-or-later
"""Reuse trusted Blender 4.3.2 ANGLE_BASED on source-triangle split pieces."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from unwrap_stage6_true_crown_caps_blender import _unwrap

INPUT_SCHEMA = "stage6-genuine-high-protrusion-source-edge-bisect-AB-v1"
OUTPUT_SCHEMA = "stage6-real-high-protrusion-source-meridian-native-ABF-v1"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-bisect", required=True, type=Path)
    parser.add_argument("--source-caps", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    if bpy.app.version[:3] != (4, 3, 2):
        raise ValueError("only trusted Blender 4.3.2 ANGLE_BASED UV")
    if args.output.exists() or args.output.is_symlink() or any(
        not p.is_file() or p.is_symlink()
        for p in (args.source_bisect, args.source_caps)
    ):
        raise ValueError("original source missing or would overwrite previous output")
    raw = args.source_bisect.read_bytes()
    specs = json.loads(raw)
    original = args.source_caps.read_bytes()
    if (
        specs.get("schema") != INPUT_SCHEMA
        or specs.get("same_run_real_3d_original_three_caps_sha256")
        != hashlib.sha256(original).hexdigest()
        or specs.get("factory_cutting_patterns_approved") != 0
        or len(specs.get("variants", [])) != 2
    ):
        raise ValueError("not original source-aligned Stage6 split seam study")
    rows = []
    for variant in specs["variants"]:
        for part in variant["side_protrusions"]:
            for panel in part["panels"]:
                name = panel["id"]
                outline = panel["boundary_panel_vertex_ids_in_order"]
                # Adapt only the dictionary fields required by the existing
                # source-vertex-preserving ABF operator; it never adds cuts.
                adapter = {
                    "id": name,
                    "vertices_xyz_mm": panel["vertices_xyz_mm"],
                    "triangles_local_vertex_indices": panel[
                        "triangles_local_vertex_indices"
                    ],
                    "original_rim_vertex_ids_in_cap_local_order": outline,
                    "source_boundary_edges": len(outline),
                }
                uv = _unwrap(adapter, name, len(outline))
                rows.append({"route": variant["route"], **uv})
    if len(rows) != 8:
        raise ValueError("all two seam variants times four original panels required")
    result = {
        "schema": OUTPUT_SCHEMA,
        "source_bisect_study_sha256": hashlib.sha256(raw).hexdigest(),
        "blender_version": "4.3.2",
        "solver": "ANGLE_BASED",
        "original_source_3d_panels": 8,
        "entries": rows,
        "third_party_native_solver_reused_not_reimplemented": True,
        "factory_cutting_patterns_approved": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, separators=(",", ":"), ensure_ascii=False) + "\n",
        encoding="utf8",
    )
    print("STAGE6_REAL_SOURCE_SIDE_8PANELS_NATIVE_BLENDER_ABF_RESEARCH", flush=True)


if __name__ == "__main__":
    main()
