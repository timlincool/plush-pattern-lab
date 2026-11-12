"""Permanent three-run evidence of true Stage6 source 2D disks and holdouts."""

import json
from pathlib import Path

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/stage6_ear_root_slit_lscm_20261112/summary.json"
PROGRESS = ROOT / "docs/PRODUCTION_PROGRESS.json"


def _report():
    return json.loads(EVIDENCE.read_text(encoding="utf8"))


def test_three_real_original_stage6_runs_keep_identical_3d_and_source_svg():
    report = _report()
    assert report["source_original_public_stage6_blend_sha256"] == SOURCE_SHA256
    assert report["original_source_proxy_vertex_count"] == 59306
    assert report["original_source_proxy_triangle_count"] == 116568
    assert report["trusted_python_ci"]["tests_passed"] == 644
    a, b, c = report["trusted_main_blender_4_3_2_runs"]
    assert [x["run_id"] for x in (a, b, c)] == [43208785020, 43208995243, 43209510152]
    assert all(x["conclusion"] == "success" for x in (a, b, c))
    assert (
        a["raw_full_lscm_research_json_sha256"]
        == c["raw_full_lscm_research_json_sha256"]
    )
    assert (
        a["raw_full_lscm_research_json_sha256"]
        != b["raw_full_lscm_research_json_sha256"]
    )
    assert report["three_runs_all_original_3d_input_json_byte_identical"]
    assert report["first_and_third_full_lscm_raw_json_byte_identical"]
    assert not report["all_three_full_lscm_raw_json_byte_identical"]
    assert len(report["three_runs_source_lscm_review_svg_sha256"]) == 64
    source_hashes = report["source_original_41mesh_and_3d_sliced_reference_sha256"]
    assert len(source_hashes) == 4
    assert all(len(value) == 64 for value in source_hashes.values())


def test_all_twelve_source_disks_record_real_2d_seam_and_strain_failures():
    report = _report()
    rows = report["all_twelve_source_cut_and_2d_study_observations"]
    assert len(rows) == 12
    assert len({tuple(r[:3]) for r in rows}) == 12
    assert {row[0] for row in rows} == {"N15", "N17"}
    assert {row[1] for row in rows} == {"left", "right"}
    assert {row[2] for row in rows} == {"medial", "posterior", "lateral"}
    assert all(row[3] > 15 and row[4] >= 1680 for row in rows)
    assert all(row[5] > 0.1 and row[6] > 0.03 for row in rows)
    n15_left_back = next(row for row in rows if row[:3] == ["N15", "left", "posterior"])
    assert n15_left_back[7] < 12
    assert report[
        "all_twelve_no_flipped_triangles_or_positive_area_face_overlap_detected"
    ]
    assert report[
        "all_twelve_lscm_p95_edge_length_relative_error_over_10percent_research_screen"
    ]
    assert report[
        "all_twelve_two_planar_source_cut_sides_length_mismatch_over_3percent_research_screen"
    ]


def test_raw_lscm_replay_is_only_numerical_and_p3_p4_still_blocked():
    report = _report()
    envelope = report["sparse_LSCM_numeric_reproducibility"]
    assert (
        envelope["maximum_vertex_2d_displacement_between_any_two_repeated_runs_mm"]
        < 1e-5
    )
    assert envelope["maximum_difference_in_any_2d_p95_edge_relative_error"] < 1e-7
    assert envelope["maximum_difference_in_any_2d_seam_mismatch_fraction"] < 1e-7
    assert not envelope["claimed_bitwise_identity_of_raw_2d_optimization"]
    assert envelope["source_2d_quality_flags_stable_across_all_three_runs"]
    progress = json.loads(PROGRESS.read_text(encoding="utf8"))
    phases = {phase["id"]: phase for phase in progress["phases"]}
    assert phases["P3"]["status"] == report["P3_status"] == "in_progress"
    assert phases["P4"]["status"] == report["P4_status"] == "not_started"
    assert EVIDENCE.relative_to(ROOT).as_posix() in {
        item["path"] for item in phases["P3"]["evidence"]
    }
    assert not progress["overall"]["factory_sample_pack_ready"]
    assert report["manufacturer_cutting_patterns_approved"] == 0
    assert not report["physical_6mm_allowance_and_fabric_test_done"]
    assert not report[
        "four_view_original_design_and_independent_ear_cloud_mesh_assembly_signed_off"
    ]
