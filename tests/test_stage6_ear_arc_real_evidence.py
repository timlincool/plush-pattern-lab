"""Preserve real Stage6 partial-arc evidence, factory holdouts and source SHA."""

import json
from pathlib import Path

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/stage6_ear_arc_quadrants_20261111/summary.json"
PROGRESS = ROOT / "docs/PRODUCTION_PROGRESS.json"


def _evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf8"))


def test_real_source_arcs_two_trusted_staged_runs_and_five_stable_raw_sha():
    d = _evidence()
    assert d["source_original_public_blend_sha256"] == SOURCE_SHA256
    assert d["source_proxy_original_triangle_count"] == 116568
    assert d["trusted_python_ci"]["tests_passed"] == 583
    a, b = d["trusted_stage6_blender_4_3_2_runs"]
    assert a["run_id"] == 42965611336
    assert b["run_id"] == 42966064172
    assert a["run_conclusion"] == b["run_conclusion"] == "success"
    assert a["artifact_zip_sha256"] != b["artifact_zip_sha256"]
    assert len(d["original_research_file_sha256_identical_across_both_trusted_runs"]) == 5
    assert all(
        len(sha) == 64
        for sha in d["original_research_file_sha256_identical_across_both_trusted_runs"].values()
    )
    assert d["original_research_five_files_exact_byte_identical_twice"]
    assert not d["full_action_artifact_zip_byte_identical"]


def test_source_all_16_quadrants_keep_a_medial_and_posterior_asymmetry():
    d = _evidence()
    rows = d["all_16_source_quadrant_observations"]
    assert len(rows) == 16
    assert len({(r[0], r[2], r[3]) for r in rows}) == 16
    lookup = {(r[0], r[2], r[3]): r for r in rows}
    assert lookup["A", "left", "medial"][7] == [0, 0, 0, 2]
    assert lookup["A", "right", "medial"][7] == [0, 0, 0, 6]
    assert lookup["B", "left", "medial"][7] == [0, 0, 0, 7]
    assert lookup["B", "right", "medial"][7] == [0, 6, 0, 0]
    assert lookup["A", "left", "posterior"][7] == [0, 0, 1, 0]
    assert lookup["A", "right", "posterior"][7] == [0, 11, 5, 1]
    assert all(len(row[7]) == 4 and row[4] > 0 for row in rows)
    assert d["all_partial_arc_endpoints_unpaired"] == 2


def test_p3_source_review_is_not_physical_cutting_authority():
    d = _evidence()
    p = json.loads(PROGRESS.read_text(encoding="utf8"))
    phase = {row["id"]: row for row in p["phases"]}
    assert phase["P3"]["status"] == d["P3_status"] == "in_progress"
    assert phase["P4"]["status"] == d["P4_status"] == "not_started"
    assert EVIDENCE.relative_to(ROOT).as_posix() in {
        row["path"] for row in phase["P3"]["evidence"]
    }
    assert not p["overall"]["factory_sample_pack_ready"]
    assert d["approved_manufacturer_cutting_patterns"] == 0
    assert not d["sewing_3d_to_2d_net_match_and_allowance_verified"]
    assert not d["physical_fabric_turnover_and_factory_verified"]
    assert not d["anatomical_design_four_views_signed_off"]
