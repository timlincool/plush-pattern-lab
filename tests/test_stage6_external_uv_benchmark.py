"""Reject invalid external UV comparisons, mismatched source IDs and factory claims."""

from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

from plush_pattern_lab.validation import stage6_external_uv_benchmark as bench


def _fixture():
    rows = []
    results = []
    for a in ("N15", "N17"):
        for side in ("left", "right"):
            for direction in ("medial", "posterior", "lateral"):
                name = f"{a}_sloped_source_band"
                original = {
                    "source_variant": name,
                    "original_source_side": side,
                    "source_slit_direction": direction,
                    "original_source_patch_sha256": f"{a}{side}",
                    "cut_disk_source_xyz_mm": [[0.0, 0.0, 0.0]] * 24,
                    "cut_disk_original_source_triangle_indices": [[0, 1, 2]] * 32,
                    "source_3d_cut_length_mm": 20,
                    "uniform_scale_normalized_edge_diagnostics": {
                        "scaled_2d_p95_abs_edge_relative_error": 0.35
                    },
                    "true_source_seam_3d_vs_lscm_2d_pairing": {
                        "scaled_planar_2d_two_sides_length_mismatch_fraction_of_source_3d": 0.15
                    },
                    "original_source_planar_face_geometry_diagnostics": {
                        "reversed_or_collapsed_triangle_count": 0,
                        "overlapping_positive_area_triangle_pair_count": 0,
                    },
                }
                rows.append(original)
                for method in bench.METHODS:
                    results.append(
                        {
                            "source_variant": name,
                            "source_side": side,
                            "slit_direction": direction,
                            "source_patch_sha256": f"{a}{side}",
                            "method": method,
                            "status": "completed",
                            "vertex_count": 24,
                            "triangle_count": 32,
                            "max_same_topological_vertex_uv_loop_disagreement": 0.0,
                            "uv_per_original_source_disk_vertex": [[0.0, 0.0]] * 24,
                            "runtime_seconds": 0.2,
                        }
                    )
    source = {
        "schema": bench.ORIGINAL_SCHEMA,
        "original_public_blend_sha256": "stage6-fixed-test",
        "factory_cutting_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
        "candidate_2d_research_disks": rows,
    }
    native = {
        "schema": bench.NATIVE_SCHEMA,
        "blender_version": "4.3.2",
        "source_study_sha256": "test-immutable-source-sha",
        "source_blend_sha256": "stage6-fixed-test",
        "methods": list(bench.METHODS),
        "third_party_commercial_service_used": False,
        "cutting_patterns_approved": 0,
        "entries": results,
    }
    return source, native


def _synthetic_metrics(row, uv, method):
    assert uv.shape == (24, 2)
    assert method in bench.METHODS
    return {
        "method": method,
        "scaled_2d_p95_abs_edge_relative_error": 0.25,
        "2d_two_sides_length_mismatch_fraction_of_source_3d": 0.05,
        "inverted_or_collapsed_2d_source_faces": 0,
        "overlapping_positive_area_face_pairs": 0,
        "passes_unverified_research_thresholds": False,
    }


def test_free_native_two_solver_twelve_original_disk_matrix_complete(monkeypatch):
    monkeypatch.setattr(bench, "_metrics", _synthetic_metrics)
    source, native = _fixture()
    measured = bench.compare_native_to_existing(
        source, native, "test-immutable-source-sha"
    )
    assert measured["schema"] == bench.SCHEMA
    assert measured["total_source_disks"] == 12
    assert measured["native_solver_cases"] == 24
    assert measured["factory_cutting_patterns_approved"] == 0
    assert measured["P4_status"] == "not_started"
    for method in bench.METHODS:
        assert measured["method_comparison_summary"][method]["better_both"] == 12
        assert (
            measured["method_comparison_summary"][method]["research_gates_passed"] == 0
        )
    chart = bench.render_comparison_svg(measured)
    assert "NO FACTORY PATTERNS" in chart
    assert "N15 l medi" in chart and "N17 r late" in chart


@pytest.mark.parametrize(
    "mutate",
    (
        "source_hash",
        "commercial_paid",
        "fake_factory",
        "one_solver_missing",
        "duplicate_candidate",
        "different_source_patch",
        "new_uv_vertex_split",
        "wrong_source_triangle_count",
        "blender_version",
    ),
)
def test_mismatched_free_external_benchmark_fails_closed(monkeypatch, mutate):
    monkeypatch.setattr(bench, "_metrics", _synthetic_metrics)
    source, native = _fixture()
    if mutate == "source_hash":
        native["source_study_sha256"] = "not-the-source"
    elif mutate == "commercial_paid":
        native["third_party_commercial_service_used"] = True
    elif mutate == "fake_factory":
        source["factory_cutting_patterns_approved"] = 1
    elif mutate == "one_solver_missing":
        native["entries"].pop()
    elif mutate == "duplicate_candidate":
        native["entries"][0] = deepcopy(native["entries"][1])
    elif mutate == "different_source_patch":
        native["entries"][0]["source_patch_sha256"] = "tampered"
    elif mutate == "new_uv_vertex_split":
        native["entries"][0]["max_same_topological_vertex_uv_loop_disagreement"] = 0.01
    elif mutate == "wrong_source_triangle_count":
        native["entries"][0]["triangle_count"] -= 1
    else:
        native["blender_version"] = "4.5.0"
    with pytest.raises(ValueError):
        bench.compare_native_to_existing(source, native, "test-immutable-source-sha")


def test_native_uv_research_not_just_zero_vertex_array(monkeypatch):
    source, native = _fixture()
    target = native["entries"][0]
    target["uv_per_original_source_disk_vertex"] = [[float("nan"), 0.0]] * 24
    # Feed through the *real* evaluator, not the monkeypatched mock.
    with pytest.raises(ValueError):
        bench.compare_native_to_existing(source, native, "test-immutable-source-sha")


def test_external_score_recovers_true_planar_source_edge_lengths():
    # Real independent edge-error primitive: flat 3D→identical XY must remain zero.
    xyz = np.array([[0, 0, 0], [5, 0, 0], [0, 4, 0], [5, 4, 0]], dtype=float)
    tri = np.array([[0, 1, 2], [1, 3, 2]], dtype=np.int64)
    uv = xyz[:, :2] / 10
    scaled, _, scores = bench._scale_free_gauge(xyz, tri, uv)
    assert np.allclose(scaled - scaled[0], xyz[:, :2] - xyz[0, :2])
    assert scores["scaled_2d_p95_abs_edge_relative_error"] < 1e-12
