"""Independent original-source three-cap 3D/2D ABF research rejection gate.

Use the project's existing common UV metric evaluator. This scores each real
upper source surface separately; lower side UV has not been constructed, so a
matched *two-sided 2D net seam* must never be claimed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from plush_pattern_lab.validation.stage6_ear_slit_lscm import (
    _face_overlap_and_winding,
    _scale_free_gauge,
)

INPUT_SCHEMA = "stage6-genuine-source-z230-three-open-caps-v1"
UV_SCHEMA = "stage6-real-source-three-crown-cap-native-ABF-research-v1"
RESULT_SCHEMA = "stage6-real-source-z230-three-cap-ABF-independent-rejection-audit-v1"
CUT_RIM = (189, 113, 112)
COMPONENTS = ("central_crown", "left_high_protrusion", "right_high_protrusion")


def _score_one(cap, measured, name, expected_rim):
    xyz = np.asarray(cap["vertices_xyz_mm"], dtype=float)
    faces = np.asarray(cap["triangles_local_vertex_indices"], dtype=int)
    coords = np.asarray(measured["uv_per_3d_cap_source_vertex"], dtype=float)
    rim = np.asarray(cap["original_rim_vertex_ids_in_cap_local_order"], dtype=int)
    if (
        cap.get("id") != name
        or measured.get("source_cap_id") != name
        or cap.get("source_boundary_edges") != expected_rim
        or measured.get("original_cut_rim_edges") != expected_rim
        or measured.get("source_vertex_count") != len(xyz)
        or measured.get("source_triangle_count") != len(faces)
        or coords.shape != (len(xyz), 2)
        or len(rim) != expected_rim
        or len(set(rim.tolist())) != expected_rim
        or not np.isfinite(coords).all()
        or measured.get("maximum_split_UV_loop_disagreement", 1) > 1e-5
    ):
        raise ValueError("untrusted native UV arrays or source seam identities")
    mm, _, edge = _scale_free_gauge(xyz, faces, coords)
    surface = _face_overlap_and_winding(xyz, faces, mm)
    seam = float(np.linalg.norm(mm[rim] - np.roll(mm[rim], -1, axis=0), axis=1).sum())
    original = float(cap["source_3d_rim_perimeter_mm"])
    mismatch = abs(seam - original) / original
    p95 = edge["scaled_2d_p95_abs_edge_relative_error"]
    accepted = (
        p95 <= 0.1
        and mismatch <= 0.03
        and surface["reversed_or_collapsed_triangle_count"] == 0
        and surface["overlapping_positive_area_triangle_pair_count"] == 0
    )
    return {
        "source_cap_name": name,
        "original_source_cut_rim_edges": expected_rim,
        "source_3d_rim_perimeter_mm": original,
        "ABF_2d_single_side_netline_perimeter_mm": seam,
        "ABF_2d_vs_source_3d_rim_relative_length_difference": mismatch,
        "source_3d_edge_to_ABF_2d_p95_relative_error": p95,
        "ABF_folding_or_collapsed_triangles": surface[
            "reversed_or_collapsed_triangle_count"
        ],
        "ABF_positive_area_overlapping_triangle_pairs": surface[
            "overlapping_positive_area_triangle_pair_count"
        ],
        "ABF_absolute_surface_overlap_area_mm2": surface["overlap_triangle_area_mm2"],
        "conditional_research_screen_passed": accepted,
        "lower_matching_2d_sewing_side_has_not_been_unwrapped": True,
        "research_screen_is_not_supplier_or_fabric_approval": True,
    }


def audit_real_source_abf(geometry, source_summary, native, geometry_digest):
    if (
        geometry.get("schema") != INPUT_SCHEMA
        or geometry.get("industrial_cutting_patterns_approved") != 0
        or geometry.get("P4_status") != "not_started"
        or source_summary.get("full_3d_source_caps_json_sha256") != geometry_digest
        or native.get("schema") != UV_SCHEMA
        or native.get("source_caps_geometry_sha256") != geometry_digest
        or native.get("blender_version") != "4.3.2"
        or native.get("solver") != "ANGLE_BASED"
        or native.get("factory_cutting_patterns_approved") != 0
        or len(native.get("entries", [])) != 3
        or len(geometry.get("upper_caps", [])) != 3
    ):
        raise ValueError("real source 3D cap and native ABF source hash must match")
    rows = [
        _score_one(cap, uv, label, count)
        for cap, uv, label, count in zip(
            geometry["upper_caps"], native["entries"], COMPONENTS, CUT_RIM
        )
    ]
    return {
        "schema": RESULT_SCHEMA,
        "same_run_real_source_geometry_SHA256": geometry_digest,
        "same_3d_upper_and_lower_original_source_seams_verified": geometry[
            "upper_to_lower_source_netline_matched_at_1e_6_mm"
        ],
        "three_real_stage6_original_triangle_mesh_caps_scored": len(rows),
        "native_solver": "Blender 4.3.2 ANGLE_BASED",
        "same_metric_source_3d_edges_and_flat_abf_mm": True,
        "all_caps_research_gates_passed": all(
            row["conditional_research_screen_passed"] for row in rows
        ),
        "caps": rows,
        "research_only_missing_lower_2d_match_and_material": True,
        "factory_cutting_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
    }


def _raw(path):
    if not path.is_file() or path.is_symlink():
        raise ValueError("missing or symlinked original research input")
    return path.read_bytes()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-caps", type=Path, required=True)
    parser.add_argument("--source-summary", type=Path, required=True)
    parser.add_argument("--abf-uv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise ValueError("cannot overwrite real source cap ABF research results")
    original_bytes = _raw(args.source_caps)
    result = audit_real_source_abf(
        json.loads(original_bytes),
        json.loads(_raw(args.source_summary)),
        json.loads(_raw(args.abf_uv)),
        hashlib.sha256(original_bytes).hexdigest(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(
        "STAGE6_THREE_TRUE_SOURCE_ABF_3D_2D_RESEARCH_GATES",
        json.dumps(
            {
                "parts": len(result["caps"]),
                "research_passed": result["all_caps_research_gates_passed"],
                "factory_approved": False,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
