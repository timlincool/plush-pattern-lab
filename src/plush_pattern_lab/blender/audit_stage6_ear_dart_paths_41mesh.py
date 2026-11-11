"""Screen original source ear-dart research routes against all 41 raw Meshes.

Blender 4.3.2 original product meshes only; hair, fabric, sewing untested.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import bpy
import numpy as np

from plush_pattern_lab.blender.audit_hoof_interfaces import sha256_file
from plush_pattern_lab.blender.audit_stage6_section_mesh_correspondence import (
    _checked_scene_registry,
    _five_view_hits,
    _independent_neighbor_hits,
    _object_bvh_cache,
)
from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256
from plush_pattern_lab.validation.full_scene_seam_visibility import VIEWS

REPORT_SCHEMA = "stage6-source-dart-route-41-product-mesh-first-hit-v1"
SOURCE_SCHEMA = "stage6-source-ear-medial-arc-dart-tip-routes-v1"
EXPECTED_PROXY_SHA = "5b52e3fd09c83b19c5b9d95d6d8d859a147ff4deef90f1518f868d2e82e3a2dd"
SAMPLES_PER_ROUTE = 16


def _validate_inputs(args):
    paths = (args.input, args.paths, args.registry)
    if (
        args.source_sha256 != SOURCE_SHA256
        or any(not p.is_file() or p.is_symlink() for p in paths)
        or args.output.suffix != ".json"
        or args.output.exists()
        or args.output.is_symlink()
        or args.input.suffix != ".blend"
        or sha256_file(args.input) != SOURCE_SHA256
    ):
        raise ValueError("wrong pinned public Stage6 or protected output")
    routes = json.loads(args.paths.read_text(encoding="utf8"))
    registry = json.loads(args.registry.read_text(encoding="utf8"))
    if (
        routes.get("schema") != SOURCE_SCHEMA
        or routes.get("public_original_stage6_blend_sha256") != SOURCE_SHA256
        or routes.get("original_25percent_proxy_sha256") != EXPECTED_PROXY_SHA
        or routes.get("original_source_proxy_vertex_count") != 59306
        or routes.get("original_source_proxy_triangle_count") != 116568
        or routes.get("factory_cutting_patterns_approved") != 0
        or routes.get("P4_status") != "not_started"
        or routes.get("P3_status") != "in_progress"
        or routes.get("original_source_proxy_unique_mesh_edge_count") != 175876
        or registry.get("source_sha256") != SOURCE_SHA256
    ):
        raise ValueError("untrusted source-routed dart or product Mesh identity")
    return routes, registry


def _sample_one_branch(ids, points, cache, bounds):
    count = min(len(ids), SAMPLES_PER_ROUTE)
    indices = [(k * (len(ids) - 1)) // (count - 1) for k in range(count)]
    observed = []
    views = {row[0]: Counter() for row in VIEWS}
    nearby = Counter()
    for i in indices:
        xyz = points[i]
        hits = _five_view_hits(cache, bounds, xyz)
        prox = _independent_neighbor_hits(cache, xyz)
        for name, row in hits.items():
            views[name][row["classification"]] += 1
        for neighbor in prox["nearby_raw_meshes_within_6mm"]:
            if neighbor["distance_mm"] <= 3:
                nearby[neighbor["mesh"]] += 1
        observed.append(
            {
                "original_source_proxy_vertex_id": ids[i],
                "original_source_vertex_xyz_mm": xyz,
                "first_original_mesh_hits": hits,
                "independent_mesh_proximity": prox,
            }
        )
    return {
        "original_route_vertex_count": len(ids),
        "original_vertex_id_and_xyz_samples": observed,
        "sample_count": len(observed),
        "five_view_first_hit_counts": {
            name: dict(sorted(summary.items())) for name, summary in views.items()
        },
        "within_3mm_independent_raw_meshes": dict(sorted(nearby.items())),
        "actual_stitch_coverage_not_proven": True,
    }


def _audit_candidate(item, cache, bounds):
    groups = item["disjoint_original_source_route_ids"]
    points = item["disjoint_original_source_route_xyz_mm"]
    if len(groups) != 2 or len(points) != 2:
        raise ValueError("two original source route branches are required")
    for ids, xyz in zip(groups, points):
        if (
            len(ids) != len(xyz)
            or len(ids) < 2
            or any(not isinstance(i, int) or i < 0 or i >= 59306 for i in ids)
            or not np.isfinite(np.asarray(xyz, dtype=float)).all()
        ):
            raise ValueError("invalid original source route Vertex ID and XYZ pairs")
    digest = hashlib.sha256(
        np.asarray(groups[0] + groups[1], dtype="<i8").tobytes()
        + np.asarray(points[0] + points[1], dtype="<f8").tobytes()
    ).hexdigest()
    if (
        digest != item["source_3d_dart_route_identity_sha256"]
        or groups[0][-1] != groups[1][-1]
        or set(groups[0][:-1]) & set(groups[1][:-1])
    ):
        raise ValueError("source route provenance or joint-only termination changed")
    return {
        "side": item["side"],
        "tip_target_z_mm": item["tip_target_z_mm"],
        "original_source_route_sha256": digest,
        "source_branches": [
            _sample_one_branch(ids, xyz, cache, bounds)
            for ids, xyz in zip(groups, points)
        ],
        "source_path_first_hit_not_sewing_or_design_proof": True,
        "factory_cutting_approved": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--paths", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    if bpy.app.version[:3] != (4, 3, 2):
        raise ValueError("pinned Blender 4.3.2 required")
    routes, registry = _validate_inputs(args)
    bpy.ops.wm.open_mainfile(filepath=str(args.input.resolve()), load_ui=False)
    roles = _checked_scene_registry(registry)
    cache, bounds = _object_bvh_cache(roles)
    report = {
        "schema": REPORT_SCHEMA,
        "original_public_blend_sha256": SOURCE_SHA256,
        "same_run_original_source_dart_routes_sha256": sha256_file(args.paths),
        "source_proxy_sha256": EXPECTED_PROXY_SHA,
        "original_product_meshes_raycasted": len(cache),
        "original_curves_not_tested": sum(
            obj.type in ("CURVE", "CURVES") for obj in bpy.data.objects
        ),
        "route_candidates": [
            _audit_candidate(item, cache, bounds) for item in routes["candidates"]
        ],
        "not_fur_cloth_or_material_simulation": True,
        "cutting_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
    }
    if len(cache) != 41 or len(report["route_candidates"]) != 4:
        raise ValueError("original 41Mesh candidate audit not complete")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf8",
    )
    print(
        "STAGE6_SOURCE_DART_41MESH_ROUTING_RESEARCH_NOT_SEWABLE",
        json.dumps(
            [
                {
                    "side": row["side"],
                    "tip_z": row["tip_target_z_mm"],
                    "views": [
                        branch["five_view_first_hit_counts"]
                        for branch in row["source_branches"]
                    ],
                }
                for row in report["route_candidates"]
            ]
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
