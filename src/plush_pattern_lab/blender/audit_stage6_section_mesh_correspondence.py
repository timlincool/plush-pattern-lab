"""Audit true Stage6 z125/z230/z245 contours vs 41 raw product Meshes.

Run only on trusted main Blender 4.3.2 against SHA-locked public Stage6.
No authored hair, design registration, seam strength or cloth is validated.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

from plush_pattern_lab.blender.audit_hoof_interfaces import sha256_file
from plush_pattern_lab.blender.audit_stage6_full_mesh_visibility import (
    EXPECTED_PROXY_SHA,
    RESEARCH_MM_TOLERANCE,
    _checked_scene_registry,
    _closest_hit,
    _object_bvh_cache,
)
from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256
from plush_pattern_lab.validation.full_scene_seam_visibility import (
    SOURCE_MESH,
    VIEWS,
    classify_first_surface,
)
from plush_pattern_lab.validation.stage6_section_mesh_correspondence import (
    AUDIT_SCHEMA,
    SEARCH_RADIUS_MM,
    classify_independent_mesh_neighbors,
    plan_original_contour_samples,
    summarize_loop_observations,
)


def _verify_inputs(args):
    paths = (args.input, args.summary, args.detail, args.registry)
    if (
        args.source_sha256 != SOURCE_SHA256
        or any(not p.is_file() or p.is_symlink() for p in paths)
        or args.output.suffix != ".json"
        or args.output.exists()
        or args.output.is_symlink()
        or args.output.resolve() in {p.resolve() for p in paths}
        or args.input.suffix != ".blend"
    ):
        raise ValueError("untrusted Stage6 input or evidence output overwrite")
    if sha256_file(args.input) != SOURCE_SHA256:
        raise ValueError("original public Stage6 blend SHA mismatch")
    source = json.loads(args.summary.read_text(encoding="utf8"))
    if (
        source.get("schema") != "stage6-real-sculpt-contour-vs-split-A-B-trial-qa-v1"
        or source.get("original_public_blend_sha256") != SOURCE_SHA256
        or source.get("source_25percent_proxy_ply_sha256") != EXPECTED_PROXY_SHA
        or source.get("factory_cutting_approved") != 0
        or source.get("full_original_source_contour_detail_sha256")
        != sha256_file(args.detail)
        or [source.get(f"actual_closed_component_count_{z}") for z in (125, 230, 245)]
        != [2, 3, 2]
    ):
        raise ValueError("original source study not from pinned same-run proxy")
    detail = json.loads(args.detail.read_text(encoding="utf8"))
    registry = json.loads(args.registry.read_text(encoding="utf8"))
    if registry.get("source_sha256") != SOURCE_SHA256:
        raise ValueError("Stage6 41-Mesh registry not pinned to public source")
    return detail, registry


def _independent_neighbor_hits(cache, xyz_mm):
    """Closest actual triangle surfaces inside 6 mm, not BBox-only labels."""
    point = np.asarray(xyz_mm, dtype=np.float64) / 1000.0
    probe = Vector(tuple(point))
    search_m = SEARCH_RADIUS_MM / 1000.0
    neighbors = []
    for mesh in cache:
        if mesh["name"] == SOURCE_MESH:
            continue
        bbox = mesh["bounds"]
        outside = np.maximum(np.maximum(bbox[0] - point, point - bbox[1]), 0)
        if np.linalg.norm(outside) > search_m:
            continue
        location, _, _, distance = mesh["tree"].find_nearest(probe, search_m)
        if location is not None:
            neighbors.append(
                {
                    "mesh": mesh["name"],
                    "group": mesh["role"],
                    "distance_mm": float(round(distance * 1000, 6)),
                    "in_active_scene": mesh["in_active_scene"],
                    "hidden_from_render": mesh["hidden_from_render"],
                }
            )
    return classify_independent_mesh_neighbors(neighbors)


def _five_view_hits(cache, bounds, xyz_mm):
    results = {}
    for view in VIEWS:
        hit = _closest_hit(cache, xyz_mm, view, bounds)
        cls = classify_first_surface(
            xyz_mm,
            None if hit is None else hit["xyz_mm"],
            None if hit is None else hit["role"],
            view[1],
            view[2],
            RESEARCH_MM_TOLERANCE,
        )
        results[view[0]] = {
            "mesh": None if hit is None else hit["object"],
            "group": None if hit is None else hit["role"],
            "mesh_hidden_from_render": (
                None if hit is None else hit["hidden_from_render"]
            ),
            **cls,
        }
    return results


def _audit_section(plan, cache, bounds):
    loops = []
    for loop in plan["loops"]:
        observations = []
        for sample in loop["sampled_source_edges"]:
            xyz = sample["source_xyz_mm"]
            observations.append(
                {
                    **sample,
                    **_independent_neighbor_hits(cache, xyz),
                    "five_view_first_hit": _five_view_hits(cache, bounds, xyz),
                }
            )
        loops.append(summarize_loop_observations(loop, observations))
    return {
        "z_mm": plan["z_mm"],
        "original_closed_loop_count": len(loops),
        "loops": loops,
    }


def _report(detail, registry, summary_path, detail_path, registry_path):
    roles = _checked_scene_registry(registry)
    cache, bounds = _object_bvh_cache(roles)
    plan = plan_original_contour_samples(detail)
    return {
        "schema": AUDIT_SCHEMA,
        "status": "RESEARCH_RAW_3D_MESH_PROXIMITY_NOT_ANATOMICAL_OWNERSHIP",
        "source_original_blend_sha256": SOURCE_SHA256,
        "original_25percent_source_proxy_sha256": EXPECTED_PROXY_SHA,
        "same_run_true_source_summary_sha256": sha256_file(summary_path),
        "same_run_true_source_detail_sha256": sha256_file(detail_path),
        "checked_42_mesh_registry_sha256": sha256_file(registry_path),
        "blender_version": bpy.app.version_string,
        "raw_product_mesh_objects_checked": len(cache),
        "raw_independent_mesh_candidates": len(cache) - 1,
        "studio_floor_excluded": True,
        "original_curve_and_hair_objects_not_tested": sum(
            obj.type in ("CURVE", "CURVES") for obj in bpy.data.objects
        ),
        "original_mesh_modifiers_not_evaluated": True,
        "independent_mesh_bvh_search_radius_mm": SEARCH_RADIUS_MM,
        "four_direction_plus_top_raw_mesh_first_hit": [v[0] for v in VIEWS],
        "sections": [_audit_section(section, cache, bounds) for section in plan],
        "design_inputs_requiring_human_registration": [
            "design/reference-v25/images/original-design.png",
            "design/reference-v25/images/selected-D-appearance.png",
        ],
        "geometry_proximity_not_physical_attachment": True,
        "product_anatomical_role_not_automatically_inferred": True,
        "design_and_fabric_five_view_signoff_pending": True,
        "factory_cutting_patterns_approved": 0,
        "P3_sewn_and_physical_prototype_gate_passed": False,
        "P4_started": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--detail", required=True, type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    if bpy.app.version[:3] != (4, 3, 2):
        raise ValueError("requires pinned Blender 4.3.2")
    detail, registry = _verify_inputs(args)
    bpy.ops.wm.open_mainfile(filepath=str(args.input.resolve()), load_ui=False)
    report = _report(detail, registry, args.summary, args.detail, args.registry)
    if report["raw_product_mesh_objects_checked"] != 41 or [
        s["original_closed_loop_count"] for s in report["sections"]
    ] != [2, 3, 2]:
        raise ValueError("original Stage6 component or product Mesh count changed")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(
        "STAGE6_3D_SECTION_41_PRODUCT_MESH_PROXIMITY_AND_5VIEW_RESEARCH",
        json.dumps(
            {
                "source_z_contours": [
                    [s["z_mm"], len(s["loops"])] for s in report["sections"]
                ],
                "z230_nearby_mesh_classes": [
                    row["independent_mesh_proximity_counts"]
                    for row in report["sections"][1]["loops"]
                ],
                "factory_approved": False,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
