"""Whole-scene role inventory must never pretend to be a sewn pattern."""

from copy import deepcopy

import pytest

from plush_pattern_lab.validation.component_inventory import (
    CORE_OBJECTS,
    SOURCE_SHA256,
    build_scene_inventory,
    name_hints,
)


def _sample_scene():
    meshes = [
        {
            "name": name,
            "type": "MESH",
            "vertices": 1500,
            "edges": 3000,
            "faces": 2000,
            "material_slots": 2,
            "bbox_extent_mm": [120.0, 80.0, 25.0],
        }
        for name in CORE_OBJECTS
    ]
    meshes.append(
        {
            "name": "Hanging grey tail overlay",
            "type": "MESH",
            "vertices": 12,
            "edges": 28,
            "faces": 10,
            "material_slots": 1,
            "bbox_extent_mm": [21.0, 11.0, 7.0],
        }
    )
    meshes.append(
        {
            "name": "unclassified shell 02",
            "type": "MESH",
            "vertices": 25,
            "edges": 31,
            "faces": 10,
            "material_slots": 0,
            "bbox_extent_mm": [8.0, 5.0, 9.0],
        }
    )
    meshes.append({"name": "render-hair-curves", "type": "CURVES"})
    return meshes


def test_full_model_inventory_separates_name_hints_from_real_patterns():
    result = build_scene_inventory(_sample_scene(), SOURCE_SHA256, "4.3.2")
    assert result["scene_objects_total"] == 8
    assert result["mesh_objects_total"] == 7
    assert result["nonmesh_objects_total"] == 1
    assert result["object_types"] == {"CURVES": 1, "MESH": 7}
    assert result["mesh_role_hint_counts_nonexclusive"]["leg_or_hoof"] == 4
    assert result["mesh_objects_without_role_hints"] == 1
    assert result["core_body_and_four_hoof_meshes_present"]
    assert len(result["all_mesh_object_inventory"]) == 7
    assert not result["all_sewable_panels_identified"]
    assert not result["all_role_assignment_reviewed_by_human"]
    assert not result["factory_handoff_ready"]
    assert all(
        part["production_part_status"] == "UNCLASSIFIED_NOT_A_SEWABLE_PATTERN"
        for part in result["all_mesh_object_inventory"]
    )


def test_role_hints_are_explicitly_unverified_and_nonexclusive():
    assert name_hints("PRIMARY continuous sculpt | new anatomy") == ["body_or_head"]
    assert name_hints("Rounded hoof base.002") == ["leg_or_hoof"]
    assert name_hints("Hanging grey tail overlay") == ["tail"]
    assert name_hints("cloud Hair fibers") == [
        "cloud_overlay",
        "fur_or_visual_proxy",
    ]
    assert name_hints("Part 007") == []


@pytest.mark.parametrize(
    "change",
    ["wrong_source", "missing_hoof", "duplicate", "negative_face",
     "invalid_extent", "nan_extent", "missing_extent"],
)
def test_wrong_source_or_unverifiable_geometry_rejected(change):
    rows = _sample_scene()
    source = SOURCE_SHA256
    if change == "wrong_source":
        source = "0" * 64
    elif change == "missing_hoof":
        rows = rows[:3] + rows[4:]
    elif change == "duplicate":
        rows[4] = deepcopy(rows[3])
    elif change == "negative_face":
        rows[0]["faces"] = -1
    elif change == "invalid_extent":
        rows[0]["bbox_extent_mm"] = [1, -2, 3]
    elif change == "nan_extent":
        rows[0]["bbox_extent_mm"] = [1, float("nan"), 3]
    else:
        rows[0]["bbox_extent_mm"] = None
    with pytest.raises(ValueError):
        build_scene_inventory(rows, source, "4.3.2")
