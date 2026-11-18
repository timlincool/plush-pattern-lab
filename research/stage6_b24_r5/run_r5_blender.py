"""Native Blender 4.3.2 Cloth simulation of R5 source-guided side protrusions.

This is evaluated physics, not a sewing pattern, stuffed sample, or proof of
attachment of the 4 separate original Stage6 visual ear meshes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from research.stage6_b24_r3.run_r3_blender import (  # noqa: E402
    _evaluate_frame,
    _packed_faces_to_blender,
    _setup_scene,
)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _verify_input(stage, qa, independent):
    design = json.loads(Path(qa).read_text(encoding="utf8"))
    check = json.loads(Path(independent).read_text(encoding="utf8"))
    if (
        design.get("schema")
        != "stage6-R5-source-two-side-lobe-open-headcap-40pieces-v1"
    ):
        raise ValueError("not a pinned R5 source-guided pattern experiment")
    if design.get("R5_stage_npz_SHA256") != _sha(stage):
        raise ValueError("R5 2D rest or 3D preposition changed after source QA")
    if (
        design.get("factory_approved_cut_patterns") != 0
        or check.get("factory_cutting_patterns_approved") != 0
    ):
        raise ValueError("not approved for factory cutting")
    if (
        check.get("schema")
        != "stage6-R5-independent-40-piece-matched-netline-and-strain-v1"
    ):
        raise ValueError("independent R5 netline audit is absent")
    shape = check["preposition_global_edge_strain"]
    if (
        shape["P95_pct"] >= 10.5
        or shape["max_pct"] >= 75
        or check["new_2d_paired_line_length_max_mismatch_mm"] >= 0.0001
        or not check["new_R5_narrow_gores_do_not_self_overlap"]
    ):
        raise ValueError("R5 source-guided seam/material research gate failed")


def _input_mesh(stage):
    with np.load(stage, allow_pickle=False) as payload:
        init = payload["initial_3d_prepositioned_vertices_m"].copy()
        rest = payload["true_independent_flat_2d_rest_xy_m"].copy()
        springs = payload["original_sewing_spring_vertex_pairs"].copy()
        face_lengths = payload["face_lengths"].copy()
        face_ids = payload["face_vertex_ids"].copy()
        roles = payload["face_material_roles"].copy()
    if (
        init.shape != (3139, 3)
        or rest.shape != (3139, 2)
        or springs.shape != (1170, 2)
        or len(face_lengths) != 2378
    ):
        raise ValueError("R5 Blender source panel topology mismatch")
    if not np.isfinite(init).all() or not np.isfinite(rest).all():
        raise ValueError("R5 source has nonfinite 3D/2D material coordinates")
    faces = _packed_faces_to_blender(face_ids, face_lengths, roles)
    return init, rest, springs, faces, roles, face_lengths, face_ids


def _save_result(args, mesh_data, blender_obj, scene, materials, final, elapsed):
    init, rest, springs, faces, roles, face_lengths, face_ids = mesh_data
    args.out.mkdir(parents=True, exist_ok=True)
    npz = args.out / "R5_GENUINE_EVALUATED_CLOTH_FRAME40.npz"
    np.savez_compressed(
        npz,
        evaluated_blender_cloth_vertices_m=final,
        initial_3d_prepositioned_vertices_m=init,
        true_independent_flat_2d_rest_xy_m=rest,
        original_sewing_spring_vertex_pairs=springs,
        face_lengths=face_lengths,
        face_vertex_ids=face_ids,
        face_material_roles=roles,
    )
    mesh = bpy.data.meshes.new("R5_TRUE_CLOTH_40FRAME_SOURCE_SURROGATE")
    mesh.from_pydata(final.tolist(), [], faces)
    mesh.update()
    obj = bpy.data.objects.new("R5_ACTUAL_CLOTH_NOT_FACTORY_APPROVED", mesh)
    scene.collection.objects.link(obj)
    for mat in materials.materials:
        mesh.materials.append(mat)
    for polygon, role in zip(mesh.polygons, roles):
        polygon.material_index = int(role)
    blender_obj.hide_render = True
    blend = args.out / "R5_TRUE_Blender_4_3_2_40frames.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend.resolve()))
    a = np.linalg.norm(init[springs[:, 0]] - init[springs[:, 1]], axis=1) * 1000
    b = np.linalg.norm(final[springs[:, 0]] - final[springs[:, 1]], axis=1) * 1000
    report = {
        "schema": "stage6-R5-source-guided-two-side-lobes-real-Blender-Cloth-v1",
        "blender_version": bpy.app.version_string,
        "genuine_evaluated_Blender_depgraph_mesh": True,
        "source_r5_research_input_SHA256": _sha(args.stage),
        "source_r5_independent_audit_SHA256": _sha(args.audit),
        "native_40_frames": args.frames,
        "physical_research_panels": 40,
        "old_R3_panels": 24,
        "new_side_lobe_panels": 16,
        "R3_original_spring_pairs_preserved": 986,
        "all_sewing_springs": len(springs),
        "evaluated_vertices": len(final),
        "surface_faces": len(faces),
        "initial_mean_spring_gap_mm": float(a.mean()),
        "final_mean_spring_gap_mm": float(b.mean()),
        "final_max_spring_gap_mm": float(b.max()),
        "physical_solver_seconds": elapsed,
        "self_collision_and_pressure": False,
        "original_real_Stage6_ear_meshes_sewn": 0,
        "factory_cut_patterns_approved": 0,
        "actual_evaluated_npz_sha256": _sha(npz),
        "actual_blender_file_sha256": _sha(blend),
    }
    (args.out / "R5_TRUE_BLENDER_REPORT.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print("STAGE6_R5_REAL_CLOTH_COMPLETE", json.dumps(report), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("stage", "qa", "audit", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--frames", type=int, default=40)
    args = p.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    if bpy.app.version[:3] != (4, 3, 2) or args.frames != 40:
        raise ValueError("only pinned Blender 4.3.2 / 40 frames allowed")
    if args.out.is_symlink() or (args.out.exists() and any(args.out.iterdir())):
        raise ValueError("never overwrite prior true physics experiment")
    _verify_input(args.stage, args.qa, args.audit)
    result = _input_mesh(args.stage)
    obj, scene, materials = _setup_scene(*result[:5], args.frames)
    obj.name = "R5_NATIVE_40_PIECE_SOURCE_LOBE_SEWING"
    final, elapsed = _evaluate_frame(
        scene, obj, result[0].shape, result[2], args.frames
    )
    _save_result(args, result, obj, scene, materials, final, elapsed)


if __name__ == "__main__":
    main()
