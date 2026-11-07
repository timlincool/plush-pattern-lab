"""Pinned Stage6 B radial seams versus historic face registration, five views.

Outputs are a body-only proxy research SVG and front first-hit JSON, not a
design-approved sewing plan or source Blender asset.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from propose_stage6_shell_panels import PROXY_SHA256, load_pinned_proxy

from plush_pattern_lab.patterns.source_seam_view_svg import (
    render_source_seam_orthoview_svg,
)
from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256
from plush_pattern_lab.validation.seam_face_projection import audit_front_paths


def review_visible_b_routes(points, triangles, multi, face_registration):
    if (
        multi.get("schema") != "stage6-source-pinned-multi-disk-lscm-research-v1"
        or multi.get("source_blend_sha256") != SOURCE_SHA256
        or multi.get("source_proxy_sha256") != PROXY_SHA256
    ):
        raise ValueError("untrusted same-run Stage6 radial path evidence")
    candidates = [
        row for row in multi["candidates"] if row["candidate"] == "B_three_disks"
    ]
    if len(candidates) != 1 or len(candidates[0]["radial_seams"]) != 3:
        raise ValueError("missing exact source B three-disk radial paths")
    if not candidates[0]["all_3d_radial_seam_edges_paired_exactly"]:
        raise ValueError("original 3D radial sewing identity was lost")
    report = audit_front_paths(
        points, triangles, candidates[0]["radial_seams"], face_registration
    )
    if len(report["routes"]) != 3:
        raise ValueError("missing measured source radial path")
    report["source_original_blend_sha256"] = SOURCE_SHA256
    report["source_proxy_ply_sha256"] = PROXY_SHA256
    report["candidate"] = "B_three_disks"
    svg = render_source_seam_orthoview_svg(points, report, face_registration)
    return report, svg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--multidisk-summary", type=Path, required=True)
    parser.add_argument("--face-reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--svg", type=Path, required=True)
    args = parser.parse_args()
    if args.source_sha256 != SOURCE_SHA256:
        raise ValueError("not the immutable public Stage6 source SHA")
    if (
        args.multidisk_summary.suffix != ".json"
        or args.face_reference.suffix != ".json"
        or not args.multidisk_summary.is_file()
        or not args.face_reference.is_file()
    ):
        raise ValueError("missing real candidate JSON or historic facial data")
    if (
        args.output.suffix != ".json"
        or args.svg.suffix != ".svg"
        or args.output.exists()
        or args.svg.exists()
        or args.output.is_symlink()
        or args.svg.is_symlink()
        or args.output.resolve() == args.svg.resolve()
    ):
        raise ValueError("new and separate non-production JSON/SVG required")
    multi_bytes = args.multidisk_summary.read_bytes()
    reference_bytes = args.face_reference.read_bytes()
    summary = json.loads(multi_bytes)
    face = json.loads(reference_bytes)
    points, faces = load_pinned_proxy(args.input)
    report, svg = review_visible_b_routes(points, faces, summary, face)
    report["source_multidisk_summary_sha256"] = hashlib.sha256(multi_bytes).hexdigest()
    report["historical_face_reference_sha256"] = hashlib.sha256(
        reference_bytes
    ).hexdigest()
    svg_bytes = svg.encode("utf8")
    report["body_only_five_view_svg_sha256"] = hashlib.sha256(svg_bytes).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.svg.parent.mkdir(parents=True, exist_ok=True)
    args.svg.write_bytes(svg_bytes)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(
        "STAGE6_HISTORIC_FACE_SEAM_SOURCE_5VIEWS",
        json.dumps(
            [
                {
                    "path": item["path_id"],
                    "source_front_surface_samples": item[
                        "source_front_near_side_vertex_count"
                    ],
                    "historical_face_alert_samples": item[
                        "historical_front_face_feature_alert_vertex_count"
                    ],
                    "design_approved": False,
                }
                for item in report["routes"]
            ]
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
