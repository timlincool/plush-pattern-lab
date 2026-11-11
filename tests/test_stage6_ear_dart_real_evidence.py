"""Lock genuine Stage6 source-ear dart 3D path evidence and fabrication holdouts."""

import json
from pathlib import Path

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/stage6_ear_dart_termination_20261111/summary.json"
PROGRESS = ROOT / "docs/PRODUCTION_PROGRESS.json"


def _real():
    return json.loads(EVIDENCE.read_text(encoding="utf8"))


def test_two_trusted_main_blender_runs_have_five_matching_raw_source_proofs():
    report = _real()
    assert report["source_original_blend_sha256"] == SOURCE_SHA256
    assert report["proxy_original_vertices"] == 59306
    assert report["proxy_original_triangles"] == 116568
    assert report["proxy_unique_original_edges"] == 175876
    first, repeat = report["trusted_stage6_main_blender_4_3_2_runs"]
    assert first["conclusion"] == repeat["conclusion"] == "success"
    assert {first["run_id"], repeat["run_id"]} == {
        42971171926, 42971362151
    }
    assert first["artifact_id"] != repeat["artifact_id"]
    assert first["artifact_zip_sha256"] != repeat["artifact_zip_sha256"]
    raw = report["original_research_five_files_sha256_identical_across_trusted_runs"]
    assert len(raw) == 5
    assert all(len(value) == 64 for value in raw.values())
    assert report["all_five_raw_research_files_exact_byte_identical_twice"]
    assert not report["complete_action_zip_byte_identical"]


def test_real_source_ear_dart_two_depths_force_disjoint_branches_but_not_sewing():
    report = _real()
    rows = report["four_verified_original_route_options"]
    assert [(x["side"], x["target_z_mm"]) for x in rows] == [
        ("left", 225),
        ("left", 219),
        ("right", 225),
        ("right", 219),
    ]
    assert [row["source_tip_vertex_id"] for row in rows] == [
        42096, 42214, 51470, 51615
    ]
    assert [row["unconstrained_early_shared_source_vertices"] for row in rows] == [
        7, 14, 1, 0
    ]
    assert all(len(x["source_3d_route_sha256"]) == 64 for x in rows)
    assert rows[0]["source_mesh_vertex_gap_beyond_tip_4mm_mm"] < 2
    assert rows[1]["source_mesh_vertex_gap_beyond_tip_4mm_mm"] < 1
    assert all(x["under_2mm_research_screen"] for x in rows[:2])
    assert all(not x["under_2mm_research_screen"] for x in rows[2:])
    assert rows[2]["four_view_near_body_first_hits_per_branch"] == [9, 1]
    assert rows[3]["four_view_near_body_first_hits_per_branch"] == [12, 7]
    assert report["right_deeper_tip_does_not_reduce_first_hit_risk"]


def test_real_source_3d_route_does_not_start_factory_patterns():
    report = _real()
    progress = json.loads(PROGRESS.read_text(encoding="utf8"))
    phases = {row["id"]: row for row in progress["phases"]}
    assert phases["P3"]["status"] == report["P3_status"] == "in_progress"
    assert phases["P4"]["status"] == report["P4_status"] == "not_started"
    assert EVIDENCE.relative_to(ROOT).as_posix() in {
        row["path"] for row in phases["P3"]["evidence"]
    }
    assert not progress["overall"]["factory_sample_pack_ready"]
    assert report["manufacturer_cutting_patterns_approved"] == 0
    assert not report["true_two_sided_3d_to_2d_sewing_netlines_generated"]
    assert not report["real_fabric_6mm_allowance_turnout_and_filling_tested"]
    assert not report["actual_designed_hidden_seam_confirmed"]
