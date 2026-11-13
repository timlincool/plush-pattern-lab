# SPDX-License-Identifier: GPL-2.0-or-later
"""Reuse real native Blender 4.3.2 ABF for four Stage6 lower source disks."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from importlib import import_module
from pathlib import Path

import bpy

_SCRIPTS = str(Path(__file__).resolve().parent)
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
_unwrap = import_module("unwrap_stage6_true_crown_caps_blender")._unwrap

INPUT_SCHEMA = "stage6-seven-original-ports-six-source-interrim-disk-cuts-v1"
OUTPUT_SCHEMA = "stage6-true-lower-seven-port-four-disks-native-Blender-ABF-v1"
ZONES = ("left_front", "left_rear", "right_front", "right_rear")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    if (
        bpy.app.version[:3] != (4, 3, 2)
        or not args.source.is_file()
        or args.source.is_symlink()
        or args.output.exists()
        or args.output.is_symlink()
        or args.output.suffix != ".json"
    ):
        raise ValueError("trusted native Blender or original Stage6 source missing")
    raw = args.source.read_bytes()
    spec = json.loads(raw)
    if (
        spec.get("schema") != INPUT_SCHEMA
        or spec.get("source_y_split_mm") != 20
        or spec.get("source_3d_six_interrim_paths") != 6
        or spec.get("factory_cutting_patterns_approved") != 0
        or [p.get("id") for p in spec.get("source_topological_disks", [])]
        != list(ZONES)
    ):
        raise ValueError("original complete six-cut 3D geometry required")
    entries = []
    for part in spec["source_topological_disks"]:
        outline = part["final_original_source_disk_rim_vertex_ids_in_order"]
        source = {
            "id": part["id"],
            "vertices_xyz_mm": part["source_3d_xyz_mm"],
            "triangles_local_vertex_indices": part[
                "triangles_local_vertex_indices"
            ],
            "source_boundary_edges": len(outline),
            "original_rim_vertex_ids_in_cap_local_order": outline,
        }
        entries.append(_unwrap(source, part["id"], len(outline)))
    output = {
        "schema": OUTPUT_SCHEMA,
        "source_six_cut_original_3D_disks_sha256": hashlib.sha256(raw).hexdigest(),
        "blender_version": "4.3.2",
        "solver": "ANGLE_BASED",
        "four_genuine_source_3D_disks": len(entries),
        "native_original_source_vertex_ABF_results": entries,
        "new_UV_solver_implemented": False,
        "factory_cutting_patterns_approved": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf8",
    )
    print("STAGE6_REAL_LOWER_FOUR_SOURCE_DISKS_NATIVE_BLENDER_ABF_ONLY", flush=True)


if __name__ == "__main__":
    main()
