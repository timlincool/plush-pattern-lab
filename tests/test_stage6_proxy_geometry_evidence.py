"""Independent Stage6 PLY/BVH/five-view measurements stay traceable and bounded."""

import json
from pathlib import Path

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "experiments/stage6_proxy_geometry_20261105/summary.json"


def test_real_blender_proxy_geometry_evidence_is_pinned_to_public_source():
    data = json.loads(PROOF.read_text(encoding="utf-8"))
    assert data["schema"] == "stage6-real-proxy-geometry-screen-evidence-v1"
    assert data["source"]["source_asset_sha256"] == SOURCE_SHA256
    assert data["source"]["trusted_run"].endswith("/41959067621")
    assert data["reference"]["face_winding_conflicts"] == 0
    assert data["reference"]["nonadjacent_bvh_triangle_intersection_pairs"] == 0
    assert not data["reference"]["outward_normals_proven"]
    assert [row["ratio"] for row in data["models"]] == [0.5, 0.25]
    assert [row["faces"] for row in data["models"]] == [233138, 116568]
    assert not data["approved_cut_patterns"]
    assert not data["manufacturing_ready"]


def test_view_metrics_preserve_real_depth_outliers_not_just_high_iou():
    data = json.loads(PROOF.read_text(encoding="utf-8"))
    assert data["method"]["views"] == [
        "front",
        "back",
        "left",
        "right",
        "top",
    ]
    for model in data["models"]:
        assert model["winding_conflicts"] == 0
        assert model["nonadjacent_bvh_intersections"] == 0
        for view in model["views"].values():
            assert 0 < view["silhouette_iou"] <= 1
            assert view["silhouette_mismatch_rays"] >= 0
            assert 0 <= view["first_hit_depth_p95_mm"]
            assert view["first_hit_depth_max_mm"] >= view["first_hit_depth_p95_mm"]
    quarter = data["models"][1]
    assert quarter["views"]["front"]["silhouette_iou"] == 1.0
    assert quarter["views"]["left"]["silhouette_iou"] < 1.0
    assert quarter["views"]["top"]["first_hit_depth_max_mm"] > 1.4


def test_factory_progress_keeps_proxy_screen_as_early_p3_evidence():
    state = json.loads(
        (ROOT / "docs/PRODUCTION_PROGRESS.json").read_text(encoding="utf8")
    )
    p3 = next(item for item in state["phases"] if item["id"] == "P3")
    assert any(
        evidence["path"] == "experiments/stage6_proxy_geometry_20261105/summary.json"
        for evidence in p3["evidence"]
    )
    metric = state["verified_baseline"]["stage6_proxy_independent_screen"]
    assert metric["winding_conflicts"] == [0, 0]
    assert metric["nonadjacent_bvh_intersection_pairs"] == [0, 0]
    assert metric["twenty_five_percent_top_max_first_hit_depth_mm"] > 1.4
    assert metric["cut_patterns_approved"] == 0
