"""Boundary identity and surface metric counterexamples for shell proxy studies."""

from copy import deepcopy

import numpy as np
import pytest

from plush_pattern_lab.validation.manufacturing_proxy_quality import (
    register_original_hoof_seams,
    sampled_surface_distances_mm,
)


def _rings():
    theta = 2 * np.pi * np.arange(512) / 512
    records = []
    for k in range(4):
        radius = 9 + k + 0.13 * np.sin(3 * theta)
        coords = np.column_stack(
            (
                radius * np.cos(theta) + 50 * k,
                radius * np.sin(theta),
                np.full(512, 10.0 * k) + 0.01 * np.cos(theta),
            )
        )
        records.append(
            {
                "vertex_ids": list(range(512 * k, 512 * (k + 1))),
                "xyz_mm": coords.tolist(),
            }
        )
    return records


def _proxy(rings):
    result = []
    for item in rings:
        result.append(
            {
                "vertex_ids": np.roll(
                    np.asarray(item["vertex_ids"]) + 10000, 127
                ).tolist(),
                "xyz_mm": np.roll(item["xyz_mm"], 127, axis=0).tolist(),
            }
        )
    return result[::-1]


def test_four_full_hoop_registrations_with_cyclic_permutations():
    original = _rings()
    result = register_original_hoof_seams(original, _proxy(original))
    assert result["all_original_seam_points_and_winding_preserved"]
    assert result["source_to_proxy_vertex_identity_is_explicit"]
    assert len(result["registrations"]) == 4
    assert all(row["vertex_count"] == 512 for row in result["registrations"])
    assert all(row["max_gap_mm"] < 1e-8 for row in result["registrations"])
    for k, row in enumerate(result["registrations"]):
        assert row["source_ring_index"] == k
        assert len(row["original_to_proxy_vertex_id"]) == 512
        assert row["original_to_proxy_vertex_id"][0] == [512 * k, 10000 + 512 * k]
        assert row["matching_direction_preserved"]


def test_reversed_winding_is_not_a_valid_sewing_interface():
    original = _rings()
    candidate = _proxy(original)
    candidate[0]["vertex_ids"].reverse()
    candidate[0]["xyz_mm"].reverse()
    result = register_original_hoof_seams(original, candidate)
    assert not result["all_original_seam_points_and_winding_preserved"]
    assert not result["source_to_proxy_vertex_identity_is_explicit"]
    intact = sum(
        row["exact_world_geometry_accepted"] for row in result["registrations"]
    )
    assert intact == 3


def test_hoof_seam_motion_is_rejected_even_when_nearly_invisible():
    original = _rings()
    candidate = _proxy(original)
    candidate[0]["xyz_mm"][4][0] += 0.005
    result = register_original_hoof_seams(original, candidate)
    assert not result["all_original_seam_points_and_winding_preserved"]
    assert any(row["max_gap_mm"] > 0.0001 for row in result["registrations"])


@pytest.mark.parametrize("case", ("missing_ring", "repeated_id", "nan", "wrong_length"))
def test_bad_boundary_identity_refused_before_claiming_proxy(case):
    original = _rings()
    candidate = deepcopy(original)
    if case == "missing_ring":
        candidate.pop()
    elif case == "repeated_id":
        candidate[0]["vertex_ids"][0] = candidate[0]["vertex_ids"][1]
    elif case == "nan":
        candidate[1]["xyz_mm"][1][1] = float("nan")
    else:
        candidate[2]["xyz_mm"].pop()
        candidate[2]["vertex_ids"].pop()
    with pytest.raises(ValueError):
        register_original_hoof_seams(original, candidate)


def test_distance_metrics_are_samples_not_full_surface_certification():
    measured = sampled_surface_distances_mm([0, 0.15, 0.25, 0.5])
    assert measured["sample_count"] == 4
    assert measured["max_mm"] == 0.5
    assert measured["mean_mm"] == pytest.approx(0.225)
    assert "not exact Hausdorff" in measured["sampling_note"]


@pytest.mark.parametrize("data", ([], [float("nan")], [-0.1], [[1], [2]]))
def test_invalid_surface_samples_rejected(data):
    with pytest.raises(ValueError):
        sampled_surface_distances_mm(data)
