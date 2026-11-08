"""Actual complete Stage6 41-product-Mesh visibility for rerouted B high2 seams.

Blender source must match the pinned public Release. Material, real hair
visibility, factory seam construction and visual design remain unapproved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import bpy

from plush_pattern_lab.blender.audit_hoof_interfaces import build_report, sha256_file
from plush_pattern_lab.blender.audit_stage6_full_mesh_visibility import (
    VIEWS,
    _checked_scene_registry,
    _object_bvh_cache,
    _sample_one_path,
)
from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

CANDIDATES = ("C_low_neck_boundary", "D_lateral_high_boundary")
PROXY_SHA256 = "5b52e3fd09c83b19c5b9d95d6d8d859a147ff4deef90f1518f868d2e82e3a2dd"


def _validated_reroute(current, source_hash):
    if (
        current.get("schema") != "stage6-source-linked-B-high2-anatomic-avoidance-ab-v1"
        or current.get("source_original_blend_sha256") != source_hash
        or current.get("source_proxy_ply_sha256") != PROXY_SHA256
        or current.get("source_faces") != 36833
        or current.get("approved_industrial_cutting_patterns") != 0
    ):
        raise ValueError("not same-run source-linked research B2 reroute")
    names = [row["candidate"] for row in current.get("candidates", [])]
    if names != list(CANDIDATES):
        raise ValueError("two exact previously validated B2 reroute candidates required")
    return current["candidates"]


def _per_candidate_mesh_views(candidate, cache, world_bounds, source):
    original = candidate["source_body_front_historic_face"]["routes"]
    if [len(row["source_vertex_ids"]) for row in original[:2]] != [33, 143]:
        raise ValueError("source base and high route1 original vertices changed")
    views = [
        {
            "view": view[0],
            "paths": [
                _sample_one_path(cache, world_bounds, path, view) for path in original
            ],
        }
        for view in VIEWS
    ]
    front_witnesses = views[0]["paths"][2]["historic_v14_alert_samples"]
    front_source = original[2]["historic_face_proximity_witnesses"]
    if len(front_witnesses) != len(front_source):
        raise ValueError("historic front-face risks do not match original source IDs")
    return views


def _research_scene_report(item, cache, world_bounds, prior, source_bytes_sha):
    views = _per_candidate_mesh_views(item, cache, world_bounds, prior)
    return {
        "schema": "stage6-original-full-41-product-mesh-source-seam-occlusion-v1",
        "candidate": item["candidate"],
        "status": "RESEARCH_ONLY_ORIGINAL_PRODUCT_MESH_FIRST_HIT",
        "source_blend_sha256": SOURCE_SHA256,
        "source_proxy_25_percent_sha256": PROXY_SHA256,
        "source_research_reroute_summary_sha256": source_bytes_sha,
        "historical_face_v14_sha256": prior["historical_face_v14_sha256"],
        "product_meshes_raytested": len(cache),
        "all_original_mesh_objects": 42,
        "studio_floor_excluded": True,
        "original_other_curve_objects_not_raycasted": sum(
            obj.type in ("CURVE", "CURVES") for obj in bpy.data.objects
        ),
        "product_meshes_with_render_hide": [
            x["name"] for x in cache if x["hidden_from_render"]
        ],
        "product_meshes_not_in_active_scene": [
            x["name"] for x in cache if not x["in_active_scene"]
        ],
        "product_mesh_role_counts": dict(
            sorted(Counter(x["role"] for x in cache).items())
        ),
        "world_bounds_mm": (world_bounds * 1000).round(4).tolist(),
        "only_raw_unmodified_Mesh_triangles_tested": True,
        "historical_face_v14_is_not_final_stage6_embroidery": True,
        "no_rendered_hair_or_fabric_thickness_tested": True,
        "view_results": views,
        "approved_for_manufacturer_cutting": False,
    }


def _validated_public_blender(args):
    if args.source_sha256 != SOURCE_SHA256:
        raise ValueError("only verified public Stage6 SHA is accepted")
    if (
        not args.input.is_file()
        or args.input.is_symlink()
        or args.input.suffix != ".blend"
        or args.reroute.suffix != ".json"
        or not args.reroute.is_file()
        or not args.registry.is_file()
        or args.output_dir.is_symlink()
    ):
        raise ValueError("original public Stage6 research input missing")
    if sha256_file(args.input) != SOURCE_SHA256:
        raise ValueError("public Blender source bytes do not match original SHA")
    if bpy.app.version[:3] != (4, 3, 2):
        raise ValueError("trusted Stage6 Blender 4.3.2 required")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--reroute", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    _validated_public_blender(args)
    outputs = [args.output_dir / f"{name}_full41mesh.json" for name in CANDIDATES]
    if any(path.exists() or path.is_symlink() for path in outputs):
        raise ValueError("never overwrite source-linked visibility evidence")
    previous_bytes = args.reroute.read_bytes()
    previous = json.loads(previous_bytes)
    original = _validated_reroute(previous, args.source_sha256)
    registry = json.loads(args.registry.read_text(encoding="utf8"))
    bpy.ops.wm.open_mainfile(filepath=str(args.input.resolve()), load_ui=False)
    hoof = build_report(SOURCE_SHA256)
    if not hoof["all_geometry_interfaces_match"]:
        raise ValueError("source hoof edges no longer match the public evidence")
    roles = _checked_scene_registry(registry)
    cache, world_bounds = _object_bvh_cache(roles)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for item, path in zip(original, outputs):
        report = _research_scene_report(
            item, cache, world_bounds, previous,
            hashlib.sha256(previous_bytes).hexdigest(),
        )
        path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf8",
        )
        print(
            "STAGE6_FULL41MESH_B2_ALTERNATIVE_FIRST_HIT",
            json.dumps(
                {
                    "candidate": item["candidate"],
                    "product_meshes": len(cache),
                    "front_new_route": report["view_results"][0]["paths"][2][
                        "classifications"
                    ],
                    "historic_v14_alerts": len(
                        report["view_results"][0]["paths"][2][
                            "historic_v14_alert_samples"
                        ]
                    ),
                    "approved": False,
                }
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
