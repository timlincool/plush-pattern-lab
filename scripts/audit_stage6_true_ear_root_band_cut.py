"""Reproduce true original Stage6 3D ear-root cuts and paired source netlines.

Both sides of each seam are the SAME original 3D cut; no 2D cloth pattern.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from propose_stage6_shell_panels import PROXY_SHA256, load_pinned_proxy

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256
from plush_pattern_lab.validation.stage6_true_ear_root_band_cut import (
    SCHEMA,
    analyze_real_source_ear_root_bands,
)
from plush_pattern_lab.validation.stage6_true_ear_root_band_svg import (
    render_real_root_band_svg,
)

SOURCE_STUDY_SCHEMA = "stage6-original-source-ear-root-two-height-ring-ab-v1"
BVH_SCHEMA = "stage6-original-source-ear-root-ab-41mesh-five-view-v1"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inputs(args):
    paths = (args.proxy, args.study, args.visibility)
    outputs = (args.output, args.svg)
    if (
        args.source_sha256 != SOURCE_SHA256
        or any(not p.is_file() or p.is_symlink() for p in paths)
        or any(p.exists() or p.is_symlink() for p in outputs)
        or len({p.resolve() for p in (*paths, *outputs)}) != 5
        or args.output.suffix != ".json"
        or args.svg.suffix != ".svg"
        or _sha(args.proxy) != PROXY_SHA256
    ):
        raise ValueError("untrusted Stage6 proxy or research output overwrite")
    source = json.loads(args.study.read_text(encoding="utf8"))
    visibility = json.loads(args.visibility.read_text(encoding="utf8"))
    if (
        source.get("schema") != SOURCE_STUDY_SCHEMA
        or source.get("original_public_stage6_blend_sha256") != SOURCE_SHA256
        or source.get("source_25pct_proxy_ply_sha256") != PROXY_SHA256
        or source.get("manufacturing_cutting_approved") != 0
        or visibility.get("schema") != BVH_SCHEMA
        or visibility.get("original_public_blend_sha256") != SOURCE_SHA256
        or visibility.get("same_run_ear_root_study_sha256") != _sha(args.study)
        or visibility.get("raw_product_meshes_raycasted") != 41
        or visibility.get("P4_started") is not False
    ):
        raise ValueError("cross-run or manufacturing-approved source-ear study")
    return source


def _original_source_ring_provenance(report, study):
    for side, patch in zip(
        ("left", "right"), report["original_source_ear_root_band_patches"]
    ):
        if patch["side"] != side:
            raise ValueError("source ear side order changed")
        for option, key in zip(
            study["candidate_options"],
            ("body_to_root_3d_paired_netline", "root_to_upper_ear_3d_paired_netline"),
        ):
            matched = next(
                row for row in option["source_side_loops"] if row["side"] == side
            )
            measured = patch[key]
            height = option["source_plane_z_mm"]
            expected = {
                ("e", *sorted(pair), height)
                for pair in matched["full_crossed_original_proxy_vertex_id_pairs"]
            }
            observed = {
                tuple(value)
                for value in measured["original_source_3d_ordered_ring_vertex_keys"]
            }
            if (
                expected != observed
                or measured["original_crossed_source_triangle_segment_count"]
                != len(expected)
                or abs(
                    measured["paired_3d_netline_length_each_side_mm"]
                    - matched["source_3d_ring_perimeter_mm"]
                )
                > 1e-6
                or measured["max_source_3d_pair_position_error_mm"] != 0
            ):
                raise ValueError(
                    "true 3D seam differs from authentic source A/B contour"
                )


def _validate_real_gate(report):
    if (
        report["schema"] != SCHEMA
        or report["original_source_vertex_count"] != 59306
        or report["original_source_triangle_count"] != 116568
        or report["source_cut_zone_component_counts"]
        != {"below": 1, "root": 3, "above": 3}
        or report["research_z_levels_mm"] != [230, 235]
        or len(report["original_source_ear_root_band_patches"]) != 2
        or report["source_area_absolute_reconstruction_error_mm2"] >= 1e-4
        or report["approved_factory_cutting_patterns"] != 0
        or report["P3_status"] != "in_progress"
        or report["P4_status"] != "not_started"
    ):
        raise ValueError("original 3D source ear patch or factory gate changed")
    for row, faces, tip, low, high in zip(
        report["original_source_ear_root_band_patches"],
        (829, 879),
        (1240, 1261),
        (113, 112),
        (110, 117),
    ):
        band = row["actual_3d_root_band"]
        graph = row["between_two_3d_seams_source_surface_graph"]
        if (
            band["derived_source_triangle_count"] != faces
            or row["actual_3d_ear_upper_tip"]["derived_source_triangle_count"] != tip
            or band["euler_characteristic"] != 0
            or band["closed_boundary_loop_count"] != 2
            or row["body_to_root_3d_paired_netline"][
                "original_crossed_source_triangle_segment_count"
            ]
            != low
            or row["root_to_upper_ear_3d_paired_netline"][
                "original_crossed_source_triangle_segment_count"
            ]
            != high
            or graph["fraction_upper_source_seam_under_12mm_graph_width"] != 1.0
            or not graph["below_two_research_6mm_allowances_somewhere"]
            or row["real_source_2d_paper_pattern_generated"]
        ):
            raise ValueError("3D paired mesh seams or genuine narrow width changed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proxy", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--visibility", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--svg", type=Path, required=True)
    args = parser.parse_args()
    source = _inputs(args)
    points, faces = load_pinned_proxy(args.proxy)
    report = analyze_real_source_ear_root_bands(points, faces)
    _validate_real_gate(report)
    _original_source_ring_provenance(report, source)
    image = render_real_root_band_svg(report)
    report.update(
        {
            "original_public_stage6_blend_sha256": SOURCE_SHA256,
            "original_25pct_proxy_ply_sha256": PROXY_SHA256,
            "same_run_ear_root_source_study_sha256": _sha(args.study),
            "same_run_original_41mesh_visibility_sha256": _sha(args.visibility),
            "root_band_research_svg_sha256": hashlib.sha256(
                image.encode("utf8")
            ).hexdigest(),
        }
    )
    for output in (args.output, args.svg):
        output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf8",
    )
    args.svg.write_text(image, encoding="utf8")
    print(
        "STAGE6_TRUE_3D_EAR_ROOT_PAIRED_NETLINES_BUT_NOT_SEWABLE_2D",
        json.dumps(
            [
                {
                    "side": p["side"],
                    "source_band_triangle_count": p["actual_3d_root_band"][
                        "derived_source_triangle_count"
                    ],
                    "paired_lower_mm": p["body_to_root_3d_paired_netline"][
                        "paired_3d_netline_length_each_side_mm"
                    ],
                    "paired_upper_mm": p["root_to_upper_ear_3d_paired_netline"][
                        "paired_3d_netline_length_each_side_mm"
                    ],
                    "min_source_surface_graph_width_mm": p[
                        "between_two_3d_seams_source_surface_graph"
                    ]["surface_graph_shortest_path_min_p05_median_p95_max_mm"][0],
                    "approved": False,
                }
                for p in report["original_source_ear_root_band_patches"]
            ]
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
