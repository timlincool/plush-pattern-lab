"""纯数值缝环校验：方向、循环起点、一对一映射与错误输入。"""

import numpy as np
import pytest

from plush_pattern_lab.validation.boundary_match import (
    as_ring_mm,
    cyclic_match_mm,
    perimeter_mm,
    unique_centroid_mapping,
    verify_mating_loops,
)


def ellipse(center=(0, 0, 0), count=32):
    phase = np.arange(count, dtype=np.float64) * (2 * np.pi / count)
    return np.stack(
        [
            np.cos(phase) * 13 + center[0],
            np.sin(phase) * 11 + center[1],
            np.full(count, center[2]),
        ],
        axis=1,
    )


def test_same_ring_opposite_winding_and_cyclic_start():
    original = ellipse()
    opposite = np.roll(original[::-1], 7, axis=0)
    score = verify_mating_loops(original, opposite)
    assert score["world_boundary_geometry_match"]
    assert score["reversed_boundary_winding"]
    assert score["max_gap_mm"] == 0
    assert score["perimeter_delta_mm"] == pytest.approx(0, abs=1e-10)
    assert score["vertex_count"] == 32


def test_identical_boundary_direction_is_not_mating_winding():
    a = ellipse()
    result = verify_mating_loops(a, np.roll(a, 9, axis=0))
    assert result["max_gap_mm"] == 0
    assert not result["reversed_boundary_winding"]
    assert not result["world_boundary_geometry_match"]


def test_off_plane_hoof_is_rejected_even_if_perimeter_equal():
    a = ellipse()
    b = a[::-1].copy()
    b[:, 2] += 0.1
    result = verify_mating_loops(a, b)
    assert result["perimeter_delta_mm"] == pytest.approx(0, abs=1e-10)
    assert result["max_gap_mm"] == pytest.approx(0.1)
    assert not result["world_boundary_geometry_match"]


def test_perimeter_is_full_3d_not_xy_projection():
    loop = np.array([[0, 0, 0], [3, 0, 4], [0, 4, 0]], dtype=float)
    assert perimeter_mm(loop) == pytest.approx(5 + 4 + np.sqrt(41))


def test_unique_ring_mapping_on_four_permuted_parts():
    coords = [(-50, -50, 0), (50, -50, 0), (-50, 50, 0), (50, 50, 0)]
    bodies = [ellipse(center=p) for p in coords]
    hoofs = [bodies[i][::-1] for i in (2, 0, 3, 1)]
    matches = unique_centroid_mapping(bodies, hoofs)
    assert [x[0] for x in matches] == [2, 0, 3, 1]
    assert all(distance < 1e-10 for _, distance in matches)


@pytest.mark.parametrize(
    "bad",
    [
        np.array([[0, 0, 0], [1, 0, 0]]),
        np.zeros((3, 2)),
        np.array([[0, 0, 0], [1, 0, 0], [1, 0, 0]]),
        np.array([[0, 0, 0], [1, 0, 0], [float("nan"), 1, 0]]),
    ],
)
def test_reject_invalid_or_degenerate_rings(bad):
    with pytest.raises(ValueError):
        as_ring_mm(bad)


def test_reject_different_point_counts():
    with pytest.raises(ValueError, match="采样点数不同"):
        cyclic_match_mm(ellipse(count=32), ellipse(count=16))


def test_reject_over_relaxed_numeric_tolerance():
    with pytest.raises(ValueError, match="放宽"):
        verify_mating_loops(ellipse(), ellipse()[::-1], tolerance_mm=0.5)


def test_reject_duplicate_hoof_to_same_body_loop():
    body = [ellipse(center=(0, 0, 0)), ellipse(center=(100, 0, 0))]
    duplicated = [ellipse(center=(1, 0, 0)), ellipse(center=(2, 0, 0))]
    with pytest.raises(ValueError, match="唯一映射"):
        unique_centroid_mapping(body, duplicated)


def test_large_ring_refused_before_quadratic_alignment():
    phase = np.arange(4097, dtype=float) / 4097 * 2 * np.pi
    source = np.stack([np.cos(phase), np.sin(phase), phase], axis=1)
    with pytest.raises(ValueError, match="顶点数量"):
        as_ring_mm(source)
