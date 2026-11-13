"""Source-locked X/Y meridian sampling and conservative 41-Mesh observation QA.

The genuine Stage6 3D cap vertex IDs here are local to the *already cut cap*,
not original full-resolution Blend mesh IDs. No geometry is fabricated.
"""

from __future__ import annotations

import hashlib
from collections import Counter

import numpy as np

from plush_pattern_lab.validation.full_scene_seam_visibility import VIEWS
# Copy only frozen source schema constants: Blender's bundled Python lacks SciPy.
# The pure-Python regression suite checks these against the original bisector.
ROUTES = ("Y_FRONT_BACK", "X_INNER_OUTER")
CAPS = ("left_high_protrusion", "right_high_protrusion")
EXPECTED_SOURCE_FACES = (1849, 1906)
EXPECTED_SOURCE_RIMS = (113, 112)

SCHEMA = "stage6-original-X-Y-protrusion-meridian-41mesh-5view-v1"
BISECT_SCHEMA = "stage6-genuine-high-protrusion-source-edge-bisect-AB-v1"
CAPS_SCHEMA = "stage6-genuine-source-z230-three-open-caps-v1"
BLEND_SHA = "38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a"
PROXY_SHA = "5b52e3fd09c83b19c5b9d95d6d8d859a147ff4deef90f1518f868d2e82e3a2dd"
SAMPLES_PER_ROUTE = 20
VIEW_NAMES = tuple(view[0] for view in VIEWS)


def _trusted_inputs(bisect, caps, original_sha):
    if (
        bisect.get("schema") != BISECT_SCHEMA
        or bisect.get("source_original_three_caps_schema") != CAPS_SCHEMA
        or bisect.get("original_stage6_blend_sha256") != BLEND_SHA
        or bisect.get("original_source_25pct_proxy_sha256") != PROXY_SHA
        or bisect.get("same_run_real_3d_original_three_caps_sha256") != original_sha
        or bisect.get("routes") != list(ROUTES)
        or not bisect.get("source_3d_shared_new_side_seams_matched")
        or bisect.get("factory_cutting_patterns_approved") != 0
        or bisect.get("P3_status") != "in_progress"
        or bisect.get("P4_status") != "not_started"
        or caps.get("schema") != CAPS_SCHEMA
        or caps.get("original_public_stage6_blend_sha256") != BLEND_SHA
        or caps.get("source_proxy_ply_sha256") != PROXY_SHA
        or caps.get("industrial_cutting_patterns_approved") != 0
        or len(caps.get("upper_caps", [])) != 3
        or len(bisect.get("variants", [])) != 2
    ):
        raise ValueError("original signed Stage6 cap/bisect pair required")
    return {cap["id"]: cap for cap in caps["upper_caps"]}


def _source_path(original, side, cap):
    name, face_count, rim_count = side
    if (
        cap.get("name") != name
        or cap.get("source_face_count") != face_count
        or cap.get("original_z230_rim_edge_count") != rim_count
        or cap.get("original_z230_source_witness_sha256")
        != original.get("source_original_rim_edge_ids_sha256")
        or not cap.get("original_three_dimensional_source_seam_shared_twice")
        or len(cap.get("panels", [])) != 2
    ):
        raise ValueError("Stage6 true original side-cap identity changed")
    xyz = np.asarray(original["vertices_xyz_mm"], dtype=np.float64)
    faces = np.asarray(original["triangles_local_vertex_indices"], dtype=np.int64)
    ids = np.asarray(cap["original_cap_meridian_vertex_ids"], dtype=np.int64)
    if (
        xyz.ndim != 2
        or xyz.shape[1] != 3
        or faces.shape != (face_count, 3)
        or ids.ndim != 1
        or len(ids) < 4
        or len(set(ids.tolist())) != len(ids)
        or np.any(ids < 0)
        or np.any(ids >= len(xyz))
        or not np.isfinite(xyz).all()
    ):
        raise ValueError("invalid genuine Stage6 meridian source vertices")
    length = float(np.linalg.norm(np.diff(xyz[ids], axis=0), axis=1).sum())
    if abs(length - cap["source_3d_meridian_length_mm"]) > 1e-7:
        raise ValueError("3D meridian original source length changed")
    return xyz, ids, length


def _verify_twice(original, cap, xyz, ids):
    visited = []
    for panel in cap["panels"]:
        mapping = np.asarray(
            panel["source_original_cap_vertex_id_per_panel_vertex"], dtype=np.int64
        )
        local = np.asarray(panel["seam_panel_vertex_ids_in_order"], dtype=np.int64)
        points = np.asarray(panel["vertices_xyz_mm"], dtype=np.float64)
        if (
            len(mapping) != len(points)
            or np.any(local < 0)
            or np.any(local >= len(mapping))
            or not np.array_equal(mapping[local], ids)
            or not np.allclose(points[local], xyz[ids], atol=1e-7, rtol=0)
            or not panel.get("topological_Euler") == 1
        ):
            raise ValueError("seam copies lost real source 3D vertex identity")
        visited.extend(panel["source_original_cap_face_ids"])
    count = len(original["triangles_local_vertex_indices"])
    if len(visited) != count or set(visited) != set(range(count)):
        raise ValueError("original cap triangles duplicated or omitted across panels")


def plan_original_meridian_samples(bisect, caps, caps_sha):
    """Screen both predeclared routes and both real caps: no cherry-picking."""
    originals = _trusted_inputs(bisect, caps, caps_sha)
    plans = []
    for expected_route, variant in zip(ROUTES, bisect["variants"]):
        if (
            variant["route"] != expected_route
            or len(variant.get("side_protrusions", [])) != 2
            or not variant.get("single_central_real_source_crown_retained")
        ):
            raise ValueError("lost predeclared original X/Y routes")
        for name, nfaces, nrim, side in zip(
            CAPS,
            EXPECTED_SOURCE_FACES,
            EXPECTED_SOURCE_RIMS,
            variant["side_protrusions"],
        ):
            xyz, ids, length = _source_path(originals[name], (name, nfaces, nrim), side)
            _verify_twice(originals[name], side, xyz, ids)
            n = min(SAMPLES_PER_ROUTE, len(ids))
            chosen = [(k * (len(ids) - 1)) // (n - 1) for k in range(n)]
            digest = hashlib.sha256(
                np.asarray(ids, dtype="<i8").tobytes()
                + np.asarray(xyz[ids], dtype="<f8").tobytes()
            ).hexdigest()
            plans.append(
                {
                    "route": expected_route,
                    "side": name,
                    "cap_local_source_path_sha256": digest,
                    "full_original_3d_cap_meridian_vertices": len(ids),
                    "full_original_3d_netline_length_mm": length,
                    "sampled_cap_local_source_vertices": [
                        {
                            "original_path_index": k,
                            "cap_local_source_vertex_id": int(ids[k]),
                            "original_source_xyz_mm": xyz[ids[k]].tolist(),
                        }
                        for k in chosen
                    ],
                }
            )
    if len(plans) != 4:
        raise ValueError("must examine four real Stage6 meridian options")
    return plans


def summarize_observations(plan, observations):
    samples = plan["sampled_cap_local_source_vertices"]
    if len(observations) != len(samples) or not 2 <= len(samples) <= 20:
        raise ValueError("missing or surplus real source visibility samples")
    counts = {name: Counter() for name in VIEW_NAMES}
    groups = Counter()
    neighbors = Counter()
    for expected, observation in zip(samples, observations):
        if any(observation.get(key) != expected[key] for key in expected):
            raise ValueError("BVH sample did not preserve source cap vertex identity")
        five = observation.get("five_view_first_hit", {})
        if set(five) != set(VIEW_NAMES):
            raise ValueError("each actual source sample needs all five real BVH views")
        for name, result in five.items():
            label = result.get("classification")
            if not isinstance(label, str) or label not in {
                "no_authored_mesh_first_hit",
                "self_occluded_by_original_body",
                "occluded_by_another_product_mesh",
                "proxy_source_ahead_of_full_mesh_surface_unresolved",
                "near_original_body_first_surface",
                "coincident_with_another_product_mesh_unresolved",
            }:
                raise ValueError(
                    "unrecognized original first-surface BVH classification"
                )
            counts[name][label] += 1
        contact = observation.get("independent_mesh_proximity", {})
        for hit in contact.get("nearby_raw_meshes_within_6mm", []):
            if hit.get("distance_mm", -1) <= 3:
                groups[hit["group"]] += 1
                neighbors[hit["mesh"]] += 1
    return {
        "route": plan["route"],
        "side": plan["side"],
        "source_path_sha256": plan["cap_local_source_path_sha256"],
        "original_source_path_vertices": plan["full_original_3d_cap_meridian_vertices"],
        "source_3d_netline_length_mm": plan["full_original_3d_netline_length_mm"],
        "sampled_original_cap_vertices_not_all_source_edges": len(observations),
        "five_view_first_surface_classification_counts": {
            name: dict(sorted(values.items())) for name, values in counts.items()
        },
        "independent_mesh_groups_within_3mm_sample_hits": dict(sorted(groups.items())),
        "independent_mesh_names_within_3mm_sample_hits": dict(
            sorted(neighbors.items())
        ),
        "source_original_vertex_observations": observations,
        "no_approved_ear_cloud_seam_design_or_fabric_hiddenness": True,
        "factory_cutting_patterns_approved": 0,
    }
