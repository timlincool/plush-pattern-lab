"""Fail-closed true-source 7-port/4-zone structure and 1:1 image contract."""

from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

from plush_pattern_lab.patterns.stage6_lower_seven_port_svg import (
    render_seven_real_rims_a4,
)
from plush_pattern_lab.validation.stage6_lower_seven_port_graph import (
    CAP_IDS,
    CAPS_SCHEMA,
    EXPECTED_PORTS,
    PROXY_SHA,
    RIM_COUNTS,
    SCHEMA,
    SOURCE_SHA,
    _cap_source_port,
    _check_locked_source,
)


def _toy_cap():
    angle = 2 * np.pi * np.arange(6) / 6
    xyz = np.column_stack((10 * np.cos(angle), 10 * np.sin(angle), [230.0] * 6))
    length = float(np.linalg.norm(xyz - np.roll(xyz, -1, axis=0), axis=1).sum())
    cap = {
        "id": "central_crown",
        "vertices_xyz_mm": xyz.tolist(),
        "original_rim_vertex_ids_in_cap_local_order": list(range(6)),
        "source_3d_rim_perimeter_mm": length,
    }
    border = {tuple(sorted((i, (i + 1) % 6))): 0 if i < 3 else 2 for i in range(6)}
    return xyz, cap, border


def _locked_meta():
    caps = {
        "schema": CAPS_SCHEMA,
        "original_public_stage6_blend_sha256": SOURCE_SHA,
        "source_proxy_ply_sha256": PROXY_SHA,
        "industrial_cutting_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
        "upper_to_lower_source_netline_matched_at_1e_6_mm": True,
        "lower_single_original_surface": {
            "source_Euler_characteristic": -5,
            "original_four_hoof_rings_exactly_512_edges_each": True,
        },
        "upper_caps": [
            {"id": name, "source_boundary_edges": count}
            for name, count in zip(CAP_IDS, RIM_COUNTS)
        ],
    }
    full = {
        "schema": "stage6-source-pinned-whole-shell-seam-plan-v1",
        "source_original_model_sha256": SOURCE_SHA,
        "proxy_ply_sha256": PROXY_SHA,
        "shorter_3d_seam_graph_study_y_mm": 20.0,
        "scenarios": [
            {"split_y_mm": z, "source_triangles": 116568} for z in (20.0, 25.0)
        ],
    }
    return caps, full


def test_original_3d_upper_crown_rim_spans_two_lower_zones_exactly():
    xyz, cap, owners = _toy_cap()
    score = _cap_source_port(xyz, cap, owners)
    assert score["source_cap"] == "central_crown"
    assert score["lower_zone_edges"] == {"left_front": 3, "right_front": 3}
    assert score["cross_zone_transition_count"] == 2
    assert len(score["transition_original_3D_xyz_mm"]) == 2
    assert sum(score["lower_zone_arcs_mm"].values()) == pytest.approx(
        cap["source_3d_rim_perimeter_mm"]
    )
    assert score["original_3D_join_not_paired_2D_fabric_netline"]
    assert EXPECTED_PORTS[0] == {"left_front": 95, "right_front": 94}


@pytest.mark.parametrize("fault", ("vertex", "missing_edge", "duplicated", "length"))
def test_original_crown_rim_corruption_cannot_claim_source_3d_seam(fault):
    xyz, cap, owners = _toy_cap()
    if fault == "vertex":
        cap["vertices_xyz_mm"][0][0] += 0.1
    elif fault == "missing_edge":
        del owners[(0, 1)]
    elif fault == "duplicated":
        cap["original_rim_vertex_ids_in_cap_local_order"][1] = 0
    else:
        cap["source_3d_rim_perimeter_mm"] += 1
    with pytest.raises(ValueError):
        _cap_source_port(xyz, cap, owners)


@pytest.mark.parametrize(
    "fault",
    (
        "wrong_blend",
        "wrong_proxy",
        "fake_approved",
        "missing_head",
        "changed_rim",
        "changed_source_four_zone",
        "changed_split",
        "missing_hoof",
    ),
)
def test_refuse_forged_seven_opening_source_or_older_surrogate(fault):
    caps, full = _locked_meta()
    if fault == "wrong_blend":
        caps["original_public_stage6_blend_sha256"] = "forged"
    elif fault == "wrong_proxy":
        full["proxy_ply_sha256"] = "wrong"
    elif fault == "fake_approved":
        caps["industrial_cutting_patterns_approved"] = 1
    elif fault == "missing_head":
        caps["upper_caps"].pop()
    elif fault == "changed_rim":
        caps["upper_caps"][1]["source_boundary_edges"] -= 1
    elif fault == "changed_source_four_zone":
        full["scenarios"][1]["source_triangles"] = 4
    elif fault == "changed_split":
        full["scenarios"][0]["split_y_mm"] = 19
    else:
        caps["lower_single_original_surface"][
            "original_four_hoof_rings_exactly_512_edges_each"
        ] = False
    with pytest.raises(ValueError):
        _check_locked_source([None] * 59306, [None] * 116568, caps, full)


def test_old_source_2d_or_factory_approval_cannot_be_drawn_as_verified():
    caps, _ = _locked_meta()
    bad = {"schema": SCHEMA, "factory_cutting_patterns_approved": 1}
    with pytest.raises(ValueError):
        render_seven_real_rims_a4([], [], caps, bad, 20.0, None)
    forged = deepcopy(bad)
    forged["factory_cutting_patterns_approved"] = 0
    with pytest.raises(ValueError):
        render_seven_real_rims_a4([], [], caps, forged, 20.0, None)
