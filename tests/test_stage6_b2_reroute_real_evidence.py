"""Preserve actual Stage6 C/D source facial reroute failures and P3/P4 gates."""

import json
from pathlib import Path

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/stage6_b2_reroute_20261108/summary.json"
PROGRESS = ROOT / "docs/PRODUCTION_PROGRESS.json"


def test_two_real_original_source_reroutes_avoid_old_nose_not_fabric_research():
    j = json.loads(EVIDENCE.read_text(encoding="utf8"))
    assert j["immutable_public_original_blend_sha256"] == SOURCE_SHA256
    assert j["trusted_main_workflow_conclusion"] == "success"
    assert j["python_tests_passed"] == 456
    assert j["immutable_source_region_faces"] == 36833
    assert j["source_original_B_radial_prefix_routes_unchanged"]
    c, d = j["new_research_candidates"]
    assert c["name"] == "C_low_neck_boundary"
    assert d["name"] == "D_lateral_high_boundary"
    assert [x["true_original_panel_faces"] for x in (c, d)] == [
        [22184, 5635, 9014],
        [25510, 2309, 9014],
    ]
    assert all(x["historic_v14_nose_mouth_alerts"] == 0 for x in (c, d))
    assert all(x["all_three_panels_topological_disk_euler_one"] for x in (c, d))
    assert all(x["all_3d_original_source_radial_edges_two_sided"] for x in (c, d))
    assert all(x["status"] == "REJECTED_FOR_FABRIC_CUTTING" for x in (c, d))
    assert j["approved_industrial_cutting_patterns"] == 0


def test_real_seam_stretch_and_visibility_still_reject_both_candidates():
    j = json.loads(EVIDENCE.read_text(encoding="utf8"))
    c, d = j["new_research_candidates"]
    assert (
        c["front_41product_mesh_first_hit_path2"][
            "near_original_main_body_source_surface"
        ]
        == 54
    )
    assert (
        d["front_41product_mesh_first_hit_path2"][
            "near_original_main_body_source_surface"
        ]
        == 0
    )
    assert c["radial_two_independent_UV_side_length_disagreement_mm"][1] > 217
    assert d["radial_two_independent_UV_side_length_disagreement_mm"][2] > 208
    assert c["full_original_LSCM_by_piece"][2]["uv_positive_area_overlap_pairs"] > 10000
    assert d["full_original_LSCM_by_piece"][0]["uv_positive_area_overlap_pairs"] > 23000
    assert d["true_original_panel_faces"][1] == 2309
    assert d["source_vertex_to_preserved_high1_nearest_3d_mm"] < 1.1
    assert j["P4_factory_pattern_phase"] == "not_started"


def test_real_failed_reroute_evidence_does_not_promote_factory_patterns():
    progress = json.loads(PROGRESS.read_text(encoding="utf8"))
    p3 = next(x for x in progress["phases"] if x["id"] == "P3")
    p4 = next(x for x in progress["phases"] if x["id"] == "P4")
    assert p3["status"] == "in_progress"
    assert p4["status"] == "not_started"
    assert EVIDENCE.relative_to(ROOT).as_posix() in [
        row["path"] for row in p3["evidence"]
    ]
    assert not progress["overall"]["factory_sample_pack_ready"]
    assert not progress["overall"]["mass_production_ready"]
