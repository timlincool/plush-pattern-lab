"""Real Stage6 alternative B-high2 source-edge routes and full LSCM rejection QA.

C ends below historic face; D ends on a lateral upper source boundary.
Research candidates only: no material approval or official design seam.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from compare_stage6_multidisk_radial import _paired_radial_sides, _score_one_panel
from propose_stage6_shell_panels import PROXY_SHA256, load_pinned_proxy
from unroll_stage6_leftfront import _source_region

from plush_pattern_lab.patterns.source_seam_view_svg import (
    render_source_seam_orthoview_svg,
)
from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256
from plush_pattern_lab.validation.seam_face_projection import audit_front_paths
from plush_pattern_lab.validation.stage6_b_face_reroute import (
    EXPECTED_REGION_FACES,
    reroute_original_b_high2,
)


def _trusted_previous(raw, old_face, current_hash):
    if (
        raw.get("schema") != "stage6-source-pinned-multi-disk-lscm-research-v1"
        or raw.get("source_blend_sha256") != SOURCE_SHA256
        or raw.get("source_proxy_sha256") != PROXY_SHA256
        or old_face.get("schema")
        != "stage6-pinned-source-front-shell-historical-face-v14-review-v1"
        or old_face.get("source_multidisk_summary_sha256") != current_hash
    ):
        raise ValueError("original B source paths and historic face are not same-run")
    if old_face.get("source_original_blend_sha256") != SOURCE_SHA256:
        raise ValueError("original source face report is not the public Stage6 source")
    candidates = [r for r in raw["candidates"] if r["candidate"] == "B_three_disks"]
    if len(candidates) != 1:
        raise ValueError("missing current B_three_disks source data")
    candidate = candidates[0]
    if candidate["individual_panel_face_counts"] != [20915, 6904, 9014]:
        raise ValueError("source B original face topology changed")
    if not candidate["all_3d_radial_seam_edges_paired_exactly"]:
        raise ValueError("unpaired original B source edge")
    return candidate["radial_seams"]


def _source_path_records(source_paths, lengths):
    return [
        {
            "path_id": k,
            "original_source_vertex_ids": path.tolist(),
            "source_3d_length_mm": length,
        }
        for k, (path, length) in enumerate(zip(source_paths, lengths))
    ]


def _score_candidate(xyz, faces, source, historic, trial):
    quality, uv_detail = [], []
    for index, panel in enumerate(trial["panels"]):
        row, detail = _score_one_panel(panel, trial["source_paths"], index)
        quality.append(row)
        uv_detail.append(detail)
    seams = _paired_radial_sides(
        trial["source_paths"], trial["path_lengths_3d_mm"], quality
    )
    route_records = _source_path_records(
        trial["source_paths"], trial["path_lengths_3d_mm"]
    )
    face_review = audit_front_paths(xyz, faces, route_records, historic)
    new_path = trial["source_paths"][2]
    new_xyz = xyz[new_path]
    warnings = face_review["routes"][2][
        "historical_front_face_feature_alert_vertex_count"
    ]
    summary = {
        "candidate": trial["candidate"],
        "result": "RESEARCH_REJECTED_FOR_CUTTING_PENDING_REAL_FABRIC",
        "target_research_constraints": trial["target_research_constraints"],
        "original_B_first_two_source_paths_exact": trial[
            "source_original_B_prefix_paths_exact"
        ],
        "original_source_faces_preserved_once": (
            trial["source_face_count"] == EXPECTED_REGION_FACES
        ),
        "original_source_faces": trial["source_face_count"],
        "source_panels": [row["face_count"] for row in trial["panels"]],
        "three_single_boundary_euler_one_disks": all(
            p["disk_euler"] == 1 for p in trial["panels"]
        ),
        "real_source_3d_radial_seams_paired": trial[
            "source_3d_radial_seam_edges_exactly_paired"
        ],
        "source_original_radial_paths_3d_mm": trial["path_lengths_3d_mm"],
        "original_radial_seams": seams,
        "new_path_source_vertex_ids": new_path.tolist(),
        "new_path_start_end_xyz_mm": np.round(new_xyz[[0, -1]], 4).tolist(),
        "new_path_bbox_min_max_xyz_mm": [
            np.round(new_xyz.min(axis=0), 4).tolist(),
            np.round(new_xyz.max(axis=0), 4).tolist(),
        ],
        "source_body_front_historic_face": face_review,
        "new_path_historic_v14_feature_alerts": warnings,
        "all_original_source_panel_2d_lscm_qa": quality,
        "full_product_mesh_occlusion_not_yet_proven": True,
        "cutting_patterns_approved": 0,
    }
    detail = {
        "candidate": trial["candidate"],
        "per_panel_source_face_ids_and_uv": uv_detail,
        "historic_source_body_front_review": face_review,
        "approved_for_cutting": False,
    }
    svg = render_source_seam_orthoview_svg(xyz, face_review, historic)
    return summary, detail, svg


def run_actual_source_reroute_ab(xyz, faces, previous, previous_face, historic, current_hash):
    routes = _trusted_previous(previous, previous_face, current_hash)
    selected = _source_region(xyz, faces)
    trials = reroute_original_b_high2(xyz, faces, selected, routes)
    results, details, svg = [], [], {}
    for trial in trials:
        row, detail, plot = _score_candidate(xyz, faces, routes, historic, trial)
        results.append(row)
        details.append(detail)
        svg[trial["candidate"]] = plot
    return {
        "schema": "stage6-source-linked-B-high2-anatomic-avoidance-ab-v1",
        "source_original_blend_sha256": SOURCE_SHA256,
        "source_proxy_ply_sha256": PROXY_SHA256,
        "original_B_current_run_summary_sha256": current_hash,
        "source_faces": EXPECTED_REGION_FACES,
        "candidates": results,
        "historical_v14_face_not_design_approved": True,
        "original_41_Mesh_visibility_to_be_checked_in_next_step": True,
        "cannot_use_lscm_failure_as_approved_fabric_rest": True,
        "approved_industrial_cutting_patterns": 0,
    }, {
        "schema": "stage6-source-linked-B-high2-anatomic-avoidance-detail-v1",
        "source_original_blend_sha256": SOURCE_SHA256,
        "candidates": details,
        "approved_for_cutting": False,
    }, svg


def _validate_output_paths(args):
    destinations = [
        args.summary, args.detail, args.svg_dir / "C_low_neck_boundary.svg",
        args.svg_dir / "D_lateral_high_boundary.svg",
    ]
    if (
        args.summary.suffix != ".json"
        or args.detail.suffix != ".json"
        or args.svg_dir.is_symlink()
        or len(set(p.resolve() for p in destinations)) != len(destinations)
        or any(p.exists() or p.is_symlink() for p in destinations)
    ):
        raise ValueError("must use fresh distinct source-only research outputs")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--proxy", type=Path, required=True)
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--previous-summary", type=Path, required=True)
    p.add_argument("--previous-face", type=Path, required=True)
    p.add_argument("--historic-face", type=Path, required=True)
    p.add_argument("--summary", type=Path, required=True)
    p.add_argument("--detail", type=Path, required=True)
    p.add_argument("--svg-dir", type=Path, required=True)
    a = p.parse_args()
    if a.source_sha256 != SOURCE_SHA256:
        raise ValueError("not the pinned public source model SHA")
    _validate_output_paths(a)
    raw = a.previous_summary.read_bytes()
    old = json.loads(raw)
    old_face = json.loads(a.previous_face.read_text(encoding="utf8"))
    historic_bytes = a.historic_face.read_bytes()
    historic = json.loads(historic_bytes)
    xyz, faces = load_pinned_proxy(a.proxy)
    summary, detail, images = run_actual_source_reroute_ab(
        xyz, faces, old, old_face, historic, hashlib.sha256(raw).hexdigest()
    )
    summary["historical_face_v14_sha256"] = hashlib.sha256(historic_bytes).hexdigest()
    detail_bytes = (json.dumps(detail, ensure_ascii=False) + "\n").encode()
    summary["detail_sha256"] = hashlib.sha256(detail_bytes).hexdigest()
    a.summary.parent.mkdir(parents=True, exist_ok=True)
    a.detail.parent.mkdir(parents=True, exist_ok=True)
    a.svg_dir.mkdir(parents=True, exist_ok=True)
    a.detail.write_bytes(detail_bytes)
    for name, image in images.items():
        (a.svg_dir / f"{name}.svg").write_text(image, encoding="utf8")
    a.summary.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf8",
    )
    print(
        "STAGE6_SOURCE_B_HIGH2_FACE_AVOIDANCE_AB_RESEARCH",
        json.dumps(
            [
                {
                    "name": x["candidate"],
                    "face_counts": x["source_panels"],
                    "source_seam_mm": x["source_original_radial_paths_3d_mm"][2],
                    "historic_v14_face_alerts": x["new_path_historic_v14_feature_alerts"],
                    "uv_overlap_pairs": [
                        p["uv_positive_area_overlaps"]
                        for p in x["all_original_source_panel_2d_lscm_qa"]
                    ],
                    "approved": False,
                }
                for x in summary["candidates"]
            ]
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
