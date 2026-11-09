"""True source Stage6 independent torso/head A/B evidence is not factory approval."""

import json
from pathlib import Path

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/stage6_two_volume_headneck_ab_20261110/summary.json"
PROGRESS = ROOT / "docs/PRODUCTION_PROGRESS.json"


def test_real_stage6_two_split_volume_source_sha_and_digital_seams():
    item = json.loads(EVIDENCE.read_text(encoding="utf8"))
    assert item["original_public_blend_sha256"] == SOURCE_SHA256
    assert item["stage6_result"] == "success"
    assert item["python_tests_passed"] == 503
    assert item["original_four_512_edge_hoof_rings_and_13_lower_trial_pieces_unmodified"]
    variants = item["alternatives"]
    assert [x["name"] for x in variants] == [
        "A_separate_stuffed_head",
        "B_integrated_neck_port",
    ]
    assert [x["digital_matched_relation_count"] for x in variants] == [25, 23]
    assert all(x["total_research_pieces"] == 24 for x in variants)
    assert all(x["A4_pages_per_independent_variant"] == 15 for x in variants)
    assert all(not x["approved_for_factory_cutting"] for x in variants)


def test_actual_neck_shape_drift_and_minimal_b_port_margin_remain_blockers():
    j = json.loads(EVIDENCE.read_text(encoding="utf8"))
    a, b = j["alternatives"]
    assert a["source_reference_neck_root_xy_scale"] == 0.74
    assert b["source_reference_neck_root_xy_scale"] == 0.64
    assert a["maximum_true_source_neck_z145_to_new_port_xy_move_mm"] > 25
    assert b["maximum_true_source_neck_z145_to_new_port_xy_move_mm"] > 29
    assert a["body_source_surrogate_3d_vs_2d_corner_meridian_max_error_mm"] > 54
    assert b["extra_clearance_over_two_unverified_6mm_allowances_plus_1mm_mm"] < 0.5
    assert not a["actual_external_hand_ladder_seam_strength_tested"]
    assert not b["turning_and_stuffing_through_original_BAND3_trial_gap_tested"]
    assert j["source_anatomic_section_observation"][
        "original_front_neck_source_ring_is_not_an_actual_mesh_cut_edge"
    ] is not False


def test_research_svg_manifests_and_factory_stage_are_not_misrepresented():
    j = json.loads(EVIDENCE.read_text(encoding="utf8"))
    art = j["trusted_run_artifact"]
    assert art["all_25_upstream_manifest_files_sha256_checked"]
    assert art["total_new_A4_svg_pages_in_A_B_comparison"] == 22
    assert j["standalone_research_archives"][
        "each_contains_original_lower_4_A4_and_own_new_11_A4"
    ]
    assert j["factory_cut_patterns_approved"] == 0
    p = json.loads(PROGRESS.read_text(encoding="utf8"))
    p3 = next(x for x in p["phases"] if x["id"] == "P3")
    p4 = next(x for x in p["phases"] if x["id"] == "P4")
    assert p3["status"] == "in_progress"
    assert p4["status"] == "not_started"
    assert EVIDENCE.relative_to(ROOT).as_posix() in [
        x["path"] for x in p3["evidence"]
    ]
    assert not p["overall"]["factory_sample_pack_ready"]
    assert not p["overall"]["mass_production_ready"]
