"""A Stage6 component draft is not a material BOM or approved cut-pattern set."""

import json
from pathlib import Path

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "design/manufacturing/STAGE6_COMPONENT_REGISTRY_DRAFT.json"
PROGRESS = ROOT / "docs/PRODUCTION_PROGRESS.json"


def test_project_progress_tracks_components_without_promoting_factory_readiness():
    data = json.loads(REGISTER.read_text(encoding="utf-8"))
    progress = json.loads(PROGRESS.read_text(encoding="utf-8"))
    p2 = next(item for item in progress["phases"] if item["id"] == "P2")
    assert data["source_sha256"] == SOURCE_SHA256
    assert data["model_mesh_count"] == 42
    assert data["approved_cut_patterns"] == 0
    assert not data["manufacturing_handoff_ready"]
    assert p2["status"] == "in_progress"
    assert any(
        item["path"] == "design/manufacturing/STAGE6_COMPONENT_REGISTRY_DRAFT.json"
        for item in p2["evidence"]
    )
    audit = progress["verified_baseline"]["draft_component_registry"]
    assert audit["visual_mesh_candidates"] == 42
    assert audit["proposed_assembly_connections"] == 40
    assert audit["geometrically_matched_3d_only"] == 4
    assert audit["unresolved_tab_support_anchors"] == 10
    assert audit["approved_manufacturing_panels"] == 0
    assert not audit["factory_accepted"]
    assert not progress["overall"]["factory_sample_pack_ready"]
    assert next(
        row for row in progress["phases"] if row["id"] == "P4"
    )["status"] == "not_started"
