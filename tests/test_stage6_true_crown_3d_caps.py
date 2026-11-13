"""Adversarial source-edge tests; real full Stage6 PLY is checked by trusted CI."""

from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

from plush_pattern_lab.validation.stage6_true_crown_3d_caps import (
    _closed_ring_sizes,
    _match_rim_to_original,
    validate_witness,
)


def _square():
    vertices = np.asarray(
        [[0, 0, 230], [3, 0, 230], [3, 2, 230], [0, 2, 230]], dtype=float
    )
    rim = np.asarray([[0, 1], [1, 2], [2, 3], [3, 0]])
    source = {
        "true_interpolated_contour_xy_mm": vertices[:, :2].tolist(),
        "contour_perimeter_mm": 10.0,
    }
    return vertices, rim, source


def test_true_source_cut_rim_must_preserve_each_segment_and_mm():
    xyz, rim, source = _square()
    order, length = _match_rim_to_original(xyz, rim, source)
    assert order == [0, 1, 2, 3]
    assert length == pytest.approx(10)
    assert _closed_ring_sizes(rim) == [4]


@pytest.mark.parametrize(
    "fault", ("offset", "duplicate", "wrong_edge", "wrong_perimeter")
)
def test_source_cut_cannot_silently_replace_real_original_edge(fault):
    xyz, rim, source = _square()
    xyz, rim, source = xyz.copy(), rim.copy(), deepcopy(source)
    if fault == "offset":
        xyz[0, 0] += 0.01
    elif fault == "duplicate":
        rim[-1] = rim[0]
    elif fault == "wrong_edge":
        rim[-1] = [1, 3]
    else:
        source["contour_perimeter_mm"] = 11.0
    with pytest.raises(ValueError):
        _match_rim_to_original(xyz, rim, source)


def test_source_cut_rejects_open_and_branching_seam_graph():
    with pytest.raises(ValueError):
        _closed_ring_sizes(np.asarray([[0, 1], [1, 2], [2, 3]]))
    with pytest.raises(ValueError):
        _closed_ring_sizes(np.asarray([[0, 1], [1, 2], [2, 0], [0, 3]]))


def test_permanent_witness_requires_exact_sha_and_original_source():
    fake = {
        "schema": "fake",
        "factory_patterns_approved": 0,
        "source_component_count": 3,
    }
    with pytest.raises(ValueError):
        validate_witness(np.zeros((8, 3)), np.zeros((4, 3)), fake, b"fake")
