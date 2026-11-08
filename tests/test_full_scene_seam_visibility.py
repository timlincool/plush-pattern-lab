"""Synthetic full-scene BVH classification controls and real registry pin."""

import json
from pathlib import Path

import pytest

from plush_pattern_lab.validation.full_scene_seam_visibility import (
    SOURCE_MESH,
    STUDIO_FLOOR,
    VIEWS,
    classify_first_surface,
    count_scene_view,
    verified_scene_registry,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "design/manufacturing/STAGE6_COMPONENT_REGISTRY_DRAFT.json"


def _fixture():
    registry = json.loads(REGISTRY.read_text(encoding="utf8"))
    counts = {row["source_mesh"]: row["source_faces"] for row in registry["component_rows"]}
    return registry, counts


def test_original_42_mesh_roles_exclude_studio_floor_but_keep_clouds():
    registry, counts = _fixture()
    groups = verified_scene_registry(registry, counts)
    assert len(counts) == 42
    assert len(groups) == 41
    assert STUDIO_FLOOR not in groups
    assert groups[SOURCE_MESH] == "core_body_mesh"
    assert sum(role == "decorative_cloud_layers" for role in groups.values()) == 7
    assert sum(role == "facial_markers" for role in groups.values()) == 4
    assert len(VIEWS) == 5
    assert [row[0] for row in VIEWS] == ["front", "back", "left", "right", "top"]


@pytest.mark.parametrize(
    "corruption",
    ["missing", "wrong_faces", "studio_floor", "duplicate", "bad_role"],
)
def test_tampered_mesh_names_polygon_counts_or_roles_fail_closed(corruption):
    registry, counts = _fixture()
    if corruption == "missing":
        counts.pop("Grey head cloud halo")
    elif corruption == "wrong_faces":
        counts[SOURCE_MESH] -= 1
    elif corruption == "studio_floor":
        registry["component_rows"][-1]["scene_group"] = "tail_overlay"
    elif corruption == "duplicate":
        registry["component_rows"][2]["source_mesh"] = SOURCE_MESH
    else:
        registry["component_rows"][3]["scene_group"] = "unsafe_unknown"
    with pytest.raises(ValueError):
        verified_scene_registry(registry, counts)


@pytest.mark.parametrize(
    ("axis", "sign", "hit", "role", "label"),
    [
        (1, 1, [0, -2, 0], "decorative_cloud_layers", "occluded_by_another_product_mesh"),
        (1, 1, [0, -2, 0], "core_body_mesh", "self_occluded_by_original_body"),
        (1, 1, [0, 0.1, 0], "core_body_mesh", "near_original_body_first_surface"),
        (
            1,
            1,
            [0, 0.1, 0],
            "facial_markers",
            "coincident_with_another_product_mesh_unresolved",
        ),
        (
            1,
            1,
            [0, 2, 0],
            "core_body_mesh",
            "proxy_source_ahead_of_full_mesh_surface_unresolved",
        ),
        (1, -1, [0, 2, 0], "ears", "occluded_by_another_product_mesh"),
        (2, -1, [0, 0, 2], "tail_overlay", "occluded_by_another_product_mesh"),
    ],
)
def test_signed_orthographic_first_hit_classification(
    axis, sign, hit, role, label
):
    row = classify_first_surface([0, 0, 0], hit, role, axis, sign, 0.7)
    assert row["classification"] == label


def test_missing_hit_kept_unresolved_and_not_approved_as_visible():
    row = classify_first_surface([0, 0, 0], None, None, 1, 1, 0.7)
    assert row["classification"] == "no_authored_mesh_first_hit"
    assert row["depth_mm"] is None


@pytest.mark.parametrize(
    "mutator",
    ["nan", "bad_axis", "bad_direction", "unbounded", "studio_floor_hit"],
)
def test_invalid_source_or_view_geometry_is_rejected(mutator):
    point = [0, 0, 0]
    args = [[0, -2, 0], "facial_markers", 1, 1, 0.7]
    if mutator == "nan":
        point[0] = float("nan")
    elif mutator == "bad_axis":
        args[2] = 3
    elif mutator == "bad_direction":
        args[3] = 2
    elif mutator == "unbounded":
        args[4] = 10
    else:
        args[1] = "studio_floor_not_plush"
    with pytest.raises(ValueError):
        classify_first_surface(point, *args)


def test_unresolved_human_design_state_not_counted_as_mesh_occlusion():
    rows = [
        {"classification": "near_original_body_first_surface"},
        {"classification": "occluded_by_another_product_mesh"},
        {"classification": "proxy_source_ahead_of_full_mesh_surface_unresolved"},
        {"classification": "no_authored_mesh_first_hit"},
    ]
    counts = count_scene_view(rows)
    assert counts["sample_count"] == 4
    assert counts["other_mesh_occluded_count"] == 1
    assert counts["near_body_surface_count"] == 1
    assert counts["unresolved_or_no_hit_count"] == 2
