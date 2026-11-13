# SPDX-License-Identifier: GPL-2.0-or-later
"""Read-only 41 raw product Mesh BVH for Stage6 genuine X/Y side-meridians.

Actual Blender 4.3.2 scene, shared BVH helpers; no authored fur or real cloth.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy

from plush_pattern_lab.blender.audit_hoof_interfaces import sha256_file
from plush_pattern_lab.blender.audit_stage6_section_mesh_correspondence import (
    _checked_scene_registry,
    _five_view_hits,
    _independent_neighbor_hits,
    _object_bvh_cache,
)
from plush_pattern_lab.validation.stage6_protrusion_route_visibility import (
    BLEND_SHA,
    PROXY_SHA,
    SCHEMA,
    plan_original_meridian_samples,
    summarize_observations,
)


def _inputs(args):
    files = (args.input, args.bisect, args.caps, args.registry, args.abf_quality)
    if (
        bpy.app.version[:3] != (4, 3, 2)
        or args.source_sha256 != BLEND_SHA
        or any(not p.is_file() or p.is_symlink() for p in files)
        or args.input.suffix != ".blend"
        or args.output.suffix != ".json"
        or args.output.exists()
        or args.output.is_symlink()
        or args.output.resolve() in {p.resolve() for p in files}
        or sha256_file(args.input) != BLEND_SHA
    ):
        raise ValueError("require protected original Stage6 and new report path")
    geometry = json.loads(args.bisect.read_bytes())
    caps = json.loads(args.caps.read_bytes())
    registry = json.loads(args.registry.read_bytes())
    scores = json.loads(args.abf_quality.read_bytes())
    if (
        registry.get("source_sha256") != BLEND_SHA
        or scores.get("schema")
        != "stage6-real-source-side-meridian-ABF-two-sided-netline-audit-v1"
        or scores.get("factory_cutting_patterns_approved") != 0
        or scores.get("source_bisect_study_sha256")
        != hashlib.sha256(args.bisect.read_bytes()).hexdigest()
        or geometry.get("original_source_25pct_proxy_sha256") != PROXY_SHA
    ):
        raise ValueError("original mesh registry or same-run ABF quality mismatch")
    return geometry, caps, registry, scores


def _one_path(plan, cache, bounds):
    sampled = []
    for row in plan["sampled_cap_local_source_vertices"]:
        coords = row["original_source_xyz_mm"]
        sampled.append(
            {
                **row,
                "five_view_first_hit": _five_view_hits(cache, bounds, coords),
                "independent_mesh_proximity": _independent_neighbor_hits(cache, coords),
            }
        )
    return summarize_observations(plan, sampled)


def _report(geometry, caps, registry, scores, files):
    _source, bisect, caps_path, registry_path, abf_path = files
    plans = plan_original_meridian_samples(
        geometry, caps, sha256_file(caps_path)
    )
    roles = _checked_scene_registry(registry)
    cache, bounds = _object_bvh_cache(roles)
    if len(cache) != 41:
        raise ValueError("must raycast all original 41 product meshes")
    observations = [_one_path(plan, cache, bounds) for plan in plans]
    if len(observations) != 4:
        raise ValueError("source X/Y directions or one ear side disappeared")
    return {
        "schema": SCHEMA,
        "source_original_blend_sha256": BLEND_SHA,
        "source_original_25pct_proxy_sha256": PROXY_SHA,
        "same_run_true_caps_sha256": sha256_file(caps_path),
        "same_run_source_meridians_sha256": sha256_file(bisect),
        "same_run_ABF_two_sided_score_sha256": sha256_file(abf_path),
        "same_run_original_41mesh_registry_sha256": sha256_file(registry_path),
        "blender_version": bpy.app.version_string,
        "all_41_original_product_mesh_BVH_raycasted": len(cache),
        "original_hair_curve_objects_not_evaluated": sum(
            obj.type in ("CURVE", "CURVES") for obj in bpy.data.objects
        ),
        "original_mesh_modifiers_not_evaluated": True,
        "source_routes_examined": [row["route"] for row in observations],
        "route_observations": observations,
        "previous_ABF_research_comparison_schema": scores["schema"],
        "original_source_proxy_cap_local_vertex_ids_not_full_Blend_ids": True,
        "raycast_proximity_and_occlusion_not_sewable_hidden_seam": True,
        "real_fabric_and_original_design_registration_not_tested": True,
        "factory_cutting_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--bisect", type=Path, required=True)
    parser.add_argument("--caps", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--abf-quality", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    geometry, caps, registry, scores = _inputs(args)
    bpy.ops.wm.open_mainfile(filepath=str(args.input.resolve()), load_ui=False)
    result = _report(
        geometry,
        caps,
        registry,
        scores,
        (args.input, args.bisect, args.caps, args.registry, args.abf_quality),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf8",
    )
    print(
        "STAGE6_X_Y_REAL_SOURCE_41MESH_5VIEW_NOT_APPROVED",
        json.dumps(
            [
                {
                    "route": row["route"],
                    "side": row["side"],
                    "views": row["five_view_first_surface_classification_counts"],
                    "nearby": row["independent_mesh_groups_within_3mm_sample_hits"],
                }
                for row in result["route_observations"]
            ]
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
