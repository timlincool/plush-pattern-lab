"""Independent Blender ABF QA for exact original Stage6 side-cap seam copies.

Preserve 3D-source vertex identity, one-sided cut-rim, two-sided new seam.
This is a research metric audit only: lower cap has no corresponding 2D seam.
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

SCHEMA = "stage6-real-source-side-meridian-ABF-two-sided-netline-audit-v1"
INPUT_SCHEMA = "stage6-genuine-high-protrusion-source-edge-bisect-AB-v1"
UV_SCHEMA = "stage6-real-high-protrusion-source-meridian-native-ABF-v1"
ROUTES = ("Y_FRONT_BACK", "X_INNER_OUTER")


def _score(panel, entry):
    coords = np.asarray(entry["uv_per_3d_cap_source_vertex"], dtype=float)
    xyz = np.asarray(panel["vertices_xyz_mm"], dtype=float)
    triangles = np.asarray(panel["triangles_local_vertex_indices"], dtype=int)
    if (
        entry["source_cap_id"] != panel["id"]
        or entry["source_vertex_count"] != len(xyz)
        or entry["source_triangle_count"] != len(triangles)
        or entry["original_cut_rim_edges"]
        != len(panel["boundary_panel_vertex_ids_in_order"])
        or entry["maximum_split_UV_loop_disagreement"] > 1e-5
        or coords.shape != (len(xyz), 2)
        or not np.isfinite(coords).all()
    ):
        raise ValueError("ABF panel UV does not match original 3D triangles")
    mm, _, edge = _scale_free_gauge(xyz, triangles, coords)
    overlap = _face_overlap_and_winding(xyz, triangles, mm)
    source_map = np.asarray(
        panel["source_original_cap_vertex_id_per_panel_vertex"], dtype=int
    )
    rim = np.asarray(panel["boundary_panel_vertex_ids_in_order"], dtype=int)
    source_rim = panel["source_original_z230_boundary_edges_on_panel"]
    original_ids = panel["seam_original_cap_vertex_ids_in_order"]
    path = np.asarray(panel["seam_panel_vertex_ids_in_order"], dtype=int)
    if (
        not np.array_equal(source_map[path], original_ids)
        or len(set(rim.tolist())) != len(rim)
        or source_rim < 2
    ):
        raise ValueError("Blender vertex seam identity or original Z230 rim invalid")
    seam_mm = np.linalg.norm(np.diff(mm[path], axis=0), axis=1)
    seam_xyz = np.linalg.norm(np.diff(xyz[path], axis=0), axis=1)
    return {
        "id": panel["id"],
        "original_3d_source_face_count": len(triangles),
        "source_3d_cut_rim_edges": source_rim,
        "source_edge_p95_relative_length_error": edge[
            "scaled_2d_p95_abs_edge_relative_error"
        ],
        "source_edge_p50_relative_length_error": edge[
            "scaled_2d_p50_abs_edge_relative_error"
        ],
        "ABF_source_surface_flip_count": overlap[
            "reversed_or_collapsed_triangle_count"
        ],
        "ABF_positive_area_overlap_count": overlap[
            "overlapping_positive_area_triangle_pair_count"
        ],
        "ABF_2d_cut_path_segment_mm": seam_mm.tolist(),
        "original_3d_cut_path_segment_mm": seam_xyz.tolist(),
        "ABF_2d_cut_path_length_mm": float(seam_mm.sum()),
        "original_3d_cut_path_length_mm": float(seam_xyz.sum()),
        "all_three_dimensional_original_vertex_IDs_preserved": True,
    }


def _one_pair(part, native):
    if len(part["panels"]) != 2:
        raise ValueError("a source side protrusion must have two genuine pieces")
    pieces = []
    for panel in part["panels"]:
        if panel["id"] not in native:
            raise ValueError("source panel missing native Blender ABF UV")
        pieces.append(_score(panel, native[panel["id"]]))
    first, second = pieces
    lengths = np.asarray([p["ABF_2d_cut_path_segment_mm"] for p in pieces])
    actual_3d = np.asarray(first["original_3d_cut_path_segment_mm"])
    if lengths.shape != (
        2,
        len(part["original_cap_meridian_vertex_ids"]) - 1,
    ) or not np.allclose(
        actual_3d, second["original_3d_cut_path_segment_mm"], atol=1e-8
    ):
        raise ValueError("source path segment and seam direction not paired")
    original_len = float(actual_3d.sum())
    two_sides = abs(float(lengths[0].sum() - lengths[1].sum())) / original_len
    segment_abs = float(np.abs(lengths[0] - lengths[1]).sum() / original_len)
    results = {
        "source_cap": part["name"],
        "route": part["route"],
        "new_source_meridian_3d_length_mm": original_len,
        "two_ABF_2d_seam_total_relative_mismatch": two_sides,
        "two_ABF_2d_seam_segment_absolute_mismatch_fraction": segment_abs,
        "two_source_panels": pieces,
        "all_original_source_crown_faces_covered_by_exactly_one_panel": True,
        "ABF_research_shape_gate_passed": all(
            row["source_edge_p95_relative_length_error"] <= 0.1
            and row["ABF_source_surface_flip_count"] == 0
            and row["ABF_positive_area_overlap_count"] == 0
            for row in pieces
        ),
        "ABF_research_two_side_cut_line_gate_passed": segment_abs <= 0.03,
        "original_Z230_base_rim_lower_ABF_side_unavailable": True,
        "physical_cloth_and_visible_seam_unverified": True,
    }
    results["all_limited_ABF_seam_research_gates_passed"] = (
        results["ABF_research_shape_gate_passed"]
        and results["ABF_research_two_side_cut_line_gate_passed"]
    )
    return results


def audit(source, native, source_digest):
    if (
        source.get("schema") != INPUT_SCHEMA
        or source.get("factory_cutting_patterns_approved") != 0
        or source.get("P3_status") != "in_progress"
        or source.get("P4_status") != "not_started"
        or not source.get("source_three_dimensional_face_ids_and_Z230_rims_unchanged")
        or native.get("schema") != UV_SCHEMA
        or native.get("source_bisect_study_sha256") != source_digest
        or native.get("solver") != "ANGLE_BASED"
        or native.get("blender_version") != "4.3.2"
        or native.get("factory_cutting_patterns_approved") != 0
        or len(native.get("entries", [])) != 8
    ):
        raise ValueError("not a source-identical signed Stage6 native ABF study")
    indexed = {row["source_cap_id"]: row for row in native["entries"]}
    if len(indexed) != 8:
        raise ValueError("native ABF result repeated source-panel IDs")
    if [x["route"] for x in source["variants"]] != list(ROUTES):
        raise ValueError("route order or type changed from preregistered alternatives")
    results = []
    for variant in source["variants"]:
        rows = [_one_pair(part, indexed) for part in variant["side_protrusions"]]
        results.append(
            {
                "route": variant["route"],
                "side_source_panels": rows,
                "source_3d_panel_count": 4,
                "all_limited_research_gates_passed": all(
                    r["all_limited_ABF_seam_research_gates_passed"] for r in rows
                ),
            }
        )
    return {
        "schema": SCHEMA,
        "source_bisect_study_sha256": source_digest,
        "ABF_same_source_triangulation_tested": True,
        "matched_pair_2d_cut_seams_compared_independently": True,
        "options": results,
        "P3_status": "in_progress",
        "P4_status": "not_started",
        "factory_cutting_patterns_approved": 0,
        "original_crown_3d_visible_seam_or_ear_cloud_ownership_approved": False,
        "physical_sample_tested": False,
    }


def _raw(path):
    if not path.is_file() or path.is_symlink():
        raise ValueError("missing source evidence or symlinked input")
    return path.read_bytes()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-bisect", required=True, type=Path)
    parser.add_argument("--native", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise ValueError("refuse to overwrite real source ABF seam evidence")
    raw = _raw(args.source_bisect)
    outcome = audit(
        json.loads(raw),
        json.loads(_raw(args.native)),
        hashlib.sha256(raw).hexdigest(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(outcome, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(
        "STAGE6_ACTUAL_ORIGINAL_SIDE_MERIDIAN_ABF_TWO_SIDE_QA",
        json.dumps(
            {
                "routes": [r["route"] for r in outcome["options"]],
                "factory_approved": False,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
