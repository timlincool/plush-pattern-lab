"""Source-profile upper mother trial: exact seam pairing is not source fit."""

from __future__ import annotations

import copy
import math
from xml.etree import ElementTree

import numpy as np
import pytest

from plush_pattern_lab.patterns.stage6_lower_mother_toile import (
    build_source_hoof_lower_toile,
    extract_original_hoof_rings,
)
from plush_pattern_lab.patterns.stage6_upper_mother_toile import (
    PROFILE_Z_MM,
    build_upper_mother_from_lower,
)
from plush_pattern_lab.patterns.stage6_upper_mother_toile_svg import (
    render_stage6_upper_mother_a4,
)
from plush_pattern_lab.validation.stage6_upper_mother_toile_qc import (
    audit_source_profile_upper_mother,
)

TARGET_PERIMETERS = (101.640317, 93.309140, 119.100288, 119.100290)


def _lower_and_source(*, facial_jump=True):
    xyz, faces = [], []
    for (cx, cy), total in zip(
        ((-29, -34), (29, -34), (-29, 81), (29, 81)), TARGET_PERIMETERS
    ):
        n = 512
        theta = 2 * np.pi * np.arange(n) / n
        radius = total / (2 * n * math.sin(math.pi / n))
        xy = np.column_stack((cx + radius * np.cos(theta), cy + radius * np.sin(theta)))
        offset = len(xyz)
        xyz.extend(np.column_stack((xy, np.full(n, 20.0))).tolist())
        xyz.append([cx, cy, 20])
        faces.extend(
            [
                [offset + i, offset + (i + 1) % n, offset + n]
                for i in range(n)
            ]
        )
    hoof_count = len(xyz)
    for z, cy, xhalf, yhalf in (
        (130, 28, 36, 93),
        (155, -43 if facial_jump else 28, 33, 33),
        (180, -50, 52, 37),
        (205, -47, 56, 36),
        (230, -47, 64, 22),
    ):
        t = np.linspace(0, 2 * np.pi, 180, endpoint=False)
        xyz.extend(
            np.column_stack(
                (xhalf * np.cos(t), cy + yhalf * np.sin(t), np.full(len(t), z))
            ).tolist()
        )
    all_points = np.asarray(xyz, dtype=float)
    rings = extract_original_hoof_rings(
        all_points[:hoof_count], np.asarray(faces)
    )
    lower = build_source_hoof_lower_toile(rings)
    return lower, all_points


def _trial():
    lower, xyz = _lower_and_source()
    return lower, build_upper_mother_from_lower(lower, xyz)


def test_actual_lower_open_four_bands_have_exact_new_upper_gore_partners():
    lower, upper = _trial()
    qa = audit_source_profile_upper_mother(upper, lower)
    assert qa["all_12_new_sewing_relations_matched_in_2d"]
    assert len(qa["four_real_lower_band_to_upper_source_stitch_relations"]) == 4
    assert len(qa["four_independent_new_upper_side_seam_relations"]) == 4
    assert len(qa["four_top_cap_indexed_16_edge_stitch_relations"]) == 4
    assert upper["new_upper_piece_count"] == 5
    assert upper["total_research_stitch_pieces"] == 18
    assert all(
        row["max_net_stitch_segment_mismatch_mm"] < 1e-7
        for row in qa["four_real_lower_band_to_upper_source_stitch_relations"]
    )
    assert qa["factory_cutting_approved"] == 0


def test_historic_neck_cross_section_jumps_even_when_all_stitches_match():
    lower, upper = _trial()
    report = audit_source_profile_upper_mother(upper, lower)
    assert tuple(upper["source_profile_z_mm"]) == PROFILE_Z_MM
    assert upper["max_source_observed_profile_center_step_mm"] > 50
    assert report["neck_split_or_anatomical_articulation_review_required"]
    assert report["source_3d_meridian_lengths_not_preserved"]
    assert not report["actual_source_body_silhouette_not_certified"] is False
    assert not report["real_fabric_and_stuffing_tested"]
    assert upper["source_proxy_used_only_as_envelope_reference"]


def test_upper_five_a4_svgs_stay_true_size_and_not_production_patterns():
    lower, upper = _trial()
    pages = render_stage6_upper_mother_a4(upper)
    assert sorted(pages) == [f"upper-sheet-{k:02d}.svg" for k in range(1, 6)]
    for data in pages.values():
        root = ElementTree.fromstring(data)
        assert root.attrib["width"] == "210mm"
        assert root.attrib["height"] == "297mm"
        assert root.attrib["viewBox"] == "0 0 210 297"
        assert "NOT ORIGINAL STAGE6 CUTTING PATTERN" in data
        assert "Calibration 10 x 10 mm" in data
    for i in range(4):
        assert f'data-part="UPPER-{i + 1}"' in pages[
            f"upper-sheet-{i + 1:02d}.svg"
        ]
    assert 'data-part="TOP-CAP-TRIAL"' in pages["upper-sheet-05.svg"]
    assert lower["yoke"]["upper_body_shell_seam_unpaired"]


@pytest.mark.parametrize(
    "corruption",
    ["wrong_band", "bad_bottom", "bad_top", "bad_side", "factory", "missing_cap"],
)
def test_source_stitch_tampering_is_refused_instead_of_masked(corruption):
    lower, upper = _trial()
    upper = copy.deepcopy(upper)
    if corruption == "wrong_band":
        upper["upper_gore_pieces"][0]["paired_lower_band"] = "BAND-3"
    elif corruption == "bad_bottom":
        upper["upper_gore_pieces"][0]["bottom_stitch_xy_mm"][4][0] += 1
    elif corruption == "bad_top":
        upper["upper_gore_pieces"][0]["upper_stitch_xy_mm"][4][0] += 1
    elif corruption == "bad_side":
        upper["upper_gore_pieces"][0]["left_stitch_xy_mm"][2][1] += 2
    elif corruption == "factory":
        upper["industrial_cut_patterns_approved"] = 1
    else:
        upper["research_top_cap"]["stitch_ring_xy_mm"] = []
    with pytest.raises(ValueError):
        audit_source_profile_upper_mother(upper, lower)


def test_incomplete_real_source_z_slices_cannot_invent_head_profile():
    lower, xyz = _lower_and_source()
    xyz = xyz[np.abs(xyz[:, 2] - 230) > 0.1]
    with pytest.raises(ValueError):
        build_upper_mother_from_lower(lower, xyz)


def test_invalid_lower_source_reference_cannot_be_silently_upgraded():
    lower, xyz = _lower_and_source()
    lower["source_hoof_open_edges"] = 1024
    with pytest.raises(ValueError):
        build_upper_mother_from_lower(lower, xyz)
