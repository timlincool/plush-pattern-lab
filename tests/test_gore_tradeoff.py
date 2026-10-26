import importlib.util
from pathlib import Path

import pytest

P = Path(__file__).resolve().parents[1] / "scripts" / "gore_tradeoff.py"
m = importlib.util.module_from_spec(importlib.util.spec_from_file_location("trade", P))
m.__loader__.exec_module(m)


def test_strain_vs_seam_and_cut_tradeoff():
    r = m.sweep()
    options = r["options"]
    assert len(options) == 6
    assert r["fewest_panels_meeting_study_threshold"] == 10
    assert all(
        a["worst_principal_strain"] > b["worst_principal_strain"]
        for a, b in zip(options, options[1:])
    )
    assert all(
        a["total_sewing_length_mm"] < b["total_sewing_length_mm"]
        for a, b in zip(options, options[1:])
    )
    assert all(
        a["total_cut_outline_area_mm2"] < b["total_cut_outline_area_mm2"]
        for a, b in zip(options, options[1:])
    )
    assert not r["material_measured"]


def test_rejects_invalid_study_threshold_and_candidates():
    with pytest.raises(ValueError):
        m.sweep(study_threshold=0.70)
    with pytest.raises(ValueError):
        m.sweep(candidates=(8, 8, 10))


def test_no_feasible_candidate_is_reported_not_invented():
    r = m.sweep(study_threshold=0.02)
    assert r["fewest_panels_meeting_study_threshold"] is None
