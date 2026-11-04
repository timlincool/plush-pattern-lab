"""Keep the factory production roadmap evidence-based and discoverable."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRESS = ROOT / "docs/PRODUCTION_PROGRESS.json"
PHASES = {f"P{i}" for i in range(8)}


def load_progress():
    return json.loads(PROGRESS.read_text(encoding="utf-8"))


def test_factory_progress_has_a_unique_canonical_home():
    progress = load_progress()
    assert progress["schema"] == "cloud-alpaca-production-progress-v1"
    for name in (
        "docs/FACTORY_ROADMAP.md",
        "docs/PRODUCTION_PROGRESS.json",
        "docs/FACTORY_HANDOFF.md",
    ):
        assert (ROOT / name).is_file()
    assert progress["canonical_document"] == "docs/FACTORY_ROADMAP.md"
    assert progress["factory_handoff"] == "docs/FACTORY_HANDOFF.md"
    assert progress["source_repository"] == "timlincool/plush-pattern-lab"


def test_all_factory_gates_have_independent_proofs():
    progress = load_progress()
    rows = progress["phases"]
    assert len(rows) == 8
    assert {row["id"] for row in rows} == PHASES
    allowed = set(progress["status_vocabulary"])
    assert allowed == {
        "not_started",
        "in_progress",
        "partial_evidence",
        "accepted",
        "blocked_external",
    }
    for row in rows:
        assert row["status"] in allowed
        assert row["acceptance"] and row["name"]
        assert isinstance(row["blockers"], list)
        if row["status"] == "accepted":
            assert row["evidence"], row["id"]
        for evidence in row["evidence"]:
            path = Path(evidence["path"])
            assert not path.is_absolute() and ".." not in path.parts
            assert (ROOT / path).is_file(), row["id"]


def test_no_manufacturing_claim_without_physical_factory_evidence():
    progress = load_progress()
    overall = progress["overall"]
    assert not overall["factory_sample_pack_ready"]
    assert not overall["mass_production_ready"]
    assert not overall["approved_golden_sample_exists"]
    assert not overall["physical_plush_sample_exists"]
    assert overall["estimated_percent_complete"] is None
    phases = {row["id"]: row for row in progress["phases"]}
    for phase in ("P5", "P6", "P7"):
        assert phases[phase]["status"] != "accepted"
    assert not progress["verified_baseline"]["geometry_actual_model"][
        "manufacturing_approved"
    ]


def test_readme_agents_and_feature_map_link_to_one_roadmap():
    for path in (
        "README.md",
        "AGENTS.md",
        ".agents/skills/feature-map/SKILL.md",
    ):
        text = (ROOT / path).read_text(encoding="utf-8")
        for name in ("FACTORY_ROADMAP.md", "PRODUCTION_PROGRESS.json"):
            assert name in text, path
    assert len(load_progress()["next_actions"]) >= 3
