"""Counterexamples: a topologically closed sewn shell can still self-intersect."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from plush_pattern_lab.validation import assess_contact_integrity as veto

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "assess_contact_integrity.py"


def fixture():
    sim = {
        "status": "ACTUAL_CAPPED_CLOTH_SEWING_RESEARCH_ONLY",
        "self_collision_enabled": True,
        "vertices": 2390,
        "total_face_count": 1560,
        "total_sewing_springs": 828,
    }
    tri = {
        "status": "FINITE_ZERO_THICKNESS_TRIANGLE_INTERSECTION_SCREEN",
        "research_trial_self_collision_enabled": True,
        "vertex_count": 2390,
        "triangle_count": 3120,
        "sewing_identity_links": 828,
        "shared_vertex_pairs_excluded": 0,
        "nonadjacent_seam_related_pair_count": 0,
        "nonadjacent_other_pair_count": 0,
        "nonadjacent_total_intersections": 0,
    }
    return sim, tri


def test_nonadjacent_crossing_rejects_collision_free_claim():
    sim, tri = fixture()
    tri["nonadjacent_other_pair_count"] = 7
    tri["nonadjacent_total_intersections"] = 7
    gate = veto.assess(sim, tri)
    assert gate["status"] == "RESEARCH_CONTACT_SCREEN_REJECTED"
    assert gate["all_nonadjacent_intersections"] == 7
    assert gate["physical_cloth_or_stuffing_approved"] is False


def test_seam_related_crossing_is_not_silently_dismissed():
    sim, tri = fixture()
    tri["nonadjacent_seam_related_pair_count"] = 851
    tri["nonadjacent_total_intersections"] = 851
    result = veto.assess(sim, tri)
    assert not result["finite_zero_thickness_screen_pass"]
    assert result["other_nonadjacent_intersections"] == 0


def test_clear_screen_is_not_material_certification():
    sim, tri = fixture()
    result = veto.assess(sim, tri)
    assert result["finite_zero_thickness_screen_pass"]
    assert result["status"] == "FINITE_TRIANGLE_CONTACT_SCREEN_CLEAR_NOT_CERTIFIED"
    assert not result["physical_cloth_or_stuffing_approved"]


@pytest.mark.parametrize(
    "field,bad",
    [
        ("nonadjacent_total_intersections", -1),
        ("nonadjacent_other_pair_count", float("nan")),
        ("nonadjacent_other_pair_count", True),
        ("triangle_count", 9999),
        ("sewing_identity_links", 900),
    ],
)
def test_bad_or_untrusted_evidence_refused(field, bad):
    sim, tri = fixture()
    tri[field] = bad
    with pytest.raises(ValueError):
        veto.assess(sim, tri)


def test_wrong_simulation_sha_and_collision_mode_refused():
    sim, tri = fixture()
    tri["source_report_sha256"] = "wrong"
    with pytest.raises(ValueError):
        veto.assess(sim, tri, report_sha256="expected")
    tri["source_report_sha256"] = "expected"
    sim["self_collision_enabled"] = False
    with pytest.raises(ValueError):
        veto.assess(sim, tri, report_sha256="expected")


def test_cli_always_saves_veto_then_exits_nonzero_only_when_promotion_requested(
    tmp_path,
):
    sim, tri = fixture()
    tri["nonadjacent_other_pair_count"] = 1
    tri["nonadjacent_total_intersections"] = 1
    source = tmp_path / "sim.json"
    source.write_text(json.dumps(sim))
    tri["source_report_sha256"] = veto.sha256(source)
    path = tmp_path / "tri.json"
    path.write_text(json.dumps(tri))
    out = tmp_path / "gate.json"
    command = [
        sys.executable,
        str(SOURCE),
        "--simulation-report",
        str(source),
        "--triangle-report",
        str(path),
        "--output",
        str(out),
        "--require-pass",
    ]
    p = subprocess.run(command, capture_output=True, text=True)
    assert p.returncode == 2
    assert json.loads(out.read_text())["status"] == "RESEARCH_CONTACT_SCREEN_REJECTED"
