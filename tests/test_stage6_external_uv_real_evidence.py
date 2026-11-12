"""Pinned three-run zero-fee Blender ABF/Conformal original Stage6 evidence."""

import json
from pathlib import Path
from statistics import median

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/stage6_free_native_uv_benchmark_20261112/summary.json"
PROGRESS = ROOT / "docs/PRODUCTION_PROGRESS.json"


def _data():
    return json.loads(EVIDENCE.read_text(encoding="utf8"))


def test_three_trusted_runs_same_real_original_blender_uv_coordinates():
    record = _data()
    assert record["original_public_stage6_blend_sha256"] == SOURCE_SHA256
    runs = record["independent_successful_trusted_stage6_runs"]
    assert [r["run_id"] for r in runs] == [
        43247441115,
        43247668180,
        43248045350,
    ]
    assert all(r["conclusion"] == "success" for r in runs)
    assert len({r["artifact_zip_sha256"] for r in runs}) == 3
    uv = record[
        "all_three_native_uv_source_index_aligned_arrays_identical_after_excluding_runtime"
    ]
    assert uv["maximum_absolute_uv_vertex_coordinate_difference_across_replays"] == 0
    assert len(uv["canonical_uv_identity_and_coordinates_sha256"]) == 64
    assert uv["total_uv_source_disk_vertices_across_24_runs"] == 24440
    assert uv["maximum_p95_edge_error_difference"] < 1e-12
    assert uv["maximum_paired_2d_seam_mismatch_fraction_difference"] < 1e-12
    assert not uv["full_raw_uv_json_bitwise_identical"]
    assert record["latest_passing_trusted_python_ci"]["passed_tests"] == 659


def test_real_blender_abf_improves_source_but_no_solvers_pass_all_gates():
    record = _data()
    scores = record["method_comparisons"]
    a = scores["BLENDER_ANGLE_BASED"]
    c = scores["BLENDER_CONFORMAL"]
    assert a["lower_p95_than_original_count"] == 11
    assert a["lower_seam_mismatch_than_original_count"] == 8
    assert a["both_better_count"] == 7
    assert c["both_better_count"] == 4
    assert a["passes_all_research_thresholds_count"] == 0
    assert c["passes_all_research_thresholds_count"] == 0
    assert a["total_source_face_flips"] == 0
    assert a["total_positive_area_face_overlaps"] == 0
    assert c["total_source_face_flips"] == 3
    assert c["total_positive_area_face_overlaps"] == 15
    matrix = record[
        "twelve_real_original_source_case_observations_rounded_to_6_decimals"
    ]
    assert len(matrix) == 12
    assert len({tuple(r[:3]) for r in matrix}) == 12
    assert sum(r[4] < r[3] for r in matrix) == 11
    assert sum(r[7] < r[6] for r in matrix) == 8
    assert sum(r[4] < r[3] and r[7] < r[6] for r in matrix) == 7
    assert sum(r[5] < r[3] and r[8] < r[6] for r in matrix) == 4
    assert (
        abs(median(r[4] for r in matrix) - a["median_p95_relative_edge_error"]) < 1e-6
    )
    assert (
        abs(
            median(r[7] for r in matrix)
            - a["median_relative_two_side_seam_length_mismatch"]
        )
        < 1e-6
    )
    assert record["best_observed_native_abf_case"]["ready_for_cutting"] is False


def test_free_native_uv_output_does_not_start_industrial_cutting():
    d = _data()
    progress = json.loads(PROGRESS.read_text(encoding="utf8"))
    phases = {phase["id"]: phase for phase in progress["phases"]}
    assert phases["P3"]["status"] == d["P3_status"] == "in_progress"
    assert phases["P4"]["status"] == d["P4_status"] == "not_started"
    assert EVIDENCE.relative_to(ROOT).as_posix() in {
        x["path"] for x in phases["P3"]["evidence"]
    }
    assert not progress["overall"]["factory_sample_pack_ready"]
    assert d["factory_cutting_patterns_approved"] == 0
    assert d["no_paid_or_closed_source_product_used"]
    assert d["original_source_mesh_modified"] is False
    assert d["original_source_seam_paths_modified"] is False
    assert d["no_fabric_properties_or_real_stitching_verified"]
