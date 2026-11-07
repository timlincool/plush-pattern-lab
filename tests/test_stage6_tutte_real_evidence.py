"""Lock true source-pinned Tutte data as a geometric rejection, not a stencil."""

import json
from pathlib import Path

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/stage6_tutte_convex_20261108/summary.json"
PROGRESS = ROOT / "docs/PRODUCTION_PROGRESS.json"


def test_real_tutte_control_has_nonoverlap_but_unacceptable_interior_strain():
    report = json.loads(EVIDENCE.read_text(encoding="utf8"))
    assert report["original_public_blend_sha256"] == SOURCE_SHA256
    assert report["trusted_run_result"] == "success"
    assert report["identical_raw_summary_and_detail_sha256_across_runs"]
    assert report["python_tests_passed"] == 410
    assert report["total_source_faces"] == 36833
    assert report["source_panel_faces"] == [20915, 6904, 9014]
    assert all(row["uv_positive_area_overlap_pairs"] == 0 for row in report["panels"])
    assert all(row["uv_flipped_faces"] == 0 for row in report["panels"])
    assert all(row["edge_length_relative_error_p95"] > 2 for row in report["panels"])
    assert all(not row["approved"] for row in report["panels"])
    assert report["approved_industrial_cut_patterns"] == 0


def test_source_tutte_seam_match_is_not_independent_fabric_evidence():
    data = json.loads(EVIDENCE.read_text(encoding="utf8"))
    assert all(
        s["two_sides_difference_mm"] < 0.002
        for s in data["paired_original_source_radial_seams"]
    )
    assert data["source_sewing_seams_reconstructed_but_not_independent_fabric_proof"]
    p = json.loads(PROGRESS.read_text(encoding="utf8"))
    p3 = next(row for row in p["phases"] if row["id"] == "P3")
    p4 = next(row for row in p["phases"] if row["id"] == "P4")
    assert p3["status"] == "in_progress"
    assert p4["status"] == "not_started"
    assert EVIDENCE.relative_to(ROOT).as_posix() in [
        row["path"] for row in p3["evidence"]
    ]
    assert not p["overall"]["factory_sample_pack_ready"]
