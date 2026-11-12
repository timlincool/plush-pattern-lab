"""Audit twelve true source Stage6 side-slit LSCM research disks.

All input is already same-run source-pinned Blender/PLY evidence. The entire
geometry is retained in research JSON; SVG contains no industrial cut lines.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256
from plush_pattern_lab.validation.stage6_ear_slit_disk import (
    ROUTES,
    STUDIES,
    create_source_slit_disk,
)
from plush_pattern_lab.validation.stage6_ear_slit_disk import (
    SCHEMA as SOURCE_SCHEMA,
)
from plush_pattern_lab.validation.stage6_ear_slit_lscm import (
    SCHEMA,
    evaluate_original_source_slit_disk,
)
from plush_pattern_lab.validation.stage6_ear_slit_svg import (
    render_source_slit_lscm_atlas,
)

ROOT = Path(__file__).resolve().parents[1]
REF_SCHEMA = "stage6-original-source-nonhorizontal-ear-root-two-real-blender-replays-v1"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_sources(args):
    inputs = (args.source, args.visibility, args.reference)
    outputs = (args.output, args.svg)
    if (
        any(not p.is_file() or p.is_symlink() for p in inputs)
        or any(p.exists() or p.is_symlink() for p in outputs)
        or len({p.resolve() for p in (*inputs, *outputs)}) != 5
        or args.output.suffix != ".json"
        or args.svg.suffix != ".svg"
    ):
        raise ValueError("source not present or attempt to overwrite existing evidence")
    report = json.loads(args.source.read_text(encoding="utf8"))
    reference = json.loads(args.reference.read_text(encoding="utf8"))
    visibility = json.loads(args.visibility.read_text(encoding="utf8"))
    if (
        report.get("schema")
        != "stage6-real-original-source-nonhorizontal-ear-root-paired-3d-v1"
        or reference.get("schema") != REF_SCHEMA
        or report.get("original_public_stage6_blend_sha256") != SOURCE_SHA256
        or reference.get("original_public_blend_sha256") != SOURCE_SHA256
        or report.get("original_25percent_proxy_ply_sha256")
        != reference.get("original_25pct_proxy_ply_sha256")
        or report.get("factory_cutting_patterns_approved") != 0
        or reference.get("factory_cutting_patterns_approved") != 0
        or reference.get("P4_status") != "not_started"
        or report.get("P4_status") != "not_started"
        or report.get("same_run_original_41mesh_visibility_sha256")
        != _sha(args.visibility)
        or visibility.get("raw_product_meshes_raycasted") != 41
        or reference.get("seven_raw_files_sha256_matching_across_both_trusted_runs", {})
        .get("true_stage6_nonhorizontal_ear_root_paired_3d_json")
        != _sha(args.source)
    ):
        raise ValueError("source 3D cut or 41Mesh research does not match pinned run")
    return report, reference


def _reference_for_patch(reference, name, side):
    study = next(
        (row for row in reference["source_curved_3d_cut_research_variants"]
         if row["study"] == name),
        None,
    )
    if study is None:
        raise ValueError("unknown original source surface study")
    patch = next((row for row in study["sides"] if row["side"] == side), None)
    if patch is None:
        raise ValueError("unknown original-source ear side")
    return patch


def _twelve_trials(source, reference):
    choices = []
    if [x["name"] for x in source["proposed_surface_designs"]] != list(STUDIES):
        raise ValueError("source nonhorizontal study order changed")
    for study in source["proposed_surface_designs"]:
        patches = study["original_ear_root_patches"]
        if [row["side"] for row in patches] != ["left", "right"]:
            raise ValueError("original source left/right root identity changed")
        for patch in patches:
            ref = _reference_for_patch(reference, study["name"], patch["side"])
            for direction in ROUTES:
                disk = create_source_slit_disk(study, patch, ref, direction)
                candidate = evaluate_original_source_slit_disk(disk)
                if (
                    candidate["source_slit_direction"] != direction
                    or candidate["not_a_factory_cutting_or_sewing_approval"] is not True
                    or candidate["original_source_planar_face_geometry_diagnostics"][
                        "overlapping_positive_area_triangle_pair_count"
                    ] != 0
                    or candidate["original_source_planar_face_geometry_diagnostics"][
                        "reversed_or_collapsed_triangle_count"
                    ] != 0
                ):
                    raise ValueError("source research disk topology or planar overlap changed")
                choices.append(candidate)
    if len(choices) != 12:
        raise ValueError("not all preregistered source side-slit candidates were tested")
    return choices


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--visibility", required=True, type=Path)
    parser.add_argument("--reference", default=ROOT / "experiments/stage6_nonhorizontal_ear_root_20261112/summary.json", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--svg", required=True, type=Path)
    args = parser.parse_args()
    source, reference = _read_sources(args)
    choices = _twelve_trials(source, reference)
    report = {
        "schema": SCHEMA,
        "original_source_slit_schema": SOURCE_SCHEMA,
        "original_public_blend_sha256": SOURCE_SHA256,
        "pinned_25pct_proxy_sha256": source["original_25percent_proxy_ply_sha256"],
        "same_run_nonhorizontal_3d_source_report_sha256": _sha(args.source),
        "same_run_41mesh_visibility_sha256": _sha(args.visibility),
        "permanent_source_reference_sha256": _sha(args.reference),
        "tested_original_source_root_regions": list(STUDIES),
        "all_predeclared_three_slit_directions": list(ROUTES),
        "candidate_2d_research_disks": choices,
        "source_3d_netlines_matched_but_2d_sewn_netlines_not_verified": True,
        "actual_fabric_grain_6mm_allowance_turnout_and_filling_not_tested": True,
        "upper_original_ear_rim_still_below_12mm_xy_source_screen": True,
        "signed_off_inner_outer_ear_and_cloud_mesh_assembly_not_tested": True,
        "original_high_density_stage6_not_directly_parameterized": True,
        "factory_cutting_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
    }
    svg = render_source_slit_lscm_atlas(report)
    report["research_svg_sha256"] = hashlib.sha256(svg.encode("utf8")).hexdigest()
    for path in (args.output, args.svg):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf8"
    )
    args.svg.write_text(svg, encoding="utf8")
    print(
        "STAGE6_REAL_SOURCE_ANNULI_CUT_TO_12_LSCM_RESEARCH_DISKS_BUT_NOT_FABRIC",
        json.dumps(
            [
                {
                    "study": row["source_variant"],
                    "side": row["original_source_side"],
                    "direction": row["source_slit_direction"],
                    "p95_scaled_edge_error": round(
                        row["uniform_scale_normalized_edge_diagnostics"][
                            "scaled_2d_p95_abs_edge_relative_error"
                        ], 5
                    ),
                    "2d_paired_source_seam_mismatch_fraction": round(
                        row["true_source_seam_3d_vs_lscm_2d_pairing"][
                            "scaled_planar_2d_two_sides_length_mismatch_fraction_of_source_3d"
                        ], 5
                    ),
                }
                for row in choices
            ]
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
