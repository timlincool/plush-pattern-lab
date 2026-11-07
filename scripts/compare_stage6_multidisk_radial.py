"""Pinned Stage6 real left-front additional radial panels and complete LSCM QA.

A and B differ ONLY in source-mesh radial path geometry and panel count.
Every output is research-only. There is NO fabric, silhouette, or seam approval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from propose_stage6_shell_panels import PROXY_SHA256, load_pinned_proxy
from unroll_stage6_leftfront import _source_region

from plush_pattern_lab.patterns.mesh_lscm_candidate import flatten_cut_panel
from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256
from plush_pattern_lab.validation.multi_radial_panels import (
    split_annulus_by_radial_paths,
)
from plush_pattern_lab.validation.real_panel_slit import slit_real_panel

TRIALS = (
    ("A_two_disks", ((0.5, 220.0),)),
    ("B_three_disks", ((2 / 3, 220.0), (0.5, 190.0))),
)
FACES = 36833
CUTOFF_CUFF = 512


def _verified_baseline(xyz, faces, baseline):
    if (
        baseline.get("schema") != "stage6-leftfront-whole-panel-lscm-v1"
        or baseline.get("source_original_model_sha256") != SOURCE_SHA256
        or baseline.get("topology", {}).get("original_annulus_faces") != FACES
        or baseline.get("topology", {}).get("source_cuff_edges") != CUTOFF_CUFF
        or baseline.get("status") != "REJECTED_FOR_DIRECT_SINGLE_PIECE"
    ):
        raise ValueError("untrusted original leftfront full-panel baseline")
    selected = _source_region(xyz, faces)
    disk = slit_real_panel(xyz, faces, selected, CUTOFF_CUFF)
    source_ids = disk["slit_path_source_vertex_ids"].tolist()
    if source_ids != baseline.get("slit_path_original_vertex_ids"):
        raise ValueError("baseline 3D cut path differs from pinned current source")
    if disk["cut_disk_euler"] != 1:
        raise ValueError("original slit did not create a true disk")
    return selected, source_ids


def _panel_uv_edges(panel, score, uv):
    edges = np.asarray(score["boundary"]["boundary_edge_uv_ids"], dtype=int)
    ids = np.asarray(score["boundary"]["boundary_edge_source_vertex_ids"])
    lengths = np.linalg.norm(uv[edges[:, 1]] - uv[edges[:, 0]], axis=1)
    return {
        tuple(sorted((int(a), int(b)))): float(length)
        for (a, b), length in zip(ids, lengths)
    }


def _path_sides_in_panel(source_paths, lookup, panel_index):
    result = {}
    for index, path in enumerate(source_paths):
        pairs = [
            tuple(sorted((int(a), int(b))))
            for a, b in zip(path[:-1], path[1:])
        ]
        present = [edge in lookup for edge in pairs]
        if any(present) and not all(present):
            raise ValueError("a radial seam is partly absent from one 2D panel")
        if all(present):
            result[str(index)] = {
                "panel_id": panel_index,
                "edge_count": len(pairs),
                "uv_seam_length_mm": sum(lookup[edge] for edge in pairs),
                "not_a_material_seam_measurement": True,
            }
    return result


def _score_one_panel(panel, source_paths, index):
    result, uv = flatten_cut_panel(panel, iteration_cap=8000)
    lookup = _panel_uv_edges(panel, result, uv)
    quality = result["strain_screen"]
    summary = {
        "panel_id": index,
        "source_faces": panel["face_count"],
        "source_vertices": panel["vertex_count"],
        "topological_disk_euler": panel["disk_euler"],
        "source_boundary_edges": panel["boundary_edge_count"],
        "source_original_hoof_edges": panel["source_cuff_edges"],
        "source_original_outer_seam_edges": panel["source_outer_seam_edges"],
        "source_radial_seam_edges": len(panel["source_slit_edge_global_ids"]),
        "status": result["status"],
        "solver": result["solver"],
        "triangle_edge_relative_error": quality["triangle_edge_relative_error"],
        "uv_flipped_triangles": quality["inverted_winding_triangles"],
        "uv_near_zero_triangles": quality["near_zero_uv_area_triangles"],
        "uv_positive_area_overlaps": result["global_2d_overlap"][
            "overlapping_nonzero_area_triangle_pairs"
        ],
        "uv_overlap_search_truncated": result["global_2d_overlap"][
            "overlap_search_truncated"
        ],
        "original_to_uv_boundary": result["boundary"]["perimeter_by_source_role"],
        "uv_seam_sides": _path_sides_in_panel(source_paths, lookup, index),
        "approved_for_fabric_cutting": False,
    }
    detail = {
        "panel_id": index,
        "source_face_id_by_panel_face": panel["source_face_ids"].tolist(),
        "source_vertex_id_by_panel_uv_vertex": panel["source_vertex_ids"].tolist(),
        "panel_face_uv_vertex_ids": panel["faces"].tolist(),
        "panel_uv_vertex_mm": np.round(uv, 8).tolist(),
        "source_boundary_edges": panel["source_cuff_edge_global_ids"]
        + panel["source_outer_edge_global_ids"]
        + panel["source_slit_edge_global_ids"],
        "approved_for_fabric_cutting": False,
    }
    return summary, detail


def _paired_radial_sides(source_paths, path_lengths, panels):
    rows = []
    for index, path in enumerate(source_paths):
        sides = [
            row["uv_seam_sides"][str(index)]
            for row in panels
            if str(index) in row["uv_seam_sides"]
        ]
        if len(sides) != 2 or any(
            side["edge_count"] != len(path) - 1 for side in sides
        ):
            raise ValueError("new radial seam was not tracked on both UV panels")
        rows.append(
            {
                "path_id": index,
                "original_source_vertex_ids": path.tolist(),
                "source_3d_length_mm": path_lengths[index],
                "endpoint_source_xyz_mm": None,
                "panel_sides": sides,
                "candidate_2d_side_length_difference_mm": abs(
                    sides[0]["uv_seam_length_mm"]
                    - sides[1]["uv_seam_length_mm"]
                ),
                "both_3d_sides_have_same_source_edges": True,
            }
        )
    return rows


def _trial(xyz, faces, selected, base_path, title, extra):
    candidate = split_annulus_by_radial_paths(
        xyz, faces, selected, base_path, extra
    )
    summaries = []
    details = []
    for index, panel in enumerate(candidate["panels"]):
        summary, detail = _score_one_panel(
            panel, candidate["source_paths"], index
        )
        summaries.append(summary)
        details.append(detail)
    paired = _paired_radial_sides(
        candidate["source_paths"],
        candidate["path_lengths_3d_mm"],
        summaries,
    )
    for seam in paired:
        path = seam["original_source_vertex_ids"]
        seam["endpoint_source_xyz_mm"] = np.round(
            xyz[[path[0], path[-1]]], 4
        ).tolist()
    face_counts = [p["face_count"] for p in candidate["panels"]]
    result = {
        "candidate": title,
        "radial_route_constraints": candidate["research_extra_specs"],
        "result": "REJECTED_FOR_FABRIC_CUTTING_RESEARCH_ONLY",
        "disk_count": len(candidate["panels"]),
        "all_source_faces_preserved_once": sum(face_counts) == FACES,
        "individual_panel_face_counts": face_counts,
        "largest_panel_fraction": max(face_counts) / FACES,
        "all_3d_radial_seam_edges_paired_exactly": candidate[
            "source_3d_seams_exactly_paired"
        ],
        "total_original_radial_seam_mm": sum(
            candidate["path_lengths_3d_mm"]
        ),
        "extra_radial_seam_mm": sum(
            candidate["path_lengths_3d_mm"][1:]
        ),
        "radial_seams": paired,
        "panel_uv_quality": summaries,
        "design_visible_seam_review": "NOT_REVIEWED",
        "fabric_mechanics": "NOT_MEASURED",
        "facing_and_assembly": "NOT_APPROVED",
        "approved_for_cutting": False,
    }
    return result, {"candidate": title, "panels": details}


def run_real_radial_ab(xyz, faces, baseline):
    selected, original_slit = _verified_baseline(xyz, faces, baseline)
    summaries, details = [], []
    for title, extra in TRIALS:
        summary, detail = _trial(
            xyz, faces, selected, original_slit, title, extra
        )
        summaries.append(summary)
        details.append(detail)
    return {
        "schema": "stage6-source-pinned-multi-disk-lscm-research-v1",
        "source_blend_sha256": SOURCE_SHA256,
        "source_proxy_sha256": PROXY_SHA256,
        "source_original_leftfront_faces": FACES,
        "source_original_hoof_open_ring_edges": CUTOFF_CUFF,
        "baseline_status": baseline["status"],
        "status": "RESEARCH_ONLY_NO_FABRIC_STENCILS",
        "candidates": summaries,
        "source_unchanged": True,
        "design_visible_seams_not_yet_checked": True,
        "factory_material_approval_missing": True,
        "approved_cutting_patterns": 0,
    }, {
        "schema": "stage6-source-pinned-multi-disk-face-uv-detail-v1",
        "source_blend_sha256": SOURCE_SHA256,
        "candidates": details,
        "approved_for_cutting": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--detail", type=Path, required=True)
    args = parser.parse_args()
    if args.source_sha256 != SOURCE_SHA256:
        raise ValueError("invalid public source identity")
    if args.baseline.suffix != ".json" or not args.baseline.is_file():
        raise ValueError("missing trusted current-run baseline JSON")
    if any(
        path.suffix != ".json" or path.exists() or path.is_symlink()
        for path in (args.summary, args.detail)
    ):
        raise ValueError("research JSON must be new, separate unused files")
    if args.summary.resolve() == args.detail.resolve():
        raise ValueError("research output paths must be distinct")
    points, faces = load_pinned_proxy(args.input)
    baseline = json.loads(args.baseline.read_text(encoding="utf8"))
    summary, detail = run_real_radial_ab(points, faces, baseline)
    payload = (json.dumps(detail, ensure_ascii=False) + "\n").encode()
    summary["detail_sha256"] = hashlib.sha256(payload).hexdigest()
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.detail.parent.mkdir(parents=True, exist_ok=True)
    args.detail.write_bytes(payload)
    args.summary.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf8",
    )
    print(
        "STAGE6_REAL_MULTI_DISK_RADIAL_UV_RESEARCH",
        json.dumps([
            {
                "name": c["candidate"],
                "face_counts": c["individual_panel_face_counts"],
                "extra_seam_mm": c["extra_radial_seam_mm"],
                "panel_rejections": [
                    row["status"] for row in c["panel_uv_quality"]
                ],
                "uv_overlap_pairs": [
                    row["uv_positive_area_overlaps"] for row in c["panel_uv_quality"]
                ],
                "approved_for_cutting": False,
            }
            for c in summary["candidates"]
        ]),
        flush=True,
    )


if __name__ == "__main__":
    main()
