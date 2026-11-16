"""R4 central source crown: add a second material ring to the R3 cap.

This is NOT an original 3D-surface flattening or a true physical sewing result.
Only the center crown is modified; the two side protrusions remain unsewn.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import Polygon

from research.stage6_b24_r3.build_r3_matched_body import radial_fit

SOURCE_SHA = "5b52e3fd09c83b19c5b9d95d6d8d859a147ff4deef90f1518f868d2e82e3a2dd"
R3_SHA = "d93afe5667bc2c808e4700c5554a858b1df9b1574c9e23de1cb2c08b42c27fc3"
CAP_START = 4 * 34 + 4 * 68 + 4 * 85 + 128
Z_INNER = 234.0
SOURCE_BLEND = 0.50


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read_pinned(stage, source):
    for path, expected in ((stage, R3_SHA), (source, SOURCE_SHA)):
        path = Path(path)
        if not path.is_file() or path.is_symlink() or _hash(path) != expected:
            raise ValueError("source not equal to signed-off R3/Stage6 evidence")
    with np.load(stage, allow_pickle=False) as r3:
        data = {name: r3[name].copy() for name in r3.files}
    if (
        data["initial_3d_prepositioned_vertices_m"].shape != (2635, 3)
        or data["true_independent_flat_2d_rest_xy_m"].shape != (2635, 2)
        or data["original_sewing_spring_vertex_pairs"].shape != (986, 2)
        or len(data["face_lengths"]) != 1990
    ):
        raise ValueError("pinned R3 24-panel vertex or spring topology changed")
    return data, trimesh.load(source, force="mesh")


def _source_central(mesh, z):
    section = mesh.section(plane_origin=(0, 0, z), plane_normal=(0, 0, 1))
    if section is None:
        raise ValueError("Stage6 actual head section is absent")
    loops = []
    for vertices in section.discrete:
        if len(vertices) < 12 or np.linalg.norm(vertices[0] - vertices[-1]) > 0.001:
            continue
        candidate = Polygon(vertices[:, :2])
        if candidate.is_valid and candidate.area > 30:
            loops.append(candidate)
    if len(loops) != 3:
        raise ValueError("original center crown and two side contours not found")
    return max(loops, key=lambda part: part.area), len(loops)


def _crown_material(outer, outer_uv, center_uv, ring):
    radial = radial_fit(outer, ring)
    center = outer.mean(axis=0)
    baseline = center + 0.61 * (outer - center)
    actual_inner = baseline * (1 - SOURCE_BLEND) + radial * SOURCE_BLEND
    top = np.column_stack((outer, np.full(64, 230.0)))
    inner = np.column_stack((actual_inner, np.full(64, Z_INNER)))
    spoke = np.linalg.norm(top - inner, axis=1)
    inners = np.linalg.norm(inner - np.roll(inner, -1, axis=0), axis=1)
    options = []
    for ratio in np.arange(0.40, 0.801, 0.01):
        uv_inner = center_uv + ratio * (outer_uv - center_uv)
        mat_spoke = np.linalg.norm(outer_uv - uv_inner, axis=1)
        mat_inner = np.linalg.norm(uv_inner - np.roll(uv_inner, -1, axis=0), axis=1)
        if min(mat_spoke.min(), mat_inner.min()) < 0.25:
            continue
        stretch = np.concatenate(
            (abs(spoke / mat_spoke - 1), abs(inners / mat_inner - 1))
        )
        options.append((float(np.percentile(stretch, 95)), float(stretch.max()),
                        float(ratio), uv_inner))
    if not options:
        raise ValueError("no valid nonzero material ring")
    p95, worst, ratio, flat = min(options, key=lambda item: item[:2])
    if p95 > 0.105 or worst > 0.15:
        raise ValueError("original source top crown creates too much material strain")
    return actual_inner, flat, ratio, p95 * 100, worst * 100


def _packed_old_faces(data):
    output = []
    cursor = 0
    for count, color in zip(data["face_lengths"], data["face_material_roles"]):
        face = tuple(int(i) for i in data["face_vertex_ids"][cursor:cursor + int(count)])
        output.append((face, int(color)))
        cursor += int(count)
    if cursor != len(data["face_vertex_ids"]):
        raise ValueError("source R3 face stream is truncated")
    return output


def _new_crown_topology(old, old_cap_outer, tip, start):
    cap_vertices = set(int(i) for i in old_cap_outer) | {tip}
    caps = {i for i, (face, _) in enumerate(old) if set(face) <= cap_vertices}
    if len(caps) != 64:
        raise ValueError("R3 expected exactly one original 64-face cap fan")
    result = [row for i, row in enumerate(old) if i not in caps]
    for i in range(64):
        next_i = (i + 1) % 64
        a, b = int(old_cap_outer[i]), int(old_cap_outer[next_i])
        c, d = start + next_i, start + i
        result.extend([((a, b, c, d), 1), ((d, c, tip), 1)])
    if len(result) != 2054:
        raise ValueError("reviewed 2054-face R4 topology changed")
    return result


def _revise(data, source):
    xyz = data["initial_3d_prepositioned_vertices_m"]
    uv = data["true_independent_flat_2d_rest_xy_m"]
    outer_ids = np.arange(CAP_START, CAP_START + 64)
    tip = CAP_START + 64
    crown230, count230 = _source_central(source, 230)
    crown234, count234 = _source_central(source, Z_INNER)
    inner, flat, ratio, p95, worst = _crown_material(
        xyz[outer_ids, :2] * 1000,
        uv[outer_ids] * 1000,
        uv[tip] * 1000,
        crown234,
    )
    augmented_xyz = np.vstack(
        (xyz, np.column_stack((inner, np.full(64, Z_INNER))) / 1000)
    )
    augmented_uv = np.vstack((uv, flat / 1000))
    faces = _new_crown_topology(_packed_old_faces(data), outer_ids, tip, len(xyz))
    if augmented_xyz.shape != (2699, 3):
        raise ValueError("R4 true upper source panel vertex topology changed")
    return augmented_xyz, augmented_uv, faces, {
        "central_source_230_mm_area": float(crown230.area),
        "central_source_234_mm_area": float(crown234.area),
        "three_real_source_loops_at_230_and_234": count230 == count234 == 3,
        "gradual_crown_source_blend": SOURCE_BLEND,
        "new_crown_inner_z_mm": Z_INNER,
        "rest_ring_scale": ratio,
        "crown_new_internal_strain_p95_pct": p95,
        "crown_new_internal_strain_max_pct": worst,
    }


def generate(stage, source, output):
    data, mesh = _read_pinned(stage, source)
    xyz, rest, faces, meta = _revise(data, mesh)
    old = data["initial_3d_prepositioned_vertices_m"]
    if not np.array_equal(old, xyz[:2635]):
        raise ValueError("R3 actual source preposition was modified")
    if not np.array_equal(
        data["true_independent_flat_2d_rest_xy_m"], rest[:2635]
    ):
        raise ValueError("R3 flat material seams were modified")
    output = Path(output)
    if output.is_symlink() or (output.exists() and any(output.iterdir())):
        raise FileExistsError("cannot overwrite previous R4 scientific result")
    output.mkdir(parents=True, exist_ok=True)
    result = output / "R4_2D_REST_AND_3D_PREPOSITION_NOT_SIMULATED.npz"
    np.savez_compressed(
        result,
        initial_3d_prepositioned_vertices_m=xyz,
        true_independent_flat_2d_rest_xy_m=rest,
        original_sewing_spring_vertex_pairs=data["original_sewing_spring_vertex_pairs"],
        face_lengths=np.asarray([len(face) for face, _ in faces], dtype=np.int32),
        face_vertex_ids=np.asarray([i for face, _ in faces for i in face], dtype=np.int32),
        face_material_roles=np.asarray([role for _, role in faces], dtype=np.int8),
    )
    report = {
        "schema": "stage6-r4-source-crown-24-panel-2d-study-v1",
        "source_proxy_SHA256": SOURCE_SHA,
        "R3_original_stage_SHA256": R3_SHA,
        "R4_new_stage_SHA256": _hash(result),
        "original_24_2d_panels_remain": True,
        "old_986_sewing_springs_unchanged": True,
        "old_2635_vertices_and_2d_netline_unchanged": True,
        "new_3d_material_vertices": 64,
        "new_total_vertices": len(xyz),
        "new_total_polygons": len(faces),
        "side_ear_protrusions_physically_sewn": False,
        "Blender_R4_real_frame_not_yet_evaluated": True,
        "factory_patterns_approved": 0,
        **meta,
    }
    (output / "R4_SOURCE_CROWN_QA.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("r3", "source", "out"):
        parser.add_argument("--" + field, required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(generate(args.r3, args.source, args.out), ensure_ascii=False))


if __name__ == "__main__":
    main()
