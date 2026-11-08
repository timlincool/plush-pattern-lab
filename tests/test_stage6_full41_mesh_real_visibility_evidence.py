"""Pin the two trusted full product-Mesh front-hit runs as design warnings."""

import json
from pathlib import Path

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    ROOT / "experiments/stage6_full_product_mesh_visibility_20261108/summary.json"
)
PROGRESS = ROOT / "docs/PRODUCTION_PROGRESS.json"


def test_real_full_product_mesh_source_and_five_view_sha():
    row = json.loads(EVIDENCE.read_text(encoding="utf8"))
    assert row["source_blend_sha256"] == SOURCE_SHA256
    assert row["source_product_meshes_raycasted"] == 41
    assert row["authored_mesh_objects_total"] == 42
    assert row["excluded_studio_floor_mesh"] == 1
    assert row["source_curve_or_hair_objects_not_raycasted"] == 423
    assert row["view_names"] == ["front", "back", "left", "right", "top"]
    repeat = row["after_format_trusted_blender_reproduction"]
    assert repeat["conclusion"] == "success"
    assert repeat["five_view_svg_byte_identical_to_first_run"]
    assert repeat[
        "full_json_view_results_structurally_and_numerically_identical_to_first_run"
    ]
    assert repeat["source_geometry_and_historic_v14_alerts_unchanged"]


def test_all_eight_historic_nose_alerts_first_hit_main_shell_not_cloud():
    row = json.loads(EVIDENCE.read_text(encoding="utf8"))
    face = row["front"]["path2"]
    assert face["original_source_vertices"] == 132
    assert face["near_original_main_body_first_surface"] == 71
    assert face["occluded_by_another_product_Mesh"] == 55
    assert face["original_main_body_self_occluded"] == 5
    assert face["near_coincident_with_other_product_Mesh_unresolved"] == 1
    assert face["historic_nose_mouth_v14_alerts"] == 8
    assert face["all_eight_historic_alert_source_points_first_hit_original_main_body"]
    assert face[
        "all_eight_historic_alert_source_points_without_separate_product_Mesh_occlusion"
    ]
    ids = [v["id"] for v in face["historic_face_warning_vertex_witnesses"]]
    assert len(ids) == len(set(ids)) == 8
    assert 40436 in ids
    assert max(
        abs(v["depth_mm"]) for v in face["historic_face_warning_vertex_witnesses"]
    ) < 0.011


def test_geometry_evidence_does_not_promote_manufacturing_gates():
    evidence = json.loads(EVIDENCE.read_text(encoding="utf8"))
    assert evidence["factory_paper_patterns_approved"] == 0
    assert evidence["design_approved_in_full_scene"] is False
    assert evidence["P4_industrial_cut_patterns_status"] == "not_started"
    progress = json.loads(PROGRESS.read_text(encoding="utf8"))
    p3 = next(p for p in progress["phases"] if p["id"] == "P3")
    p4 = next(p for p in progress["phases"] if p["id"] == "P4")
    assert p3["status"] == "in_progress"
    assert p4["status"] == "not_started"
    assert EVIDENCE.relative_to(ROOT).as_posix() in [
        item["path"] for item in p3["evidence"]
    ]
    assert not progress["overall"]["factory_sample_pack_ready"]
    assert not progress["overall"]["mass_production_ready"]
