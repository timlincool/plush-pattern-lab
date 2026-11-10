"""Preserve genuine Stage6 source-plane multi-loop facts and fabrication holdouts."""

import json
from pathlib import Path

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/stage6_real_mesh_sections_20261111/summary.json"
PROGRESS = ROOT / "docs/PRODUCTION_PROGRESS.json"


def test_actual_source_triangle_plane_z125_z230_z245_multi_loop_hard_facts():
    real = json.loads(EVIDENCE.read_text(encoding="utf8"))
    assert real["public_original_stage6_blend_sha256"] == SOURCE_SHA256
    assert real["original_mesh_vertex_count"] == 59306
    assert real["original_mesh_triangle_count"] == 116568
    z = real["source_true_plane_heights_mm"]
    c = real["source_true_connected_closed_loop_counts"]
    assert len(z) == len(c) == 13
    assert (c[z.index(125)], c[z.index(230)], c[z.index(245)]) == (2, 3, 2)
    rings = real["actual_original_source_key_heights"]["z230"]
    assert len(rings["perimeters_mm"]) == 3
    assert rings["perimeters_mm"][0] > 153
    assert 45 < rings["perimeters_mm"][1] < 46
    assert 45 < rings["perimeters_mm"][2] < 46


def test_ab_single_head_top_cap_mismatch_and_true_centroid_are_not_fabric():
    real = json.loads(EVIDENCE.read_text(encoding="utf8"))
    ab = real["ab_trial_true_source_boundary_xy_hausdorff_mm"]
    assert ab["height_z_mm"] == [135, 145, 155, 180, 205, 230]
    assert ab["A_separate_stuffed_head"][-1] > 38
    assert ab["B_integrated_neck_port"][-1] > 38
    assert real["source_z230_true_middle_loop_perimeter_mm"] < 154
    assert real["ab_research_one_loop_top_cap_z230_perimeter_mm"] > 319
    assert real["both_trial_heads_ignore_two_side_components_at_z230"]
    assert 24 < real["actual_source_135_to145_true_contour_centroid_y_shift_mm"] < 25
    assert real[
        "previous_source_135_to145_percentile_envelope_center_shift_is_not_same_metric"
    ]
    assert real["true_source_3d_contour_is_not_a_fabric_rest_pattern"]


def test_two_trusted_stage6_runs_have_identical_original_section_evidence():
    proof = json.loads(EVIDENCE.read_text(encoding="utf8"))
    archive = proof["research_artifacts"]
    assert proof["first_stage6_run_result"] == "success"
    assert proof["repeat_stage6_run_result"] == "success"
    assert proof["python_tests_passed"] == 514
    assert archive[
        "all_three_source_research_files_byte_identical_across_two_trusted_main_runs"
    ]
    assert len(archive["exact_raw_research_file_sha256"]) == 3
    progress = json.loads(PROGRESS.read_text(encoding="utf8"))
    p3 = next(row for row in progress["phases"] if row["id"] == "P3")
    p4 = next(row for row in progress["phases"] if row["id"] == "P4")
    assert p3["status"] == "in_progress"
    assert p4["status"] == "not_started"
    assert EVIDENCE.relative_to(ROOT).as_posix() in [
        row["path"] for row in p3["evidence"]
    ]
    assert proof["approved_manufacturer_patterns"] == 0
    assert not progress["overall"]["factory_sample_pack_ready"]
