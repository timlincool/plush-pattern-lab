"""Genuine Stage6 3D cap ABF must not be mistaken for a sewn 2D lower side."""

from __future__ import annotations

from copy import deepcopy

import pytest

from audit_stage6_true_crown_caps_abf import (
    INPUT_SCHEMA,
    RESULT_SCHEMA,
    UV_SCHEMA,
    _score_one,
    audit_real_source_abf,
)


def _flat_square():
    cap = {
        "id": "synthetic_fixture_only",
        "source_boundary_edges": 4,
        "vertices_xyz_mm": [
            [0.0, 0.0, 0.0], [3.0, 0.0, 0.0],
            [3.0, 2.0, 0.0], [0.0, 2.0, 0.0],
        ],
        "triangles_local_vertex_indices": [[0, 1, 2], [0, 2, 3]],
        "original_rim_vertex_ids_in_cap_local_order": [0, 1, 2, 3],
        "source_3d_rim_perimeter_mm": 10.0,
    }
    native = {
        "source_cap_id": "synthetic_fixture_only",
        "source_vertex_count": 4,
        "source_triangle_count": 2,
        "original_cut_rim_edges": 4,
        "uv_per_3d_cap_source_vertex": [
            [0, 0], [0.3, 0], [0.3, 0.2], [0, 0.2],
        ],
        "maximum_split_UV_loop_disagreement": 0.0,
    }
    return cap, native


def test_same_3d_to_native_abf_quality_scaling_does_not_create_lower_seam():
    cap, uv = _flat_square()
    observed = _score_one(cap, uv, "synthetic_fixture_only", 4)
    assert observed["source_3d_rim_perimeter_mm"] == pytest.approx(10.0)
    assert observed["ABF_2d_single_side_netline_perimeter_mm"] == pytest.approx(10.0)
    assert observed["source_3d_edge_to_ABF_2d_p95_relative_error"] < 1e-10
    assert observed["ABF_positive_area_overlapping_triangle_pairs"] == 0
    assert observed["conditional_research_screen_passed"]
    assert observed["lower_matching_2d_sewing_side_has_not_been_unwrapped"]


@pytest.mark.parametrize("fault", ("mismatched_rim", "UV_split", "nonfinite", "scale"))
def test_abf_source_rim_cannot_be_silently_changed(fault):
    cap, uv = _flat_square()
    if fault == "mismatched_rim":
        cap["original_rim_vertex_ids_in_cap_local_order"][-1] = 2
    elif fault == "UV_split":
        uv["maximum_split_UV_loop_disagreement"] = 0.3
    elif fault == "nonfinite":
        uv["uv_per_3d_cap_source_vertex"][0][0] = float("nan")
    else:
        cap["source_3d_rim_perimeter_mm"] = 11.0
    if fault == "scale":
        result = _score_one(cap, uv, "synthetic_fixture_only", 4)
        assert not result["conditional_research_screen_passed"]
    else:
        with pytest.raises(ValueError):
            _score_one(cap, uv, "synthetic_fixture_only", 4)


def _mock_study():
    cap, native = _flat_square()
    caps = [{**deepcopy(cap), "id": name} for name in (
        "central_crown", "left_high_protrusion", "right_high_protrusion"
    )]
    uvs = [{**deepcopy(native), "source_cap_id": c["id"]} for c in caps]
    for c, uv, rim in zip(caps, uvs, (189, 113, 112)):
        c["source_boundary_edges"] = rim
        uv["original_cut_rim_edges"] = rim
    geometry = {
        "schema": INPUT_SCHEMA,
        "industrial_cutting_patterns_approved": 0,
        "P4_status": "not_started",
        "upper_caps": caps,
        "upper_to_lower_source_netline_matched_at_1e_6_mm": True,
    }
    summary = {"full_3d_source_caps_json_sha256": "same-source-sha"}
    uv_output = {
        "schema": UV_SCHEMA,
        "source_caps_geometry_sha256": "same-source-sha",
        "blender_version": "4.3.2",
        "solver": "ANGLE_BASED",
        "factory_cutting_patterns_approved": 0,
        "entries": uvs,
    }
    return geometry, summary, uv_output


def test_three_cap_3d_abf_contract_cannot_promote_factory(monkeypatch):
    import audit_stage6_true_crown_caps_abf as module

    def fake_score(cap, uv, name, count):
        assert cap["id"] == uv["source_cap_id"] == name
        assert cap["source_boundary_edges"] == count
        return {"conditional_research_screen_passed": False}

    monkeypatch.setattr(module, "_score_one", fake_score)
    geometry, summary, uv_output = _mock_study()
    result = audit_real_source_abf(geometry, summary, uv_output, "same-source-sha")
    assert result["schema"] == RESULT_SCHEMA
    assert result["three_real_stage6_original_triangle_mesh_caps_scored"] == 3
    assert not result["all_caps_research_gates_passed"]
    assert result["research_only_missing_lower_2d_match_and_material"]
    assert result["factory_cutting_patterns_approved"] == 0


@pytest.mark.parametrize("fault", ("uv_sha", "wrong_solver", "factory_approved"))
def test_same_run_native_abf_source_lock_rejects_stale_or_faked_data(fault):
    geometry, summary, native = _mock_study()
    if fault == "uv_sha":
        native["source_caps_geometry_sha256"] = "wrong"
    elif fault == "wrong_solver":
        native["solver"] = "CONFORMAL"
    else:
        native["factory_cutting_patterns_approved"] = 1
    with pytest.raises(ValueError):
        audit_real_source_abf(geometry, summary, native, "same-source-sha")
