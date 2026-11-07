"""Pinned Stage6 B-three-disk convex-border Tutte control; NEVER a cut pattern.

Checks original source face/vertex IDs and every shared source radial seam. Full
UV overlap, flips and distortion are independently reported, not inferred.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from compare_stage6_uv_solvers import (
    _quality,
    _reconstruct_real_panel,
    _source_pair_lengths,
    _two_sided_radial_seams,
)
from propose_stage6_shell_panels import PROXY_SHA256, load_pinned_proxy

from plush_pattern_lab.patterns.tutte_disk_candidate import tutte_convex_disk_candidate
from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

EXPECTED_SOURCE_FACES = 36833


def compare_real_b_tutte(points, faces, baseline, detailed):
    if (
        baseline.get("schema") != "stage6-source-pinned-multi-disk-lscm-research-v1"
        or baseline.get("source_blend_sha256") != SOURCE_SHA256
        or baseline.get("source_proxy_sha256") != PROXY_SHA256
        or detailed.get("schema") != "stage6-source-pinned-multi-disk-face-uv-detail-v1"
        or detailed.get("source_blend_sha256") != SOURCE_SHA256
    ):
        raise ValueError("untrusted original Stage6 B-three source-link schema")
    summary = next(
        x for x in baseline["candidates"] if x["candidate"] == "B_three_disks"
    )
    detail = next(
        x for x in detailed["candidates"] if x["candidate"] == "B_three_disks"
    )
    if len(summary["panel_uv_quality"]) != 3 or len(detail["panels"]) != 3:
        raise ValueError("missing B-three source-linked original panel")
    reports, detailed_uv, side_lengths = [], [], []
    for evidence, record in zip(summary["panel_uv_quality"], detail["panels"]):
        disk, _ = _reconstruct_real_panel(
            points, faces, record, evidence, summary["radial_seams"]
        )
        uv, method = tutte_convex_disk_candidate(disk)
        geometry = _quality(disk, uv)
        reports.append(
            {
                "panel_id": int(evidence["panel_id"]),
                "original_source_face_count": len(disk["faces"]),
                "source_face_ids_unchanged": True,
                "solver": method,
                "uv_qa": geometry,
                "research_cut_status": "REJECTED_NOT_FABRIC_AT_REST",
                "approved_for_cutting": False,
            }
        )
        detailed_uv.append(
            {
                "panel_id": int(evidence["panel_id"]),
                "source_face_ids": record["source_face_id_by_panel_face"],
                "source_vertex_ids": disk["source_vertex_ids"].tolist(),
                "faces_uv_indices": disk["faces"].tolist(),
                "tutte_uv_mm": np.round(uv, 8).tolist(),
                "approved_for_cutting": False,
            }
        )
        side_lengths.append(_source_pair_lengths(disk, uv))
    if (
        sum(item["original_source_face_count"] for item in reports)
        != EXPECTED_SOURCE_FACES
    ):
        raise ValueError("real source face IDs lost during convex boundary mapping")
    paired = _two_sided_radial_seams(summary["radial_seams"], side_lengths)
    return {
        "schema": "stage6-source-pinned-tutte-bthree-control-v1",
        "source_original_blend_sha256": SOURCE_SHA256,
        "source_proxy_sha256": PROXY_SHA256,
        "candidate": "B_three_disks",
        "full_original_source_face_count": EXPECTED_SOURCE_FACES,
        "panels": reports,
        "paired_original_source_radial_seams": paired,
        "boundary_seams_forced_to_near_source_lengths_by_construction": True,
        "does_not_approximate_real_fabric_rest_shapes": True,
        "face_and_attachment_design_visibility_unreviewed": True,
        "approved_industrial_paper_patterns": 0,
    }, {
        "schema": "stage6-source-pinned-tutte-bthree-face-uv-detail-v1",
        "source_original_blend_sha256": SOURCE_SHA256,
        "panels": detailed_uv,
        "approved_for_cutting": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--prior-summary", type=Path, required=True)
    parser.add_argument("--prior-detail", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--detail", type=Path, required=True)
    args = parser.parse_args()
    if args.source_sha256 != SOURCE_SHA256:
        raise ValueError("unexpected original public Blender identity")
    if args.prior_summary.suffix != ".json" or args.prior_detail.suffix != ".json":
        raise ValueError("prior research must be current-run JSON")
    if any(
        x.suffix != ".json" or x.exists() or x.is_symlink()
        for x in (args.summary, args.detail)
    ):
        raise ValueError("research outputs must be unused, distinct JSON paths")
    if args.summary.resolve() == args.detail.resolve():
        raise ValueError("research output identities must be distinct")
    previous_bytes = args.prior_detail.read_bytes()
    previous_summary = json.loads(args.prior_summary.read_text(encoding="utf8"))
    if (
        previous_summary.get("detail_sha256")
        != hashlib.sha256(previous_bytes).hexdigest()
    ):
        raise ValueError("source linked real UV detail hash does not match its summary")
    xyz, faces = load_pinned_proxy(args.input)
    report, detail = compare_real_b_tutte(
        xyz, faces, previous_summary, json.loads(previous_bytes)
    )
    payload = (json.dumps(detail, ensure_ascii=False) + "\n").encode("utf8")
    report["detail_sha256"] = hashlib.sha256(payload).hexdigest()
    args.detail.parent.mkdir(parents=True, exist_ok=True)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.detail.write_bytes(payload)
    args.summary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(
        "STAGE6_TUTTE_CONVEX_BORDER_THREE_DISK_RESEARCH",
        json.dumps(
            [
                {
                    "panel_id": row["panel_id"],
                    "p95_triangle_edge_error": row["uv_qa"][
                        "raw_triangle_edge_relative_error_p95"
                    ],
                    "uv_overlap_pairs": row["uv_qa"][
                        "uv_nonzero_area_overlap_face_pairs"
                    ],
                    "uv_flips": row["uv_qa"]["uv_flipped_faces"],
                    "factory_approved": False,
                }
                for row in report["panels"]
            ]
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
