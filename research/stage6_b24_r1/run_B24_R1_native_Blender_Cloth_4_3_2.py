"""Run real native Blender Cloth B24-R1 from genuine revised 2D rest patterns.

This file must run INSIDE trusted Blender 4.3.2 via `-b -t 1 --python`.
Never mark R1 physical sewing as finished before THIS solver successfully runs.
The output mesh comes only from evaluated depsgraph after advancing each frame.

Example:
  blender --disable-autoexec --python-exit-code 1 -b -t 1 \
    --python run_B24_R1_native_Blender_Cloth_4_3_2.py -- \
    --input B24_R1_NEW_2D_REST_NEW_3D_PREPOSITION_NOT_SOLVED.npz \
    --qa B24_R1_staging_QA.json --out R1_Physical_Simulation
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


def read_input(path, qa_file):
    qa = json.loads(qa_file.read_text(encoding="utf8"))
    if qa.get("stage_npz_sha256") != hashlib.sha256(path.read_bytes()).hexdigest():
        raise ValueError("B24 R1 staged 2D rest source SHA mismatch")
    if (
        qa.get("original_interpanel_spring_pairs_preserved") != 974
        or qa.get("factory_patterns_approved") != 0
    ):
        raise ValueError("B24 R1 research source lineage changed")
    with np.load(path, allow_pickle=False) as data:
        vertices = np.array(data["initial_3d_prepositioned_vertices_m"], float)
        rest = np.array(data["true_independent_flat_2d_rest_xy_m"], float)
        lengths = np.array(data["face_lengths"], int)
        ids = np.array(data["face_vertex_ids"], int)
        roles = np.array(data["face_material_roles"], int)
        spring = np.array(data["original_sewing_spring_vertex_pairs"], int)
    if (
        vertices.shape != (2431, 3)
        or rest.shape != (2431, 2)
        or spring.shape != (974, 2)
        or lengths.shape != (1798,)
        or lengths.sum() != len(ids)
        or np.any(lengths < 3)
        or np.any(lengths > 4)
        or len(roles) != len(lengths)
        or np.any(ids < 0)
        or np.any(ids >= 2431)
        or np.any(spring < 0)
        or np.any(spring >= 2431)
        or not np.isfinite(vertices).all()
        or not np.isfinite(rest).all()
    ):
        raise ValueError(
            "B24 R1 staged source has invalid topology/material coordinates"
        )
    polygons = []
    offset = 0
    for n in lengths:
        polygons.append([int(x) for x in ids[offset : offset + n]])
        offset += int(n)
    return vertices, rest, polygons, spring, roles


def _setup_native_sewing(init, rest, faces, pairs, roles, frames):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mesh = bpy.data.meshes.new("B24_R1_24_INDEPENDENT_2D_REST_SHAPES")
    mesh.from_pydata(init.tolist(), pairs.tolist(), faces)
    mesh.update()
    obj = bpy.data.objects.new("B24_R1_REAL_CLOTH_SOLVER_NOT_FACTORY_TOY", mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    obj.shape_key_add(name="R1_initial_3D_preposition_only")
    key = obj.shape_key_add(name="R1_true_flat_2D_static_pattern_rest_shape")
    for j, uv in enumerate(rest):
        key.data[j].co = (float(uv[0]), float(uv[1]), 0.0)
    for color in (
        (0.83, 0.82, 0.74, 1),
        (0.96, 0.90, 0.80, 1),
        (0.78, 0.81, 0.86, 1),
        (0.76, 0.75, 0.79, 1),
    ):
        mat = bpy.data.materials.new("R1 research textile group")
        mat.diffuse_color = color
        mesh.materials.append(mat)
    for polygon, role in zip(mesh.polygons, roles):
        polygon.material_index = int(role)
    cloth = obj.modifiers.new("Blender_4_3_2_R1_NATIVE_CLOTH_SEWING", "CLOTH")
    cloth.settings.rest_shape_key = key
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
    return obj, mesh, scene


def _evaluate_actual_cloth_frames(obj, init, pairs, frames):
    deps = bpy.context.evaluated_depsgraph_get()
    gap_initial = np.linalg.norm(init[pairs[:, 0]] - init[pairs[:, 1]], axis=1)
    final = None
    started = time.monotonic()
    for frame in range(1, frames + 1):
        scene.frame_set(frame)
        ev = obj.evaluated_get(deps)
        em = ev.to_mesh()
        try:
            arr = np.empty(3 * len(em.vertices), dtype=np.float32)
            em.vertices.foreach_get("co", arr)
            final = arr.reshape(-1, 3).astype(float)
        finally:
            ev.to_mesh_clear()
        if final.shape != init.shape or not np.isfinite(final).all():
            raise ValueError("R1 native Blender evaluated mesh invalid")
        if frame % 10 == 0:
            gap = np.linalg.norm(final[pairs[:, 0]] - final[pairs[:, 1]], axis=1)
            print(
                "B24_R1_FRAME",
                frame,
                "seam_mean_mm",
                float(np.mean(gap) * 1000),
                flush=True,
            )
    gap_final = np.linalg.norm(final[pairs[:, 0]] - final[pairs[:, 1]], axis=1)
    return final, gap_initial, gap_final, started


def _persist_evaluated_snapshot(
    args, init, rest, faces, pairs, roles, mesh, obj, scene,
    final, gap_initial, gap_final, started
):
    args.out.mkdir(parents=True, exist_ok=True)
    saved = args.out / "B24_R1_actual_evaluated_Cloth_frame40.npz"
    face_lengths = np.array([len(x) for x in faces], dtype=np.int32)
    face_ids = np.array([int(v) for polygon in faces for v in polygon], dtype=np.int32)
    np.savez_compressed(
        saved,
        evaluated_blender_cloth_vertices_m=final,
        initial_3d_prepositioned_vertices_m=init,
        true_independent_flat_2d_rest_xy_m=rest,
        face_lengths=face_lengths,
        face_vertex_ids=face_ids,
        face_material_roles=roles.astype(np.int8),
        original_sewing_spring_vertex_pairs=pairs.astype(np.int32),
    )
    snapshot = bpy.data.meshes.new("B24_R1_ACTUAL_EVALUATED_FRAME")
    snapshot.from_pydata(final.tolist(), [], faces)
    snapshot.update()
    preview = bpy.data.objects.new("B24_R1_TRUE_CLOTH_FRAME_NOT_APPROVED", snapshot)
    scene.collection.objects.link(preview)
    for mat in mesh.materials:
        snapshot.materials.append(mat)
    for polygon, role in zip(snapshot.polygons, roles):
        polygon.material_index = int(role)
    obj.hide_render = True
    blend_file = args.out / "B24_R1_real_cloth_evaluated_frame40.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_file.resolve()))
    audit = {
        "schema": "B24-R1-NATIVE-BLENDER-REAL-CLOTH-v1",
        "blender": bpy.app.version_string,
        "input_file_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "trusted_2D_rest_shape": True,
        "evaluated_depsgraph_mesh_used": True,
        "pieces": 24,
        "springs": len(pairs),
        "frames": args.frames,
        "initial_seam_gap_mean_mm": float(gap_initial.mean() * 1000),
        "final_seam_gap_mean_mm": float(gap_final.mean() * 1000),
        "final_seam_gap_max_mm": float(gap_final.max() * 1000),
        "evaluated_vertices": len(final),
        "surface_polygons": len(faces),
        "elapsed_s": round(time.monotonic() - started, 3),
        "source_caps_not_sewn": True,
        "true_stuffing_pressure_enabled": False,
        "cloth_self_collision_enabled": False,
        "factory_approved_patterns": 0,
        "actual_npz_sha256": hashlib.sha256(saved.read_bytes()).hexdigest(),
        "actual_blend_sha256": hashlib.sha256(blend_file.read_bytes()).hexdigest(),
        "R1_appearance_gate": "NOT_YET_ASSESSED",
    }
    (args.out / "B24_R1_native_blender_report.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print("B24_R1_REAL_CLOTH_SOLVER_COMPLETE", json.dumps(audit), flush=True)



def run(args):
    if bpy.app.version[:3] != (4, 3, 2):
        raise ValueError("exact trusted Blender 4.3.2 required")
    if args.out.exists() and any(args.out.iterdir()):
        raise ValueError("refuse to overwrite a previous R1 physics result")
    init, rest, faces, pairs, roles = read_input(args.input, args.qa)
    obj, mesh, scene = _setup_native_sewing(
        init, rest, faces, pairs, roles, args.frames
    )
    final, gap_initial, gap_final, started = _evaluate_actual_cloth_frames(
        obj, init, pairs, args.frames
    )
    _persist_evaluated_snapshot(
        args, init, rest, faces, pairs, roles, mesh, obj, scene,
        final, gap_initial, gap_final, started
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--qa", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--frames", type=int, default=40)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    if not 24 <= args.frames <= 64:
        raise ValueError("unreviewed frame budget")
    run(args)


if __name__ == "__main__":
    main()
