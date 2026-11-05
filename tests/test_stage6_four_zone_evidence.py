"""Pinned actual Stage6 full-shell candidate seam graph is not a cut pattern."""

import json
from pathlib import Path

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/stage6_whole_shell_partition_20261105/summary.json"


def test_entire_actual_shell_face_census_and_four_cuffs_are_grounded():
    proof = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert proof["schema"] == "stage6-real-four-zone-whole-main-shell-evidence-v1"
    assert proof["source"]["model_sha256"] == SOURCE_SHA256
    assert proof["source"]["trusted_run_url"].endswith("/41962253061")
    assert proof["source"]["source_proxy_triangles"] == 116568
    assert proof["shorter_measured_3d_seam_candidate_y_mm"] == 20
    assert len(proof["scenarios"]) == 2
    for scenario in proof["scenarios"]:
        assert sum(scenario["face_counts"]) == 116568
        assert scenario["all_four_regions_topology_valid"]
        assert scenario["fourway_junctions"] == 2
        assert scenario["cut_edges"] > 0
        assert not scenario["approved_factory_patterns"]
    assert proof["each_region_verified"]["source_original_open_boundary_edges"] if (
        "source_original_open_boundary_edges" in proof["each_region_verified"]
    ) else proof["each_region_verified"]["original_hoof_open_boundary_edges"] == 512
    assert proof["each_region_verified"]["euler_characteristic"] == 0


def test_shorter_seam_is_not_equivalent_to_making_a_sewable_paper_pattern():
    proof = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    a, b = proof["scenarios"]
    assert a["shared_3d_seam_length_mm"] < b["shared_3d_seam_length_mm"]
    assert a["cut_edges"] == 835
    assert b["cut_edges"] == 839
    assert len(a["interfaces"]) == len(b["interfaces"]) == 4
    assert not proof["net_sewing_lines_exported"]
    assert not proof["fabric_cut_patterns_approved"]
    assert not proof["manufacturing_ready"]
    assert proof["requirements_before_sewing"]


def test_factory_progress_keeps_real_topological_zones_as_pending_p3():
    state = json.loads(
        (ROOT / "docs/PRODUCTION_PROGRESS.json").read_text(encoding="utf-8")
    )
    p3 = next(p for p in state["phases"] if p["id"] == "P3")
    assert any(
        x["path"] == "experiments/stage6_whole_shell_partition_20261105/summary.json"
        for x in p3["evidence"]
    )
    m = state["verified_baseline"]["stage6_whole_shell_four_region"]
    assert m["real_main_shell_faces_partitioned"] == 116568
    assert m["each_region_exact_original_512_vertex_hoof_ring"]
    assert m["total_shared_3d_seam_edges"] == 835
    assert m["topological_four_way_seam_junctions"] == 2
    assert m["net_sewing_patterns_approved"] == 0
    assert not m["two_dimensional_rest_shapes_generated"]
