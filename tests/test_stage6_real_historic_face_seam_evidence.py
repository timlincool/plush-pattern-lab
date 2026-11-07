"""Measured source B high facial seam must stay a design risk, never a stencil."""

import json
from pathlib import Path

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/stage6_face_seam_review_20261108/summary.json"
PROGRESS = ROOT / "docs/PRODUCTION_PROGRESS.json"


def test_real_source_face_risk_and_view_sha_are_frozen():
    report = json.loads(EVIDENCE.read_text(encoding="utf8"))
    assert report["source_original_blend_sha256"] == SOURCE_SHA256
    assert report["trusted_main_result"] == "success"
    assert report["post_refactor_python_tests_passed"] == 418
    assert report["source_25percent_proxy_ply_sha256"] == (
        "5b52e3fd09c83b19c5b9d95d6d8d859a147ff4deef90f1518f868d2e82e3a2dd"
    )
    paths = report["paths"]
    assert [p["source_vertex_count"] for p in paths] == [33, 143, 132]
    assert [p["body_front_first_hit_near_count"] for p in paths] == [32, 0, 126]
    assert [p["historic_eye_nose_mouth_proximity_alert_count"] for p in paths] == [
        0,
        0,
        8,
    ]
    assert report["critical_witness"]["source_vertex_id"] == 40436
    assert report["critical_witness"]["historic_xz_stroke_distance_mm"] < 0.6
    assert not report["critical_witness"]["full_scene_42_mesh_occlusion_audited"]
    assert report["manufacturer_paper_patterns_approved"] == 0


def test_full_character_visibility_and_factory_signoff_still_missing():
    data = json.loads(EVIDENCE.read_text(encoding="utf8"))
    assert not data["view_visualization"][
        "complete_cloud_eye_ear_tail_mesh_or_fur_visibility_test"
    ]
    progress = json.loads(PROGRESS.read_text(encoding="utf8"))
    p3 = next(x for x in progress["phases"] if x["id"] == "P3")
    p4 = next(x for x in progress["phases"] if x["id"] == "P4")
    assert p3["status"] == "in_progress"
    assert p4["status"] == "not_started"
    assert EVIDENCE.relative_to(ROOT).as_posix() in [
        item["path"] for item in p3["evidence"]
    ]
    assert not progress["overall"]["factory_sample_pack_ready"]
    assert not progress["overall"]["mass_production_ready"]
