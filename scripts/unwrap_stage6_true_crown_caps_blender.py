# SPDX-License-Identifier: GPL-2.0-or-later
"""Use actual Blender 4.3.2 native ABF to unwrap three genuine Stage6 caps.

Only fixed original-source research 3D mesh files are accepted. No factory paper.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import bpy

INPUT_SCHEMA = "stage6-genuine-source-z230-three-open-caps-v1"
OUTPUT_SCHEMA = "stage6-real-source-three-crown-cap-native-ABF-research-v1"
COMPONENTS = ("central_crown", "left_high_protrusion", "right_high_protrusion")
RINGS = (189, 113, 112)


def _validate_cap(cap, name, ring):
    points = cap["vertices_xyz_mm"]
    faces = cap["triangles_local_vertex_indices"]
    rim = cap["original_rim_vertex_ids_in_cap_local_order"]
    if (
        cap.get("id") != name
        or cap.get("source_boundary_edges") != ring
        or len(rim) != ring
        or len(set(rim)) != ring
        or any(len(p) != 3 or not all(math.isfinite(x) for x in p) for p in points)
        or any(
            len(f) != 3
            or len(set(f)) != 3
            or any(not isinstance(i, int) or not 0 <= i < len(points) for i in f)
            for f in faces
        )
    ):
        raise ValueError("original source cap mesh or rim identity has changed")
    return points, faces


def _unwrap(cap, name, ring):
    points, faces = _validate_cap(cap, name, ring)
    mesh = bpy.data.meshes.new("stage6-original-z230-ABF-" + name)
    obj = bpy.data.objects.new(mesh.name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    started = time.perf_counter()
    try:
        mesh.from_pydata(points, [], faces)
        mesh.update()
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        mesh.uv_layers.new(name="source_triangle_ABF_research")
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        outcome = bpy.ops.uv.unwrap(
            method="ANGLE_BASED", fill_holes=False, correct_aspect=False, margin=0.0
        )
        bpy.ops.object.mode_set(mode="OBJECT")
        if "FINISHED" not in outcome:
            raise ValueError("native Blender ABF refused real source crown cap")
        uv_layers = mesh.uv_layers.active.data
        indexed = [[] for _ in points]
        for loop in mesh.loops:
            uv = uv_layers[loop.index].uv
            indexed[loop.vertex_index].append([float(uv[0]), float(uv[1])])
        if any(not samples for samples in indexed):
            raise ValueError("source cap vertex absent from Blender UV")
        coordinates, largest_loop_mismatch = [], 0.0
        for samples in indexed:
            mid = [sum(s[i] for s in samples) / len(samples) for i in (0, 1)]
            coordinates.append(mid)
            largest_loop_mismatch = max(
                largest_loop_mismatch,
                *(math.hypot(s[0] - mid[0], s[1] - mid[1]) for s in samples),
            )
        if largest_loop_mismatch > 1e-5 or any(
            not math.isfinite(v) for p in coordinates for v in p
        ):
            raise ValueError(
                "Blender split one real source cut cap into untracked UV islands"
            )
        return {
            "source_cap_id": name,
            "source_vertex_count": len(points),
            "source_triangle_count": len(faces),
            "original_cut_rim_edges": ring,
            "uv_per_3d_cap_source_vertex": coordinates,
            "maximum_split_UV_loop_disagreement": largest_loop_mismatch,
            "native_ABF_runtime_seconds": round(time.perf_counter() - started, 5),
            "native_UV_has_no_fabric_mm_until_independent_global_rescale": True,
        }
    finally:
        if obj.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-caps", type=Path, required=True)
    parser.add_argument("--source-summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    if bpy.app.version[:3] != (4, 3, 2):
        raise ValueError("only trusted Blender 4.3.2 native ABF source study")
    if (
        args.output.exists()
        or args.output.is_symlink()
        or any(
            not p.is_file() or p.is_symlink()
            for p in (args.source_caps, args.source_summary)
        )
    ):
        raise ValueError("real source input absent or would overwrite prior result")
    blob = args.source_caps.read_bytes()
    raw = json.loads(blob)
    summary = json.loads(args.source_summary.read_bytes())
    if (
        raw.get("schema") != INPUT_SCHEMA
        or raw.get("industrial_cutting_patterns_approved") != 0
        or summary.get("full_3d_source_caps_json_sha256")
        != hashlib.sha256(blob).hexdigest()
    ):
        raise ValueError("genuine source full cap geometry / summary SHA mismatch")
    caps = raw["upper_caps"]
    if len(caps) != 3:
        raise ValueError("expected exactly three authentic original upper caps")
    results = [
        _unwrap(cap, label, size) for cap, label, size in zip(caps, COMPONENTS, RINGS)
    ]
    output = {
        "schema": OUTPUT_SCHEMA,
        "source_caps_geometry_sha256": hashlib.sha256(blob).hexdigest(),
        "blender_version": "4.3.2",
        "solver": "ANGLE_BASED",
        "source_original_3d_piece_count": 3,
        "entries": results,
        "factory_cutting_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf8",
    )
    print("STAGE6_THREE_REAL_SOURCE_CROWN_3D_CAPS_NATIVE_ABF_RESEARCH", flush=True)


if __name__ == "__main__":
    main()
