"""Read-only Stage6 whole-scene mesh/object survey for production planning.

Source must be the exact public Stage6 release and Blender 4.3.2 must be
invoked with --disable-autoexec. Never treat name-based role hints as cut parts.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

from plush_pattern_lab.blender.audit_hoof_interfaces import (
    build_report,
    sha256_file,
)
from plush_pattern_lab.validation.component_inventory import build_scene_inventory


def _mesh_row(obj, result):
    mesh = obj.data
    result.update(
        vertices=len(mesh.vertices),
        edges=len(mesh.edges),
        faces=len(mesh.polygons),
        material_slots=len(obj.material_slots),
        bbox_extent_mm=None,
    )
    if not mesh.vertices:
        return
    corners = np.asarray(
        [tuple(obj.matrix_world @ Vector(point)) for point in obj.bound_box],
        dtype=np.float64,
    )
    if corners.shape != (8, 3) or not np.isfinite(corners).all():
        raise ValueError("invalid Blender world-space object bounding box")
    extents = (corners.max(axis=0) - corners.min(axis=0)) * 1000
    result["bbox_extent_mm"] = [round(float(x), 3) for x in extents]


def _scene_rows():
    """Include scene assets and data-linked meshes without evaluating modifiers."""
    rows = []
    scene = bpy.context.scene
    for obj in sorted(bpy.data.objects, key=lambda item: item.name):
        row = {
            "name": obj.name,
            "type": obj.type,
            "in_active_scene": scene.objects.get(obj.name) is not None,
        }
        if obj.type == "MESH":
            _mesh_row(obj, row)
        rows.append(row)
    return rows


def extract_scene_inventory(source_digest):
    """The strict four-hoof geometry gate runs before any scene triage."""
    prior = build_report(source_digest)
    if not prior["all_geometry_interfaces_match"]:
        raise ValueError("Stage6 source four-hoof interface gate failed")
    records = _scene_rows()
    report = build_scene_inventory(records, source_digest, bpy.app.version_string)
    report["active_scene_name"] = bpy.context.scene.name
    report["objects_in_active_scene"] = sum(
        row["in_active_scene"] for row in records
    )
    report["objects_not_in_active_scene"] = sum(
        not row["in_active_scene"] for row in records
    )
    report["scene_object_scope"] = "all bpy.data.objects (including unlinked)"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    if bpy.app.version[:3] != (4, 3, 2):
        raise ValueError("Blender 4.3.2 is required for the source audit")
    if not args.input.is_file() or args.input.suffix != ".blend":
        raise ValueError("source Blender model must be a readable .blend")
    if args.output.suffix != ".json" or args.output.exists():
        raise ValueError("output must be a new JSON evidence file")
    if args.output.is_symlink():
        raise ValueError("refusing a symlinked evidence file")
    digest = sha256_file(args.input)
    if digest != args.source_sha256:
        raise ValueError("mismatching source SHA-256; never load the Blender scene")
    bpy.ops.wm.open_mainfile(filepath=str(args.input.resolve()), load_ui=False)
    report = extract_scene_inventory(digest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        "STAGE6_FULL_SCENE_COMPONENT_TRIAGE",
        json.dumps(
            {
                "total": report["scene_objects_total"],
                "types": report["object_types"],
                "mesh_count": report["mesh_objects_total"],
                "unclassified_meshes": report["mesh_objects_without_role_hints"],
                "roles": report["mesh_role_hint_counts_nonexclusive"],
                "top_meshes": [
                    {
                        "name": row["name"],
                        "faces": row["mesh_faces"],
                        "extent_mm": row["bbox_extent_mm"],
                        "hints": row["triage_role_hints_only"],
                    }
                    for row in report["dominant_meshes_top_24"][:12]
                ],
                "approved_patterns": False,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
