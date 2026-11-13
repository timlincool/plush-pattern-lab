"""Real-source crown correction rejects synthetic caps and altered Source IDs."""

from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
from build_stage6_crown_230_overlay import (
    SCHEMA,
    _locked_json,
    _page_points,
    load_compact_witness,
    measure,
    render,
)


def _ring(x, y, size, index):
    xy = np.array(
        [
            [x - size, y - size],
            [x + size, y - size],
            [x + size, y + size],
            [x - size, y + size],
        ],
        dtype=float,
    )
    ids = np.array(
        [[index + j, index + j + 1] for j in range(4)], dtype="<i8"
    )
    digest = hashlib.sha256(
        ids.tobytes() + xy.astype("<f8").tobytes()
    ).hexdigest()
    return {
        "true_interpolated_contour_xy_mm": xy.tolist(),
        "crossed_original_mesh_vertex_id_edge_pairs": ids.tolist(),
        "original_source_edge_and_interpolated_xy_sha256": digest,
        "contour_perimeter_mm": float(8 * size),
        "closed_loop": True,
        "simple_polygon": True,
    }


def _fixture():
    loops = [
        _ring(0, -47, 2, 0),
        _ring(-8, -47, 1, 10),
        _ring(8, -47, 1, 20),
    ]
    source = {
        "schema": "stage6-true-triangle-plane-component-loops-v1",
        "factory_cutting_approved": 0,
        "sections": [
            {
                "plane_z_mm": 230,
                "true_source_plane_intersection_component_count": 3,
                "source_contours": loops,
            }
        ],
    }
    angles = np.linspace(0, 2 * np.pi, 64, endpoint=False)
    cap = np.column_stack((11 * np.cos(angles), -47 + 7 * np.sin(angles)))
    options = [
        {
            "name": name,
            "head_rings_z_mm": [145, 155, 180, 205, 230],
            "head_top_cap": {"outer_stitch_xy_mm": cap.tolist()},
        }
        for name in ("A_separate_stuffed_head", "B_integrated_neck_port")
    ]
    study = {
        "schema": "stage6-separated-torso-headneck-mother-trial-ab-v1",
        "factory_cutting_patterns_approved": 0,
        "options": options,
    }
    return source, study


def test_true_three_source_loops_and_trial_one_cap_print_full_scale():
    source, study = _fixture()
    result, loops, cap = measure(source, study)
    assert result["schema"] == SCHEMA
    assert result["real_original_source_components"] == 3
    assert result["source_original_boundary_edges_per_component"] == [4, 4, 4]
    assert result["source_true_loop_perimeters_mm"] == [16, 8, 8]
    assert result["old_A_B_single_surrogate_cap_to_actual_central_ratio"] > 1
    assert result["old_24piece_head_cap_rejected_as_anatomical_source_approximation"]
    assert result["factory_cutting_patterns_approved"] == 0
    assert result["P4_status"] == "not_started"
    svg = render(loops, cap, result)
    assert 'width="210mm" height="297mm"' in svg
    assert 'id="actual-central"' in svg
    assert 'id="actual-left"' in svg
    assert 'id="actual-right"' in svg
    assert 'id="old-surrogate"' in svg
    assert svg.count('data-true-source-edges="4"') == 3
    assert "NOT A CUT/SEW PATTERN" in svg
    assert "M 50,249 L 150,249" in svg


@pytest.mark.parametrize(
    "mutation",
    (
        "fake_factory",
        "missing_source_loop",
        "tampered_source_vertex",
        "tampered_edge_identity",
        "duplicate_ear_loop",
        "wrong_left_right",
        "A_B_caps_differ",
        "old_cap_wrong_height",
    ),
)
def test_source_or_old_cap_tampering_rejected(mutation):
    source, study = _fixture()
    rows = source["sections"][0]["source_contours"]
    if mutation == "fake_factory":
        source["factory_cutting_approved"] = 1
    elif mutation == "missing_source_loop":
        rows.pop()
    elif mutation == "tampered_source_vertex":
        rows[0]["true_interpolated_contour_xy_mm"][0][0] += 0.2
    elif mutation == "tampered_edge_identity":
        rows[0]["crossed_original_mesh_vertex_id_edge_pairs"][0][0] = 999
    elif mutation == "duplicate_ear_loop":
        rows[2] = deepcopy(rows[1])
    elif mutation == "wrong_left_right":
        rows[1], rows[2] = rows[2], rows[1]
    elif mutation == "A_B_caps_differ":
        study["options"][1]["head_top_cap"]["outer_stitch_xy_mm"][0][0] += 1
    else:
        study["options"][0]["head_rings_z_mm"][-1] = 225
    with pytest.raises(ValueError):
        measure(source, study)


def test_one_to_one_page_transform_does_not_rescale_measurements():
    xy = np.array([[0, -47], [60, -47]], dtype=float)
    x, y = _page_points(xy)
    assert x[1] - x[0] == pytest.approx(60)
    assert y[0] == y[1] == pytest.approx(99)


def test_original_input_sha_check_rejects_unauthorized_json(tmp_path):
    fake = tmp_path / "untrusted.json"
    fake.write_text("{}", encoding="utf8")
    with pytest.raises(ValueError, match="SHA256 changed"):
        _locked_json(fake, "0" * 64)

def test_real_trusted_stage6_414_crossing_edges_replay_after_artifact_expiry():
    root = Path(__file__).resolve().parents[1]
    witness = root / "experiments/stage6_z230_true_crown_20261113/witness.json"
    source, trial = load_compact_witness(witness)
    measured, loops, cap = measure(source, trial)
    assert measured["source_original_boundary_edges_per_component"] == [
        189, 113, 112
    ]
    assert measured["source_true_loop_perimeters_mm"] == pytest.approx(
        [153.0939971276184, 45.51675545730191, 45.510986167806784]
    )
    assert measured["old_A_B_single_surrogate_cap_perimeter_mm"] == pytest.approx(
        319.77053282271424
    )
    assert measured["central_vs_surrogate_planar_boundary_hausdorff_mm"] == (
        pytest.approx(38.212240865383805)
    )
    assert "NOT A CUT/SEW PATTERN" in render(loops, cap, measured)
    assert measured["factory_cutting_patterns_approved"] == 0


def test_repacked_source_witness_sha_tamper_is_not_silently_accepted(tmp_path):
    root = Path(__file__).resolve().parents[1]
    original = root / "experiments/stage6_z230_true_crown_20261113/witness.json"
    forged = tmp_path / "witness.json"
    forged.write_bytes(original.read_bytes().replace(b"230", b"231", 1))
    with pytest.raises(ValueError, match="SHA256 changed"):
        load_compact_witness(forged)
