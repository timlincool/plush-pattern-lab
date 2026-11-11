"""Fail-closed section component association, raw-Mesh proximity, five views."""

from copy import deepcopy

import pytest

from plush_pattern_lab.validation.stage6_section_mesh_correspondence import (
    AUDIT_SCHEMA,
    classify_independent_mesh_neighbors,
    plan_original_contour_samples,
    summarize_loop_observations,
)


def _contour(n=6):
    return {
        "closed_loop": True,
        "simple_polygon": True,
        "contour_perimeter_mm": 10,
        "contour_centroid_xy_mm": [0.0, 0.0],
        "original_source_edge_and_interpolated_xy_sha256": "a" * 64,
        "true_interpolated_contour_xy_mm": [[float(i), 0.5] for i in range(n)],
        "crossed_original_mesh_vertex_id_edge_pairs": [[i, i + 1] for i in range(n)],
    }


def _source_detail():
    return {
        "schema": "stage6-true-triangle-plane-component-loops-v1",
        "source_geometry_type": "actual_source_triangle_edges_intersected_exactly",
        "factory_cutting_approved": 0,
        "sections": [
            {
                "plane_z_mm": z,
                "true_source_plane_intersection_component_count": n,
                "source_contours": [_contour() for _ in range(n)],
            }
            for z, n in [(125, 2), (230, 3), (245, 2)]
        ],
    }


def test_sample_plan_preserves_all_lateral_loops_and_original_source_edge_ids():
    plan = plan_original_contour_samples(_source_detail())
    assert [len(x["loops"]) for x in plan] == [2, 3, 2]
    assert [x["z_mm"] for x in plan] == [125, 230, 245]
    assert plan[1]["loops"][2]["sampled_source_edges"][0]["source_xyz_mm"] == [
        0.0,
        0.5,
        230,
    ]
    assert plan[1]["loops"][2]["total_original_crossed_source_edges"] == 6
    assert AUDIT_SCHEMA.endswith("5view-v1")


def test_long_loops_have_deterministic_spaced_unique_source_ids():
    detail = _source_detail()
    detail["sections"][1]["source_contours"][1] = _contour(103)
    plan = plan_original_contour_samples(detail)
    idx = [
        x["source_edge_ordinal"] for x in plan[1]["loops"][1]["sampled_source_edges"]
    ]
    assert len(idx) == len(set(idx)) == 48
    assert idx[0] == 0 and idx[-1] < 103
    assert idx[25] == 53


@pytest.mark.parametrize(
    "mutation",
    ["count", "removed", "duplicate_z", "fake_approved", "broken_edge", "open_loop"],
)
def test_tampered_original_source_or_wrong_component_count_fails_closed(mutation):
    detail = _source_detail()
    if mutation == "count":
        detail["sections"][1]["true_source_plane_intersection_component_count"] = 1
    elif mutation == "removed":
        detail["sections"].pop()
    elif mutation == "duplicate_z":
        detail["sections"].append(deepcopy(detail["sections"][0]))
    elif mutation == "fake_approved":
        detail["factory_cutting_approved"] = 1
    elif mutation == "broken_edge":
        detail["sections"][0]["source_contours"][0][
            "crossed_original_mesh_vertex_id_edge_pairs"
        ] = [[1, 1]] * 6
    else:
        detail["sections"][0]["source_contours"][0]["closed_loop"] = False
    with pytest.raises(ValueError):
        plan_original_contour_samples(detail)


def test_nearest_mesh_only_proximity_never_confers_anatomical_identity():
    neighbor = {"mesh": "Pink inset ear -1", "group": "ears", "distance_mm": 0.4}
    classified = classify_independent_mesh_neighbors([neighbor])
    assert (
        classified["proximity_classification"]
        == "one_independent_mesh_within_3mm_not_ownership"
    )
    assert classified["nearest_independent_raw_mesh"] == neighbor
    assert classified["physical_attachment_or_ear_identity_proven"] is False
    assert (
        classify_independent_mesh_neighbors([])["proximity_classification"]
        == "no_independent_mesh_within_3mm"
    )


def test_multiple_close_raw_meshes_remain_ambiguous():
    result = classify_independent_mesh_neighbors(
        [
            {"mesh": "Pink inset ear -1", "group": "ears", "distance_mm": 1},
            {
                "mesh": "Grey head cloud halo",
                "group": "decorative_cloud_layers",
                "distance_mm": 0.5,
            },
        ]
    )
    assert result["close_independent_mesh_count"] == 2
    assert "ambiguous" in result["proximity_classification"]
    assert result["nearest_independent_raw_mesh"]["group"] == "decorative_cloud_layers"


@pytest.mark.parametrize(
    "hits",
    [
        [{"mesh": "Studio floor", "group": "studio_floor_not_plush", "distance_mm": 0}],
        [
            {
                "mesh": "PRIMARY continuous sculpt | new anatomy",
                "group": "core_body_mesh",
                "distance_mm": 0,
            }
        ],
        [{"mesh": "Ear", "group": "ears", "distance_mm": float("nan")}],
        [{"mesh": "Ear", "group": "ears", "distance_mm": -1}],
        [{"mesh": "Ear", "group": "ears", "distance_mm": 7}],
        [
            {"mesh": "Ear", "group": "ears", "distance_mm": 1},
            {"mesh": "Ear", "group": "ears", "distance_mm": 2},
        ],
    ],
)
def test_invalid_mesh_hits_are_rejected(hits):
    with pytest.raises(ValueError):
        classify_independent_mesh_neighbors(hits)


def test_five_view_summary_refuses_dropped_original_edge_or_missing_view():
    loop = plan_original_contour_samples(_source_detail())[1]["loops"][0]
    evidence = []
    for sample in loop["sampled_source_edges"]:
        observed = dict(sample)
        observed.update(classify_independent_mesh_neighbors([]))
        observed["five_view_first_hit"] = {
            key: {"mesh": None, "classification": "no_authored_mesh_first_hit"}
            for key in ["front", "back", "left", "right", "top"]
        }
        evidence.append(observed)
    result = summarize_loop_observations(loop, evidence)
    assert result["observed_edge_sample_count"] == 6
    assert result["five_view_first_hit_summary"]["front"]["classification_counts"] == {
        "no_authored_mesh_first_hit": 6
    }
    assert not result["hidden_manufacturing_seam_confirmed"]
    with pytest.raises(ValueError):
        summarize_loop_observations(loop, evidence[:-1])
    changed = deepcopy(evidence)
    changed[0]["five_view_first_hit"].pop("front")
    with pytest.raises(ValueError):
        summarize_loop_observations(loop, changed)
