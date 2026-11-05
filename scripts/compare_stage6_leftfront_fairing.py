"""Compare two seam-locked 3D fairing proposals on PINNED real Stage6 PLY.

No overwrite, no approved fabric cut, no external scripts or editable assets.
Both proposals are recomputed from the original geometry, not in sequence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from propose_stage6_shell_panels import PROXY_SHA256, load_pinned_proxy
from unroll_stage6_leftfront import REAL_CUFF_EDGES, REAL_FACES, _source_region

from plush_pattern_lab.patterns.mesh_lscm_candidate import flatten_cut_panel
from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256
from plush_pattern_lab.validation.intrinsic_curvature_screen import (
    audit_intrinsic_curvature,
)
from plush_pattern_lab.validation.manufacturing_surface_ab import (
    fair_manufacturing_surface,
)
from plush_pattern_lab.validation.real_panel_slit import slit_real_panel

TRIALS = (
    ("A_light", 3, 0.2, 0.25),
    ("B_strong", 5, 0.35, 0.5),
)
EXPECTED_REGION_VERTICES = 18913


def _base_and_protected(xyz, faces):
    selected = _source_region(xyz, faces)
    disk = slit_real_panel(xyz, faces, selected, REAL_CUFF_EDGES)
    if (
        disk["original_annulus_vertices"] != EXPECTED_REGION_VERTICES
        or disk["original_annulus_faces"] != REAL_FACES
        or disk["cut_disk_euler"] != 1
    ):
        raise ValueError("Stage6 region, source seams or slit topology drifted")
    used = np.unique(np.asarray(faces, dtype=np.int64)[selected].ravel())
    mapping = np.full(len(xyz), -1, dtype=np.int64)
    mapping[used] = np.arange(len(used))
    local_faces = mapping[np.asarray(faces, dtype=np.int64)[selected]]
    disk_ids = np.asarray(disk["source_vertex_ids"], dtype=np.int64)
    boundary = np.asarray(disk["boundary_edges"], dtype=np.int64)
    fixed_source = np.unique(disk_ids[boundary.ravel()])
    fixed = mapping[fixed_source]
    if np.any(fixed < 0) or len(fixed) != 1024:
        raise ValueError("expected original hoof, outer, and radial slit source IDs")
    return disk, used, local_faces, fixed


def _flatten_metrics(disk):
    score, _ = flatten_cut_panel(disk, iteration_cap=8000)
    return {
        "status": score["status"],
        "solver": score["solver"],
        "edge_relative_error": score["strain_screen"]["triangle_edge_relative_error"],
        "flipped_triangles": score["strain_screen"]["inverted_winding_triangles"],
        "near_zero_uv_triangles": score["strain_screen"]["near_zero_uv_area_triangles"],
        "positive_area_overlapping_triangle_pairs": score["global_2d_overlap"][
            "overlapping_nonzero_area_triangle_pairs"
        ],
        "overlap_search_truncated": score["global_2d_overlap"][
            "overlap_search_truncated"
        ],
        "boundary_perimeter_by_original_role": score["boundary"][
            "perimeter_by_source_role"
        ],
        "rejection_reasons": score["rejection_reasons"],
        "approved_cutting_pattern": False,
    }


def _trial(xyz, disk, used, local_faces, fixed, spec):
    name, steps, alpha, cap = spec
    proposal, geometry = fair_manufacturing_surface(
        xyz[used],
        local_faces,
        fixed,
        steps=steps,
        alpha=alpha,
        max_shift_mm=cap,
    )
    whole = xyz.copy()
    whole[used] = proposal
    disk_ids = np.asarray(disk["source_vertex_ids"], dtype=np.int64)
    modified = {**disk, "points_xyz_mm": whole[disk_ids]}
    baseline_boundary = np.asarray(disk["boundary_edges"], dtype=np.int64)
    if not np.array_equal(
        modified["points_xyz_mm"][baseline_boundary],
        np.asarray(disk["points_xyz_mm"])[baseline_boundary],
    ):
        raise ValueError("original 3D hoof, outer or slit seam changed")
    return {
        "trial": name,
        "three_dimensional_surface": geometry,
        "intrinsic_curvature_screen": audit_intrinsic_curvature(modified),
        "two_dimensional_full_panel_lscm": _flatten_metrics(modified),
        "source_face_topology_unchanged": True,
        "all_original_sewing_seam_coordinates_exact": True,
        "accepted_for_production": False,
    }


def run_real_surface_ab(xyz, faces, baseline):
    disk, used, local_faces, fixed = _base_and_protected(xyz, faces)
    if (
        baseline.get("schema") != "stage6-leftfront-whole-panel-lscm-v1"
        or baseline.get("source_original_model_sha256") != SOURCE_SHA256
        or baseline.get("topology", {}).get("original_annulus_faces") != REAL_FACES
        or baseline.get("status") != "REJECTED_FOR_DIRECT_SINGLE_PIECE"
    ):
        raise ValueError("unverified current-run original LSCM baseline")
    base_uv = baseline["geometry_quality"]
    trials = [_trial(xyz, disk, used, local_faces, fixed, spec) for spec in TRIALS]
    return {
        "schema": "stage6-real-leftfront-seam-locked-surface-ab-v1",
        "source_original_blend_sha256": SOURCE_SHA256,
        "input_proxy_sha256": PROXY_SHA256,
        "research_region": "left_front",
        "source_region_faces": REAL_FACES,
        "source_region_vertices": EXPECTED_REGION_VERTICES,
        "source_protected_3d_vertices": len(fixed),
        "baseline": {
            "curvature": audit_intrinsic_curvature(disk),
            "uv_status": baseline["status"],
            "uv_p95_relative_edge_error": base_uv["strain_screen"][
                "triangle_edge_relative_error"
            ]["p95"],
            "uv_positive_area_overlap_pairs": base_uv["global_2d_overlap"][
                "overlapping_nonzero_area_triangle_pairs"
            ],
        },
        "trials": trials,
        "original_reference_model_untouched": True,
        "candidate_is_not_independent_blender_bvh_or_silhouette_verified": True,
        "no_material_response_or_dart_layout_validated": True,
        "manufacturer_seam_or_cut_pattern_approved": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.source_sha256 != SOURCE_SHA256:
        raise ValueError("unexpected source model identity")
    if (
        args.input.suffix != ".ply"
        or args.baseline.suffix != ".json"
        or args.output.suffix != ".json"
        or args.output.exists()
        or args.output.is_symlink()
    ):
        raise ValueError("requires pinned PLY, baseline JSON and unused JSON output")
    xyz, faces = load_pinned_proxy(args.input)
    baseline = json.loads(args.baseline.read_text(encoding="utf8"))
    result = run_real_surface_ab(xyz, faces, baseline)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf8",
    )
    print(
        "STAGE6_REAL_LEFTFRONT_MANUFACTURING_SURFACE_AB",
        json.dumps(
            [
                {
                    "trial": item["trial"],
                    "curvature_p95_degrees": item["intrinsic_curvature_screen"][
                        "abs_defect_degrees_p95"
                    ],
                    "surface_area_ratio_min": item["three_dimensional_surface"][
                        "face_area_ratio_min"
                    ],
                    "uv_edge_error_p95": item["two_dimensional_full_panel_lscm"][
                        "edge_relative_error"
                    ]["p95"],
                    "uv_overlap_pairs": item["two_dimensional_full_panel_lscm"][
                        "positive_area_overlapping_triangle_pairs"
                    ],
                    "approved_for_cutting": False,
                }
                for item in result["trials"]
            ]
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
