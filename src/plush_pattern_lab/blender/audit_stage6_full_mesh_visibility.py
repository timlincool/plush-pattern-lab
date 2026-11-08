"""Read-only BVH front/back/left/right/top source-seam visibility audit.

The source is always the verified public Stage6 Blender 4.3.2 file, never an
outside PR's model. Audits 41 raw product Mesh objects; excludes the floor.
Hair curves, evaluated modifiers and final design alignment remain unknown.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from plush_pattern_lab.blender.audit_hoof_interfaces import (
    BODY,
    build_report,
    sha256_file,
)
from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256
from plush_pattern_lab.validation.full_scene_seam_visibility import (
    VIEWS,
    classify_first_surface,
    count_scene_view,
    verified_scene_registry,
)

EXPECTED_PROXY_SHA = "5b52e3fd09c83b19c5b9d95d6d8d859a147ff4deef90f1518f868d2e82e3a2dd"
PRIOR_SCHEMA = "stage6-pinned-source-front-shell-historical-face-v14-review-v1"
RESEARCH_MM_TOLERANCE = 0.7


def _checked_scene_registry(registry):
    counts = {
        obj.name: len(obj.data.polygons)
        for obj in bpy.data.objects
        if obj.type == "MESH"
    }
    roles = verified_scene_registry(registry, counts)
    if registry.get("source_sha256") != SOURCE_SHA256 or BODY not in roles:
        raise ValueError("unrecognized original Stage6 scene or main shell")
    return roles


def _mesh_bvh(obj, role):
    mesh = obj.data
    mesh.calc_loop_triangles()
    vertices = np.asarray(
        [tuple(obj.matrix_world @ vert.co) for vert in mesh.vertices],
        dtype=np.float64,
    )
    if vertices.ndim != 2 or vertices.shape[1] != 3:
        raise ValueError("missing real Blender product Mesh vertices")
    if not np.isfinite(vertices).all():
        raise ValueError("nonfinite original Stage6 Mesh vertex coordinates")
    triangles = [tuple(int(i) for i in tri.vertices) for tri in mesh.loop_triangles]
    if not triangles:
        raise ValueError("stage6 product Mesh cannot be empty")
    tree = BVHTree.FromPolygons(
        [tuple(v) for v in vertices], triangles, all_triangles=True, epsilon=0.0
    )
    return {
        "name": obj.name,
        "role": role,
        "tree": tree,
        "bounds": np.stack((vertices.min(axis=0), vertices.max(axis=0))),
        "triangles": len(triangles),
        "polygons": len(mesh.polygons),
        "in_active_scene": bpy.context.scene.objects.get(obj.name) is not None,
        "hidden_from_render": bool(obj.hide_render),
        "mesh_modifiers_not_evaluated": True,
    }


def _object_bvh_cache(roles):
    rows = [
        _mesh_bvh(bpy.data.objects[name], role) for name, role in sorted(roles.items())
    ]
    if len(rows) != 41:
        raise ValueError("expected 41 original Stage6 product Mesh BVH candidates")
    bounds = np.stack([row["bounds"] for row in rows])
    global_bounds = np.stack((bounds[:, 0].min(axis=0), bounds[:, 1].max(axis=0)))
    return rows, global_bounds


def _ray_object(record, origin, direction, max_distance, transverse_axes):
    bbox = record["bounds"]
    uv = np.asarray(origin)[list(transverse_axes)]
    if np.any(uv < bbox[0, list(transverse_axes)] - 1e-9) or np.any(
        uv > bbox[1, list(transverse_axes)] + 1e-9
    ):
        return None
    position, _, _, distance = record["tree"].ray_cast(origin, direction, max_distance)
    if position is None:
        return None
    return position, float(distance)


def _closest_hit(records, point_xyz_mm, view, bounds):
    _, axis, sign, transverse = view
    point = np.asarray(point_xyz_mm, dtype=np.float64) / 1000
    near = bounds[0, axis] - 0.025 if sign == 1 else bounds[1, axis] + 0.025
    ray = point.copy()
    ray[axis] = near
    direction = Vector(tuple(float(sign) if i == axis else 0.0 for i in range(3)))
    start = Vector(tuple(ray))
    max_distance = float(bounds[1, axis] - bounds[0, axis] + 0.05)
    nearest = None
    for record in records:
        match = _ray_object(record, start, direction, max_distance, transverse)
        if match is None:
            continue
        hit, distance = match
        if nearest is None or distance < nearest["distance"]:
            nearest = {
                "distance": distance,
                "object": record["name"],
                "role": record["role"],
                "xyz_mm": (np.asarray(hit) * 1000).tolist(),
                "in_active_scene": record["in_active_scene"],
                "hidden_from_render": record["hidden_from_render"],
            }
    return nearest


def _sample_one_path(records, bounds, prior, view):
    name, axis, sign, _ = view
    path_id = int(prior["path_id"])
    ids = prior["source_vertex_ids"]
    coords = prior["source_points_xyz_mm"]
    if len(ids) < 2 or len(ids) != len(coords):
        raise ValueError("invalid prior current-run source path")
    alerts = {
        int(row["source_vertex_id"])
        for row in prior["historic_face_proximity_witnesses"]
    }
    samples = []
    for vertex_id, xyz in zip(ids, coords):
        hit = _closest_hit(records, xyz, view, bounds)
        status = classify_first_surface(
            xyz,
            None if hit is None else hit["xyz_mm"],
            None if hit is None else hit["role"],
            axis,
            sign,
            RESEARCH_MM_TOLERANCE,
        )
        samples.append(
            {
                "original_source_vertex_id": int(vertex_id),
                "original_source_xyz_mm": xyz,
                "first_product_mesh": None if hit is None else hit["object"],
                "first_product_group": None if hit is None else hit["role"],
                "first_product_hit_xyz_mm": None if hit is None else hit["xyz_mm"],
                "first_product_in_active_scene": (
                    None if hit is None else hit["in_active_scene"]
                ),
                "first_product_hidden_from_render": (
                    None if hit is None else hit["hidden_from_render"]
                ),
                "historic_face_v14_alert": name == "front" and vertex_id in alerts,
                **status,
            }
        )
    result = count_scene_view(samples)
    result.update(
        {
            "view": name,
            "path_id": path_id,
            "source_3d_length_mm": prior["source_3d_seam_length_mm"],
            "source_vertex_ids_exactly_preserved": True,
            "first_hit_product_mesh_counts": dict(
                sorted(
                    Counter(s["first_product_mesh"] for s in samples).items(),
                    key=lambda item: str(item[0]),
                )
            ),
            "historic_v14_alert_samples": [
                s for s in samples if s["historic_face_v14_alert"]
            ],
            "samples": samples,
        }
    )
    return result


def _audit_all_views(cache, bounds, prior):
    paths = prior["routes"]
    if [len(r["source_vertex_ids"]) for r in paths] != [33, 143, 132]:
        raise ValueError("verified B source path vertex IDs changed")
    return [
        {
            "view": view[0],
            "paths": [_sample_one_path(cache, bounds, row, view) for row in paths],
        }
        for view in VIEWS
    ]


def _validated_inputs(blend_path, digest, report, registry):
    if digest != SOURCE_SHA256:
        raise ValueError("wrong original public Stage6 Blend SHA")
    if (
        report.get("schema") != PRIOR_SCHEMA
        or report.get("candidate") != "B_three_disks"
        or report.get("source_original_blend_sha256") != digest
        or report.get("source_proxy_ply_sha256") != EXPECTED_PROXY_SHA
    ):
        raise ValueError("missing same-run pinned source B face review")
    if (
        registry.get("source_sha256") != digest
        or not blend_path.is_file()
        or blend_path.is_symlink()
        or blend_path.suffix != ".blend"
    ):
        raise ValueError("unverified original public Stage6 scene")
    if sha256_file(blend_path) != digest:
        raise ValueError("untrusted original Stage6 Blend bytes")


def _report(roles, cache, bounds, prior):
    return {
        "schema": "stage6-original-full-41-product-mesh-source-seam-occlusion-v1",
        "status": "RESEARCH_REAL_MESH_VISIBILITY_NOT_FACTORY_APPROVAL",
        "source_blend_sha256": SOURCE_SHA256,
        "source_proxy_25_percent_sha256": EXPECTED_PROXY_SHA,
        "original_b_source_paths_sha256": prior["source_multidisk_summary_sha256"],
        "historical_face_v14_sha256": prior["historical_face_reference_sha256"],
        "blender_version": bpy.app.version_string,
        "all_source_meshes_including_studio_floor": 42,
        "product_meshes_raytested": len(cache),
        "excluded_studio_floor_count": 1,
        "original_other_curve_objects_not_raycasted": sum(
            obj.type in ("CURVE", "CURVES") for obj in bpy.data.objects
        ),
        "product_mesh_roles": dict(sorted(Counter(roles.values()).items())),
        "product_meshes_unlinked_to_active_scene": [
            x["name"] for x in cache if not x["in_active_scene"]
        ],
        "product_meshes_with_render_hide": [
            x["name"] for x in cache if x["hidden_from_render"]
        ],
        "world_product_bounds_mm": (bounds * 1000).round(3).tolist(),
        "only_raw_unmodified_Mesh_triangles_tested": True,
        "not_render_visibility_or_sewn_structure_proof": True,
        "not_fur_hair_or_material_simulation": True,
        "ray_depth_tolerance_mm_research": RESEARCH_MM_TOLERANCE,
        "view_results": _audit_all_views(cache, bounds, prior),
        "approved_for_manufacturer_cutting": False,
        "factory_tech_pack_complete": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--prior", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    if bpy.app.version[:3] != (4, 3, 2):
        raise ValueError("Stage6 audit requires Blender 4.3.2")
    if (
        args.output.suffix != ".json"
        or args.output.exists()
        or args.output.is_symlink()
        or not args.prior.is_file()
        or not args.registry.is_file()
    ):
        raise ValueError("missing review inputs or used JSON evidence path")
    prior = json.loads(args.prior.read_text(encoding="utf8"))
    registry = json.loads(args.registry.read_text(encoding="utf8"))
    _validated_inputs(args.input, args.source_sha256, prior, registry)
    bpy.ops.wm.open_mainfile(filepath=str(args.input.resolve()), load_ui=False)
    hoof = build_report(args.source_sha256)
    if not hoof["all_geometry_interfaces_match"]:
        raise ValueError("original four-hoof 3D interface verification failed")
    roles = _checked_scene_registry(registry)
    cache, bounds = _object_bvh_cache(roles)
    report = _report(roles, cache, bounds, prior)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(
        "STAGE6_COMPLETE_41_MESH_SEAM_OCCLUSION",
        json.dumps(
            {
                "meshes": len(cache),
                "curves_not_raytested": report[
                    "original_other_curve_objects_not_raycasted"
                ],
                "front": [
                    {
                        "path": x["path_id"],
                        "first_meshes": x["first_hit_product_mesh_counts"],
                        "geometry_classification": x["classifications"],
                        "historic_face_alerts": len(x["historic_v14_alert_samples"]),
                    }
                    for x in report["view_results"][0]["paths"]
                ],
                "manufacturer_cutting_approved": False,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
