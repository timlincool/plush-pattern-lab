"""Real Blender Cloth sewing of source-linked Stage6 B 24-piece *research* toile.

All displayed sewn vertices come from evaluated Blender Cloth, never image AI.
Original Stage6 is only a visual comparison and source-informed prepositioning.
The 24 pieces use surrogate rest patterns, no fur, actual fill or approved BOM.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

SOURCE_SHA = "38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a"
SCHEMA = "stage6-b-24piece-same-source-real-Blender-Cloth-sewn-preview-v1"
SOURCE_UPPER = "stage6-separated-torso-headneck-mother-trial-ab-v1"
SOURCE_LOWER = "stage6-source-hoof-anchored-lower-mother-toile-v1"
GRAPH_SCHEMA = "stage6-split-head-torso-24piece-panel-interface-trial-v1"
FOOTS = ("FL", "FR", "RL", "RR")
COLORS = (
    (0.83, 0.82, 0.74),
    (0.96, 0.90, 0.80),
    (0.78, 0.81, 0.86),
    (0.76, 0.75, 0.79),
)
VIEWS = (
    ("three_quarter", (1.6, -2.3, 1.25)),
    ("side", (2.7, 0.03, 1.20)),
    ("front", (0.03, -2.7, 1.0)),
)


def _read(args):
    if bpy.app.version[:3] != (4, 3, 2):
        raise ValueError("only pinned original Blender 4.3.2 supported")
    for path in (args.upper, args.lower, args.graph, args.original, args.yoke_mesh):
        if not path.is_file() or path.is_symlink():
            raise ValueError("missing verified Stage6 source or symlinked file")
    if hashlib.sha256(args.original.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError("original public Stage6 Blend SHA differs")
    if args.out.exists() and any(args.out.iterdir()):
        raise ValueError("do not overwrite an earlier physical simulation")
    upper_raw = args.upper.read_bytes()
    lower_raw = args.lower.read_bytes()
    graph_raw = args.graph.read_bytes()
    upper, lower, graph = (json.loads(s) for s in (upper_raw, lower_raw, graph_raw))
    constrained = json.loads(args.yoke_mesh.read_bytes())
    if (
        constrained.get("schema") != "stage6-b24-four-hoof-hole-constrained-yoke-mesh-v1"
        or constrained.get("source_lower_mother_json_sha256")
        != hashlib.sha256(lower_raw).hexdigest()
        or constrained.get("source_2d_fabric_boundaries") != 5
        or constrained.get("original_stitch_loop_boundary_edges") != 320
        or constrained.get("factory_cutting_patterns_approved") != 0
        or len(constrained.get("triangles_local_original_yoke_vertex_ids", [])) != 326
    ):
        raise ValueError("same-run Shapely original four-hoof-hole yoke evidence required")
    lower["_trusted_constrained_yoke_faces"] = constrained[
        "triangles_local_original_yoke_vertex_ids"
    ]
    variant = next(
        (x for x in upper.get("options", []) if x["name"] == "B_integrated_neck_port"),
        None,
    )
    if (
        upper.get("schema") != SOURCE_UPPER
        or lower.get("schema") != SOURCE_LOWER
        or graph.get("schema") != GRAPH_SCHEMA
        or variant is None
        or graph.get("variant") != "B_integrated_neck_port"
        or graph.get("total_research_pieces") != 24
        or graph.get("numerically_paired_interface_count") != 46
        or graph.get("factory_cut_patterns_approved") != 0
        or len(variant["torso_gore_pieces"]) != 4
        or len(variant["headneck_gore_pieces"]) != 4
        or len(lower["outer_quarter_bands"]) != 4
        or len(lower["original_source_hoofs"]) != 4
        or variant.get("industrial_cut_patterns_approved") != 0
        or lower.get("approved_industrial_paper_patterns") != 0
    ):
        raise ValueError("expected same-run actual B24 research seam contract")
    return (
        variant,
        lower,
        graph,
        {
            "upper_sha256": hashlib.sha256(upper_raw).hexdigest(),
            "lower_sha256": hashlib.sha256(lower_raw).hexdigest(),
            "graph_sha256": hashlib.sha256(graph_raw).hexdigest(),
            "original_blend_sha256": SOURCE_SHA,
        },
    )


class MeshBuilder:
    def __init__(self):
        self.xyz = []
        self.rest = []
        self.faces = []
        self.face_color = []
        self.springs = []
        self.spring_pairs = set()
        self.parts = []
        self.seam_kinds = Counter()

    def patch(self, name, xyz, rest, faces, role):
        if len(xyz) != len(rest) or len(xyz) < 3 or not faces:
            raise ValueError("invalid genuine research 2D panel surface")
        xyz = np.asarray(xyz, dtype=float)
        rest = np.asarray(rest, dtype=float)
        if xyz.shape[1] != 3 or rest.shape[1] != 2:
            raise ValueError("invalid 3D placement / 2D material coordinates")
        if not np.isfinite(xyz).all() or not np.isfinite(rest).all():
            raise ValueError("nonfinite real pattern coordinates")
        start = len(self.xyz)
        self.xyz.extend((xyz * 0.001).tolist())
        stride = len(self.parts)
        shift = np.asarray(((stride % 6) * 0.38, (stride // 6) * 0.38))
        self.rest.extend((rest * 0.001 + shift).tolist())
        for face in faces:
            if len(set(face)) != len(face):
                raise ValueError("degenerate trial piece face")
            if min(face) < 0 or max(face) >= len(xyz):
                raise ValueError("trial piece face outside indexed material polygon")
            self.faces.append([start + int(i) for i in face])
            self.face_color.append(role)
        self.parts.append(
            {"id": name, "vertex_count": len(xyz), "face_count": len(faces)}
        )
        return [start + i for i in range(len(xyz))]

    def seam(self, first, second, kind):
        if len(first) != len(second) or len(first) < 2:
            raise ValueError("not an equal-index real 2D sewing boundary")
        p = np.asarray(self.xyz)
        direct = np.linalg.norm(p[first] - p[second], axis=1).sum()
        reverse = np.linalg.norm(p[first] - p[second[::-1]], axis=1).sum()
        ends = second if direct <= reverse else second[::-1]
        for a, b in zip(first, ends):
            if a == b:
                raise ValueError("sewing spring was not an interpanel boundary")
            edge = tuple(sorted((int(a), int(b))))
            if edge not in self.spring_pairs:
                self.spring_pairs.add(edge)
                self.springs.append(edge)
        self.seam_kinds[kind] += 1


def _grid(builder, name, xyz, rest, role):
    positions = np.asarray(xyz)
    planar = np.asarray(rest)
    if positions.shape[:2] != planar.shape[:2]:
        raise ValueError("sewing gore station/rest counts differ")
    rows, columns = positions.shape[:2]
    faces = [
        (
            j * columns + k,
            (j + 1) * columns + k,
            (j + 1) * columns + k + 1,
            j * columns + k + 1,
        )
        for j in range(rows - 1)
        for k in range(columns - 1)
    ]
    flat = builder.patch(
        name, positions.reshape(-1, 3), planar.reshape(-1, 2), faces, role
    )
    grid = np.asarray(flat).reshape(rows, columns)
    return {
        "top": grid[-1].tolist(),
        "bottom": grid[0].tolist(),
        "left": grid[:, 0].tolist(),
        "right": grid[:, -1].tolist(),
    }


def _gores(builder, pieces, rings, heights, role):
    geom = np.asarray(rings, dtype=float)
    z = np.asarray(heights, dtype=float)
    if geom.shape != (len(z), 64, 2):
        raise ValueError("Stage6 real 64-station source-envelope profile changed")
    center = geom.mean(axis=1)
    result = []
    for i, piece in enumerate(pieces):
        xyz, planar = [], []
        left = np.asarray(piece["left_stitch_xy_mm"], dtype=float)
        right = np.asarray(piece["right_stitch_xy_mm"], dtype=float)
        if left.shape != (len(z), 2) or right.shape != left.shape:
            raise ValueError("original B24 gore station identity changed")
        for row in range(len(z)):
            arc = geom[row, (i * 16 + np.arange(17)) % 64]
            lengths = np.r_[0, np.cumsum(np.linalg.norm(np.diff(arc, axis=0), axis=1))]
            frac = lengths / lengths[-1]
            coord = np.column_stack((arc, np.full(17, z[row])))
            # Only prepositioning: 2mm radial separation is NOT a source surface.
            direction = arc - center[row]
            norm = np.linalg.norm(direction, axis=1)
            coord[:, :2] += 2 * direction / np.maximum(norm[:, None], 1e-6)
            xyz.append(coord)
            x = left[row, 0] + frac * (right[row, 0] - left[row, 0])
            planar.append(np.column_stack((x, np.full(17, left[row, 1]))))
        result.append(_grid(builder, piece["id"], xyz, planar, role))
    for i in range(4):
        builder.seam(
            result[i]["right"], result[(i + 1) % 4]["left"],
            ("torso" if role == 0 else "headneck") + "_side"
        )
    return result


def _bands(builder, lower, body):
    bottom = np.asarray(lower["yoke"]["outer_stitch_xy_mm"], dtype=float)
    top = np.asarray(body["body_synthetic_rings_xy_mm"][0], dtype=float)
    pieces = []
    for i, band in enumerate(lower["outer_quarter_bands"]):
        idx = (i * 16 + np.arange(17)) % 64
        xyz = [
            np.column_stack((bottom[idx], np.full(17, 60.0))),
            np.column_stack((top[idx], np.full(17, 100.0))),
        ]
        step = np.asarray(band["stitch_bottom_station_x_mm"])
        rest = [
            np.column_stack((step, np.full(17, 0.0))),
            np.column_stack((step, np.full(17, 40.0))),
        ]
        pieces.append(_grid(builder, band["id"], xyz, rest, 0))
    for i in range(4):
        builder.seam(pieces[i]["right"], pieces[(i + 1) % 4]["left"], "band_side")
    return pieces


def _annulus(builder, name, outer, inner, z, role):
    outer, inner = np.asarray(outer), np.asarray(inner)
    if outer.shape != (64, 2) or inner.shape != (64, 2):
        raise ValueError("two original 64-segment shoulder rings needed")
    xyz = np.vstack(
        (
            np.column_stack((outer, np.full(64, z))),
            np.column_stack((inner, np.full(64, z))),
        )
    )
    rest = np.vstack((outer, inner))
    faces = [(i, (i + 1) % 64, 64 + (i + 1) % 64, 64 + i) for i in range(64)]
    ids = builder.patch(name, xyz, rest, faces, role)
    return {"outer": ids[:64], "inner": ids[64:]}


def _top_cap(builder, piece, ring, z):
    xyz_ring = np.asarray(ring)
    rest_ring = np.asarray(piece["outer_stitch_xy_mm"])
    center = xyz_ring.mean(axis=0)
    xyz = np.vstack(
        (
            np.column_stack((xyz_ring, np.full(64, z))),
            [[center[0], center[1], z + 6.0]],
        )
    )
    rest = np.vstack((rest_ring, rest_ring.mean(axis=0)))
    ids = builder.patch(
        piece["id"], xyz, rest, [(64, i, (i + 1) % 64) for i in range(64)], 1
    )
    return ids[:64]


def _collar(builder, piece, lower_ring, upper_ring):
    start = np.asarray(piece["lower_and_upper_stitch_station_x_mm"], dtype=float)
    if start.shape != (65,):
        raise ValueError("not a real 64-station B collar research pattern")
    bottom = np.asarray(lower_ring)
    top = np.asarray(upper_ring)
    xyz = np.stack(
        (
            np.column_stack((bottom[np.arange(65) % 64], np.full(65, 135.0))),
            np.column_stack((top[np.arange(65) % 64], np.full(65, 145.0))),
        )
    )
    rest = np.stack(
        (
            np.column_stack((start, np.zeros(65))),
            np.column_stack((start, np.full(65, 10.0))),
        )
    )
    result = _grid(builder, "COLLAR-TRIAL", xyz, rest, 0)
    builder.seam(result["left"], result["right"], "collar_side")
    return result


def _yoke(builder, lower):
    outer = np.asarray(lower["yoke"]["outer_stitch_xy_mm"], dtype=float)
    holes = [
        np.asarray(lower["yoke"]["source_hoof_holes_stitch_xy_mm"][k], dtype=float)[::8]
        for k in FOOTS
    ]
    if outer.shape != (64, 2) or any(h.shape != (64, 2) for h in holes):
        raise ValueError("original four 512-edge hoof source samples changed")
    xy = np.vstack([outer, *holes])
    faces = lower["_trusted_constrained_yoke_faces"]
    if len(faces) != 326 or any(
        len(face) != 3 or any(not 0 <= int(v) < len(xy) for v in face)
        for face in faces
    ):
        raise ValueError("no same-run four-hoof-hole original source CDT")
    edges = Counter(
        tuple(sorted((int(u), int(v))))
        for face in faces
        for u, v in zip(face, face[1:] + face[:1])
    )
    border = {key for key, count in edges.items() if count == 1}
    want = {
        tuple(sorted((i + offset, (i + 1) % 64 + offset)))
        for offset in (0, 64, 128, 192, 256)
        for i in range(64)
    }
    if (
        border != want
        or set(edges.values()) - {1, 2}
        or len(set(tuple(sorted(face)) for face in faces)) != 326
    ):
        raise ValueError("five original 2D yoke stitch boundaries not preserved")
    ids = builder.patch(
        "YOKE-01",
        np.column_stack((xy, np.full(len(xy), 60.0))),
        xy,
        faces,
        0,
    )
    return {
        "outer": ids[:64],
        "holes": {
            name: ids[64 * (i + 1) : 64 * (i + 2)] for i, name in enumerate(FOOTS)
        },
    }


def _legs(builder, lower):
    sleeves = {}
    for name in FOOTS:
        source = lower["original_source_hoofs"][name]
        ring = np.asarray(source["source_stitch_ring_xy_mm"])[::8]
        if ring.shape != (64, 2) or source["source_original_hoof_edges"] != 512:
            raise ValueError("real original Stage6 hoof did not have 512 vertices")
        segment = np.linalg.norm(np.diff(np.vstack((ring, ring[:1])), axis=0), axis=1)
        stations = np.r_[0.0, np.cumsum(segment)]
        xyz = []
        rest = []
        for elevation, z in enumerate((20.0, 40.0, 60.0)):
            xy = ring[np.arange(65) % 64]
            xyz.append(np.column_stack((xy, np.full(65, z))))
            rest.append(np.column_stack((stations, np.full(65, elevation * 20.0))))
        sleeve = _grid(builder, "LEG-" + name, xyz, rest, 0)
        builder.seam(sleeve["left"], sleeve["right"], "leg_tube_side")
        rest_top = ring
        center = rest_top.mean(axis=0)
        sole_xyz = np.vstack(
            (np.column_stack((ring, np.full(64, 20.0))), [[center[0], center[1], 19.0]])
        )
        sole_rest = np.vstack((ring, center))
        ids = builder.patch(
            "SOLE-" + name,
            sole_xyz,
            sole_rest,
            [(64, i, (i + 1) % 64) for i in range(64)],
            3,
        )
        builder.seam(sleeve["bottom"][:64], ids[:64], "sole_to_leg")
        sleeves[name] = sleeve
    return sleeves


def _assemble(body, lower):
    builder = MeshBuilder()
    bands = _bands(builder, lower, body)
    torso = _gores(
        builder,
        body["torso_gore_pieces"],
        body["body_synthetic_rings_xy_mm"],
        body["body_rings_z_mm"],
        0,
    )
    head = _gores(
        builder,
        body["headneck_gore_pieces"],
        body["head_synthetic_rings_xy_mm"],
        body["head_rings_z_mm"],
        1,
    )
    outer = body["shoulder_cap"]["outer_stitch_xy_mm"]
    inner = body["shoulder_cap"]["upper_head_opening_stitch_xy_mm"][0]
    shoulder = _annulus(builder, "SHOULDER-CAP-TRIAL", outer, inner, 135.0, 0)
    top = _top_cap(
        builder, body["head_top_cap"], body["head_synthetic_rings_xy_mm"][-1], 230.0
    )
    collar = _collar(
        builder,
        body["neck_collar_if_integrated"],
        inner,
        body["head_synthetic_rings_xy_mm"][0],
    )
    yoke = _yoke(builder, lower)
    legs = _legs(builder, lower)
    for i in range(4):
        ring = [(i * 16 + k) % 64 for k in range(17)]
        builder.seam(bands[i]["top"], torso[i]["bottom"], "band_to_torso")
        builder.seam(
            bands[i]["bottom"], [yoke["outer"][k] for k in ring], "band_to_yoke"
        )
        builder.seam(
            torso[i]["top"], [shoulder["outer"][k] for k in ring], "torso_to_shoulder"
        )
        builder.seam(head[i]["top"], [top[k] for k in ring], "head_to_cap")
        builder.seam(
            head[i]["bottom"],
            [collar["top"][k] for k in range(i * 16, i * 16 + 17)],
            "head_to_collar",
        )
    builder.seam(shoulder["inner"], collar["bottom"][:64], "collar_to_shoulder")
    for foot in FOOTS:
        builder.seam(legs[foot]["top"][:64], yoke["holes"][foot], "leg_to_yoke")
    if len(builder.parts) != 24:
        raise ValueError("expected all B 24 independent original trial pieces")
    return builder


def _scene_mesh(builder, frames):
    mesh = bpy.data.meshes.new("B24_ACTUAL_2D_REST_PIECES")
    mesh.from_pydata(builder.xyz, builder.springs, builder.faces)
    mesh.update()
    obj = bpy.data.objects.new("SOURCE_B24_REAL_CLOTH_SEWING_EXPERIMENT", mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    obj.shape_key_add(name="OriginalSourceInspired3DPreposition")
    rest = obj.shape_key_add(name="Actual2DPieceRestCoordinates")
    for i, p in enumerate(builder.rest):
        rest.data[i].co = (p[0], p[1], 0.0)
    for i, color in enumerate(COLORS):
        m = bpy.data.materials.new("Research fabric group " + str(i))
        m.diffuse_color = (*color, 1.0)
        obj.data.materials.append(m)
    for poly, role in zip(obj.data.polygons, builder.face_color):
        poly.material_index = role
    cloth = obj.modifiers.new("BLENDER_43_NATIVE_SEWING_SPRINGS", "CLOTH")
    cloth.settings.rest_shape_key = rest
    cloth.settings.use_sewing_springs = True
    cloth.settings.sewing_force_max = 50.0
    cloth.settings.mass = 0.025 / len(builder.xyz)
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
    return obj, scene


def _run_cloth(builder, frames):
    obj, scene = _scene_mesh(builder, frames)
    pairs = np.asarray(builder.springs, dtype=int)
    original = np.asarray(builder.xyz, dtype=float)
    first_gap = np.linalg.norm(original[pairs[:, 0]] - original[pairs[:, 1]], axis=1)
    latest = None
    deps = bpy.context.evaluated_depsgraph_get()
    started = time.monotonic()
    for frame in range(1, frames + 1):
        scene.frame_set(frame)
        evaluated = obj.evaluated_get(deps)
        trial = evaluated.to_mesh()
        try:
            vec = np.empty(3 * len(trial.vertices), np.float32)
            trial.vertices.foreach_get("co", vec)
            latest = vec.reshape(-1, 3).astype(float)
        finally:
            evaluated.to_mesh_clear()
        if len(latest) != len(original) or not np.isfinite(latest).all():
            raise ValueError("Blender cloth changed topology or yielded nonfinite XYZ")
        if frame % 12 == 0:
            gaps = np.linalg.norm(latest[pairs[:, 0]] - latest[pairs[:, 1]], axis=1)
            print(
                "STAGE6_B24_REAL_CLOTH_FRAME",
                frame,
                "seam_mean_mm",
                float(gaps.mean() * 1000),
                flush=True,
            )
    final_gap = np.linalg.norm(latest[pairs[:, 0]] - latest[pairs[:, 1]], axis=1)
    snapshot = bpy.data.meshes.new("B24_ACTUAL_SOLVER_FRAME")
    snapshot.from_pydata(latest.tolist(), [], builder.faces)
    snap = bpy.data.objects.new("B24_EVALUATED_CLOTH_NOT_A_FACTORY_TOY", snapshot)
    scene.collection.objects.link(snap)
    for material in obj.data.materials:
        snap.data.materials.append(material)
    for polygon, role in zip(snap.data.polygons, builder.face_color):
        polygon.material_index = role
        polygon.use_smooth = True
    obj.hide_render = True
    report = {
        "cloth_solver": "Blender 4.3.2 native Cloth Sewing Springs",
        "original_2D_surrogate_research_pieces": len(builder.parts),
        "original_2D_seam_interface_groups": dict(builder.seam_kinds),
        "physically_connected_sewing_springs": len(builder.springs),
        "vertices": len(builder.xyz),
        "surface_faces": len(builder.faces),
        "simulated_frames": frames,
        "solver_seconds": round(time.monotonic() - started, 2),
        "initial_sewing_spring_gap_mean_mm": float(first_gap.mean() * 1000),
        "final_sewing_spring_gap_mean_mm": float(final_gap.mean() * 1000),
        "final_sewing_spring_gap_max_mm": float(final_gap.max() * 1000),
        "all_original_2D_piece_vertices_baked_from_evaluated_Cloth": True,
        "source_hoof_512_to_64_sampler_used_for_visual_simulation": True,
        "pressure_fill_enabled": False,
        "fabric_self_collision_enabled": False,
        "physically_measured_polyester_filling": False,
        "original_Stage6_visual_target_not_deformation_constraint": True,
        "actual_Stage6_original_face_surface_flattened": False,
        "whole_character_ear_cloud_tail_drop_embroidery_incomplete": True,
        "factory_cutting_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
    }
    return snap, report


def _camera(scene, bounds, direction, tag, out, color_type):
    corners = np.asarray(bounds, dtype=float)
    target = (corners.min(axis=0) + corners.max(axis=0)) / 2
    length = float(np.max(corners.max(axis=0) - corners.min(axis=0)))
    if length <= 1e-5:
        raise ValueError("source/rendered geometry bbox collapsed")
    camera_data = bpy.data.cameras.new("TrueGeometryCamera_" + tag)
    camera = bpy.data.objects.new("TrueGeometryCamera_" + tag, camera_data)
    scene.collection.objects.link(camera)
    pos = np.asarray(direction, dtype=float)
    pos = pos / np.linalg.norm(pos)
    camera.location = tuple(target + pos * 2.8 * length)
    quat = (Vector(target) - camera.location).to_track_quat("-Z", "Y")
    camera.rotation_euler = quat.to_euler()
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = length * 1.45
    scene.camera = camera
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.color_type = color_type
    scene.display.shading.light = "STUDIO"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.render.resolution_x = 760
    scene.render.resolution_y = 760
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(out)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera, do_unlink=True)


def _render_simulated(snap, out):
    scene = bpy.context.scene
    xyz = np.asarray([tuple(v.co) for v in snap.data.vertices])
    for name, direction in VIEWS:
        _camera(
            scene, xyz, direction, name, out / ("sewn_" + name + ".png"), "MATERIAL"
        )


def _render_original(original, out):
    bpy.ops.wm.open_mainfile(filepath=str(original.resolve()), load_ui=False)
    scene = bpy.context.scene
    for obj in bpy.data.objects:
        if obj.type in {"CAMERA", "LIGHT"} or "studio floor" in obj.name.lower():
            obj.hide_render = True
        elif obj.type in {"MESH", "CURVE", "CURVES"}:
            obj.hide_render = False
            name = obj.name.lower()
            if "cloud" in name:
                color = (0.65, 0.64, 0.71, 1)
            elif "pink" in name:
                color = (0.91, 0.66, 0.71, 1)
            elif "hoof" in name:
                color = (0.66, 0.64, 0.69, 1)
            elif "eye" in name or "pupil" in name:
                color = (0.24, 0.20, 0.16, 1)
            else:
                color = (0.90, 0.87, 0.79, 1)
            obj.color = color
    target = bpy.data.objects.get("PRIMARY continuous sculpt | new anatomy")
    if target is None or target.type != "MESH":
        raise ValueError("original Stage6 target main body object missing")
    from mathutils import Vector as V  # noqa: PLC0415

    bbox = np.asarray(
        [tuple(target.matrix_world @ V(corner)) for corner in target.bound_box]
    )
    scene.display.shading.color_type = "OBJECT"
    for name, direction in VIEWS:
        _camera(
            scene, bbox, direction, name, out / ("target_" + name + ".png"), "OBJECT"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("upper", "lower", "graph", "original", "out", "yoke_mesh"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--frames", type=int, default=48)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    if not 24 <= args.frames <= 64:
        raise ValueError("unreviewed Blender Cloth frame budget")
    body, lower, graph, source_sha = _read(args)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    builder = _assemble(body, lower)
    snap, report = _run_cloth(builder, args.frames)
    args.out.mkdir(parents=True, exist_ok=True)
    _render_simulated(snap, args.out)
    # Save only actual solver output; never paint a fake plush image.
    render_obj = snap
    bpy.ops.object.select_all(action="DESELECT")
    render_obj.select_set(True)
    bpy.context.view_layer.objects.active = render_obj
    try:
        bpy.ops.export_scene.gltf(
            filepath=str(args.out / "sewn_cloth.glb"),
            export_format="GLB",
            use_selection=True,
        )
        report["real_solver_mesh_glb_exported"] = True
    except Exception as exc:
        print("OPTIONAL_GLTF_EXPORT_UNAVAILABLE", type(exc).__name__, str(exc))
        report["real_solver_mesh_glb_exported"] = False
    report.update(
        {
            "schema": SCHEMA,
            "original_stage6_input_proof": source_sha,
        "same_run_source_yoke_cdt_SHA256": hashlib.sha256(
            args.yoke_mesh.read_bytes()
        ).hexdigest(),
        "original_five_stitch_boundaries_CDT_GE0S": True,
            "pattern_variant": graph["variant"],
            "status": "RESEARCH_ONLY_REAL_CLOTH_2D_TO_3D_NOT_FINAL_TOY",
            "render_views": [name for name, _ in VIEWS],
        }
    )
    (args.out / "sewing_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf8",
    )
    _render_original(args.original, args.out)
    print(
        "STAGE6_B24_REAL_CLOTH_SIM_COMPLETE",
        json.dumps(
            {
                "pieces": report["original_2D_surrogate_research_pieces"],
                "springs": report["physically_connected_sewing_springs"],
                "initial_mm": report["initial_sewing_spring_gap_mean_mm"],
                "final_mm": report["final_sewing_spring_gap_mean_mm"],
                "filling": False,
                "factory_approved": 0,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
