"""Original-face source annulus cuts, two-sided 2D seams and LSCM veto tests."""

from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

from plush_pattern_lab.validation.stage6_ear_slit_disk import (
    ROUTES,
    _canonical_sha,
    create_source_slit_disk,
    validate_original_root_patch,
)
from plush_pattern_lab.validation.stage6_ear_slit_lscm import (
    SCHEMA,
    _lower_upper_planar_clearance,
    _two_true_planar_seam_sides,
    evaluate_original_source_slit_disk,
)
from plush_pattern_lab.validation.stage6_ear_slit_svg import (
    render_source_slit_lscm_atlas,
)


def _synthetic_source_annulus(side="left", n=12):
    theta = np.arange(n) * 2 * np.pi / n
    center_x = -50 if side == "left" else 50
    lower = np.column_stack(
        (center_x + 6 * np.cos(theta), -45 + 6 * np.sin(theta), np.full(n, 220))
    )
    upper = np.column_stack(
        (center_x + 4 * np.cos(theta), -45 + 4 * np.sin(theta), np.full(n, 240))
    )
    xyz = np.vstack((lower, upper))
    triangles = []
    for i in range(n):
        j = (i + 1) % n
        triangles.extend(((i, j, n + j), (i, n + j, n + i)))
    derived = {
        "source_3d_xyz_mm": xyz.tolist(),
        "original_source_vertex_or_edge_plane_keys": [
            ["v", i] for i in range(len(xyz))
        ],
        "derived_triangle_local_vertex_ids": triangles,
        "each_derived_face_original_triangle_id": list(range(2 * n)),
        "not_industrial_2d_paper_pattern": True,
    }
    def boundary(indices):
        return {
            "original_source_3d_ordered_ring_vertex_keys": [
                ["v", int(i)] for i in indices
            ],
            "original_source_3d_ordered_ring_xyz_mm": xyz[indices].tolist(),
            "max_source_3d_pair_position_error_mm": 0,
            "two_source_3d_sides_exactly_same_with_opposite_face_winding": True,
        }

    patch = {
        "side": side,
        "actual_original_source_root_band": {
            "euler_characteristic": 0,
            "closed_boundary_loop_count": 2,
        },
        "body_to_root_paired_3d_source_netline": boundary(np.arange(n)),
        "root_to_upper_ear_paired_3d_source_netline": boundary(np.arange(n, 2 * n)),
        "source_root_band_triangles_with_original_face_ids": derived,
        "true_manufacturing_2d_pattern_generated": False,
        "fabric_and_assembly_approved": False,
    }
    study = {
        "name": "N15_sloped_source_band",
        "true_3d_source_zone_component_counts": {"below": 1, "root": 3, "above": 2},
    }
    reference = {
        "source_patch_canonical_sha256": _canonical_sha(derived),
        "source_patch_derived_triangles": 2 * n,
    }
    return study, patch, reference


@pytest.mark.parametrize("side", ("left", "right"))
@pytest.mark.parametrize("direction", ROUTES)
def test_true_source_annulus_to_disk_preserves_faces_and_3d_source_pairs(
    side, direction
):
    study, patch, ref = _synthetic_source_annulus(side)
    disk = create_source_slit_disk(study, patch, ref, direction)
    assert disk["source_study"] == study["name"]
    assert disk["slit_disk_euler_characteristic"] == 1
    assert disk["slit_disk_single_boundary"]
    assert disk["slit_disk_face_count"] == disk["original_source_face_count"] == 24
    assert np.isclose(
        disk["original_source_patch_area_mm2"], disk["source_disk_area_mm2"]
    )
    assert len(disk["original_patch_vertex_id_per_disk_vertex"]) == (
        24 + len(disk["slit_original_local_vertex_ids"])
    )
    assert not disk["sewable_or_cutting_approved"]
    report = evaluate_original_source_slit_disk(disk)
    assert report["schema"] == SCHEMA
    assert report["not_a_factory_cutting_or_sewing_approval"]
    assert report["factory_cutting_patterns_approved"] == 0
    assert (
        report["original_source_planar_face_geometry_diagnostics"][
            "reversed_or_collapsed_triangle_count"
        ]
        == 0
    )
    seam = report["true_source_seam_3d_vs_lscm_2d_pairing"]
    assert seam[
        "original_source_cut_edge_has_exactly_two_oppositely_oriented_disk_sides"
    ]
    assert seam["original_paired_3d_seam_length_each_side_mm"] > 15


@pytest.mark.parametrize(
    "tamper",
    (
        "bad_sha",
        "fake_factory",
        "source_face",
        "source_coords",
        "missing_key",
        "duplicate_id",
        "fake_pairing",
        "false_annulus",
    ),
)
def test_tampered_original_3d_source_geometry_or_authority_fails_closed(tamper):
    study, patch, reference = _synthetic_source_annulus()
    broken = deepcopy(patch)
    deriv = broken["source_root_band_triangles_with_original_face_ids"]
    if tamper == "bad_sha":
        reference["source_patch_canonical_sha256"] = "0" * 64
    elif tamper == "fake_factory":
        broken["fabric_and_assembly_approved"] = True
    elif tamper == "source_face":
        deriv["each_derived_face_original_triangle_id"][0] = 999999
        reference["source_patch_canonical_sha256"] = _canonical_sha(deriv)
    elif tamper == "source_coords":
        broken["body_to_root_paired_3d_source_netline"][
            "original_source_3d_ordered_ring_xyz_mm"
        ][0][0] += 2
    elif tamper == "missing_key":
        broken["body_to_root_paired_3d_source_netline"][
            "original_source_3d_ordered_ring_vertex_keys"
        ][0] = ["v", 123456]
    elif tamper == "duplicate_id":
        deriv["original_source_vertex_or_edge_plane_keys"][0] = ["v", 1]
        reference["source_patch_canonical_sha256"] = _canonical_sha(deriv)
    elif tamper == "fake_pairing":
        broken["root_to_upper_ear_paired_3d_source_netline"][
            "two_source_3d_sides_exactly_same_with_opposite_face_winding"
        ] = False
    else:
        broken["actual_original_source_root_band"]["euler_characteristic"] = 1
    with pytest.raises(ValueError):
        validate_original_root_patch(study, broken, reference)


def test_disk_source_id_pairing_detects_missing_duplicate_cut_boundary():
    study, patch, reference = _synthetic_source_annulus()
    disk = create_source_slit_disk(study, patch, reference, "posterior")
    uv = evaluate_original_source_slit_disk(disk)["real_2d_research_coordinates_mm"]
    bad = deepcopy(disk)
    original_len = len(
        patch["source_root_band_triangles_with_original_face_ids"]["source_3d_xyz_mm"]
    )
    bad["original_patch_vertex_id_per_disk_vertex"][original_len] = -1
    with pytest.raises(ValueError, match="two physical source seam copies"):
        _two_true_planar_seam_sides(bad, np.asarray(uv))


def test_planar_upper_lower_gap_only_vertex_screen_not_two_6mm_allowances():
    study, patch, reference = _synthetic_source_annulus()
    disk = create_source_slit_disk(study, patch, reference, "medial")
    report = evaluate_original_source_slit_disk(disk)
    gap = report["two_seams_2d_6mm_allowance_vertex_screen"]
    assert gap["sampled_vertex_gap_is_not_true_continuous_offset_allowance"]
    assert gap["scaled_2d_min_sampled_lower_upper_vertex_gap_mm"] > 0
    uv = np.array(report["real_2d_research_coordinates_mm"])
    source = deepcopy(disk)
    source["original_source_upper_boundary_vertex_ids"] = np.array([], dtype=int)
    with pytest.raises(ValueError):
        _lower_upper_planar_clearance(source, uv)


def test_research_preview_labels_manufacturing_block_and_requires_12_trials():
    study, patch, reference = _synthetic_source_annulus()
    disk = create_source_slit_disk(study, patch, reference, "lateral")
    output = evaluate_original_source_slit_disk(disk)
    report = {
        "schema": SCHEMA,
        "factory_cutting_patterns_approved": 0,
        "candidate_2d_research_disks": [output] * 12,
    }
    svg = render_source_slit_lscm_atlas(report)
    assert "NO CUTTING PATTERNS" in svg
    assert svg.count("P95 edge distortion:") == 12
    report["factory_cutting_patterns_approved"] = 1
    with pytest.raises(ValueError):
        render_source_slit_lscm_atlas(report)
