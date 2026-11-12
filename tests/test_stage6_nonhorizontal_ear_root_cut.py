"""Fail-closed original-source sloping ear-root cuts and paired 3D interface tests."""

from copy import deepcopy

import numpy as np
import pytest

from plush_pattern_lab.validation.stage6_nonhorizontal_ear_root_cut import (
    SCHEMA,
    STUDIES,
    _physical_cut_surfaces,
    _restore_original_world_coordinates,
    _split_original_source,
    compare_nonhorizontal_original_source_roots,
)
from plush_pattern_lab.validation.stage6_nonhorizontal_ear_root_svg import (
    render_nonhorizontal_ear_root_svg,
)
from plush_pattern_lab.validation.stage6_true_ear_root_band_cut import (
    _components,
    _paired_seam,
    _surface_area,
)


def _synthetic_box():
    # True source XYZ are NOT modified; Y slopes cross the two artificial cuts.
    points = np.array(
        [
            [-8, -52, 220],
            [8, -52, 220],
            [8, -38, 220],
            [-8, -38, 220],
            [-8, -52, 260],
            [8, -52, 260],
            [8, -38, 260],
            [-8, -38, 260],
        ],
        dtype=float,
    )
    faces = np.array(
        [
            [0, 2, 1],
            [0, 3, 2],
            [4, 5, 6],
            [4, 6, 7],
            [0, 1, 5],
            [0, 5, 4],
            [1, 2, 6],
            [1, 6, 5],
            [2, 3, 7],
            [2, 7, 6],
            [3, 0, 4],
            [3, 4, 7],
        ],
        dtype=int,
    )
    return points, faces


@pytest.mark.parametrize("study", STUDIES)
def test_nonhorizontal_original_mesh_cuts_true_3d_paired_seams(study):
    xyz, faces = _synthetic_box()
    original, source_faces = xyz.copy(), faces.copy()
    scalar, lower, upper = _physical_cut_surfaces(xyz, *study[1:])
    assert np.ptp(lower) > 1 and np.ptp(upper) > 1
    zones = _split_original_source(xyz, faces, scalar)
    below, root, above = (
        _components(zones[name])[0] for name in ("below", "root", "above")
    )
    assert root["euler"] == 0 and len(root["boundary_loops"]) == 2
    assert below["euler"] == above["euler"] == 1
    a = _paired_seam(zones["below"], below, zones["root"], root, 0.0)
    b = _paired_seam(zones["root"], root, zones["above"], above, 1.0)
    for seam in (a, b):
        assert seam["max_source_3d_pair_position_error_mm"] == 0
        assert seam["two_source_3d_sides_exactly_same_with_opposite_face_winding"]
        assert seam["not_a_validated_two_sided_fabric_2d_netline"]
        assert len(seam["original_source_3d_ordered_ring_vertex_keys"]) >= 8
    low_xyz = np.array(a["original_source_3d_ordered_ring_xyz_mm"])
    upper_xyz = np.array(b["original_source_3d_ordered_ring_xyz_mm"])
    assert np.ptp(low_xyz[:, 2]) > 1
    assert np.ptp(upper_xyz[:, 2]) > 1
    area = _surface_area(xyz, faces)
    cut = sum(_surface_area(zone["xyz"], zone["faces"]) for zone in zones.values())
    assert np.isclose(area, cut, atol=1e-8)
    assert np.array_equal(xyz, original) and np.array_equal(faces, source_faces)


@pytest.mark.parametrize(
    "bad",
    ["too_narrow", "vertex_cut", "nonfinite", "wrong_edge_ratio"],
)
def test_invalid_sloping_source_proposal_or_cut_is_rejected(bad):
    xyz, faces = _synthetic_box()
    if bad == "too_narrow":
        with pytest.raises(ValueError, match="too narrow"):
            _physical_cut_surfaces(xyz, 230, 235, 0)
    elif bad == "vertex_cut":
        xyz[0, 2] = 228.5 + 1.5 * np.clip(
            (xyz[0, 1] + 45) / 15, -1, 1
        )
        with pytest.raises(ValueError, match="through source vertex"):
            _physical_cut_surfaces(xyz, *STUDIES[0][1:])
    elif bad == "nonfinite":
        xyz[0, 2] = float("nan")
        with pytest.raises(ValueError):
            _physical_cut_surfaces(xyz, *STUDIES[0][1:])
    else:
        scalar, _, _ = _physical_cut_surfaces(xyz, *STUDIES[0][1:])
        zones = _split_original_source(xyz, faces, scalar)
        modified = deepcopy(zones["root"])
        key = next(x for x in modified["keys"] if x[0] == "e")
        position = modified["keys"].index(key)
        modified["keys"][position] = ("e", key[1], key[2], 9.0)
        with pytest.raises(ValueError, match="non-interior"):
            _restore_original_world_coordinates(modified, xyz, scalar)


def test_one_box_cannot_masquerade_as_full_original_three_branch_stage6():
    xyz, faces = _synthetic_box()
    with pytest.raises(ValueError, match="topology changed"):
        compare_nonhorizontal_original_source_roots(xyz, faces)


def test_research_atlas_rejects_factory_cutting_claim():
    report = {
        "schema": SCHEMA,
        "proposed_surface_designs": [{}, {}],
        "factory_cutting_patterns_approved": 1,
    }
    with pytest.raises(ValueError):
        render_nonhorizontal_ear_root_svg(report)
    report["factory_cutting_patterns_approved"] = 0
    with pytest.raises((KeyError, ValueError)):
        render_nonhorizontal_ear_root_svg(report)
