"""Two predeclared short original-edge Stage6 rear/inner ear-root slit candidates.

Cut a *single* genuine source disk along boundary-to-apex path, retaining
the apex identity while duplicating only the open slit's other vertices.
Reuses the existing face-fan and topology gates. NOT a sewn material rest shape.
"""

from __future__ import annotations

import hashlib

import numpy as np

from plush_pattern_lab.validation.real_panel_slit import (
    _cut_fan_connections,
    _duplicate_face_fan,
    _edges,
    _validate_cut_disk,
)
from plush_pattern_lab.validation.stage6_real_protrusion_bisect import (
    CAPS,
    EXPECTED_SOURCE_FACES,
    EXPECTED_SOURCE_RIMS,
    _ordered_boundary,
    _source,
)

SCHEMA = "stage6-original-ear-high-protrusion-short-open-slit-v1"
SOURCE_SCHEMA = "stage6-genuine-source-z230-three-open-caps-v1"
FULL_BISECT_SCHEMA = "stage6-genuine-high-protrusion-source-edge-bisect-AB-v1"
ROUTES = ("Y_REAR_RIM_TO_TIP", "X_INNER_RIM_TO_TIP")
BLEND_SHA = "38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a"
PROXY_SHA = "5b52e3fd09c83b19c5b9d95d6d8d859a147ff4deef90f1518f868d2e82e3a2dd"


def _source_inputs(caps, full, same_run_caps_sha):
    if (
        caps.get("schema") != SOURCE_SCHEMA
        or caps.get("original_public_stage6_blend_sha256") != BLEND_SHA
        or caps.get("source_proxy_ply_sha256") != PROXY_SHA
        or caps.get("industrial_cutting_patterns_approved") != 0
        or caps.get("P3_status") != "in_progress"
        or caps.get("P4_status") != "not_started"
        or not caps.get("upper_to_lower_source_netline_matched_at_1e_6_mm")
        or len(caps.get("upper_caps", [])) != 3
        or full.get("schema") != FULL_BISECT_SCHEMA
        or full.get("same_run_real_3d_original_three_caps_sha256")
        != same_run_caps_sha
        or full.get("routes") != ["Y_FRONT_BACK", "X_INNER_OUTER"]
        or full.get("factory_cutting_patterns_approved") != 0
        or full.get("P3_status") != "in_progress"
        or full.get("P4_status") != "not_started"
        or len(full.get("variants", [])) != 2
    ):
        raise ValueError("original unchanged Stage6 source and signed full meridians required")
    if [c["id"] for c in caps["upper_caps"][1:]] != list(CAPS):
        raise ValueError("genuine left/right Stage6 caps changed")
    return caps["upper_caps"][1:]


def _short_original_path(full_meridian, tip_id, route, side, rim):
    ids = np.asarray(full_meridian, dtype=np.int64)
    if (
        ids.ndim != 1
        or len(ids) < 15
        or len(set(ids.tolist())) != len(ids)
        or ids.tolist().count(tip_id) != 1
    ):
        raise ValueError("invalid original predeclared full source meridian")
    tip = ids.tolist().index(tip_id)
    if not 6 <= tip <= len(ids) - 7:
        raise ValueError("short physical rim-to-apex path is degenerate")
    if route == ROUTES[0] or side == CAPS[0]:
        chosen = ids[tip:][::-1]
    else:
        chosen = ids[: tip + 1]
    if (
        int(chosen[0]) not in set(rim.tolist())
        or int(chosen[-1]) != tip_id
        or set(chosen[1:]).intersection(set(rim.tolist()))
    ):
        raise ValueError("partial source slit touches second original Z230 rim point")
    return chosen


def _cut_source_fans_once(xyz, faces, path, original_rim_count):
    original_edges, inverse, counts, _, _ = _edges(faces, len(xyz))
    cut = {tuple(sorted((int(a), int(b)))) for a, b in zip(path[:-1], path[1:])}
    if len(cut) != len(path) - 1 or any(
        len(faces) < 1 or counts[np.where((original_edges == e).all(axis=1))[0][0]] != 2
        for e in cut
    ):
        raise ValueError("short slit contains noninterior or nonexistent source edge")
    # Existing face-fan splitter duplicates the seam points. The internal tip
    # must remain shared, otherwise a short dart becomes a broken mesh.
    connected_fans = _cut_fan_connections(
        original_edges, inverse, counts, path, len(faces)
    )
    updated = faces.copy()
    duplicate_path = path[:-1]
    for index, vertex in enumerate(duplicate_path):
        _duplicate_face_fan(
            faces, updated, int(vertex), connected_fans[int(vertex)], len(xyz) + index
        )
    points = np.vstack((xyz, xyz[duplicate_path]))
    source_ids = np.r_[np.arange(len(xyz)), duplicate_path]
    boundary = _validate_cut_disk(
        updated, len(points), original_rim_count, len(path) - 1
    )
    if not np.array_equal(points[updated], xyz[source_ids[updated]]):
        raise ValueError("changed Stage6 source triangle positions during cut")
    return points, updated, source_ids, boundary


def _one_candidate(original, reference, route, side, faces_count, rim_count):
    xyz, faces, rim, _, _ = _source(original, side, faces_count, rim_count)
    if (
        reference.get("name") != side
        or reference.get("source_face_count") != faces_count
        or reference.get("original_z230_rim_edge_count") != rim_count
        or not reference.get("original_three_dimensional_source_seam_shared_twice")
    ):
        raise ValueError("full meridian source identity changed")
    tip = int(reference["original_cap_tip_vertex_id"])
    if tip != int(np.argmax(xyz[:, 2])):
        raise ValueError("original cap apex identity drift")
    path = _short_original_path(
        reference["original_cap_meridian_vertex_ids"], tip, route, side, rim
    )
    new_xyz, new_faces, identity, border = _cut_source_fans_once(
        xyz, faces, path, rim_count
    )
    original3d = float(np.linalg.norm(np.diff(xyz[path], axis=0), axis=1).sum())
    if not 0 < original3d < reference["source_3d_meridian_length_mm"]:
        raise ValueError("not a shorter original source edge slit")
    original_edge_count = sum(
        1
        for a, b in border
        if tuple(sorted((int(identity[a]), int(identity[b]))))
        in {tuple(sorted((int(rim[i]), int(rim[(i + 1) % len(rim)])))) for i in range(len(rim))}
    )
    if original_edge_count != rim_count:
        raise ValueError("original source Z230 outline is not preserved")
    outline = _ordered_boundary({tuple(map(int, edge)) for edge in border})
    digest = hashlib.sha256(
        np.asarray(path, dtype="<i8").tobytes()
        + np.asarray(xyz[path], dtype="<f8").tobytes()
    ).hexdigest()
    return {
        "id": side + "_" + route,
        "source_cap_id": side,
        "route": route,
        "source_original_full_meridian_3d_mm": reference["source_3d_meridian_length_mm"],
        "slit_path_original_cap_vertex_ids": path.tolist(),
        "slit_original_local_vertex_ids": path.tolist(),
        "source_path_vertex_and_xyz_sha256": digest,
        "real_source_3d_slit_length_mm": original3d,
        "original_source_Z230_rim_edges": rim_count,
        "new_two_sided_seam_edges_per_side": len(path) - 1,
        "source_original_face_count": len(faces),
        "source_original_vertex_count": len(xyz),
        "original_patch_vertex_id_per_disk_vertex": identity.tolist(),
        "source_xyz_mm": new_xyz.tolist(),
        "disk_triangle_vertex_ids": new_faces.tolist(),
        "boundary_panel_vertex_ids_in_order": outline,
        "source_boundary_edges": len(border),
        "source_tip_vertex_not_duplicated": int(path[-1]) not in set(path[:-1]),
        "original_triangles_unmodified_in_3d": True,
        "topological_Euler": 1,
        "research_not_approved_2d_or_cloth_pattern": True,
    }


def build_short_darts(caps, full, same_run_caps_sha):
    originals = _source_inputs(caps, full, same_run_caps_sha)
    records = []
    for index, route in enumerate(ROUTES):
        full_route = full["variants"][index]
        if (
            full_route["route"] != ("Y_FRONT_BACK", "X_INNER_OUTER")[index]
            or len(full_route["side_protrusions"]) != 2
        ):
            raise ValueError("source full Y/X meridian ordering changed")
        for cap, part, side, count, rim in zip(
            originals,
            full_route["side_protrusions"],
            CAPS,
            EXPECTED_SOURCE_FACES,
            EXPECTED_SOURCE_RIMS,
        ):
            records.append(_one_candidate(cap, part, route, side, count, rim))
    if len(records) != 4:
        raise ValueError("both sides and both short predeclared slits required")
    return {
        "schema": SCHEMA,
        "original_public_blend_sha256": BLEND_SHA,
        "original_proxy_25pct_sha256": PROXY_SHA,
        "same_run_caps_sha256": same_run_caps_sha,
        "routes": list(ROUTES),
        "four_real_original_cap_short_slit_disks": records,
        "original_source_3d_mesh_faces_and_four_hoof_interfaces_unchanged": True,
        "no_UV_solver_reimplemented": True,
        "real_fabric_or_anatomical_attachment_validated": False,
        "factory_cutting_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
    }
