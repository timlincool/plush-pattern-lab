"""Keep provenance and negative results of the bounded 2026-10-26 research campaign."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments" / "capped_contact_20261026" / "results.json"


def campaign():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_evidence_is_linked_to_one_reproducible_experiment():
    report = campaign()
    assert report["source_commit"] == "8c8ba2ce0a3664654625b11c9a45a568b08efd8a"
    assert report["github_actions_run"] == 40278382515
    assert report["blender"] == "4.3.2"
    assert report["status"] == "SYNTHETIC_RESEARCH_CONTACT_SCREEN_REJECTED"
    assert report["controls"]["panel_count"] == 12
    assert report["controls"]["frames"] == 48


def test_all_parameter_experiments_still_reject_contact():
    report = campaign()
    assert len(report["pole_cut_ab"]) == 3
    assert len(report["radial_offset_ab"]) == 3
    assert len(report["normal_vs_radial_ab"]) == 4
    for family in ("pole_cut_ab", "radial_offset_ab", "normal_vs_radial_ab"):
        assert all(
            case["contact_gate"] == "RESEARCH_CONTACT_SCREEN_REJECTED"
            for case in report[family]
        )


def test_default_witnesses_are_concentrated_at_cap_junction():
    data = campaign()["baseline_self_collision"]
    disabled = next(row for row in data if row["mode"] == "disabled")
    enabled = next(row for row in data if row["mode"] == "enabled")
    assert (disabled["finite_nonadjacent_other"], enabled["finite_nonadjacent_other"]) == (
        4, 7
    )
    assert all(
        witness["zones"] == ["lower_join", "lower_join"]
        for witness in disabled["nonseam_position_witnesses"]
    )
    assert (
        len(disabled["nonseam_position_witnesses"]),
        len(enabled["nonseam_position_witnesses"]),
    ) == (4, 7)
    assert not disabled["research_contact_screen_pass"]
    assert not enabled["research_contact_screen_pass"]


def test_default_8_degree_3mm_radial_remains_the_frozen_baseline():
    evidence = campaign()
    angle = next(i for i in evidence["pole_cut_ab"] if i["pole_cut_degrees"] == 8)
    offset = next(i for i in evidence["radial_offset_ab"] if i["preposition_offset_mm"] == 3)
    original = next(i for i in evidence["normal_vs_radial_ab"] if
                    i["offset_mm"] == 3 and i["direction"] == "radial")
    assert angle["seam_related"] == offset["seam_related"] == original["seam_related"] == 900
    assert angle["nonseam"] == offset["nonseam"] == original["nonseam"] == 4
    assert angle["target_rms_mm"] == offset["target_rms_mm"] == original["rms_mm"]


def test_normal_hypothesis_was_rejected_not_marked_safe():
    rows = campaign()["normal_vs_radial_ab"]
    normal = [row for row in rows if row["direction"] == "normal"]
    assert len(normal) == 2
    assert all(row["nonseam"] == 24 for row in normal)
    worst = next(row for row in normal if row["offset_mm"] == 3)
    assert worst["geometry_gate"] == "RESEARCH_CANDIDATE_REJECTED"
    assert worst["rms_mm"] > 2.7
