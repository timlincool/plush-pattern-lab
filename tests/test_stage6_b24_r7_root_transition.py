"""Fail-closed R7 root-lift geometry and prior R5 compatibility tests."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pytest

from research.stage6_b24_r5 import build_r5_side_lobes as baseline
from research.stage6_b24_r7 import build_r7_root_transition as candidate


def _source_rings():
    angle = np.linspace(0, 2 * np.pi, 32, endpoint=False)
    disk = np.column_stack((np.cos(angle), np.sin(angle)))
    return [
        disk * width + (dx, 0) for width, dx in ((2.5, 10), (3, 54), (4, 55), (3, 60))
    ]


def test_r7_monotone_root_height_and_true_235_245_preservation():
    z = candidate.R7_LEVELS_MM
    assert z == (230, 232, 234, 235, 245)
    assert all(b > a for a, b in zip(z, z[1:]))
    assert candidate.R7_FRACTIONS == (0, 0.12, 0.46, 1, 1)


def test_r5_default_unchanged():
    assert baseline.generate.__defaults__ == (baseline._append_bridge,)


def test_r7_rejects_foldback(monkeypatch):
    monkeypatch.setattr(candidate, "R7_LEVELS_MM", (230, 240, 230, 235, 245))
    with pytest.raises(ValueError, match="non-monotone"):
        candidate.bridge({}, [], [], [], [], 1, _source_rings())


def test_r7_smooth_outward_interpolation_and_exact_builder_reuse():
    source = _source_rings()
    gores = [np.arange(i * 45, (i + 1) * 45).reshape(5, 9) for i in range(4)]
    spring_pairs = []
    with patch.object(baseline, "_append_side_gores", return_value=gores) as make:
        with patch.object(baseline, "_append_tip_wedges") as cap:
            result = candidate.bridge(
                {}, [], [], spring_pairs, np.arange(32), 1, source
            )
    _, _, _, _, _, _, ring_list, heights = make.call_args.args
    assert heights == candidate.R7_LEVELS_MM
    assert np.allclose(ring_list[0], source[0])
    assert np.allclose(ring_list[1], 0.88 * source[0] + 0.12 * source[1])
    assert np.allclose(ring_list[2], 0.54 * source[0] + 0.46 * source[1])
    assert np.allclose(ring_list[3], source[2])
    assert np.allclose(ring_list[4], source[3])
    assert len(spring_pairs) == 20
    assert cap.call_count == 1
    assert result["original_real_ear_meshes_sewn"] == 0
