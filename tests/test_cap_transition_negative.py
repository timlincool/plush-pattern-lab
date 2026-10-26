"""Freeze the rejected local cap join experiment without enabling its solver knob."""

import json
from pathlib import Path

PATH = (
    Path(__file__).resolve().parents[1]
    / "experiments"
    / "cap_transition_20261026"
    / "results.json"
)


def test_no_cap_taper_was_approved_for_production():
    data = json.loads(PATH.read_text(encoding="utf-8"))
    assert data["github_actions_run"] == 40283704780
    assert data["source_commit"] == "d7ebc95b4edf7b131398b754d8c0ed6bda203b1f"
    assert data["status"] == "LOCAL_CAP_TRANSITION_REJECTED_RETAIN_DEFAULT"
    assert [row["transition_rows"] for row in data["cases"]] == [0, 2, 4]
    assert all(
        row["contact_gate"] == "RESEARCH_CONTACT_SCREEN_REJECTED"
        for row in data["cases"]
    )


def test_local_taper_failed_to_improve_default_end_join():
    rows = json.loads(PATH.read_text(encoding="utf-8"))["cases"]
    baseline = rows[0]
    assert baseline["nonseam_intersections"] == 4
    assert baseline["seam_related_intersections"] == 900
    assert baseline["target_rms_mm"] < rows[1]["target_rms_mm"]
    assert rows[1]["nonseam_intersections"] > baseline["nonseam_intersections"]
    assert rows[2]["nonseam_intersections"] > baseline["nonseam_intersections"]
    assert rows[2]["geometry_gate"] == "RESEARCH_CANDIDATE_REJECTED"
