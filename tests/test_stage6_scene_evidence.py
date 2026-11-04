"""Pin the public Stage6 whole-character component survey to real evidence."""

import json
from pathlib import Path

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256
from plush_pattern_lab.validation.public_release_proof import MODEL_SHA256

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "experiments/stage6_scene_inventory_20261103/summary.json"


def test_real_model_full_inventory_is_verified_and_not_cut_patterns():
    data = json.loads(REPORT.read_text(encoding="utf-8"))
    assert SOURCE_SHA256 == MODEL_SHA256 == data["source"]["source_sha256"]
    assert data["source"]["trusted_run_url"].endswith("/41767796150")
    assert data["scene_objects_total"] == 469
    assert data["mesh_objects_total"] == 42
    assert data["visual_curve_objects"] == 423
    assert data["mesh_face_total_including_studio_floor"] == 620873
    assert data["object_types"] == {
        "CAMERA": 1,
        "CURVE": 388,
        "CURVES": 35,
        "LIGHT": 3,
        "MESH": 42,
    }
    assert len(data["geometry_entries"]) == 42
    assert not data["factory_sample_pack_ready"]
    assert data["manufacturing_panels_approved"] == 0


def test_scene_meshes_are_names_and_measures_not_production_fabric_parts():
    data = json.loads(REPORT.read_text(encoding="utf-8"))
    records = data["geometry_entries"]
    assert len({item["name"] for item in records}) == 42
    assert sum(item["faces"] for item in records) == 620873
    assert sum(data["provisional_group_counts"].values()) == 42
    assert all(
        not item["production_pattern_confirmed"]
        and not item["role_proven_only_by_name"]
        for item in records
    )
    body = next(
        item
        for item in records
        if item["name"] == "PRIMARY continuous sculpt | new anatomy"
    )
    assert body["faces"] == 466278
    assert body["bbox_extent_mm"] == [132.348, 226.906, 228.676]
    floor = next(item for item in records if item["name"] == "Studio floor")
    assert floor["provisional_group"] == "studio_floor_not_plush"
    assert floor["bbox_extent_mm"] == [200000, 200000, 0]


def test_factory_progress_records_inventory_without_approving_paper_patterns():
    doc = ROOT / "docs/PRODUCTION_PROGRESS.json"
    state = json.loads(doc.read_text(encoding="utf-8"))
    p2 = next(item for item in state["phases"] if item["id"] == "P2")
    assert p2["status"] == "in_progress"
    assert any(
        note["path"] == "experiments/stage6_scene_inventory_20261103/summary.json"
        for note in p2["evidence"]
    )
    assert (
        state["verified_baseline"]["stage6_whole_scene_inventory"][
            "manufacturing_panels_approved"
        ]
        == 0
    )
    assert not state["overall"]["factory_sample_pack_ready"]
