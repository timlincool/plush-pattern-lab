"""Real Blender 4.3.2 Cloth experiment: detached top/bottom caps + truncated gores.

The rest shape is 2D; 3D target-assisted placement is only an initialization.
This is not a validated fabrication/pressure/stuffing workflow. All pieces
remain independent meshes within one object and connected by loose sewing edges.
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np

from plush_pattern_lab.patterns.ellipsoid_geometry import ellipsoid_normal
from plush_pattern_lab.patterns.transition_profile import cap_offset_weight
from plush_pattern_lab.validation.audit_stitched_shell import inspect_welded_shell
from plush_pattern_lab.validation.sewing_quality import evaluate


def _append_gores(
    n,
    N,
    radial,
    z,
    right,
    verts,
    rest,
    reference,
    faces,
    face_class,
    outward_offset,
    direction,
    radius,
    half_height,
    cap_transition_rows,
):
    for i in range(n):
        az = 2 * math.pi * i / n
        outward = np.array([math.cos(az), math.sin(az), 0.0], dtype=float)
        for j in range(N):
            width = float(right[j, 0])
            yy = float(right[j, 1])
            for slot, x in enumerate((-width, 0.0, width)):
                angle = az + (slot - 1) * math.pi / n
                target = np.array(
                    (radial[j] * math.cos(angle), radial[j] * math.sin(angle), z[j]),
                    dtype=float,
                )
                vector = (
                    ellipsoid_normal(target, radius, half_height)
                    if direction == "normal"
                    else outward
                )
                factor = cap_offset_weight(j, N, cap_transition_rows)
                verts.append(tuple(target + outward_offset * factor * vector))
                reference.append(tuple(target))
                rest.append((x * 0.001 + i * 0.20, yy * 0.001))
        start = i * N * 3
        for j in range(N - 1):
            v = start + 3 * j
            w = v + 3
            faces.append((v, w, w + 1, v + 1))
            face_class.append("gore")
            faces.append((v + 1, w + 1, w + 2, v + 2))
            face_class.append("gore")


def _append_caps(spec, n, H, radial, z, verts, rest, reference, faces, face_class):
    caps = {}
    for position, cap_spec in (
        ("upper", spec["caps"]["upper"]),
        ("lower", spec["caps"]["lower"]),
    ):
        is_top = position == "upper"
        cross_rad = float(radial[0 if is_top else -1])
        cross_z = float(z[0 if is_top else -1])
        center_z = H if is_top else -H
        offset = np.array(
            (n * 0.20 + 0.10 if is_top else n * 0.20 + 0.16, 0.0), dtype=float
        )
        ring = np.asarray(cap_spec["stitch_ring_2d_mm"], dtype=float)
        if ring.shape != (2 * n, 2):
            raise RuntimeError("Caps do not have a 2N stitch polygon")
        center = len(verts)
        verts.append((0.0, 0.0, center_z))
        reference.append((0.0, 0.0, center_z))
        rest.append(tuple(offset))
        ring_indices = []
        for q, uv in enumerate(ring):
            angle = (q - 1) * math.pi / n
            target = (cross_rad * math.cos(angle), cross_rad * math.sin(angle), cross_z)
            idx = len(verts)
            ring_indices.append(idx)
            verts.append(target)
            reference.append(target)
            rest.append(tuple(offset + uv * 0.001))
        for i in range(n):
            r0 = ring_indices[2 * i]
            r1 = ring_indices[2 * i + 1]
            r2 = ring_indices[(2 * i + 2) % (2 * n)]
            if is_top:
                faces.append((center, r0, r1, r2))
            else:
                # Invert bottom winding for an outward-facing lower cap.
                faces.append((center, r2, r1, r0))
            face_class.append(position + "_cap")
        caps[position] = {
            "center_vertex": center,
            "ring_vertices": ring_indices,
            "faces": n,
        }

    return caps


def _pair_seams(n, N, caps, loose, pairs):
    def gore_index(panel, row, slot):
        return (panel * N + row) * 3 + slot

    for i in range(n):
        for j in range(1, N - 1):
            a1 = gore_index(i, j, 2)
            a2 = gore_index((i + 1) % n, j, 0)
            loose.append((a1, a2))
            pairs.append((a1, a2))
        for position, j in (("upper", 0), ("lower", N - 1)):
            indices = caps[position]["ring_vertices"]
            for slot in range(3):
                a1 = gore_index(i, j, slot)
                a2 = indices[(2 * i + slot) % (2 * n)]
                loose.append((a1, a2))
                pairs.append((a1, a2))


def _validate_trial_geometry(n, N, verts, faces, pairs):
    if len(pairs) != n * (N - 2) + 6 * n:
        raise RuntimeError("Incomplete cap and side sewing spring graph")
    arr = np.asarray(verts, dtype=float)
    fa = np.asarray(faces, dtype=int)
    if not np.isfinite(arr).all() or len(arr) > 5000:
        raise RuntimeError("Geometry non-finite or beyond audited scale")
    for f in fa:
        v0, v1, v3 = (arr[f[k]] for k in (0, 1, 3))
        if np.linalg.norm(np.cross(v1 - v0, v3 - v0)) < 1e-12:
            raise RuntimeError("Degenerate initial mesh face at index " + str(f))


def _build_geometry(
    spec, n, N, H, radial, z, right, outward_offset=0.003, direction="radial",
    cap_transition_rows=0
):
    verts, rest, reference, faces, loose, pairs, face_class = [], [], [], [], [], [], []

    _append_gores(
        n,
        N,
        radial,
        z,
        right,
        verts,
        rest,
        reference,
        faces,
        face_class,
        outward_offset,
        direction,
        float(spec["parameters"]["radius_mm"]) * 0.001,
        H,
        cap_transition_rows,
    )
    caps = _append_caps(
        spec, n, H, radial, z, verts, rest, reference, faces, face_class
    )
    # The first/last gore transverse edges now sew into the explicit caps.
    # Side gores are sewn along interior rows; end vertices join via caps.
    _pair_seams(n, N, caps, loose, pairs)
    _validate_trial_geometry(n, N, verts, faces, pairs)
    return verts, rest, reference, faces, loose, pairs, face_class


def _parse_trial():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("spec", "output", "report"):
        p.add_argument("--" + key, type=Path, required=True)
    p.add_argument("--frames", type=int, default=48)
    p.add_argument("--preposition-offset-mm", type=float, default=3.0)
    p.add_argument("--cap-transition-rows", type=int, default=0)
    p.add_argument(
        "--preposition-direction", choices=("radial", "normal"), default="radial"
    )
    p.add_argument(
        "--self-collision",
        action="store_true",
        help="Enable measured finite cloth self-contact proxy",
    )
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    if not a.spec.is_file() or a.output.exists() or a.report.exists():
        raise RuntimeError("Source missing or protected output already exists")
    if not 24 <= a.frames <= 120:
        raise RuntimeError("Frame count outside research bounds")
    if not 0 <= a.cap_transition_rows <= 8:
        raise RuntimeError("Cap transition must use 0..8 rows")
    if (
        not math.isfinite(a.preposition_offset_mm)
        or not 0.5 <= a.preposition_offset_mm <= 8
    ):
        raise RuntimeError("Reference-assisted outward separation must be 0.5..8 mm")
    spec = json.loads(a.spec.read_text(encoding="utf8"))
    if spec.get("schema") != "synthetic-capped-plush-pattern-v1":
        raise RuntimeError("Not a verified capped research pattern")
    par = spec["parameters"]
    n = int(par["panels"])
    N = int(par["segments"]) + 1
    if not (6 <= n <= 24 and 25 <= N <= 257 and len(spec["sewing_pairs"]) == 3 * n):
        raise RuntimeError("Expected N gores + two caps stitch contract")
    H = float(par["half_height_mm"]) * 0.001
    angles = np.asarray(spec["geometry"]["theta_radians"], dtype=float)
    radial = np.asarray(spec["geometry"]["radial_mm"], dtype=float) * 0.001
    z = np.asarray(spec["geometry"]["z_mm"], dtype=float) * 0.001
    left = np.asarray(spec["gore"]["left_stitch_2d_mm"], dtype=float)
    right = np.asarray(spec["gore"]["right_stitch_2d_mm"], dtype=float)
    if any(len(v) != N for v in (angles, radial, z, left, right)):
        raise RuntimeError("Discontinuous source profile")
    if min(radial) <= 0 or abs(left[0, 0] + right[0, 0]) > 1e-10:
        raise RuntimeError("Tip ring is not a symmetric non-zero open section")
    if par["pole_cut_deg"] <= 0:
        raise RuntimeError("Untrimmed zero-radius pole forbidden")
    return a, spec, n, N, H, radial, z, right


def _setup_scene(a, verts, rest, faces, loose):
    mesh = bpy.data.meshes.new("SYNTHETIC_CAPPED_2D_REST_CLOTH")
    mesh.from_pydata(verts, loose, faces)
    mesh.update()
    obj = bpy.data.objects.new("EXPERIMENT_EXPLICIT_CAP_SEWING_NOT_PRODUCTION", mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    obj.shape_key_add(name="TargetAssisted3DPlacement", from_mix=False)
    flat = obj.shape_key_add(name="IndependentFlatRestPieces", from_mix=False)
    for k, p2 in enumerate(rest):
        flat.data[k].co = (p2[0], p2[1], 0.0)
    mod = obj.modifiers.new("ACTUAL_CLOTH_SEWING_SPRINGS", "CLOTH")
    settings = mod.settings
    settings.rest_shape_key = flat
    settings.use_sewing_springs = True
    settings.sewing_force_max = 50.0
    settings.quality = 5
    settings.mass = 0.020 / len(verts)
    settings.tension_stiffness = 15.0
    settings.compression_stiffness = 15.0
    settings.shear_stiffness = 8.0
    settings.bending_stiffness = 0.5
    settings.use_pressure = False
    collision = mod.collision_settings
    collision.use_collision = bool(a.self_collision)
    collision.use_self_collision = bool(a.self_collision)
    if a.self_collision:
        # Blender 4.3.2 uses metres for separation distances; this is an
        # assumed 1mm proxy thickness, NOT measured backing material thickness.
        collision.collision_quality = 3
        collision.distance_min = 0.001
        collision.self_distance_min = 0.001
        collision.self_friction = 5.0
    scene = bpy.context.scene
    scene.gravity = (0, 0, 0)
    scene.frame_start = 1
    scene.frame_end = a.frames
    mod.point_cache.frame_start = 1
    mod.point_cache.frame_end = a.frames
    dep = bpy.context.evaluated_depsgraph_get()

    return obj, collision, scene, dep


def _simulate_frames(a, scene, obj, dep, verts, pairs):
    def gaps(q):
        g = (
            np.linalg.norm(
                q[np.asarray(pairs)[:, 0]] - q[np.asarray(pairs)[:, 1]], axis=1
            )
            * 1000
        )
        return {
            "mean_gap_mm": float(g.mean()),
            "p95_gap_mm": float(np.quantile(g, 0.95)),
            "max_gap_mm": float(g.max()),
        }

    start = np.asarray(verts, dtype=float)
    init = gaps(start)
    final = None
    trail = []
    started = time.monotonic()
    for frame in range(1, a.frames + 1):
        scene.frame_set(frame)
        evaluated = obj.evaluated_get(dep)
        m = evaluated.to_mesh()
        try:
            vec = np.empty(len(m.vertices) * 3, np.float32)
            m.vertices.foreach_get("co", vec)
            xyz = vec.reshape(-1, 3).astype(float)
        finally:
            evaluated.to_mesh_clear()
        if not np.isfinite(xyz).all() or len(xyz) != len(start):
            raise RuntimeError("Non-finite or changing solver topology")
        if frame in (1, 2, 4, 8, 16, 32, a.frames):
            trail.append({"frame": frame, **gaps(xyz)})
        if frame % 16 == 0:
            print("CAPPED_SEW_FRAME", frame, gaps(xyz), flush=True)
        final = xyz
    simulation_elapsed_s = round(time.monotonic() - started, 3)
    end = gaps(final)
    return start, init, final, trail, simulation_elapsed_s, end


def main():
    a, spec, n, N, H, radial, z, right = _parse_trial()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    verts, rest, reference, faces, loose, pairs, face_class = _build_geometry(
        spec,
        n,
        N,
        H,
        radial,
        z,
        right,
        a.preposition_offset_mm * 0.001,
        a.preposition_direction,
        a.cap_transition_rows,
    )
    obj, collision, scene, dep = _setup_scene(a, verts, rest, faces, loose)
    start, init, final, trail, simulation_elapsed_s, end = _simulate_frames(
        a, scene, obj, dep, verts, pairs
    )
    initial_quality = evaluate(
        start, np.asarray(rest), faces, pairs, np.asarray(reference), start
    )
    final_quality = evaluate(
        final, np.asarray(rest), faces, pairs, np.asarray(reference), start
    )
    # Read-only *analytical* seam weld: never overwrite any real Cloth vertices.
    # It verifies graph closure and winding, NOT collision-free sealed material.
    analytical_shell = inspect_welded_shell(final, faces, pairs)
    if end["mean_gap_mm"] >= init["mean_gap_mm"] * 0.95:
        raise RuntimeError("Sewing springs did not close even 5%")
    reversed_samples = final_quality["strain"]["orientation_reversal_samples"]
    cap_face_start = int(sum(x == "gore" for x in face_class))
    report = {
        "status": "ACTUAL_CAPPED_CLOTH_SEWING_RESEARCH_ONLY",
        "source_schema": spec["schema"],
        "blender": bpy.app.version_string,
        "panels": n,
        "separate_caps": 2,
        "gore_face_count": cap_face_start,
        "total_face_count": len(faces),
        "vertices": len(verts),
        "side_stitches": n * (N - 2),
        "cap_stitches": 6 * n,
        "total_sewing_springs": len(pairs),
        "frames": a.frames,
        "gravity": 0,
        "pressure_enabled": False,
        "self_collision_enabled": bool(collision.use_self_collision),
        "collision_assumed_thickness_mm": 1.0 if a.self_collision else None,
        "collision_quality": int(collision.collision_quality)
        if a.self_collision
        else None,
        "solver_elapsed_seconds": simulation_elapsed_s,
        "prepositioning": f"analytic target assisted, gores offset {a.preposition_offset_mm:g}mm",
        "preposition_offset_mm": a.preposition_offset_mm,
        "preposition_direction": a.preposition_direction,
        "cap_transition_rows": a.cap_transition_rows,
        "initial": init,
        "final": end,
        "trace": trail,
        "initial_geometry_quality": initial_quality,
        "final_geometry_quality": final_quality,
        "analytical_stitch_weld_topology": analytical_shell,
        "reversed_face_samples_with_region": [
            {**x, "region": face_class[x["quad_face_index"]]} for x in reversed_samples
        ],
        "not_verified": [
            "Seam vertices are only analytically identified; Blender Cloth remains independent surface pieces",
            "Blender self-collision flag alone cannot prove collision-free cloth; no independent triangle-intersection audit",
            "No physical seal, tested inter-panel contact certification or confirmed fully sewn shell",
            "No measured fabric properties or physically simulated polyester fill",
            "No independent reference reconstruction: initialization uses target",
            "Seam matching and reduction do not establish manufacturability",
        ],
    }
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    snapshot = bpy.data.meshes.new("SYNTHETIC_CAPPED_FINAL_FRAME")
    snapshot.from_pydata(final.tolist(), [], faces)
    snap = bpy.data.objects.new("CAP_FINAL_SHAPE_NOT_MANUFACTURING", snapshot)
    scene.collection.objects.link(snap)
    obj.hide_render = True
    a.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(a.output), compress=True)
    print(
        "CAPPED_SEWING_SOLVER_COMPLETED",
        json.dumps(
            {
                "panels": n,
                "gap": end,
                "shape_rms_mm": final_quality["target_shape"][
                    "rigid_aligned_correspondence_rms_mm"
                ],
                "strain_p95": final_quality["strain"]["p95_abs_principal_strain"],
                "flips": final_quality["strain"]["orientation_reversed_vs_initial"],
                "welded_topology_pass": analytical_shell[
                    "research_topological_sphere_screen_pass"
                ],
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
