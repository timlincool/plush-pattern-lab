"""Pin trusted source-linked Stage6 18-piece upper study, not production claims."""

import json
from pathlib import Path

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/stage6_upper_mother_toile_20261108/summary.json"
PROGRESS = ROOT / "docs/PRODUCTION_PROGRESS.json"


def test_real_stage6_true_lower_to_upper_source_and_seam_counts_are_fixed():
    e = json.loads(EVIDENCE.read_text(encoding="utf8"))
    assert e["source_original_stage6_blend_sha256"] == SOURCE_SHA256
    assert e["first_run_conclusion"] == "success"
    assert e["repeated_stage6_conclusion"] == "success"
    assert e["python_test_suite_passed"] == 488
    trial = e["new_trial"]
    assert trial["entire_research_piece_count"] == 18
    assert trial["total_100percent_A4_paper_pages"] == 9
    assert trial["total_new_matched_2d_stitch_relations"] == 12
    assert trial["all_12_digital_sew_stitch_relations_matched"]
    assert max(
        trial["indexed_band_to_upper_gore_max_segment_mismatch_mm"]
    ) < 1e-11
    assert trial["adjacent_upper_side_segment_max_mismatch_mm"] < 1e-11
    assert not trial["actual_animal_body_fabric_pattern_approved"]


def test_real_original_neck_source_anatomy_is_not_a_stitch_length_proof():
    e = json.loads(EVIDENCE.read_text(encoding="utf8"))
    source = e["source_sculpt_observation"]
    assert source["source_130_to155mm_envelope_center_shift_mm"] > 70
    assert source["source_neck_and_rear_torso_separation_review_required"]
    assert (
        source[
            "new_synthetic_3d_envelope_meridian_to_2d_sewing_line_max_length_mismatch_mm"
        ]
        > 89
    )
    assert source["real_original_sculpt_3d_2d_meridian_pairing_was_not_proved"]
    assert not source["final_25cm_alpaca_3d_silhouette_or_stuffed_shape_matched"]
    assert not source["original_material_grain_stretch_fur_or_stuffing_tested"]


def test_upper_svg_bytes_repeat_without_falsely_claiming_json_byte_identity():
    e = json.loads(EVIDENCE.read_text(encoding="utf8"))
    proof = e["repeat_after_style_action_artifact"]
    assert len(e["first_stage6_action_artifact"]["upper_A4_svg_sha256"]) == 5
    assert proof["all_five_upper_svg_files_byte_identical_to_first_run"]
    assert proof["assembly_sequence_bytes_identical"]
    assert "71.38606783526528" in proof["full_json_only_numeric_change"]
    assert e["industrial_cut_patterns_approved"] == 0
    progress = json.loads(PROGRESS.read_text(encoding="utf8"))
    p3 = next(x for x in progress["phases"] if x["id"] == "P3")
    p4 = next(x for x in progress["phases"] if x["id"] == "P4")
    assert p3["status"] == "in_progress"
    assert p4["status"] == "not_started"
    assert EVIDENCE.relative_to(ROOT).as_posix() in [
        item["path"] for item in p3["evidence"]
    ]
    assert not progress["overall"]["factory_sample_pack_ready"]
