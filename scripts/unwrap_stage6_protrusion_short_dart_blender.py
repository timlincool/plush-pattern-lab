# SPDX-License-Identifier: GPL-2.0-or-later
"""Native Blender 4.3.2 ABF on four genuine source open-slits, no new UV code."""

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

SOURCE_SCHEMA = "stage6-original-ear-high-protrusion-short-open-slit-v1"
OUTPUT_SCHEMA = "stage6-original-high-protrusion-short-dart-native-blender-ABF-v1"
ROUTES = ("Y_REAR_RIM_TO_TIP", "X_INNER_RIM_TO_TIP")
SIDES = ("left_high_protrusion", "right_high_protrusion")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--caps", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    if bpy.app.version[:3] != (4, 3, 2):
        raise ValueError("only pinned Blender 4.3.2 original ABF is allowed")
    if (
        args.output.exists()
        or args.output.is_symlink()
        or any(not p.is_file() or p.is_symlink() for p in (args.source, args.caps))
    ):
        raise ValueError(
            "missing original source or prior ABF output would be overwritten"
        )
    raw = args.source.read_bytes()
    study = json.loads(raw)
    if (
        study.get("schema") != SOURCE_SCHEMA
        or study.get("factory_cutting_patterns_approved") != 0
        or study.get("same_run_caps_sha256")
        != hashlib.sha256(args.caps.read_bytes()).hexdigest()
        or study.get("routes") != list(ROUTES)
        or len(study.get("four_real_original_cap_short_slit_disks", [])) != 4
    ):
        raise ValueError("short open slits not derived from same-run source mesh")
    entries = []
    for i, cap in enumerate(study["four_real_original_cap_short_slit_disks"]):
        if (
            cap["route"] != ROUTES[i // 2]
            or cap["source_cap_id"] != SIDES[i % 2]
            or not cap["original_triangles_unmodified_in_3d"]
        ):
            raise ValueError("open slit identity/order changed before native ABF")
        shim = {
            "id": cap["id"],
            "source_boundary_edges": cap["source_boundary_edges"],
            "vertices_xyz_mm": cap["source_xyz_mm"],
            "triangles_local_vertex_indices": cap["disk_triangle_vertex_ids"],
            "original_rim_vertex_ids_in_cap_local_order": cap[
                "boundary_panel_vertex_ids_in_order"
            ],
        }
        entries.append(
            {
                "route": cap["route"],
                **_unwrap(shim, cap["id"], cap["source_boundary_edges"]),
            }
        )
    result = {
        "schema": OUTPUT_SCHEMA,
        "same_run_source_short_slits_sha256": hashlib.sha256(raw).hexdigest(),
        "blender_version": "4.3.2",
        "solver": "ANGLE_BASED",
        "actual_genuine_original_source_disks_measured": len(entries),
        "entries": entries,
        "reused_native_Blender_solver_not_reimplemented": True,
        "factory_cutting_patterns_approved": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, separators=(",", ":"), ensure_ascii=False) + "\n",
        encoding="utf8",
    )
    print(
        "STAGE6_FOUR_ORIGINAL_SHORT_DARTS_REAL_BLENDER_ABF_RESEARCH_ONLY",
        flush=True,
    )


if __name__ == "__main__":
    main()
