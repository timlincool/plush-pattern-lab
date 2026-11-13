"""Two-volume Stage6 trial: seam length truth, topology and failure controls."""

import copy
import math
from xml.etree import ElementTree

import numpy as np
import pytest

from plush_pattern_lab.patterns.stage6_lower_mother_toile import (
    build_source_hoof_lower_toile,
    extract_original_hoof_rings,
)
from plush_pattern_lab.patterns.stage6_split_volume_mother import (
    OPTIONS,
    build_split_volume_mother_ab,
)
from plush_pattern_lab.patterns.stage6_split_volume_panel_interface import (
    build_split_24piece_assembly_graphs,
)
from plush_pattern_lab.patterns.stage6_split_volume_toile_svg import (
    render_split_volume_A4,
)
from plush_pattern_lab.validation.stage6_split_volume_toile_qc import (
    audit_separated_stage6_toile,
)


def _source_and_lower():
    xyz, faces = [], []
    perimeters = (101.640317, 93.309140, 119.100288, 119.100290)
    for (cx, cy), perimeter in zip(
        ((-29, -34), (29, -34), (-29, 81), (29, 81)), perimeters
    ):
        n = 512
        radius = perimeter / (2 * n * math.sin(math.pi / n))
        angles = 2 * np.pi * np.arange(n) / n
        xy = np.column_stack(
            (cx + radius * np.cos(angles), cy + radius * np.sin(angles))
        )
        begin = len(xyz)
        xyz.extend(np.column_stack((xy, np.full(n, 20.0))).tolist())
        xyz.append([cx, cy, 20])
        for j in range(n):
            faces.append([begin + j, begin + (j + 1) % n, begin + n])
    hoof_vertices = np.asarray(xyz, dtype=float)
    lower = build_source_hoof_lower_toile(
        extract_original_hoof_rings(hoof_vertices, np.asarray(faces))
    )
    bounds = (
        (115, -41, 41, -69, 138),
        (125, -38, 38, -67, 132),
        (135, -35, 35, -68, 70),
        (145, -32, 32, -68, -2),
        (155, -33, 33, -77, -10),
        (180, -53, 53, -88, -14),
        (205, -56, 56, -82, -12),
        (230, -64, 64, -69, -25),
    )
    for z, lo_x, hi_x, lo_y, hi_y in bounds:
        theta = 2 * np.pi * np.arange(180) / 180
        ring = np.column_stack(
            (
                (hi_x - lo_x) / 2 * np.cos(theta) + (hi_x + lo_x) / 2,
                (hi_y - lo_y) / 2 * np.sin(theta) + (hi_y + lo_y) / 2,
                np.full(180, z),
            )
        )
        xyz.extend(ring.tolist())
    return lower, np.asarray(xyz, dtype=float)


def _trial():
    lower, source = _source_and_lower()
    return lower, build_split_volume_mother_ab(lower, source)


def test_two_anatomically_separated_volume_options_remain_finite_and_signed():
    lower, study = _trial()
    qc = audit_separated_stage6_toile(lower, study)
    assert [row["name"] for row in study["options"]] == [
        "A_separate_stuffed_head",
        "B_integrated_neck_port",
    ]
    assert [row["new_pattern_pieces"] for row in study["options"]] == [11, 11]
    assert [row["new_plus_existing_research_pieces"] for row in study["options"]] == [
        24,
        24,
    ]
    assert len(qc["two_distinct_manufacturing_trial_variants"]) == 2
    assert all(
        row["all_new_mathematical_seam_lengths_paired"]
        for row in qc["two_distinct_manufacturing_trial_variants"]
    )
    assert qc["approved_industrial_patterns"] == 0


def test_one_option_closes_two_separate_volumes_other_has_actual_neck_port():
    lower, study = _trial()
    a, b = study["options"]
    qc = audit_separated_stage6_toile(lower, study)
    assert a["head_bottom_cap_if_separate"] is not None
    assert a["neck_collar_if_integrated"] is None
    assert not a["shoulder_cap"]["cut_inner_holes_xy_mm"]
    assert b["head_bottom_cap_if_separate"] is None
    assert b["neck_collar_if_integrated"] is not None
    assert len(b["shoulder_cap"]["cut_inner_holes_xy_mm"]) == 1
    assert qc["two_distinct_manufacturing_trial_variants"][0]["neck_connection"][
        "surface_join_is_not_a_cut_edge_seam_certified"
    ]
    assert qc["two_distinct_manufacturing_trial_variants"][1]["neck_connection"][
        "neck_opening_still_requires_physical_turning_test"
    ]


def test_unverified_neck_root_contraction_and_original_source_gap_are_reported():
    _, study = _trial()
    a, b = study["options"]
    assert study["real_source_135_to145_center_shift_xy_mm"] > 20
    assert [
        row["source_neck_port_modification"]["explicit_source_head_root_xy_scale"]
        for row in (a, b)
    ] == [0.74, 0.64]
    assert all(
        row["source_neck_port_modification"][
            "max_source_head_root_to_2d_port_vertex_xy_shift_mm"
        ]
        > 5
        for row in (a, b)
    )
    assert all(
        not row["original_real_sculpt_cutting_patterns_generated"] for row in (a, b)
    )


def test_source_linked_band_pieces_keep_exact_old_16_edge_ids_and_stitch_mm():
    lower, study = _trial()
    qc = audit_separated_stage6_toile(lower, study)
    for variant in qc["two_distinct_manufacturing_trial_variants"]:
        rows = variant["lower_band_to_torso_pairs"]
        assert len(rows) == 4
        assert max(row["max_segment_difference_mm"] for row in rows) < 1e-7
        assert rows[0]["pair"].startswith("BAND-1")


def test_each_trial_has_eleven_true_scale_A4_svg_without_software_scaling():
    _, study = _trial()
    pages = render_split_volume_A4(study)
    assert set(pages) == {row[0] for row in OPTIONS}
    for option, sheets in pages.items():
        assert len(sheets) == 11
        for name, svg in sheets.items():
            root = ElementTree.fromstring(svg)
            assert root.attrib["width"] == "210mm"
            assert root.attrib["height"] == "297mm"
            assert root.attrib["viewBox"] == "0 0 210 297"
            assert "NO FACTORY CUTTING APPROVAL" in svg
            assert "10 x 10 mm" in svg
            assert name.endswith(".svg")
            assert option in svg


@pytest.mark.parametrize(
    "fault",
    ["wrong_lower", "reordered_lower_band", "shoulder_cut", "head_bottom", "collar"],
)
def test_invalid_source_or_corrupted_matched_seams_are_refused(fault):
    lower, study = _trial()
    lower, study = copy.deepcopy(lower), copy.deepcopy(study)
    if fault == "wrong_lower":
        lower["source_hoof_open_edges"] = 512
    elif fault == "reordered_lower_band":
        study["options"][0]["torso_gore_pieces"][0][
            "source_surrogate_16_ring_edge_ids"
        ] = list(range(16, 32))
    elif fault == "shoulder_cut":
        study["options"][1]["shoulder_cap"]["cut_inner_holes_xy_mm"] = []
    elif fault == "head_bottom":
        study["options"][0]["head_bottom_cap_if_separate"] = None
    else:
        study["options"][1]["neck_collar_if_integrated"][
            "lower_and_upper_stitch_station_x_mm"
        ][17] += 2.0
    with pytest.raises(ValueError):
        audit_separated_stage6_toile(lower, study)


def test_missing_original_source_slice_and_falsified_factory_flag_are_refused():
    lower, source = _source_and_lower()
    filtered = source[np.abs(source[:, 2] - 145) > 3]
    with pytest.raises(ValueError):
        build_split_volume_mother_ab(lower, filtered)
    study = build_split_volume_mother_ab(lower, source)
    study["factory_cutting_patterns_approved"] = 1
    with pytest.raises(ValueError):
        audit_separated_stage6_toile(lower, study)


def test_synthetic_shoulder_that_cannot_hold_two_allowances_is_refused():
    lower, points = _source_and_lower()
    corrupted = points.copy()
    slab = np.abs(corrupted[:, 2] - 135) < 0.01
    corrupted[slab, 0] *= 0.6
    with pytest.raises(ValueError, match="shoulder seam clearance"):
        build_split_volume_mother_ab(lower, corrupted)


def test_full_24piece_trial_graph_distinguishes_manual_A_from_numeric_B():
    lower, study = _trial()
    graphs = build_split_24piece_assembly_graphs(lower, study)
    assert set(graphs) == set(("A_separate_stuffed_head", "B_integrated_neck_port"))
    for name, graph in graphs.items():
        assert graph["total_research_pieces"] == 24
        assert graph["lower_original_research_pieces_unchanged"] == 13
        assert graph["original_source_hoof_edge_count"] == 2048
        assert graph["print_sheet_count"] == 15
        assert len(graph["all_pieces"]) == 24
        assert len({part["id"] for part in graph["all_pieces"]}) == 24
        assert graph["P3_status"] == "in_progress"
        assert graph["P4_status"] == "not_started"
        assert graph["factory_cut_patterns_approved"] == 0
        ends = [
            endpoint
            for seam in graph["sewing_interfaces"]
            for endpoint in (seam["first"], seam["second"])
        ]
        assert len(ends) == len(set(ends))
        assert name in [trial["name"] for trial in study["options"]]
    a, b = (
        graphs[name] for name in ("A_separate_stuffed_head", "B_integrated_neck_port")
    )
    assert len(a["sewing_interfaces"]) == 45
    assert a["numerically_paired_interface_count"] == 44
    assert a["manual_unverified_surface_attachment_count"] == 1
    assert len(a["components_without_unverified_manual_join"]) == 2
    assert any(
        edge["kind"] == "UNPROVEN_MANUAL_SURFACE_ATTACHMENT"
        and edge["first_2d_netline_mm"] is None
        for edge in a["sewing_interfaces"]
    )
    assert len(b["sewing_interfaces"]) == 46
    assert b["numerically_paired_interface_count"] == 46
    assert b["manual_unverified_surface_attachment_count"] == 0
    assert len(b["components_without_unverified_manual_join"]) == 1
    assert any(
        edge["kind"] == "shoulder_port_to_collar" for edge in b["sewing_interfaces"]
    )
    assert (
        sum(edge["kind"] == "collar_top_to_headneck" for edge in b["sewing_interfaces"])
        == 4
    )


def test_full_24piece_trial_rejects_duplicate_or_corrupted_source_seam():
    lower, study = _trial()
    study = copy.deepcopy(study)
    study["options"][1]["headneck_gore_pieces"][0]["lower_stitch_xy_mm"][8][0] += 0.5
    with pytest.raises(ValueError, match="neck|root|source|seam"):
        build_split_24piece_assembly_graphs(lower, study)


def test_full_24piece_trial_rejects_missing_real_hoof_index():
    lower, study = _trial()
    lower = copy.deepcopy(lower)
    lower["original_source_hoofs"]["FL"]["source_vertex_ids"][1] += 7
    with pytest.raises(ValueError):
        build_split_24piece_assembly_graphs(lower, study)
