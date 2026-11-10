"""Reconstruct true Stage6 triangle-plane loop topology vs source-informed A/B.

Writes geometry evidence only. Original public Blender, proxy, and already
generated A/B source trial bytes must match the trusted main runner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from propose_stage6_shell_panels import PROXY_SHA256, load_pinned_proxy

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256
from plush_pattern_lab.validation.stage6_source_contour_vs_trial import (
    compare_true_contours_to_split_study,
    render_true_source_contours_svg,
)
from plush_pattern_lab.validation.stage6_true_source_contours import (
    real_source_section_series,
)


def _inputs(args):
    if args.source_sha256 != SOURCE_SHA256:
        raise ValueError("not the original public source SHA")
    if not args.trial.is_file() or args.trial.is_symlink():
        raise ValueError("same-run original torso-head A/B study is missing")
    output = (args.summary, args.detail, args.svg)
    if (
        len({p.resolve() for p in output}) != 3
        or any(p.exists() or p.is_symlink() for p in output)
        or args.summary.suffix != ".json"
        or args.detail.suffix != ".json"
        or args.svg.suffix != ".svg"
    ):
        raise ValueError("refuse to replace source geometric audit assets")


def _compact(real):
    return [
        {
            "source_plane_z_mm": item["plane_z_mm"],
            "actual_original_closed_contour_count": item[
                "true_source_plane_intersection_component_count"
            ],
            "source_original_mesh_segment_count": item[
                "total_original_source_triangle_plane_segments"
            ],
            "source_contour_component_perimeters_mm": [
                c["contour_perimeter_mm"] for c in item["source_contours"]
            ],
            "source_contour_component_centers_xy_mm": [
                c["contour_centroid_xy_mm"] for c in item["source_contours"]
            ],
            "source_contour_component_areas_mm2": [
                c["enclosed_plane_area_mm2"] for c in item["source_contours"]
            ],
        }
        for item in real["sections"]
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proxy", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--trial", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--detail", type=Path, required=True)
    parser.add_argument("--svg", type=Path, required=True)
    args = parser.parse_args()
    _inputs(args)
    original_trial = args.trial.read_bytes()
    study = json.loads(original_trial)
    source, faces = load_pinned_proxy(args.proxy)
    real = real_source_section_series(source, faces)
    qa = compare_true_contours_to_split_study(real, study)
    if (
        qa["actual_closed_component_count_125"] != 2
        or qa["actual_closed_component_count_230"] != 3
        or qa["actual_closed_component_count_245"] != 2
    ):
        raise ValueError("actual original Stage6 plane-loop topology has changed")
    atlas = render_true_source_contours_svg(real)
    detail = json.dumps(real, ensure_ascii=False, indent=2) + "\n"
    qa["original_public_blend_sha256"] = SOURCE_SHA256
    qa["source_25percent_proxy_ply_sha256"] = PROXY_SHA256
    qa["same_run_split_volume_trial_sha256"] = hashlib.sha256(
        original_trial
    ).hexdigest()
    qa["full_original_source_contour_detail_sha256"] = hashlib.sha256(
        detail.encode("utf8")
    ).hexdigest()
    qa["true_original_mesh_source_section_atlas_svg_sha256"] = hashlib.sha256(
        atlas.encode("utf8")
    ).hexdigest()
    qa["actual_source_section_compact_summary"] = _compact(real)
    for file in (args.summary, args.detail, args.svg):
        file.parent.mkdir(parents=True, exist_ok=True)
    args.detail.write_text(detail, encoding="utf8")
    args.svg.write_text(atlas, encoding="utf8")
    args.summary.write_text(
        json.dumps(qa, ensure_ascii=False, indent=2) + "\n",
        encoding="utf8",
    )
    print(
        "STAGE6_TRUE_SOURCE_MULTI_LOOP_SECTIONS_REJECT_SINGLE_RING_TOP_CAP",
        json.dumps(
            {
                "source_planes": [
                    [row["source_plane_z_mm"], row["actual_original_closed_contour_count"]]
                    for row in qa["actual_source_section_compact_summary"]
                ],
                "candidate_max_true_vs_surrogate_boundary_gap_mm": {
                    row["name"]: row[
                        "max_2d_true_source_contour_boundary_hausdorff_mm"
                    ]
                    for row in qa["candidates"]
                },
                "source_3d_sculpt_fabric_pattern_approved": False,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
