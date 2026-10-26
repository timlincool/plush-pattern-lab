"""Render saved Blender cloth geometry and highlight REAL finite intersection witnesses.

A diagnostic rendering of the synthetic model; NOT an artistic reconstruction
of the private original design or a production/manufacturing demonstration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

from plush_pattern_lab.validation.preview_evidence import verify_snapshot

SNAPSHOT = "CAP_FINAL_SHAPE_NOT_MANUFACTURING"
TRIAL_SOURCE = "EXPERIMENT_EXPLICIT_CAP_SEWING_NOT_PRODUCTION"
PALETTE = (
    (0.26, 0.46, 0.54),
    (0.22, 0.39, 0.51),
    (0.32, 0.51, 0.46),
    (0.28, 0.37, 0.51),
)
VIEWPOINTS = {
    "three_quarter": ((0.31, -0.35, 0.22), (0.0, 0.0, 0.0), 0.195),
    "side": ((0.36, 0.01, 0.12), (0.0, 0.0, 0.0), 0.195),
    "lower_join": ((0.16, -0.25, -0.25), (0.0, 0.0, -0.047), 0.135),
}


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _material(name: str, rgb: tuple[float, float, float]):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*rgb, 1.0)
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (*rgb, 1.0)
    principled.inputs["Roughness"].default_value = 0.82
    return material


def _apply_colors(snapshot, trial: dict, intersection: dict) -> None:
    mesh = snapshot.data
    faces = trial["total_face_count"]
    n = trial["panels"]
    gores = trial["gore_face_count"]
    if len(mesh.polygons) != faces or gores % n:
        raise RuntimeError("Saved mesh face identities disagree with trusted trial")
    for color in PALETTE:
        mesh.materials.append(_material("SYNTHETIC_BODY", color))
    mesh.materials.append(_material("UPPER_CAP", (0.72, 0.43, 0.18)))
    mesh.materials.append(_material("LOWER_CAP", (0.30, 0.37, 0.52)))
    mesh.materials.append(_material("BVH_CROSSING_FACE", (0.85, 0.02, 0.12)))
    faces_per_gore = gores // n
    for face in mesh.polygons:
        if face.index < gores:
            face.material_index = (face.index // faces_per_gore) % len(PALETTE)
        else:
            face.material_index = len(PALETTE) + int(face.index >= gores + n)
        face.use_smooth = True
    mesh.calc_loop_triangles()
    marked: set[int] = set()
    for item in intersection["localization"]["witnesses"]["other"]:
        for triangle_id in item["triangle_indices"]:
            marked.add(mesh.loop_triangles[triangle_id].polygon_index)
    snapshot["SYNTHETIC_COLLISION_DIAGNOSTIC"] = len(marked)


def _camera(scene, position: tuple, target: tuple, scale: float) -> None:
    camera = bpy.data.objects.get("SYNTHETIC_INSPECTION_CAMERA")
    if camera is None:
        camera = bpy.data.objects.new(
            "SYNTHETIC_INSPECTION_CAMERA", bpy.data.cameras.new("inspection")
        )
        scene.collection.objects.link(camera)
    camera.location = position
    vector = Vector(target) - camera.location
    camera.rotation_euler = vector.to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = scale
    scene.camera = camera


def _lighting(scene) -> None:
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 720
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "Medium High Contrast"
    scene.view_settings.exposure = -0.35
    scene.world = bpy.data.worlds.new("SYNTHETIC_INSPECTION_WORLD")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.77, 0.84, 0.91, 1.0)
    background.inputs["Strength"].default_value = 0.40
    light = bpy.data.lights.new("SYNTHETIC_INSPECTION_SOFTBOX", "AREA")
    light.energy = 9
    light.shape = "DISK"
    light.size = 0.32
    obj = bpy.data.objects.new("SYNTHETIC_INSPECTION_SOFTBOX", light)
    obj.location = (0.24, -0.20, 0.31)
    scene.collection.objects.link(obj)


def _render_views(
    scene, snapshot, output: Path, trial: dict, intersection: dict
) -> list[str]:
    all_images = []
    diagnostic_faces: set[int] = set()
    mesh = snapshot.data
    for item in intersection["localization"]["witnesses"]["other"]:
        for idx in item["triangle_indices"]:
            diagnostic_faces.add(mesh.loop_triangles[idx].polygon_index)
    original_colors = [face.material_index for face in mesh.polygons]
    for name, (position, target, scale) in VIEWPOINTS.items():
        if name == "lower_join":
            for face in mesh.polygons:
                if face.index in diagnostic_faces:
                    face.material_index = len(PALETTE) + 2
        _camera(scene, position, target, scale)
        out = output / f"{name}.png"
        scene.render.filepath = str(out)
        bpy.ops.render.render(write_still=True)
        if not out.is_file() or out.stat().st_size < 15000:
            raise RuntimeError(f"Blender diagnostic view was not written: {name}")
        all_images.append(out.name)
        for face, material_id in zip(mesh.polygons, original_colors):
            face.material_index = material_id
    return all_images


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("input", "simulation-report", "triangle-report", "output-dir"):
        parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    if any(
        not path.is_file()
        for path in (args.input, args.simulation_report, args.triangle_report)
    ):
        raise RuntimeError("Missing a required trusted synthetic trial file")
    if args.output_dir.exists() or args.output_dir.is_symlink():
        raise RuntimeError("Refusing to overwrite a prior diagnostic render")
    trial_bytes = args.simulation_report.read_bytes()
    trial = json.loads(trial_bytes)
    intersection = json.loads(args.triangle_report.read_text(encoding="utf-8"))
    evidence = verify_snapshot(
        trial,
        intersection,
        blend_sha=_hash(args.input),
        trial_sha=hashlib.sha256(trial_bytes).hexdigest(),
    )
    bpy.ops.wm.open_mainfile(filepath=str(args.input.resolve()), load_ui=False)
    snapshot = bpy.data.objects.get(SNAPSHOT)
    if snapshot is None or snapshot.type != "MESH":
        raise RuntimeError("Expected exact final synthetic cloth snapshot")
    if len(snapshot.data.vertices) != trial["vertices"]:
        raise RuntimeError("Actual mesh vertex count differs from the trusted trial")
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj != snapshot:
            obj.hide_render = True
    _apply_colors(snapshot, trial, intersection)
    _lighting(bpy.context.scene)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    views = _render_views(
        bpy.context.scene, snapshot, args.output_dir, trial, intersection
    )
    evidence["render_views"] = views
    evidence["render_view_centers_are_aligned_to_synthetic_origin"] = True
    (args.output_dir / "manifest.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        "SAVED_SYNTHETIC_PREVIEW",
        json.dumps(
            {
                "status": evidence["status"],
                "views": views,
                "nonseam_intersections": evidence["finite_nonseam_intersections"],
                "annotated_faces": snapshot["SYNTHETIC_COLLISION_DIAGNOSTIC"],
            }
        ),
    )


if __name__ == "__main__":
    main()
