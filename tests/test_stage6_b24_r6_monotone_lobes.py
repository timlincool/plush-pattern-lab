"""Negative controls for independent R6 monotone-height research variant."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pytest

from research.stage6_b24_r5 import build_r5_side_lobes as baseline
from research.stage6_b24_r6 import build_r6_monotone_lobes as candidate


def _synthetic_profile():
    angle = np.linspace(0, 2 * np.pi, 32, endpoint=False)
    unit = np.column_stack((np.cos(angle), np.sin(angle)))
    return [
        unit * 2.5 + (10, 0),
        unit * 3 + (20, 0),
        unit * 4 + (45, 0),
        unit * 3 + (47, 0),
    ]


def test_r6_ascending_five_levels():
    assert candidate.R6_HEIGHTS_MM == (230, 231, 232, 235, 245)
    assert all(
        b > a for a, b in zip(candidate.R6_HEIGHTS_MM, candidate.R6_HEIGHTS_MM[1:])
    )
    assert 235 in candidate.R6_HEIGHTS_MM and 245 in candidate.R6_HEIGHTS_MM
    assert candidate.R5_REJECTED_HEIGHTS_MM[1] > candidate.R5_REJECTED_HEIGHTS_MM[2]


def test_r5_original_generator_default_unchanged():
    assert baseline.generate.__defaults__ == (baseline._append_bridge,)


def test_nonmonotone_negative_control(monkeypatch):
    monkeypatch.setattr(candidate, "R6_HEIGHTS_MM", (230, 240, 230, 235, 245))
    with pytest.raises(ValueError, match="descending"):
        candidate.bridge({}, [], [], [], [], -1, _synthetic_profile())


def test_r6_reuses_four_gores_and_four_tip_wedges():
    with patch.object(baseline, "_append_side_gores") as gores:
        with patch.object(baseline, "_append_tip_wedges") as wedges:
            gores.return_value = [
                np.arange(i * 45, (i + 1) * 45).reshape(5, 9) for i in range(4)
            ]
            result = candidate.bridge(
                {}, [], [], [], np.arange(32), -1, _synthetic_profile()
            )
            _, _, _, _, _, _, full, heights = gores.call_args.args
            assert list(heights) == list(candidate.R6_HEIGHTS_MM)
            assert np.allclose(full[3], _synthetic_profile()[2])
            assert result["actual_original_ear_Mesh_sewn"] is False
            assert wedges.called
