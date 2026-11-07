"""Trusted Stage6 2/3-panel evidence remains rejected until physical design QA."""

import json
from pathlib import Path

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/stage6_multi_radial_20261107/summary.json"
PROGRESS = ROOT / "docs/PRODUCTION_PROGRESS.json"


def test_real_multidisk_3d_pairing_does_not_imply_valid_uv():
    evidence = json.loads(EVIDENCE.read_text(encoding="utf8"))
    assert evidence["source_original_stage6_blend_sha256"] == SOURCE_SHA256
    assert evidence["trusted_main_run_result"] == "success"
    assert evidence["source_faces"] == 36833
    assert evidence["original_hoof_source_edges"] == 512
    assert evidence["geometry_only_topology_gates"][
        "all_source_faces_assigned_exactly_once"
    ]
    a, b = evidence["candidates"]
    assert a["individual_source_faces"] == [25680, 11153]
    assert b["individual_source_faces"] == [20915, 6904, 9014]
    assert [x["uv_overlapping_nonzero_area_pairs"] for x in b["panels"]] == [
        26,
        0,
        10536,
    ]
    assert b["panels"][1]["uv_edge_error_relative_p95"] > 0.4
    assert b["two_side_lscm_net_seam_candidate_disagreements_mm"][1][
        "difference_mm"
    ] > 200
    assert all(not x["approved"] for x in (a, b))
    assert evidence["approved_factory_paper_patterns"] == 0


def test_project_keeps_real_radial_uv_rejections_out_of_p4():
    progress = json.loads(PROGRESS.read_text(encoding="utf8"))
    p3 = next(p for p in progress["phases"] if p["id"] == "P3")
    p4 = next(p for p in progress["phases"] if p["id"] == "P4")
    assert p3["status"] == "in_progress"
    assert p4["status"] == "not_started"
    assert not progress["overall"]["factory_sample_pack_ready"]
    assert not progress["overall"]["mass_production_ready"]
    evidence_path = EVIDENCE.relative_to(ROOT).as_posix()
    assert evidence_path in [row["path"] for row in p3["evidence"]]
    real = progress["verified_baseline"]["stage6_multi_radial_disk_real_2d"]
    assert not real["approved_for_manufacture"]
