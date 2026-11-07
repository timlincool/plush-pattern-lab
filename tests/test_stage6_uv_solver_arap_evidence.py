"""Pin verified Stage6 B-three-panel ARAP/LSCM failure and P3 status."""

import json
from pathlib import Path

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/stage6_uv_solver_arap_20261108/summary.json"
PROGRESS = ROOT / "docs/PRODUCTION_PROGRESS.json"


def test_actual_arap_solver_source_and_experiment_are_pinned_not_manufacturing():
    item = json.loads(EVIDENCE.read_text(encoding="utf8"))
    assert item["source_original_blend_sha256"] == SOURCE_SHA256
    assert item["trusted_main_run_conclusion"] == "success"
    assert item["python_ci_tests_passed"] == 400
    assert item["source_triangles_total"] == 36833
    assert item["source_panel_faces"] == [20915, 6904, 9014]
    assert item["uv_methods"] == ["LSCM", "ARAP_PCA", "ARAP_LSCM"]
    p2 = item["panels"][1]
    assert p2["lscm"]["uv_overlap_pairs"] == 0
    assert p2["arap_pca"]["uv_overlap_pairs"] == 4057
    assert p2["arap_lscm"]["uv_overlap_pairs"] == 5610
    assert all(panel["no_accepted_solution"] for panel in item["panels"])
    assert item["interpretation"]["all_real_2d_candidates_rejected"]
    assert item["interpretation"]["industrial_paper_patterns_approved"] == 0


def test_sewing_seam_gap_and_progress_must_not_prematurely_promote_p4():
    item = json.loads(EVIDENCE.read_text(encoding="utf8"))
    gaps = item["per_method_two_sided_uv_length_disagreement_mm"]
    assert gaps["ARAP_PCA"][1] > 40
    assert gaps["ARAP_LSCM"][1] > 70
    progress = json.loads(PROGRESS.read_text(encoding="utf8"))
    p3 = next(row for row in progress["phases"] if row["id"] == "P3")
    p4 = next(row for row in progress["phases"] if row["id"] == "P4")
    assert p3["status"] == "in_progress"
    assert p4["status"] == "not_started"
    assert any(
        row["path"] == EVIDENCE.relative_to(ROOT).as_posix() for row in p3["evidence"]
    )
    assert not progress["overall"]["factory_sample_pack_ready"]
    assert not progress["overall"]["mass_production_ready"]
