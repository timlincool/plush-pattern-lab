# SPDX-License-Identifier: GPL-3.0-or-later
"""Invoke a pinned GPL sewing SVG *exporter* on existing source-indexed ABF UV.

The third-party add-on lives outside this repository and is NOT vendored.
We deliberately never run its mesh-altering "seams to sewingpattern" operator.
This emits only a non-factory research boundary, without seam allowance.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import bpy

BLEND_SHA = "38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a"
ADDON_COMMIT = "919d031628264bb466840827a81f657133931de7"
ADDON_BLOB = "9bf263002593d6e9b09c7868da703a213948148c"
IDENTITY = ("N15_sloped_source_band", "left", "lateral")
OUTPUT_NAME = "N15_left_lateral_ABF_RESEARCH_ONLY_no_allowance.svg"


def _pick(source, native, scored, source_sha, native_sha):
    if (
        source.get("original_public_blend_sha256") != BLEND_SHA
        or source.get("factory_cutting_patterns_approved") != 0
        or native.get("source_study_sha256") != source_sha
        or native.get("source_blend_sha256") != BLEND_SHA
        or native.get("blender_version") != "4.3.2"
        or scored.get("same_run_source_study_sha256") != source_sha
        or scored.get("same_run_free_blender_native_raw_sha256") != native_sha
        or scored.get("factory_cutting_patterns_approved") != 0
    ):
        raise ValueError("external exporter requires one original locked Stage6 run")
    originals = [
        x for x in source["candidate_2d_research_disks"]
        if (x["source_variant"], x["original_source_side"], x["source_slit_direction"])
        == IDENTITY
    ]
    uv_rows = [
        x for x in native["entries"]
        if (x["source_variant"], x["source_side"], x["slit_direction"])
        == IDENTITY and x["method"] == "ANGLE_BASED"
    ]
    rows = [
        x for x in scored["full_same_metric_comparisons"]
        if (x["source_variant"], x["source_side"], x["original_source_slit"])
        == IDENTITY
    ]
    if len(originals) != 1 or len(uv_rows) != 1 or len(rows) != 1:
        raise ValueError("pinned original 3D disk and matching Blender ABF missing")
    src, row = originals[0], uv_rows[0]
    abf = [
        x for x in rows[0]["external_blender_solvers"]
        if x["method"] == "ANGLE_BASED"
    ]
    if (
        len(abf) != 1
        or row["status"] != "completed"
        or row["source_patch_sha256"] != src["original_source_patch_sha256"]
        or row["max_same_topological_vertex_uv_loop_disagreement"] > 1e-5
        or row["vertex_count"] != len(src["cut_disk_source_xyz_mm"])
        or row["triangle_count"]
        != len(src["cut_disk_original_source_triangle_indices"])
    ):
        raise ValueError("external exporter cannot change original source or UV loops")
    factor = float(abf[0]["uniform_scale_from_native_uv_to_research_mm"])
    points = row["uv_per_original_source_disk_vertex"]
    if not 0 < factor < 10000 or not all(
        len(x) == 2 and all(math.isfinite(v) and -1e-6 <= v <= 1 + 1e-6 for v in x)
        for x in points
    ):
        raise ValueError("ABF UV has no finite physical millimetre gauge")
    return src, row, factor


def _load_verified_exporter(directory):
    path = directory / "op_export_sewingpattern.py"
    if (
        not directory.is_dir()
        or directory.is_symlink()
        or not path.is_file()
        or path.is_symlink()
        or not (directory / "GPL-license.txt").is_file()
    ):
        raise ValueError("external GPL add-on must be installed separately")
    blob = hashlib.sha1(b"blob " + str(path.stat().st_size).encode() + b"\\0" + path.read_bytes()).hexdigest()
    if blob != ADDON_BLOB:
        raise ValueError("external addon exporter blob changed from reviewed upstream")
    spec = importlib.util.spec_from_file_location("pinned_external_s2s_export", path)
    if spec is None or spec.loader is None:
        raise ValueError("unloadable reviewed sewing SVG exporter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    bpy.utils.register_class(module.Export_Sewingpattern)
    return module.Export_Sewingpattern


def _export(original, native_uv, gauge_mm, destination):
    mesh = bpy.data.meshes.new("STAGE6_RESEARCH_ORIGINAL_TRIANGLES")
    obj = bpy.data.objects.new("STAGE6_RESEARCH_ORIGINAL_TRIANGLES", mesh)
    bpy.context.scene.collection.objects.link(obj)
    try:
        vertices = original["cut_disk_source_xyz_mm"]
        faces = original["cut_disk_original_source_triangle_indices"]
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        layer = mesh.uv_layers.new(name="ORIGINAL_STAGE6_ABF")
        for loop in mesh.loops:
            layer.data[loop.index].uv = native_uv["uv_per_original_source_disk_vertex"][
                loop.vertex_index
            ]
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        # External GPL exporter assumes Blender metres. Our source is in mm;
        # independent common-metric ABF UV->mm factor is stored divided by 1000.
        obj["S2S_UVtoWORLDscale"] = gauge_mm / 1000.0
        result = bpy.ops.object.export_sewingpattern(
            filepath=str(destination),
            alignment_markers="OFF",
            show_peice_ids=False,
        )
        if "FINISHED" not in result or not destination.is_file():
            raise ValueError("reviewed third-party exporter did not write SVG")
    finally:
        if obj.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--addon-dir", type=Path, required=True)
    parser.add_argument("--addon-commit", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    if bpy.app.version[:3] != (4, 3, 2) or args.addon_commit != ADDON_COMMIT:
        raise ValueError("exact Blender 4.3.2 and reviewed GPL exporter commit required")
    if args.out_dir.exists() or args.out_dir.is_symlink():
        raise ValueError("never overwrite external research SVG or a symlink")
    if any(
        not p.is_file() or p.is_symlink()
        for p in (args.source, args.native, args.audit)
    ):
        raise ValueError("same-run Stage6 source, UV and independent audit required")
    source_data = args.source.read_bytes()
    native_data = args.native.read_bytes()
    source = json.loads(source_data)
    native = json.loads(native_data)
    scored = json.loads(args.audit.read_bytes())
    original, uv, factor = _pick(
        source, native, scored,
        hashlib.sha256(source_data).hexdigest(),
        hashlib.sha256(native_data).hexdigest(),
    )
    external_class = _load_verified_exporter(args.addon_dir)
    args.out_dir.mkdir(parents=True, exist_ok=False)
    try:
        _export(original, uv, factor, args.out_dir / OUTPUT_NAME)
    finally:
        bpy.utils.unregister_class(external_class)
    print("STAGE6_PINNED_EXTERNAL_S2S_ABF_RESEARCH_SVG_ONLY", OUTPUT_NAME, flush=True)


if __name__ == "__main__":
    main()
