"""Pinned true Stage6 non-horizontal 3D root cut, not approved 2D paper."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from propose_stage6_shell_panels import PROXY_SHA256, load_pinned_proxy

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256
from plush_pattern_lab.validation.stage6_nonhorizontal_ear_root_cut import (
    SCHEMA,
    compare_nonhorizontal_original_source_roots,
)
from plush_pattern_lab.validation.stage6_nonhorizontal_ear_root_svg import (
    render_nonhorizontal_ear_root_svg,
)


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_check(args):
    incoming = (args.proxy, args.study, args.visibility, args.baseline)
    outgoing = (args.output, args.svg)
    if (
        args.source_sha256 != SOURCE_SHA256
        or any(not p.is_file() or p.is_symlink() for p in incoming)
        or len({p.resolve() for p in (*incoming, *outgoing)}) != 6
        or any(p.exists() or p.is_symlink() for p in outgoing)
        or args.output.suffix != ".json"
        or args.svg.suffix != ".svg"
        or _sha(args.proxy) != PROXY_SHA256
    ):
        raise ValueError("unpinned original source or existing protected evidence")
    study = json.loads(args.study.read_text(encoding="utf8"))
    visible = json.loads(args.visibility.read_text(encoding="utf8"))
    baseline = json.loads(args.baseline.read_text(encoding="utf8"))
    if (
        study.get("original_public_stage6_blend_sha256") != SOURCE_SHA256
        or study.get("source_25pct_proxy_ply_sha256") != PROXY_SHA256
        or study.get("manufacturing_cutting_approved") != 0
        or visible.get("same_run_ear_root_study_sha256") != _sha(args.study)
        or visible.get("raw_product_meshes_raycasted") != 41
        or visible.get("manufacturing_seam_or_dart_approved") is not False
        or baseline.get("schema")
        != "stage6-true-ear-root-3d-split-and-matched-seams-v1"
        or baseline.get("same_run_ear_root_source_study_sha256") != _sha(args.study)
        or baseline.get("same_run_original_41mesh_visibility_sha256")
        != _sha(args.visibility)
        or baseline.get("approved_factory_cutting_patterns") != 0
        or baseline.get("P4_status") != "not_started"
    ):
        raise ValueError("new sloping source study cannot mix upstream evidence")
    return baseline


def _gate(report, baseline):
    if (
        report.get("schema") != SCHEMA
        or report["source_original_vertex_count"] != 59306
        or report["source_original_triangle_count"] != 116568
        or [x["name"] for x in report["proposed_surface_designs"]]
        != ["N15_sloped_source_band", "N17_sloped_source_band"]
        or report["factory_cutting_patterns_approved"] != 0
        or report["P3_status"] != "in_progress"
        or report["P4_status"] != "not_started"
    ):
        raise ValueError("source band anatomy or manufacturing status changed")
    expected = ((1680, 1755), (1865, 1940))
    for study, correct in zip(report["proposed_surface_designs"], expected):
        if (
            study["true_3d_source_zone_component_counts"]
            != {"below": 1, "root": 3, "above": 2}
            or study["source_area_reconstruction_error_mm2"] >= 1e-4
            or [
                p["actual_original_source_root_band"]["derived_source_triangle_count"]
                for p in study["original_ear_root_patches"]
            ]
            != list(correct)
        ):
            raise ValueError("sloping original face cut or area baseline changed")
        _source_paired_check(study)
    for row in baseline["original_source_ear_root_band_patches"]:
        if not row["between_two_3d_seams_source_surface_graph"][
            "below_two_research_6mm_allowances_somewhere"
        ]:
            raise ValueError("lost fixed narrow original source baseline")


def _source_paired_check(study):
    for patch in study["original_ear_root_patches"]:
        width = patch["surface_graph_between_3d_netlines"]
        lower = patch["body_to_root_paired_3d_source_netline"]
        upper = patch["root_to_upper_ear_paired_3d_source_netline"]
        if (
            patch["actual_original_source_root_band"]["euler_characteristic"] != 0
            or patch["actual_original_source_root_band"]["closed_boundary_loop_count"]
            != 2
            or width["fraction_upper_source_seam_under_12mm_graph_width"] != 0
            or width["surface_graph_shortest_path_min_p05_median_p95_max_mm"][0] <= 12.0
            or not upper["original_world_xy_minor_extent_below_12mm_research_screen"]
            or lower["max_source_3d_pair_position_error_mm"] != 0
            or upper["max_source_3d_pair_position_error_mm"] != 0
            or not lower["two_source_3d_sides_exactly_same_with_opposite_face_winding"]
            or not upper["two_source_3d_sides_exactly_same_with_opposite_face_winding"]
            or patch["true_manufacturing_2d_pattern_generated"]
        ):
            raise ValueError("source 3D seam pairing or upper rim risk failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proxy", required=True, type=Path)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--study", required=True, type=Path)
    parser.add_argument("--visibility", required=True, type=Path)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--svg", required=True, type=Path)
    args = parser.parse_args()
    baseline = _source_check(args)
    xyz, faces = load_pinned_proxy(args.proxy)
    report = compare_nonhorizontal_original_source_roots(xyz, faces)
    _gate(report, baseline)
    image = render_nonhorizontal_ear_root_svg(report)
    report.update(
        {
            "original_public_stage6_blend_sha256": SOURCE_SHA256,
            "original_25percent_proxy_ply_sha256": PROXY_SHA256,
            "same_run_original_ear_root_study_sha256": _sha(args.study),
            "same_run_original_41mesh_visibility_sha256": _sha(args.visibility),
            "same_run_previous_narrow_3d_source_band_sha256": _sha(args.baseline),
            "research_svg_sha256": hashlib.sha256(image.encode("utf8")).hexdigest(),
        }
    )
    for path in (args.output, args.svg):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    args.svg.write_text(image, encoding="utf8")
    print(
        "STAGE6_REAL_NONHORIZONTAL_3D_ROOT_SEAMS_PAIRED_RIM_TOO_NARROW_NO_PAPER",
        json.dumps(
            [
                {
                    "study": x["name"],
                    "sides": [
                        {
                            "side": p["side"],
                            "source_faces": p["actual_original_source_root_band"][
                                "derived_source_triangle_count"
                            ],
                            "graph_min_mm": p["surface_graph_between_3d_netlines"][
                                "surface_graph_shortest_path_min_p05_median_p95_max_mm"
                            ][0],
                            "upper_xy_minor_mm": p[
                                "root_to_upper_ear_paired_3d_source_netline"
                            ]["original_world_xy_minor_extent_mm"],
                        }
                        for p in x["original_ear_root_patches"]
                    ],
                }
                for x in report["proposed_surface_designs"]
            ]
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
