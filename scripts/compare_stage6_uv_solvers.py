"""Compare real Stage6 B-three-disk source UV with bounded ARAP alternatives.

All variants use unchanged source PLY faces and original radial seam paths.
Output is research-only evidence, NOT a cutting pattern or industrial approval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from propose_stage6_shell_panels import PROXY_SHA256, load_pinned_proxy

from plush_pattern_lab.patterns.arap_unroll_candidate import (
    best_similarity_scale,
    solve_research_arap,
)
from plush_pattern_lab.patterns.mesh_lscm_candidate import (
    _intrinsic_triangles,
    _overlap_metrics,
    _strain_metrics,
)
from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

METHODS = ("LSCM", "ARAP_PCA", "ARAP_LSCM")
SOURCE_FACES = 36833


def _source_boundary(record, faces, source_ids):
    edge_ids = np.asarray(record["source_boundary_edges"], dtype=np.int64)
    if edge_ids.ndim != 2 or edge_ids.shape[1] != 2:
        raise ValueError("source boundary is not a list of exact edges")
    index = np.searchsorted(source_ids, edge_ids)
    if np.any(index >= len(source_ids)):
        raise ValueError("unknown source boundary vertex")
    if not np.array_equal(source_ids[index], edge_ids):
        raise ValueError("fabric boundary source vertex identity drifted")
    pair = np.concatenate((faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]))
    unique, counts = np.unique(np.sort(pair, axis=1), axis=0, return_counts=True)
    if not np.array_equal(
        unique[counts == 1], np.unique(np.sort(index, axis=1), axis=0)
    ):
        raise ValueError("original source boundary does not match triangle incidence")
    return index, edge_ids


def _source_roles(edges, quality):
    hoof = int(quality["source_original_hoof_edges"])
    outer = int(quality["source_original_outer_seam_edges"])
    radial = int(quality["source_radial_seam_edges"])
    if hoof <= 0 or outer <= 0 or radial <= 0 or len(edges) != hoof + outer + radial:
        raise ValueError("incomplete original hoof, outer or radial seam roles")
    return edges[:hoof], edges[hoof : hoof + outer], edges[hoof + outer :]


def _source_pin_ids(source_ids, boundary_edges, radial_paths):
    boundary = {tuple(sorted(pair)) for pair in boundary_edges.tolist()}
    for row in radial_paths:
        path = row["original_source_vertex_ids"]
        edges = [tuple(sorted((int(a), int(b)))) for a, b in zip(path[:-1], path[1:])]
        if all(edge in boundary for edge in edges):
            index = np.searchsorted(source_ids, [path[0], path[-1]])
            if np.any(index >= len(source_ids)):
                raise ValueError("original source pin path is no longer present")
            if not np.array_equal(source_ids[index], [path[0], path[-1]]):
                raise ValueError("source pin identity changed")
            return int(index[0]), int(index[1])
    raise ValueError("no original radial source path anchors a complete panel")


def _reconstruct_real_panel(points, all_faces, record, quality, radial_paths):
    ids = np.asarray(record["source_vertex_id_by_panel_uv_vertex"], dtype=np.int64)
    faces = np.asarray(record["panel_face_uv_vertex_ids"], dtype=np.int64)
    originals = np.asarray(record["source_face_id_by_panel_face"], dtype=np.int64)
    uv = np.asarray(record["panel_uv_vertex_mm"], dtype=np.float64)
    if not len(ids) or np.any(np.diff(ids) <= 0) or np.any(ids < 0):
        raise ValueError("source vertex identities must be sorted and unique")
    if np.any(ids >= len(points)) or np.any(originals < 0):
        raise ValueError("source identity exceeds the fixed public PLY")
    if np.any(originals >= len(all_faces)) or faces.shape != (len(originals), 3):
        raise ValueError("source face count or identity invalid")
    if np.any(faces < 0) or np.any(faces >= len(ids)):
        raise ValueError("untrusted local triangle vertex identity")
    if not np.array_equal(ids[faces], all_faces[originals]):
        raise ValueError("cut panel 3D faces differ from original public PLY")
    if uv.shape != (len(ids), 2) or not np.isfinite(uv).all():
        raise ValueError("invalid source-linked 2D coordinates")
    border, source_edges = _source_boundary(record, faces, ids)
    cuff, outer, radial = _source_roles(source_edges, quality)
    inner, end = _source_pin_ids(ids, source_edges, radial_paths)
    return {
        "points_xyz_mm": points[ids],
        "faces": faces,
        "boundary_edges": border,
        "source_vertex_ids": ids,
        "source_cuff_edges": len(cuff),
        "source_outer_seam_edges": len(outer),
        "source_cuff_edge_global_ids": cuff.tolist(),
        "source_outer_edge_global_ids": outer.tolist(),
        "source_slit_edge_global_ids": radial.tolist(),
        "slit_pin_inner_id": inner,
        "slit_pin_outer_id": end,
    }, uv


def _source_pair_lengths(disk, uv):
    ids = np.asarray(disk["source_vertex_ids"], dtype=np.int64)
    edges = np.asarray(disk["boundary_edges"], dtype=np.int64)
    original = np.sort(ids[edges], axis=1)
    lengths = np.linalg.norm(uv[edges[:, 1]] - uv[edges[:, 0]], axis=1)
    return {tuple(pair): float(length) for pair, length in zip(original, lengths)}


def _two_sided_radial_seams(radial_paths, mappings):
    measured = []
    for original in radial_paths:
        path = original["original_source_vertex_ids"]
        pairs = [tuple(sorted((int(a), int(b)))) for a, b in zip(path[:-1], path[1:])]
        sides = []
        for index, lengths in enumerate(mappings):
            present = [edge in lengths for edge in pairs]
            if any(present) and not all(present):
                raise ValueError("source-linked radial seam is only partially present")
            if all(present):
                sides.append(
                    {
                        "panel_id": index,
                        "candidate_2d_mm": sum(lengths[e] for e in pairs),
                    }
                )
        if len(sides) != 2:
            raise ValueError("original radial seam must have exactly two UV sides")
        measured.append(
            {
                "path_id": original["path_id"],
                "source_3d_mm": original["source_3d_length_mm"],
                "uv_panel_sides": sides,
                "two_side_uv_disagreement_mm": abs(
                    sides[0]["candidate_2d_mm"] - sides[1]["candidate_2d_mm"]
                ),
                "approved_for_manufacturing": False,
            }
        )
    return measured


def _quality(disk, uv):
    faces = np.asarray(disk["faces"], dtype=np.int64)
    charts = _intrinsic_triangles(disk["points_xyz_mm"], faces)
    strain = _strain_metrics(uv[faces], charts[:4])
    overlap = _overlap_metrics(uv[faces])
    return {
        "unique_edge_similarity_fit": best_similarity_scale(
            disk["points_xyz_mm"], faces, uv
        ),
        "raw_triangle_edge_relative_error_p95": strain["triangle_edge_relative_error"][
            "p95"
        ],
        "uv_flipped_faces": strain["inverted_winding_triangles"],
        "uv_near_zero_faces": strain["near_zero_uv_area_triangles"],
        "uv_nonzero_area_overlap_face_pairs": overlap[
            "overlapping_nonzero_area_triangle_pairs"
        ],
        "uv_overlap_search_truncated": overlap["overlap_search_truncated"],
        "approved_for_cutting": False,
    }


def _study_one(disk, old_uv, panel_id, iterations):
    solutions = {"LSCM": old_uv}
    diagnostics = {"LSCM": {"method": "existing_2_pin_LSCM_current_runner"}}
    for seed in ("pca", "lscm"):
        planar, method = solve_research_arap(
            disk, old_uv, iterations=iterations, seed=seed
        )
        label = "ARAP_" + seed.upper()
        solutions[label] = planar
        diagnostics[label] = method
    summary = {
        "panel_id": panel_id,
        "source_face_count": len(disk["faces"]),
        "methods": {
            name: {"geometry": _quality(disk, uv), "solver": diagnostics[name]}
            for name, uv in solutions.items()
        },
    }
    detail = {
        "panel_id": panel_id,
        "source_vertex_id_by_uv_vertex": disk["source_vertex_ids"].tolist(),
        "source_face_uv_indices": disk["faces"].tolist(),
        "method_uv_mm": {
            name: np.round(uv, 8).tolist() for name, uv in solutions.items()
        },
        "approved_for_cutting": False,
    }
    return (
        summary,
        detail,
        {name: _source_pair_lengths(disk, uv) for name, uv in solutions.items()},
    )


def compare_stage6_b_solvers(points, faces, summary, detail, iterations=30):
    if summary.get("schema") != "stage6-source-pinned-multi-disk-lscm-research-v1":
        raise ValueError("wrong trusted multi-disk summary schema")
    if summary.get("source_blend_sha256") != SOURCE_SHA256:
        raise ValueError("source Stage6 Blender SHA changed")
    if summary.get("source_proxy_sha256") != PROXY_SHA256:
        raise ValueError("source 25% PLY SHA changed")
    if detail.get("schema") != "stage6-source-pinned-multi-disk-face-uv-detail-v1":
        raise ValueError("source 2D detail is not the original full-face schema")
    a = next(c for c in summary["candidates"] if c["candidate"] == "B_three_disks")
    b = next(c for c in detail["candidates"] if c["candidate"] == "B_three_disks")
    if len(a["panel_uv_quality"]) != 3 or len(b["panels"]) != 3:
        raise ValueError("missing complete B three-disk reference")
    reports, linked, maps = [], [], {name: [] for name in METHODS}
    for quality, original in zip(a["panel_uv_quality"], b["panels"]):
        disk, old_uv = _reconstruct_real_panel(
            points, faces, original, quality, a["radial_seams"]
        )
        report, evidence, segments = _study_one(
            disk, old_uv, int(quality["panel_id"]), iterations
        )
        reports.append(report)
        linked.append(evidence)
        for name in METHODS:
            maps[name].append(segments[name])
    if sum(item["source_face_count"] for item in reports) != SOURCE_FACES:
        raise ValueError("source triangles missing from three-disk comparison")
    seam_report = {
        name: _two_sided_radial_seams(a["radial_seams"], maps[name]) for name in METHODS
    }
    return {
        "schema": "stage6-source-pinned-b-three-uv-solver-comparison-v1",
        "source_original_blend_sha256": SOURCE_SHA256,
        "source_proxy_sha256": PROXY_SHA256,
        "candidate": "B_three_disks",
        "full_source_region_faces": SOURCE_FACES,
        "methods": list(METHODS),
        "independent_panel_results": reports,
        "paired_original_radial_seams": seam_report,
        "LSCM_raw_and_scale_corrected_are_diagnostics_only": True,
        "ARAP_does_not_guarantee_global_nonoverlap": True,
        "visual_design_or_seam_placement_reviewed": False,
        "fabric_response_or_stuffing_measured": False,
        "production_cut_patterns_approved": 0,
    }, {
        "schema": "stage6-source-pinned-b-three-uv-solver-detail-v1",
        "source_original_blend_sha256": SOURCE_SHA256,
        "panels": linked,
        "approved_for_cutting": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--previous-summary", type=Path, required=True)
    parser.add_argument("--previous-detail", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--detail", type=Path, required=True)
    args = parser.parse_args()
    if args.source_sha256 != SOURCE_SHA256:
        raise ValueError("incorrect public original Blend identity")
    if args.previous_summary.suffix != ".json":
        raise ValueError("requires verified previous Stage6 JSON")
    if args.previous_detail.suffix != ".json":
        raise ValueError("requires verified prior Stage6 UV detail")
    if any(
        path.suffix != ".json" or path.exists() or path.is_symlink()
        for path in (args.summary, args.detail)
    ):
        raise ValueError("research outputs must be distinct unused JSON paths")
    if args.summary.resolve() == args.detail.resolve():
        raise ValueError("research outputs cannot overwrite each other")
    previous = args.previous_detail.read_bytes()
    source = json.loads(args.previous_summary.read_text(encoding="utf8"))
    if source.get("detail_sha256") != hashlib.sha256(previous).hexdigest():
        raise ValueError("trusted current-run multi-panel UV detail SHA mismatch")
    xyz, faces = load_pinned_proxy(args.input)
    result, detail = compare_stage6_b_solvers(xyz, faces, source, json.loads(previous))
    packed = (json.dumps(detail, ensure_ascii=False) + "\n").encode("utf8")
    result["detail_sha256"] = hashlib.sha256(packed).hexdigest()
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.detail.parent.mkdir(parents=True, exist_ok=True)
    args.detail.write_bytes(packed)
    args.summary.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(
        "STAGE6_RESEARCH_LSCM_ARAP_THREE_DISK_SOLVER_AB",
        json.dumps(
            [
                {
                    "panel": row["panel_id"],
                    "methods": {
                        name: {
                            "p95": value["geometry"][
                                "raw_triangle_edge_relative_error_p95"
                            ],
                            "overlaps": value["geometry"][
                                "uv_nonzero_area_overlap_face_pairs"
                            ],
                            "flips": value["geometry"]["uv_flipped_faces"],
                        }
                        for name, value in row["methods"].items()
                    },
                }
                for row in result["independent_panel_results"]
            ]
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
