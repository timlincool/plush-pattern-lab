"""Fail-closed Stage6 cap-local original-X/Y meridian and 41-mesh evidence."""

from __future__ import annotations

import hashlib
from copy import deepcopy

import numpy as np
import pytest

from plush_pattern_lab.validation import stage6_protrusion_route_visibility as audit

XYZ = [[0.0, 0.0, 230.0], [1.0, 0.0, 235.0], [2.0, 0.0, 240.0], [3.0, 0.0, 230.0]]
ORIGINAL_SHA = "same-run-original-three-caps-hash"


def _case(name, nfaces, rim, route):
    faces = [[0, 1, 2]] * nfaces
    length = float(np.linalg.norm(np.diff(np.asarray(XYZ), axis=0), axis=1).sum())
    shared = {
        "source_original_cap_vertex_id_per_panel_vertex": [0, 1, 2, 3],
        "vertices_xyz_mm": deepcopy(XYZ),
        "seam_original_cap_vertex_ids_in_order": [0, 1, 2, 3],
        "seam_panel_vertex_ids_in_order": [0, 1, 2, 3],
        "topological_Euler": 1,
    }
    first = {
        **deepcopy(shared),
        "source_original_cap_face_ids": list(range(nfaces // 2)),
    }
    second = {
        **deepcopy(shared),
        "source_original_cap_face_ids": list(range(nfaces // 2, nfaces)),
    }
    return {
        "name": name,
        "route": route,
        "original_z230_rim_edge_count": rim,
        "original_z230_source_witness_sha256": "fixed-rim-" + name,
        "source_3d_meridian_length_mm": length,
        "original_cap_meridian_vertex_ids": [0, 1, 2, 3],
        "source_face_count": nfaces,
        "original_three_dimensional_source_seam_shared_twice": True,
        "panels": [first, second],
    }, {
        "id": name,
        "source_original_rim_edge_ids_sha256": "fixed-rim-" + name,
        "vertices_xyz_mm": deepcopy(XYZ),
        "triangles_local_vertex_indices": faces,
    }


def _fixture():
    variants = []
    originals = {}
    for route in audit.ROUTES:
        side_rows = []
        for name, nfaces, rim in zip(
            audit.CAPS, audit.EXPECTED_SOURCE_FACES, audit.EXPECTED_SOURCE_RIMS
        ):
            case, original = _case(name, nfaces, rim, route)
            originals[name] = original
            side_rows.append(case)
        variants.append(
            {
                "route": route,
                "side_protrusions": side_rows,
                "single_central_real_source_crown_retained": True,
            }
        )
    study = {
        "schema": audit.BISECT_SCHEMA,
        "source_original_three_caps_schema": audit.CAPS_SCHEMA,
        "original_stage6_blend_sha256": audit.BLEND_SHA,
        "original_source_25pct_proxy_sha256": audit.PROXY_SHA,
        "same_run_real_3d_original_three_caps_sha256": ORIGINAL_SHA,
        "routes": list(audit.ROUTES),
        "variants": variants,
        "source_3d_shared_new_side_seams_matched": True,
        "factory_cutting_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
    }
    original = {
        "schema": audit.CAPS_SCHEMA,
        "original_public_stage6_blend_sha256": audit.BLEND_SHA,
        "source_proxy_ply_sha256": audit.PROXY_SHA,
        "industrial_cutting_patterns_approved": 0,
        "upper_caps": [{"id": "central_crown"}, *originals.values()],
    }
    return study, original


def _observation(sample):
    return {
        **sample,
        "five_view_first_hit": {
            name: {"classification": "near_original_body_first_surface"}
            for name in audit.VIEW_NAMES
        },
        "independent_mesh_proximity": {
            "nearby_raw_meshes_within_6mm": [
                {
                    "mesh": "Grey head cloud halo",
                    "group": "decorative_cloud_layers",
                    "distance_mm": 1.25,
                }
            ]
        },
    }


def test_all_original_X_Y_meridians_are_sampled_without_invented_vertices():
    study, original = _fixture()
    plans = audit.plan_original_meridian_samples(study, original, ORIGINAL_SHA)
    assert [(row["route"], row["side"]) for row in plans] == [
        (route, side) for route in audit.ROUTES for side in audit.CAPS
    ]
    assert all(len(row["sampled_cap_local_source_vertices"]) == 4 for row in plans)
    expected = hashlib.sha256(
        np.asarray([0, 1, 2, 3], dtype="<i8").tobytes()
        + np.asarray(XYZ, dtype="<f8").tobytes()
    ).hexdigest()
    assert all(row["cap_local_source_path_sha256"] == expected for row in plans)
    for row in plans:
        observations = [
            _observation(s) for s in row["sampled_cap_local_source_vertices"]
        ]
        scored = audit.summarize_observations(row, observations)
        assert scored["sampled_original_cap_vertices_not_all_source_edges"] == 4
        assert scored["five_view_first_surface_classification_counts"]["top"] == {
            "near_original_body_first_surface": 4
        }
        assert scored["independent_mesh_groups_within_3mm_sample_hits"] == {
            "decorative_cloud_layers": 4
        }
        assert scored["no_approved_ear_cloud_seam_design_or_fabric_hiddenness"]
        assert scored["factory_cutting_patterns_approved"] == 0


@pytest.mark.parametrize(
    "fault",
    ("wrong_sha", "wrong_proxy", "fake_approved", "missing_route", "wrong_rim"),
)
def test_original_source_identity_tampering_cannot_pass(fault):
    study, original = _fixture()
    if fault == "wrong_sha":
        study["same_run_real_3d_original_three_caps_sha256"] = "forged"
    elif fault == "wrong_proxy":
        original["source_proxy_ply_sha256"] = "wrong"
    elif fault == "fake_approved":
        study["factory_cutting_patterns_approved"] = 1
    elif fault == "missing_route":
        study["variants"].pop()
    else:
        study["variants"][0]["side_protrusions"][0]["original_z230_rim_edge_count"] -= 1
    with pytest.raises(ValueError):
        audit.plan_original_meridian_samples(study, original, ORIGINAL_SHA)


@pytest.mark.parametrize(
    "fault", ("wrong_point", "lost_face", "changed_path", "wrong_copy")
)
def test_cannot_lose_original_source_seam_or_double_claim_one_triangle(fault):
    study, original = _fixture()
    part = study["variants"][0]["side_protrusions"][0]
    if fault == "wrong_point":
        part["panels"][0]["vertices_xyz_mm"][1][0] = -10
    elif fault == "lost_face":
        part["panels"][0]["source_original_cap_face_ids"].pop()
    elif fault == "changed_path":
        part["original_cap_meridian_vertex_ids"] = [3, 2, 1, 0]
    else:
        part["panels"][1]["source_original_cap_vertex_id_per_panel_vertex"][0] = 9
    with pytest.raises(ValueError):
        audit.plan_original_meridian_samples(study, original, ORIGINAL_SHA)


@pytest.mark.parametrize(
    "fault", ("removed", "wrong_vertex", "missing_view", "unknown_class")
)
def test_missing_or_relabelled_real_bvh_observations_fail_closed(fault):
    study, original = _fixture()
    plan = audit.plan_original_meridian_samples(study, original, ORIGINAL_SHA)[0]
    rows = [_observation(s) for s in plan["sampled_cap_local_source_vertices"]]
    if fault == "removed":
        rows.pop()
    elif fault == "wrong_vertex":
        rows[0]["cap_local_source_vertex_id"] = -1
    elif fault == "missing_view":
        rows[0]["five_view_first_hit"].pop("top")
    else:
        rows[0]["five_view_first_hit"]["front"]["classification"] = "certified_hidden"
    with pytest.raises(ValueError):
        audit.summarize_observations(plan, rows)
