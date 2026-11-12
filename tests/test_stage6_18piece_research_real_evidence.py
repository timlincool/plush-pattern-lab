"""Keep three independent real Stage6 18-piece toile builds reproducible."""

import json
from pathlib import Path

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/stage6_18piece_sewing_assembly_20261112/summary.json"
PROGRESS = ROOT / "docs/PRODUCTION_PROGRESS.json"


def _load():
    return json.loads(EVIDENCE.read_text(encoding="utf8"))


def test_three_trusted_source_stage6_runs_replay_same_thirteen_pack_files():
    report = _load()
    assert report["original_public_stage6_blend_sha256"] == SOURCE_SHA256
    runs = report["three_trusted_original_stage6_blender_4_3_2_runs"]
    assert [item["run_id"] for item in runs] == [
        43255281019,
        43255652947,
        43256294219,
    ]
    assert all(row["conclusion"] == "success" for row in runs)
    assert len({row["full_stage6_artifact_sha256"] for row in runs}) == 3
    assert report["all_thirteen_research_pack_file_bytes_identical_across_three_trusted_runs"]
    assert not report["full_stage6_artifact_zips_byte_identical"]
    checksums = report["research_pack_member_sha256"]
    assert len(checksums) == 13
    assert all(len(value) == 64 for value in checksums.values())
    assert len([x for x in checksums if x.startswith("print/sheet-")]) == 9
    assert report["trusted_python_ci"]["tests_passed"] == 676


def test_true_stage6_hoof_stitch_source_and_surrogate_neck_failure_kept():
    result = _load()
    assert result["existing_trial_piece_count"] == 18
    assert result["stitch_interface_pair_count"] == 32
    assert result["source_real_hoof_open_rings_each_512_edges"] == 4
    assert len(result["interface_pair_kinds_each_four"]) == 8
    assert result["maximum_numerical_2d_segment_mismatch_mm"] < 1e-4
    assert result["measured_original_Stage6_neck_profile_center_jump_mm"] > 50
    assert result["original_3d_surrogate_meridian_vs_2d_stitch_length_mismatch_mm"] > 50
    assert not result["original_head_neck_sculpt_correctly_reproduced"]
    assert not result["four_real_3d_rounded_hoof_cap_patterns_completed"]
    assert not result[
        "two_inner_outer_ears_seven_clouds_tail_eyes_ten_drops_and_ten_straps_connected"
    ]


def test_real_source_digital_sewing_graph_must_not_authorize_factory_patterns():
    record = _load()
    progress = json.loads(PROGRESS.read_text(encoding="utf8"))
    phases = {row["id"]: row for row in progress["phases"]}
    assert phases["P3"]["status"] == record["P3_status"] == "in_progress"
    assert phases["P4"]["status"] == record["P4_status"] == "not_started"
    assert EVIDENCE.relative_to(ROOT).as_posix() in {
        row["path"] for row in phases["P3"]["evidence"]
    }
    assert record["manufacturer_cutting_patterns_approved"] == 0
    assert not progress["overall"]["factory_sample_pack_ready"]
    assert record["this_is_existing_2d_surrogate_not_new_source_flattening"]
    assert not record["fabric_physical_stitching_stuffing_and_factory_validation_completed"]
