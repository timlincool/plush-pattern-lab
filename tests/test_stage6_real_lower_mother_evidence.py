"""Retain actual Stage6 4x512 source hoof ring lower-toile research evidence.

Must not equate a geometrically matching test toile with a complete character
fabric pattern or original 3D hoof sole flattening.
"""

import json
from pathlib import Path

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/stage6_lower_mother_toile_20261108/summary.json"
PROGRESS = ROOT / "docs/PRODUCTION_PROGRESS.json"


def test_real_stage6_four_different_hoof_source_rings_and_seam_lengths():
    report = json.loads(EVIDENCE.read_text(encoding="utf8"))
    assert report["original_public_blender_sha256"] == SOURCE_SHA256
    assert report["python_tests_passed"] == 474
    hoof = report["original_four_source_hoof_rings"]
    assert hoof["each_source_edge_count"] == 512
    assert hoof["total_original_source_hoof_edges"] == 2048
    lengths = hoof["actual_ring_3d_perimeters_mm"]
    assert lengths["FL"] > lengths["FR"]
    assert abs(lengths["RL"] - lengths["RR"]) < 0.001
    assert max(
        hoof["each_hoof_to_yoke_to_sleeve_to_flat_toe_max_segment_difference_mm"]
    ) < 1e-11
    assert hoof["original_3d_rounded_hoof_soles_have_not_been_unrolled"]


def test_real_A4_four_sheets_manifest_reproduced_byte_identical_on_main():
    report = json.loads(EVIDENCE.read_text(encoding="utf8"))
    first = report["temporary_github_action_artifact"]
    repeat = report["independent_post_fix_main_reproduction"]
    assert first["all_manifest_member_sha256_verified_independently"]
    assert len(first["exact_member_sha256"]) == 8
    assert repeat[
        "all_eight_lower_mother_research_members_SHA256_identical_to_first_run"
    ]
    assert repeat["all_four_1_to_1_A4_SVG_byte_identical"]
    assert repeat["run_result"] == "success"
    study = report["new_mother_study"]
    assert study["constructed_individual_pattern_pieces"] == 13
    assert study["printed_paper"]["pages"] == 4
    assert study["printed_paper"]["svg_width_mm"] == 210
    assert study["printed_paper"]["svg_height_mm"] == 297
    assert not study["certified_factory_output"]


def test_original_sculpt_and_open_upper_body_still_fail_manufacturing_gate():
    proof = json.loads(EVIDENCE.read_text(encoding="utf8"))
    study = proof["new_mother_study"]
    assert study["count_unpaired_upper_band_edges"] == 4
    assert study["new_four_upper_band_edges_to_real_torso_unpaired"]
    assert proof["original_stage6_body_at_z60_comparison"][
        "real_original_silhouette_matched"
    ] is False
    assert proof["approved_industrial_cutting_patterns"] == 0
    progress = json.loads(PROGRESS.read_text(encoding="utf8"))
    p3 = next(row for row in progress["phases"] if row["id"] == "P3")
    p4 = next(row for row in progress["phases"] if row["id"] == "P4")
    assert p3["status"] == "in_progress"
    assert p4["status"] == "not_started"
    assert EVIDENCE.relative_to(ROOT).as_posix() in [
        value["path"] for value in p3["evidence"]
    ]
    assert not progress["overall"]["factory_sample_pack_ready"]
