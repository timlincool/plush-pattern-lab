"""Read-only Stage6 source-ear ring A/B raw 41-Mesh BVH screen.

Actual original Blender 4.3.2, independent Mesh proximity, five ray views.
Neither anatomical ownership nor actual concealed, sewable seams are proved.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import bpy

from plush_pattern_lab.blender.audit_hoof_interfaces import sha256_file
from plush_pattern_lab.blender.audit_stage6_full_mesh_visibility import (
    EXPECTED_PROXY_SHA,
)
from plush_pattern_lab.blender.audit_stage6_section_mesh_correspondence import (
    _checked_scene_registry,
    _five_view_hits,
    _independent_neighbor_hits,
    _object_bvh_cache,
)
from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256
from plush_pattern_lab.validation.full_scene_seam_visibility import VIEWS
from plush_pattern_lab.validation.stage6_ear_root_ab import (
    SCHEMA,
    plan_side_source_samples,
)

REPORT_SCHEMA = "stage6-original-source-ear-root-ab-41mesh-five-view-v1"


def _inputs(args):
    files = (args.input, args.study, args.previous_41mesh, args.registry)
    if (
        args.source_sha256 != SOURCE_SHA256
        or any(not p.is_file() or p.is_symlink() for p in files)
        or args.output.exists()
        or args.output.is_symlink()
        or args.output.suffix != ".json"
        or args.output.resolve() in {p.resolve() for p in files}
        or args.input.suffix != ".blend"
        or sha256_file(args.input) != SOURCE_SHA256
    ):
        raise ValueError("untrusted original Stage6 or overwrite of evidence")
    study = json.loads(args.study.read_text(encoding="utf8"))
    previous = json.loads(args.previous_41mesh.read_text(encoding="utf8"))
    registry = json.loads(args.registry.read_text(encoding="utf8"))
    if (
        study.get("schema") != SCHEMA
        or study.get("original_public_stage6_blend_sha256") != SOURCE_SHA256
        or study.get("source_25pct_proxy_ply_sha256") != EXPECTED_PROXY_SHA
        or study.get("same_run_41_mesh_correspondence_sha256")
        != sha256_file(args.previous_41mesh)
        or study.get("manufacturing_cutting_approved") != 0
        or previous.get("schema")
        != "stage6-original-section-41-product-mesh-proximity-5view-v1"
        or previous.get("source_original_blend_sha256") != SOURCE_SHA256
        or previous.get("raw_product_mesh_objects_checked") != 41
        or registry.get("source_sha256") != SOURCE_SHA256
    ):
        raise ValueError("A/B not linked to same trusted main original Mesh study")
    return study, previous, registry


def _previous_z230(previous, study):
    source = next(
        (section for section in previous["sections"] if section["z_mm"] == 230),
        None,
    )
    if source is None or len(source["loops"]) != 3:
        raise ValueError("original source z230 three-loop 41Mesh audit missing")
    by_side = {
        "left": next(
            loop for loop in source["loops"]
            if loop["source_centroid_xy_mm"][0] < -15
        ),
        "right": next(
            loop for loop in source["loops"]
            if loop["source_centroid_xy_mm"][0] > 15
        ),
    }
    for row in study["candidate_options"][0]["source_side_loops"]:
        old = by_side[row["side"]]
        if row["source_contour_sha256"] != old["source_loop_sha256"]:
            raise ValueError("source original z230 contour differs from prior 41Mesh")
        planned = plan_side_source_samples(row, 230)
        original = old["raw_source_edge_samples"]
        for sample, witness in zip(planned, original):
            if any(sample[key] != witness[key] for key in sample):
                raise ValueError("original z230 source ID or XYZ sample not preserved")
        if len(original) != len(planned):
            raise ValueError("source sample count changed during A/B comparison")


def _screen_ring(row, z, cache, bounds):
    samples = plan_side_source_samples(row, z)
    observed = []
    near = Counter()
    counts = Counter()
    views = {v[0]: Counter() for v in VIEWS}
    for source in samples:
        xyz = source["source_xyz_mm"]
        neighbors = _independent_neighbor_hits(cache, xyz)
        first_hits = _five_view_hits(cache, bounds, xyz)
        counts[neighbors["proximity_classification"]] += 1
        for hit in neighbors["nearby_raw_meshes_within_6mm"]:
            if hit["distance_mm"] <= 3:
                near[hit["mesh"]] += 1
        for view in views:
            views[view][first_hits[view]["classification"]] += 1
        observed.append(
            {**source, **neighbors, "five_view_first_hit": first_hits}
        )
    return {
        "side": row["side"],
        "source_plane_z_mm": z,
        "source_contour_sha256": row["source_contour_sha256"],
        "original_source_crossed_edge_count": row["original_proxy_crossed_edge_count"],
        "source_edge_samples_observed": len(samples),
        "within_3mm_independent_raw_mesh_sample_counts": dict(sorted(near.items())),
        "proximity_classifications": dict(sorted(counts.items())),
        "five_view_original_mesh_first_hit": {
            v: dict(sorted(counts.items())) for v, counts in views.items()
        },
        "original_source_edge_samples": observed,
        "surface_mesh_occlusion_not_a_hidden_sewing_seam": True,
        "physical_ear_root_not_approved": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--previous-41mesh", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    if bpy.app.version[:3] != (4, 3, 2):
        raise ValueError("original Stage6 Blender 4.3.2 required")
    study, previous, registry = _inputs(args)
    _previous_z230(previous, study)
    bpy.ops.wm.open_mainfile(filepath=str(args.input.resolve()), load_ui=False)
    roles = _checked_scene_registry(registry)
    cache, bounds = _object_bvh_cache(roles)
    report = {
        "schema": REPORT_SCHEMA,
        "original_public_blend_sha256": SOURCE_SHA256,
        "same_run_ear_root_study_sha256": sha256_file(args.study),
        "same_run_original_z230_41mesh_sha256": sha256_file(args.previous_41mesh),
        "raw_product_meshes_raycasted": len(cache),
        "original_fur_curves_not_tested": sum(
            obj.type in ("CURVE", "CURVES") for obj in bpy.data.objects
        ),
        "options": [
            {
                "name": option["name"],
                "source_z_mm": option["source_plane_z_mm"],
                "sides": [
                    _screen_ring(row, option["source_plane_z_mm"], cache, bounds)
                    for row in option["source_side_loops"]
                ],
            }
            for option in study["candidate_options"]
        ],
        "not_a_design_aligned_render": True,
        "not_evaluated_fur_modifiers_or_real_fabric": True,
        "manufacturing_seam_or_dart_approved": False,
        "P3_structure_approved": False,
        "P4_started": False,
    }
    if len(cache) != 41 or [x["source_z_mm"] for x in report["options"]] != [
        230, 235
    ]:
        raise ValueError("original Stage6 A/B mesh survey changed")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf8",
    )
    print(
        "STAGE6_ORIGINAL_41MESH_EAR_ROOT_AB_VISIBLE_SEAM_RISK_RESEARCH",
        json.dumps(
            [
                {
                    "name": option["name"],
                    "sides": [
                        [side["side"], side["within_3mm_independent_raw_mesh_sample_counts"]]
                        for side in option["sides"]
                    ],
                }
                for option in report["options"]
            ]
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
