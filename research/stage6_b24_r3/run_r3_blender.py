"""Solve actual B24-R3 24-panel stitched cloth in trusted Blender 4.3.2.

Only evaluated Blender depsgraph vertices constitute physical simulation output.
No filling, self-collision, fiber physics, or factory cut-pattern proof.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import bpy
import numpy as np


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _validate_staging_sha(stage, report):
    qa = json.loads(report.read_text(encoding="utf8"))
    if qa["schema"] != "stage6-r3-matched-material-2d-body-5-station-trial-v1":
        raise ValueError("not a trusted R3 pattern contract")
    if qa["R3_stage_npz_sha256"] != _sha256(stage):
        raise ValueError("R3 flat 2D source changed after validation")
    if qa["factory_cut_patterns_approved"] != 0:
        raise ValueError("research source must not claim factory acceptance")
    if qa["rest_edge_strain_p95_percent"] >= 10.5:
        raise ValueError("R3 preposition material strain failed research gate")


def _packed_faces_to_blender(fids, flens, roles):
    faces = []
    offset = 0
    for size in flens:
        polygon = fids[offset : offset + int(size)]
        faces.append([int(i) for i in polygon])
        offset += int(size)
    if offset != len(fids) or len(roles) != len(faces):
        raise ValueError("R3 polygon index mapping changed")
    return faces


def _read_input(stage, report):
    _validate_staging_sha(stage, report)
    with np.load(stage, allow_pickle=False) as result:
        init = result["initial_3d_prepositioned_vertices_m"].copy()
        rest = result["true_independent_flat_2d_rest_xy_m"].copy()
        pairs = result["original_sewing_spring_vertex_pairs"].copy()
        flens = result["face_lengths"].copy()
        fids = result["face_vertex_ids"].copy()
        roles = result["face_material_roles"].copy()
    if init.shape != (2635, 3) or rest.shape != (2635, 2):
        raise ValueError("R3 vertex/flat material contract changed")
    if pairs.shape != (986, 2) or len(flens) != 1990:
        raise ValueError("R3 physical panels or spring counts changed")
    if not np.isfinite(init).all() or not np.isfinite(rest).all():
        raise ValueError("R3 source shape contains nonfinite vertices")
    return init, rest, pairs, _packed_faces_to_blender(fids, flens, roles), roles, flens, fids


def _setup_scene(init, rest, pairs, faces, roles, frames):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mesh = bpy.data.meshes.new("R3_TRUE_24_INDEPENDENT_2D_REST_PANELS")
    mesh.from_pydata(init.tolist(), pairs.tolist(), faces)
    mesh.update()
    cloth_object = bpy.data.objects.new("R3_REAL_B24_CLOTH", mesh)
    bpy.context.scene.collection.objects.link(cloth_object)
    bpy.context.view_layer.objects.active = cloth_object
    cloth_object.select_set(True)
    cloth_object.shape_key_add(name="R3_SOURCE_REFERENCE_PREPOSITION")
    planar_key = cloth_object.shape_key_add(name="R3_REBUILT_2D_REST_NOT_3D_SCULPT")
    for i, coord in enumerate(rest):
        planar_key.data[i].co = (float(coord[0]), float(coord[1]), 0)
    for color in (
        (0.83, 0.82, 0.74, 1),
        (0.96, 0.90, 0.80, 1),
        (0.78, 0.81, 0.86, 1),
        (0.76, 0.75, 0.79, 1),
    ):
        material = bpy.data.materials.new("R3 research material")
        material.diffuse_color = color
        mesh.materials.append(material)
    for poly, role in zip(mesh.polygons, roles):
        poly.material_index = int(role)
    cloth = cloth_object.modifiers.new("BLENDER_432_R3_SEWING_SPRINGS", "CLOTH")
    cloth.settings.rest_shape_key = planar_key
    cloth.settings.use_sewing_springs = True
    cloth.settings.sewing_force_max = 50.0
    cloth.settings.mass = 0.025 / len(init)
    cloth.settings.quality = 5
    cloth.settings.tension_stiffness = 15.0
    cloth.settings.compression_stiffness = 15.0
    cloth.settings.shear_stiffness = 8.0
    cloth.settings.bending_stiffness = 0.5
    cloth.settings.use_pressure = False
    cloth.collision_settings.use_collision = False
    cloth.collision_settings.use_self_collision = False
    scene = bpy.context.scene
    scene.gravity = (0, 0, 0)
    scene.frame_start = 1
    scene.frame_end = frames
    cloth.point_cache.frame_start = 1
    cloth.point_cache.frame_end = frames
    return cloth_object, scene, mesh


def _evaluate_frame(scene, obj, expected, pairs, frames):
    dependency = bpy.context.evaluated_depsgraph_get()
    stamp = time.monotonic()
    final = None
    for frame in range(1, frames + 1):
        scene.frame_set(frame)
        evaluated = obj.evaluated_get(dependency)
        temporary = evaluated.to_mesh()
        try:
            coordinates = np.empty(3 * len(temporary.vertices), dtype=np.float32)
            temporary.vertices.foreach_get("co", coordinates)
            final = coordinates.reshape(-1, 3).astype(np.float64)
        finally:
            evaluated.to_mesh_clear()
        if final.shape != expected or not np.isfinite(final).all():
            raise ValueError("evaluated Blender mesh is malformed")
        if frame % 10 == 0:
            gap = np.linalg.norm(final[pairs[:, 0]] - final[pairs[:, 1]], axis=1)
            print("STAGE6_R3_NATIVE_CLOTH_FRAME", frame, float(gap.mean() * 1000))
    return final, time.monotonic() - stamp


def _persist(args, info, obj, scene, materials, final, elapsed):
    init, rest, springs, faces, roles, flens, fids = info
    args.out.mkdir(parents=True, exist_ok=True)
    output = args.out / "R3_ACTUAL_EVALUATED_CLOTH_FRAME40.npz"
    np.savez_compressed(
        output,
        evaluated_blender_cloth_vertices_m=final,
        initial_3d_prepositioned_vertices_m=init,
        true_independent_flat_2d_rest_xy_m=rest,
        original_sewing_spring_vertex_pairs=springs,
        face_lengths=flens,
        face_vertex_ids=fids,
        face_material_roles=roles,
    )
    mesh = bpy.data.meshes.new("R3_ACTUAL_EVALUATED_CLOTH_FRAME40")
    mesh.from_pydata(final.tolist(), [], faces)
    mesh.update()
    picture = bpy.data.objects.new("R3_FRAME40_NOT_A_SEWN_FACTORY_TOY", mesh)
    scene.collection.objects.link(picture)
    for item in materials.materials:
        mesh.materials.append(item)
    for poly, role in zip(mesh.polygons, roles):
        poly.material_index = int(role)
    obj.hide_render = True
    blend = args.out / "R3_TRUE_Blender_4_3_2_40frames.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend.resolve()))
    first = np.linalg.norm(init[springs[:, 0]] - init[springs[:, 1]], axis=1) * 1000
    last = np.linalg.norm(final[springs[:, 0]] - final[springs[:, 1]], axis=1) * 1000
    report = {
        "schema": "stage6-R3-matched-2D-to-real-native-Blender40frames-v1",
        "blender_version": bpy.app.version_string,
        "source_stage_sha256": _sha256(args.stage),
        "true_evaluated_blender_depsgraph_used": True,
        "panels": 24,
        "springs": len(springs),
        "evaluated_vertices": len(final),
        "frames": args.frames,
        "solver_seconds": float(elapsed),
        "initial_mean_seam_gap_mm": float(first.mean()),
        "final_mean_seam_gap_mm": float(last.mean()),
        "final_max_seam_gap_mm": float(last.max()),
        "physical_pressure_fill_or_self_collision_enabled": False,
        "R3_real_sewing_ornaments": False,
        "factory_cut_patterns_approved": 0,
        "NPZ_sha256": _sha256(output),
        "BLEND_sha256": _sha256(blend),
    }
    (args.out / "R3_NATIVE_BLENDER_REPORT.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print("STAGE6_R3_REAL_CLOTH_COMPLETE", json.dumps(report), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True, type=Path)
    parser.add_argument("--qa", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--frames", type=int, default=40)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    if bpy.app.version[:3] != (4, 3, 2) or args.frames != 40:
        raise ValueError("only pinned Blender 4.3.2 with 40 frames approved for study")
    if args.out.is_symlink() or (args.out.exists() and any(args.out.iterdir())):
        raise ValueError("refuse to override prior physical output")
    info = _read_input(args.stage, args.qa)
    obj, scene, materials = _setup_scene(*info[:5], args.frames)
    final, elapsed = _evaluate_frame(scene, obj, info[0].shape, info[2], args.frames)
    _persist(args, info, obj, scene, materials, final, elapsed)


if __name__ == "__main__":
    main()