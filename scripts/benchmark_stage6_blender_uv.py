# SPDX-License-Identifier: GPL-2.0-or-later
"""Run FREE Blender 4.3.2 native ABF/Conformal on pinned Stage6 source disks.

Standalone bpy adapter: separate from the project's non-Blender Python modules.
No GPL add-on source is copied. It is invoked only by trusted main CI.
It emits research UV arrays, NEVER production sewing/cutting patterns.
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

SOURCE_SCHEMA = "stage6-ear-root-genuine-source-disk-lscm-research-v1"
BENCH_SCHEMA = "stage6-free-blender-native-uv-abf-conformal-raw-v1"
SOURCE_SHA = "38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a"
METHODS = ("ANGLE_BASED", "CONFORMAL")


def _inputs(path, output):
    if (
        not path.is_file()
        or path.is_symlink()
        or output.exists()
        or output.is_symlink()
        or output.suffix != ".json"
        or path.resolve() == output.resolve()
    ):
        raise ValueError("protected Stage6 source missing or output already exists")
    report = json.loads(path.read_text(encoding="utf8"))
    if (
        report.get("schema") != SOURCE_SCHEMA
        or report.get("original_public_blend_sha256") != SOURCE_SHA
        or report.get("factory_cutting_patterns_approved") != 0
        or report.get("P3_status") != "in_progress"
        or report.get("P4_status") != "not_started"
        or len(report.get("candidate_2d_research_disks", [])) != 12
    ):
        raise ValueError(
            "this benchmark requires the verified original Stage6 P3 study"
        )
    names = [
        (x["source_variant"], x["original_source_side"], x["source_slit_direction"])
        for x in report["candidate_2d_research_disks"]
    ]
    if len(set(names)) != 12 or any(
        not x.get("not_a_factory_cutting_or_sewing_approval")
        for x in report["candidate_2d_research_disks"]
    ):
        raise ValueError("invalid original Stage6 candidate identities or approval")
    return report


def _validate_geometry(candidate):
    points = candidate["cut_disk_source_xyz_mm"]
    faces = candidate["cut_disk_original_source_triangle_indices"]
    if (
        len(points) < 20
        or len(faces) < 30
        or any(
            len(point) != 3 or not all(math.isfinite(value) for value in point)
            for point in points
        )
        or any(
            len(face) != 3
            or len(set(face)) != 3
            or any(not isinstance(i, int) or not 0 <= i < len(points) for i in face)
            for face in faces
        )
        or len(candidate["cut_disk_source_vertex_identity"]) != len(points)
        or len(candidate["actual_slit_original_source_local_vertex_ids"]) < 2
    ):
        raise ValueError("untrusted original source disk or changed vertex IDs")
    return points, faces


def _unwrap_one(candidate, method):
    points, faces = _validate_geometry(candidate)
    mesh = bpy.data.meshes.new("stage6-native-uv-research")
    obj = bpy.data.objects.new("stage6-native-uv-research", mesh)
    bpy.context.scene.collection.objects.link(obj)
    begin = time.perf_counter()
    try:
        mesh.from_pydata(points, [], faces)
        mesh.update()
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        mesh.uv_layers.new(name="research_uv")
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        result = bpy.ops.uv.unwrap(
            method=method,
            fill_holes=False,
            correct_aspect=False,
            margin=0.0,
        )
        bpy.ops.object.mode_set(mode="OBJECT")
        if "FINISHED" not in result or mesh.uv_layers.active is None:
            raise ValueError("Blender native unwrapping returned no usable UV")
        uv_data = mesh.uv_layers.active.data
        vertices = [[] for _ in points]
        for loop in mesh.loops:
            uv = uv_data[loop.index].uv
            vertices[loop.vertex_index].append([float(uv[0]), float(uv[1])])
        if any(not row for row in vertices):
            raise ValueError("native unwrap omitted original source disk vertices")
        normalized = []
        max_disagreement = 0.0
        for samples in vertices:
            x = sum(row[0] for row in samples) / len(samples)
            y = sum(row[1] for row in samples) / len(samples)
            normalized.append([x, y])
            max_disagreement = max(
                max_disagreement,
                *(math.hypot(u - x, v - y) for u, v in samples),
            )
        if not all(math.isfinite(x) and math.isfinite(y) for x, y in normalized):
            raise ValueError("native unwrap emitted nonfinite UV coordinates")
        return {
            "status": "completed",
            "uv_per_original_source_disk_vertex": normalized,
            "max_same_topological_vertex_uv_loop_disagreement": max_disagreement,
            "vertex_count": len(points),
            "triangle_count": len(faces),
            "runtime_seconds": round(time.perf_counter() - begin, 4),
            "uv_is_texture_coordinates_not_fabric_millimetres": True,
        }
    finally:
        if obj.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    if bpy.app.version[:3] != (4, 3, 2):
        raise ValueError("blender 4.3.2 is required for apples-to-apples study")
    source = _inputs(args.input, args.output)
    output = {
        "schema": BENCH_SCHEMA,
        "blender_version": "4.3.2",
        "source_study_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "source_blend_sha256": SOURCE_SHA,
        "methods": list(METHODS),
        "entries": [],
        "uses_official_free_blender_native_solver_only": True,
        "third_party_commercial_service_used": False,
        "cutting_patterns_approved": 0,
    }
    for item in source["candidate_2d_research_disks"]:
        identity = {
            "source_variant": item["source_variant"],
            "source_side": item["original_source_side"],
            "slit_direction": item["source_slit_direction"],
            "source_patch_sha256": item["original_source_patch_sha256"],
        }
        for method in METHODS:
            result = _unwrap_one(item, method)
            output["entries"].append({**identity, "method": method, **result})
            print(
                "STAGE6_NATIVE_BLENDER_FREE_UV",
                method,
                identity["source_variant"],
                identity["source_side"],
                identity["slit_direction"],
                "runtime_s",
                result["runtime_seconds"],
                flush=True,
            )
    if len(output["entries"]) != 24:
        raise ValueError("Blender external benchmark must include all 12 x 2")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False) + "\n", encoding="utf8"
    )
    print("STAGE6_FREE_NATIVE_UV_COMPLETE_BUT_NOT_PAPER_PATTERNS", flush=True)


if __name__ == "__main__":
    main()
