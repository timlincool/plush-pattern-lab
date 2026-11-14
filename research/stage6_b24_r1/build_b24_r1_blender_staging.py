"""Rebuild B24 R1 cloth initial 3D placement AND true flat 2D rest coordinates.

The original B24 frame-40 evaluated mesh remains unchanged, never reused as
an R1 physical solution. This outputs reproducible staging for a *future*
Blender 4.3.2 Cloth run, preserving original 974 seam-spring pairs and 24
independent panel topology. All R1 2D rest shapes are genuinely rebuilt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

SNAPSHOT_SHA256 = "e7b890a3dae087df7e1c0d92c05716adcfd098279e5a067519de6a844f31fd8a"
SCALE = 0.001
SHIFTS_STEP = 0.38


def expected_segments():
    names = [f"BAND-{i}" for i in range(1, 5)]
    count = [34] * 4
    names.extend(f"TORSO-{i}" for i in range(1, 5))
    count.extend([68] * 4)
    names.extend(f"HEADNECK-{i}" for i in range(1, 5))
    count.extend([85] * 4)
    names.extend(
        ["SHOULDER-CAP-TRIAL", "HEAD-TOP-CAP-TRIAL", "COLLAR-TRIAL", "YOKE-01"]
    )
    count.extend([128, 65, 130, 320])
    for label in ("FL", "FR", "RL", "RR"):
        names.extend([f"LEG-{label}", f"SOLE-{label}"])
        count.extend([195, 65])
    if sum(count) != 2431 or len(names) != 24:
        raise AssertionError("B24 expected source panels contract broken")
    start = 0
    for i, (n, length) in enumerate(zip(names, count)):
        yield i, n, slice(start, start + length)
        start += length


def grid_rest(piece, rings, start_index):
    left = np.asarray(piece["left_stitch_xy_mm"], float)
    right = np.asarray(piece["right_stitch_xy_mm"], float)
    m = len(rings)
    if left.shape != (m, 2) or right.shape != (m, 2):
        raise ValueError("R1 gore 2D rest sizes invalid")
    per = []
    for row in range(m):
        arc = np.asarray(rings[row])[(np.arange(17) + 16 * start_index) % 64]
        segments = np.linalg.norm(np.diff(arc, axis=0), axis=1)
        fraction = np.r_[0, np.cumsum(segments)] / segments.sum()
        x = left[row, 0] + fraction * (right[row, 0] - left[row, 0])
        per.append(np.column_stack((x, np.full(17, left[row, 1]))))
    return np.asarray(per).reshape(-1, 2)


def grid_preposition(rings, heights, idx):
    centers = np.asarray(rings).mean(axis=1)
    out = []
    for row, z in enumerate(heights):
        arc = np.asarray(rings[row])[(np.arange(17) + 16 * idx) % 64]
        vec = arc - centers[row]
        norm = np.linalg.norm(vec, axis=1)
        xy = arc + 2.0 * vec / np.maximum(norm[:, None], 1e-6)
        out.append(np.column_stack((xy, np.full(17, z))))
    return np.asarray(out).reshape(-1, 3)


def _panel_replacement(name, trial, body, head, bz, hz):
    xy = None
    xyz = None
    if name.startswith("TORSO-"):
        index = int(name[-1]) - 1
        piece = trial["torso_gore_pieces"][index]
        xy = grid_rest(piece, body, index)
        xyz = grid_preposition(body, bz, index)
    elif name.startswith("HEADNECK-"):
        index = int(name[-1]) - 1
        piece = trial["headneck_gore_pieces"][index]
        xy = grid_rest(piece, head, index)
        xyz = grid_preposition(head, hz, index)
    elif name == "SHOULDER-CAP-TRIAL":
        a = body[-1]
        b = head[0]
        xy = np.vstack((a, b))
        xyz = np.column_stack((xy, np.full(128, 135.0)))
    elif name == "HEAD-TOP-CAP-TRIAL":
        ring = head[-1]
        center = ring.mean(axis=0)
        xy = np.vstack((ring, center))
        xyz = np.vstack(
            (np.column_stack((ring, np.full(64, 230.0))), [[*center, 236.0]])
        )
    elif name == "COLLAR-TRIAL":
        station = np.asarray(
            trial["neck_collar_if_integrated"]["lower_and_upper_stitch_station_x_mm"]
        )
        if station.shape != (65,):
            raise ValueError("R1 modified 64 station collar invalid")
        xy = np.vstack(
            (
                np.column_stack((station, np.zeros(65))),
                np.column_stack((station, np.full(65, 10.0))),
            )
        )
        ring = head[0][np.arange(65) % 64]
        xyz = np.vstack(
            (
                np.column_stack((ring, np.full(65, 135.0))),
                np.column_stack((ring, np.full(65, 145.0))),
            )
        )
    return xy, xyz


def _reposition_revised_upper(trial, body, head, bz, hz, initial, rest):
    edited = []
    for stride, name, where in expected_segments():
        xy, xyz = _panel_replacement(name, trial, body, head, bz, hz)
        if xy is not None:
            if xy.shape != (where.stop - where.start, 2) or xyz.shape != (len(xy), 3):
                raise ValueError("R1 panel layout mismatch " + name)
            shift = np.array([(stride % 6) * SHIFTS_STEP, (stride // 6) * SHIFTS_STEP])
            rest[where] = xy * SCALE + shift
            initial[where] = xyz * SCALE
            edited.append(name)
    if len(edited) != 11:
        raise ValueError("expected exactly 11 R1 upper pieces changed")
    if not np.isfinite(rest).all() or not np.isfinite(initial).all():
        raise ValueError("R1 XYZ/rest nonfinite")
    return edited


def _verify_immutable_lower(snapshot_file, initial, rest):
    old_p = np.load(snapshot_file)
    # Every original lower body vertex / 2D material coordinate is byte-value
    # preserved. This is much stronger than preserving an overall body bounding box.
    original_lower_slices = [
        entry[2]
        for entry in expected_segments()
        if entry[1].startswith(("BAND-", "LEG-", "SOLE-")) or entry[1] == "YOKE-01"
    ]
    for sl in original_lower_slices:
        if not np.array_equal(
            initial[sl], old_p["initial_3d_prepositioned_vertices_m"][sl]
        ) or not np.array_equal(
            rest[sl], old_p["true_independent_flat_2d_rest_xy_m"][sl]
        ):
            raise ValueError("source-linked lower panel changed")
    old_p.close()


def _save_revised_staging(
    output_dir, upper_file, initial, rest, flens, fids, colors, springs, edited
):
    # All physical sewing-spring graph edges remain the old approved numeric
    # research references; this is not a weld/closure certification.
    init_gap = (
        np.linalg.norm(initial[springs[:, 0]] - initial[springs[:, 1]], axis=1) * 1000
    )
    if not np.isfinite(init_gap).all():
        raise ValueError("invalid seam endpoints")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_npz = output_dir / "B24_R1_NEW_2D_REST_NEW_3D_PREPOSITION_NOT_SOLVED.npz"
    np.savez_compressed(
        out_npz,
        initial_3d_prepositioned_vertices_m=initial,
        true_independent_flat_2d_rest_xy_m=rest,
        face_lengths=flens,
        face_vertex_ids=fids,
        face_material_roles=colors,
        original_sewing_spring_vertex_pairs=springs,
    )
    triangles = []
    offset = 0
    for n in flens:
        face = fids[offset : offset + n]
        for j in range(1, int(n) - 1):
            triangles.append((face[0], face[j], face[j + 1]))
        offset += int(n)
    mesh = trimesh.Trimesh(vertices=initial, faces=triangles, process=False)
    mesh.visual.face_colors = np.tile([155, 186, 207, 255], (len(triangles), 1))
    out_glb = output_dir / "B24_R1_3D_PREPOSITION_ONLY_UNSIMULATED.glb"
    out_glb.write_bytes(mesh.export(file_type="glb"))
    report = {
        "schema": "B24-R1-source-inspired-preposition-2D-rest-v1",
        "source_snapshot_sha256": SNAPSHOT_SHA256,
        "R1_source_upper_sha256": hashlib.sha256(
            Path(upper_file).read_bytes()
        ).hexdigest(),
        "revised_upper_2d_rest_pieces": edited,
        "total_parts": 24,
        "unmodified_lower_source_linked_pieces": 13,
        "original_interpanel_spring_pairs_preserved": len(springs),
        "old_real_blender_cloth_evaluated_frame_NOT_used_as_new_R1_result": True,
        "mean_initial_spring_endpoint_distance_mm": float(init_gap.mean()),
        "max_initial_spring_endpoint_distance_mm": float(init_gap.max()),
        "preposition_glb_sha256": hashlib.sha256(out_glb.read_bytes()).hexdigest(),
        "stage_npz_sha256": hashlib.sha256(out_npz.read_bytes()).hexdigest(),
        "current_state": "WAITING_FOR_REAL_BLENDER_4_3_2_CLOTH_R1_RUN",
        "factory_patterns_approved": 0,
    }
    (output_dir / "B24_R1_staging_QA.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    return report


def build(snapshot_file, upper_file, output_dir):
    if hashlib.sha256(Path(snapshot_file).read_bytes()).hexdigest() != SNAPSHOT_SHA256:
        raise ValueError(
            "R1 builder SHA mismatch: only accepts verified original B24 frame 40"
        )
    upper = json.loads(Path(upper_file).read_text(encoding="utf8"))
    trial = next(p for p in upper["options"] if p["name"] == "B_integrated_neck_port")
    body = np.asarray(trial["body_synthetic_rings_xy_mm"], float)
    head = np.asarray(trial["head_synthetic_rings_xy_mm"], float)
    bz = np.asarray(trial["body_rings_z_mm"], float)
    hz = np.asarray(trial["head_rings_z_mm"], float)
    if (
        body.shape != (4, 64, 2)
        or head.shape != (5, 64, 2)
        or not np.all(np.isfinite(body))
        or not np.all(np.isfinite(head))
    ):
        raise ValueError("invalid source-linked R1 64-station rings")
    with np.load(snapshot_file, allow_pickle=False) as npz:
        initial = np.array(npz["initial_3d_prepositioned_vertices_m"], dtype=np.float64)
        rest = np.array(npz["true_independent_flat_2d_rest_xy_m"], dtype=np.float64)
        flens = np.array(npz["face_lengths"], dtype=np.int32)
        fids = np.array(npz["face_vertex_ids"], dtype=np.int32)
        colors = np.array(npz["face_material_roles"], dtype=np.int8)
        springs = np.array(npz["original_sewing_spring_vertex_pairs"], dtype=np.int32)
    if (
        initial.shape != (2431, 3)
        or rest.shape != (2431, 2)
        or springs.shape != (974, 2)
    ):
        raise ValueError("old real Cloth source topology not same as R1")
    edited = _reposition_revised_upper(trial, body, head, bz, hz, initial, rest)
    _verify_immutable_lower(snapshot_file, initial, rest)
    return _save_revised_staging(
        output_dir, upper_file, initial, rest, flens, fids, colors, springs, edited
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("snapshot", "upper", "out"):
        p.add_argument("--" + key, required=True, type=Path)
    a = p.parse_args()
    print(json.dumps(build(a.snapshot, a.upper, a.out), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
