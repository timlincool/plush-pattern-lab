"""Pin actual public Stage6 50/25pct proxy evidence and research-only gates."""

import json
from pathlib import Path

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/stage6_core_proxy_20261105/summary.json"
PROGRESS = ROOT / "docs/PRODUCTION_PROGRESS.json"


def test_two_real_lowpoly_candidates_have_strict_four_hoof_boundary_proof():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["schema"] == "stage6-real-core-shell-proxy-ab-evidence-v1"
    assert data["source"]["source_sha256"] == SOURCE_SHA256
    assert data["source"]["workflow_run"].endswith("/41953627248")
    assert data["experiment"]["original_source_counts_unchanged"]
    assert data["experiment"]["protected_vertices"] == 4096
    assert data["experiment"]["eligible_interior_vertices"] == 230065
    assert [row["ratio"] for row in data["trials"]] == [0.5, 0.25]
    assert [row["real_faces"] for row in data["trials"]] == [233138, 116568]
    assert all(
        row["topology"]["old_to_new_vertex_id_pairs"] == 2048
        and row["topology"]["all_4x512_directed_hoop_rings_unchanged"]
        and row["topology"]["connected_components"] == 1
        and row["topology"]["euler"] == -2
        and row["topology"]["nonmanifold_edges"] == 0
        and not row["approved_for_fabric_cutting"]
        for row in data["trials"]
    )


def test_research_ply_content_and_sampled_error_are_not_factory_guarantees():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert not data["full_character_pattern_exists"]
    assert not data["factory_materials_and_golden_sample_approved"]
    for row in data["trials"]:
        file = row["research_ply"]
        assert file["unit"] == "mm"
        assert file["file"].endswith(".ply")
        assert file["bytes"] > 10000
        assert len(file["sha256"]) == 64
        assert file["binary_ply_independently_parsed"]
        assert row["source_to_proxy_mm"]["p95"] <= row["source_to_proxy_mm"]["max"]
        assert row["proxy_to_source_mm"]["p95"] <= row["proxy_to_source_mm"]["max"]
        assert row["source_to_proxy_mm"]["sample_count"] > 1000
    assert any("Hausdorff" in warning for warning in data["warnings"])
    assert any("Self-intersection" in warning for warning in data["warnings"])


def test_progress_uses_measured_proxy_to_prioritize_real_whole_shell_panels():
    progress = json.loads(PROGRESS.read_text(encoding="utf-8"))
    gate = next(p for p in progress["phases"] if p["id"] == "P3")
    assert gate["status"] in {"in_progress", "accepted"}
    assert any(
        item["path"] == "experiments/stage6_core_proxy_20261105/summary.json"
        for item in gate["evidence"]
    )
    version = progress["verified_baseline"]["stage6_core_shell_proxy"]
    assert version["actual_research_proxy_candidates"] == 2
    assert version["candidate_faces"] == [233138, 116568]
    assert version["all_four_original_seams_per_proxy_max_gap_mm"] == 0
    assert version["full_character_panels_approved"] == 0
    assert not version["sample_or_factory_approved"]
