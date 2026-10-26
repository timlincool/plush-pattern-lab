"""Hard rejection tests: no 'green Blender job => accepted plush' shortcut."""

import json
import subprocess
import sys
from pathlib import Path

from plush_pattern_lab.validation import assess_research_candidate as gate
import pytest

PATH = Path(__file__).resolve().parents[1] / "scripts" / "assess_research_candidate.py"


def baseline():
    return {
        "status": "ACTUAL_CLOTH_SEWING_SPRINGS_NUMERICAL_TRIAL",
        "synthetic_panel_count": 8,
        "preposition_mode": "reference_offset",
        "reference_assisted_initialization": True,
        "final_geometry_quality": {
            "status": "NUMERICAL_DIAGNOSTICS_NOT_MANUFACTURING_APPROVAL",
            "seam": {"mean_gap_mm": 0.001, "max_gap_mm": 0.002},
            "target_shape": {"rigid_aligned_correspondence_rms_mm": 0.2},
            "strain": {
                "p95_abs_principal_strain": 0.07,
                "orientation_reversed_vs_initial": 0,
                "near_zero_area_triangles": 0,
            },
        },
    }


def test_research_geometry_pass_does_not_approve_manufacturing():
    d = gate.assess(baseline())
    assert d["passed"]
    assert d["status"] == "RESEARCH_GEOMETRY_SCREEN_PASSED"
    assert d["noncertified_requirements"]
    assert d["target_assisted_prepositioning"]


def test_zero_seam_still_rejects_wrong_shape():
    x = baseline()
    x["final_geometry_quality"]["seam"]["mean_gap_mm"] = 0
    x["final_geometry_quality"]["target_shape"][
        "rigid_aligned_correspondence_rms_mm"
    ] = 19
    d = gate.assess(x)
    assert not d["passed"]
    assert [v["metric"] for v in d["failed_checks"]] == ["aligned_target_rms_mm_max"]


def test_rejects_pole_flip_even_when_shape_is_good():
    x = baseline()
    x["final_geometry_quality"]["strain"]["orientation_reversed_vs_initial"] = 23
    x["final_geometry_quality"]["strain"]["p95_abs_principal_strain"] = 0.142
    d = gate.assess(x)
    assert not d["passed"]
    assert {f["metric"] for f in d["failed_checks"]} == {
        "orientation_reversals_max",
        "principal_strain_p95_max",
    }


def test_rejects_missing_or_nan_metrics():
    x = baseline()
    x["final_geometry_quality"]["seam"]["mean_gap_mm"] = float("nan")
    with pytest.raises(ValueError):
        gate.assess(x)
    with pytest.raises(ValueError):
        gate.assess({"status": "ACTUAL_CLOTH_SEWING_SPRINGS_NUMERICAL_TRIAL"})


def test_cli_exits_nonzero_on_explicit_promotion_failure(tmp_path):
    inp = tmp_path / "candidate.json"
    dst = tmp_path / "gate.json"
    bad = baseline()
    bad["final_geometry_quality"]["strain"]["orientation_reversed_vs_initial"] = 1
    inp.write_text(json.dumps(bad), encoding="utf8")
    p = subprocess.run(
        [
            sys.executable,
            str(PATH),
            "--report",
            str(inp),
            "--output",
            str(dst),
            "--require-pass",
        ],
        capture_output=True,
        text=True,
    )
    assert p.returncode == 2
    decision = json.loads(dst.read_text())
    assert decision["status"] == "RESEARCH_CANDIDATE_REJECTED"
    assert (
        subprocess.run(
            [sys.executable, str(PATH), "--report", str(inp), "--output", str(dst)],
            capture_output=True,
        ).returncode
        != 0
    )
