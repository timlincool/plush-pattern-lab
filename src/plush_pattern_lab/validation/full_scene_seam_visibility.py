"""Validate Stage6 authored product-Mesh occlusion without manufacturing approval.

This is a zero-thickness geometric front-hit screen. No fur curves, modifier
render evaluation, fabric thickness or embroidery stitching is certified.
"""

from __future__ import annotations

from collections import Counter

import numpy as np

SOURCE_MESH = "PRIMARY continuous sculpt | new anatomy"
STUDIO_FLOOR = "Studio floor"
VIEWS = (
    ("front", 1, 1, (0, 2)),
    ("back", 1, -1, (0, 2)),
    ("left", 0, 1, (1, 2)),
    ("right", 0, -1, (1, 2)),
    ("top", 2, -1, (0, 1)),
)
VALID_GROUPS = frozenset(
    {
        "core_body_mesh",
        "decorative_cloud_layers",
        "ears",
        "fabric_drops",
        "facial_markers",
        "flat_connectors",
        "four_hooves",
        "tail_overlay",
    }
)


def verified_scene_registry(registry, original_mesh_counts):
    """Fail closed if any source Mesh name/face count differs from the 42 draft."""
    if (
        registry.get("schema") != "stage6-draft-manufacturing-component-registry-v1"
        or registry.get("model_mesh_count") != 42
        or registry.get("non_product_scene_mesh_count") != 1
    ):
        raise ValueError("missing pinned Stage6 42-mesh manufacturing registry")
    rows = registry.get("component_rows")
    if not isinstance(rows, list) or len(rows) != 42:
        raise ValueError("Stage6 manufacturing registry must contain 42 Mesh rows")
    roles = {}
    for row in rows:
        name = row["source_mesh"]
        role = row["scene_group"]
        expected_faces = row["source_faces"]
        if name in roles or not isinstance(expected_faces, int) or expected_faces < 1:
            raise ValueError("duplicate or malformed Stage6 original mesh")
        if role not in VALID_GROUPS | {"studio_floor_not_plush"}:
            raise ValueError("unexpected Stage6 mesh category")
        if name == STUDIO_FLOOR and role != "studio_floor_not_plush":
            raise ValueError("studio floor must be excluded from product visibility")
        if name != STUDIO_FLOOR and role == "studio_floor_not_plush":
            raise ValueError("product Mesh cannot be silently excluded")
        roles[name] = (role, expected_faces)
    if set(roles) != set(original_mesh_counts):
        raise ValueError("actual source Mesh names differ from verified registry")
    if any(original_mesh_counts[name] != faces for name, (_, faces) in roles.items()):
        raise ValueError("actual source Mesh polygon count changed")
    if roles[SOURCE_MESH][0] != "core_body_mesh":
        raise ValueError("original body is not present")
    return {name: role for name, (role, _) in roles.items() if name != STUDIO_FLOOR}


def classify_first_surface(source_point, hit_point, hit_role, axis, sign, tolerance_mm):
    """Classify actual 3D first surface relative to immutable source seam XYZ."""
    src = np.asarray(source_point, dtype=np.float64)
    if src.shape != (3,) or not np.isfinite(src).all():
        raise ValueError("expected finite original 3D seam point in millimetres")
    if axis not in (0, 1, 2) or sign not in (-1, 1):
        raise ValueError("unknown orthographic ray direction")
    if not 0 < tolerance_mm <= 2.0:
        raise ValueError("invalid source-proxy reference tolerance")
    if hit_point is None:
        return {"classification": "no_authored_mesh_first_hit", "depth_mm": None}
    hit = np.asarray(hit_point, dtype=np.float64)
    if hit.shape != (3,) or not np.isfinite(hit).all():
        raise ValueError("nonfinite source-Scene BVH hit")
    if hit_role not in VALID_GROUPS:
        raise ValueError("invalid product Mesh role or studio floor hit")
    depth = float(sign * (src[axis] - hit[axis]))
    if depth > tolerance_mm:
        label = (
            "self_occluded_by_original_body"
            if hit_role == "core_body_mesh"
            else "occluded_by_another_product_mesh"
        )
    elif depth < -tolerance_mm:
        label = "proxy_source_ahead_of_full_mesh_surface_unresolved"
    else:
        label = (
            "near_original_body_first_surface"
            if hit_role == "core_body_mesh"
            else "coincident_with_another_product_mesh_unresolved"
        )
    return {"classification": label, "depth_mm": depth}


def count_scene_view(samples):
    """Keep uncertain samples distinct from product Mesh occlusion."""
    counts = Counter(item["classification"] for item in samples)
    return {
        "sample_count": len(samples),
        "classifications": dict(sorted(counts.items())),
        "other_mesh_occluded_count": counts["occluded_by_another_product_mesh"],
        "raw_body_self_occluded_count": counts["self_occluded_by_original_body"],
        "near_body_surface_count": counts["near_original_body_first_surface"],
        "unresolved_or_no_hit_count": sum(
            count
            for name, count in counts.items()
            if "unresolved" in name or name == "no_authored_mesh_first_hit"
        ),
    }
