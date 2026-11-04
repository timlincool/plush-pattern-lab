"""Classify verified public Stage 6 scene objects without manufacturing claims.

Name-derived roles are *hints only*. This module contains no Blender imports,
mesh modification, manufacturing defaults, or scene file side effects.
"""

from __future__ import annotations

from collections import Counter
from math import isfinite

SOURCE_SHA256 = "38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a"
CORE_OBJECTS = (
    "PRIMARY continuous sculpt | new anatomy",
    "Rounded hoof base",
    "Rounded hoof base.001",
    "Rounded hoof base.002",
    "Rounded hoof base.003",
)
HINT_WORDS = {
    "body_or_head": ("primary continuous sculpt", "body", "torso", "head"),
    "leg_or_hoof": ("leg", "hoof", "foot", "paw"),
    "ear": ("ear",),
    "cloud_overlay": ("cloud", "fleece", "fluff"),
    "tail": ("tail",),
    "drop_or_rain": ("drop", "raindrop", "rain"),
    "face_detail": ("eye", "nose", "mouth", "brow", "embroid"),
    "fur_or_visual_proxy": ("fur", "hair", "fiber", "fibre", "strand"),
}


def name_hints(name):
    """Keyword matches must never be treated as a production part assignment."""
    lower = name.casefold()
    return [
        label
        for label, words in HINT_WORDS.items()
        if any(word in lower for word in words)
    ]


def _validate_mesh(row):
    for key in ("vertices", "edges", "faces", "material_slots"):
        if not isinstance(row.get(key), int) or row[key] < 0:
            raise ValueError(f"invalid mesh count: {key}")
    bounds = row.get("bbox_extent_mm")
    if row["vertices"] == 0:
        if bounds is not None:
            raise ValueError("empty mesh must not claim measured bounds")
        return
    if not isinstance(bounds, list) or len(bounds) != 3:
        raise ValueError("nonempty mesh needs three bounding dimensions in mm")
    if any(not isinstance(x, (float, int)) or not isfinite(x) or x < 0 for x in bounds):
        raise ValueError("invalid mesh bounds")


def _validate_scene(records, digest):
    if digest != SOURCE_SHA256:
        raise ValueError("unrecognized Stage6 source identity")
    if not isinstance(records, list) or not 5 <= len(records) <= 10000:
        raise ValueError("invalid scene object collection")
    names = set()
    for row in records:
        name = row.get("name")
        kind = row.get("type")
        if not isinstance(name, str) or not 1 <= len(name) <= 255:
            raise ValueError("invalid object name")
        if not isinstance(kind, str) or not 1 <= len(kind) <= 48:
            raise ValueError("invalid object type")
        if name in names:
            raise ValueError("duplicate scene object name")
        names.add(name)
        if kind == "MESH":
            _validate_mesh(row)
    mapping = {row["name"]: row["type"] for row in records}
    if any(mapping.get(name) != "MESH" for name in CORE_OBJECTS):
        raise ValueError("a source-verified body or hoof mesh is missing")


def build_scene_inventory(records, source_sha256, blender_version):
    """Aggregate bounded engineering triage data; no shell seam assignment."""
    _validate_scene(records, source_sha256)
    meshes = []
    for row in records:
        if row["type"] != "MESH":
            continue
        hints = name_hints(row["name"])
        meshes.append(
            {
                "name": row["name"],
                "triage_role_hints_only": hints,
                "mesh_vertices": row["vertices"],
                "mesh_edges": row["edges"],
                "mesh_faces": row["faces"],
                "material_slot_count_not_bom": row["material_slots"],
                "bbox_extent_mm": row["bbox_extent_mm"],
                "production_part_status": "UNCLASSIFIED_NOT_A_SEWABLE_PATTERN",
            }
        )
    meshes.sort(key=lambda m: (-m["mesh_faces"], m["name"]))
    types = dict(sorted(Counter(row["type"] for row in records).items()))
    hints = Counter(label for item in meshes for label in item["triage_role_hints_only"])
    return {
        "schema": "stage6-whole-scene-component-triage-v1",
        "status": "WHOLE_SCENE_INVENTORY_NOT_PATTERN_OR_BOM",
        "source_sha256": source_sha256,
        "blender": blender_version,
        "scene_objects_total": len(records),
        "object_types": types,
        "mesh_objects_total": len(meshes),
        "nonmesh_objects_total": len(records) - len(meshes),
        "mesh_role_hint_counts_nonexclusive": dict(sorted(hints.items())),
        "mesh_objects_without_role_hints": sum(
            not m["triage_role_hints_only"] for m in meshes
        ),
        "core_body_and_four_hoof_meshes_present": True,
        "dominant_meshes_top_24": meshes[:24],
        "all_mesh_object_inventory": meshes,
        "all_role_assignment_reviewed_by_human": False,
        "all_sewable_panels_identified": False,
        "factory_handoff_ready": False,
        "limitations": [
            "Names and object types suggest roles but do not define part semantics",
            "Mesh face count and dimensions do not prove cuttable or sewable surfaces",
            "Scene contains visual render objects, which can overlap real shells",
            "Only geometry triage; no printable manufacturing patterns or materials",
        ],
    }
