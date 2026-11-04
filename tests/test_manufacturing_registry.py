"""Fail closed on Stage6 42-mesh engineering registration and fake BOM claims."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from plush_pattern_lab.validation.manufacturing_registry import (
    BODY,
    FLOOR,
    build_draft_register,
)
from scripts.build_stage6_component_register import generate

ROOT = Path(__file__).resolve().parents[1]
SCENE = ROOT / "experiments/stage6_scene_inventory_20261103/summary.json"
SEAMS = ROOT / "experiments/stage6_hoof_seams_20261030/summary.json"
REGISTER = ROOT / "design/manufacturing/STAGE6_COMPONENT_REGISTRY_DRAFT.json"


def _inputs():
    return (
        json.loads(SCENE.read_text(encoding="utf-8")),
        json.loads(SEAMS.read_text(encoding="utf-8")),
    )


def test_all_42_actual_meshes_are_accounted_for_without_fake_cut_pieces():
    scene, seams = _inputs()
    report = build_draft_register(scene, seams)
    assert report["model_mesh_count"] == 42
    assert len(report["component_rows"]) == 42
    assert len({p["source_mesh"] for p in report["component_rows"]}) == 42
    assert report["approved_cut_patterns"] == 0
    assert not report["manufacturing_handoff_ready"]
    assert not report["human_approved_component_classification"]
    assert not report["materials_confirmed"]
    assert all(part["pieces_to_cut"] is None for part in report["component_rows"])
    assert all(part["cut_pattern_id"] is None for part in report["component_rows"])
    assert all(part["approved_material_sku"] is None for part in report["component_rows"])
    assert next(
        part for part in report["component_rows"] if part["source_mesh"] == FLOOR
    )["non_product_scene_asset"]
    assert next(
        part for part in report["component_rows"] if part["source_mesh"] == BODY
    )["source_faces"] == 466278


def test_exactly_four_real_geometry_boundaries_and_ten_unknown_tab_anchors():
    scene, seams = _inputs()
    data = build_draft_register(scene, seams)
    joins = data["assembly_intents"]
    assert len(joins) == 40
    assert len({item["child_mesh"] for item in joins}) == 40
    assert data["joins_with_measured_3d_boundary_only"] == 4
    assert data["unresolved_attachment_target_count"] == 10
    assert all(not item["production_seam_approved"] for item in joins)
    assert all(not item["fabric_assembly_verified"] for item in joins)
    targets = {item["source_mesh"] for item in data["component_rows"]}
    assert all(
        j["target_mesh"] is None or j["target_mesh"] in targets for j in joins
    )
    hooves = {
        item["child_mesh"]: item["body_open_ring_index"]
        for item in joins
        if item["relation"] == "verified_3d_boundary_only"
    }
    assert hooves == {
        "Rounded hoof base": 1,
        "Rounded hoof base.001": 2,
        "Rounded hoof base.002": 0,
        "Rounded hoof base.003": 3,
    }
    assert all(
        j["child_mesh"].startswith("Connected short flat fabric tab ")
        for j in joins
        if j["anchor_missing"]
    )


def test_stored_version_is_generated_not_an_invented_manufacturing_bom():
    expected = json.loads(REGISTER.read_text(encoding="utf-8"))
    scene, seams = _inputs()
    assert build_draft_register(scene, seams) == expected
    assert generate(SCENE, SEAMS) == expected


@pytest.mark.parametrize(
    "case",
    (
        "scene_hash",
        "hooves_hash",
        "missing_mesh",
        "duplicate",
        "changed_role",
        "fake_sewn_part",
        "bad_hoof_match",
        "missing_hoof",
    ),
)
def test_source_drift_and_manufacturing_overclaims_must_be_rejected(case):
    scene, seams = _inputs()
    scene, seams = deepcopy(scene), deepcopy(seams)
    if case == "scene_hash":
        scene["source"]["source_sha256"] = "0" * 64
    elif case == "hooves_hash":
        seams["source"]["sha256"] = "0" * 64
    elif case == "missing_mesh":
        scene["geometry_entries"].pop()
    elif case == "duplicate":
        scene["geometry_entries"][1] = deepcopy(scene["geometry_entries"][0])
    elif case == "changed_role":
        scene["geometry_entries"][0]["provisional_group"] = "fabric_drops"
    elif case == "fake_sewn_part":
        scene["geometry_entries"][0]["production_pattern_confirmed"] = True
    elif case == "bad_hoof_match":
        seams["hoofs"][0]["matched_3d_max_gap_mm"] = 5.0
    else:
        seams["hoofs"].pop()
    with pytest.raises(ValueError):
        build_draft_register(scene, seams)
