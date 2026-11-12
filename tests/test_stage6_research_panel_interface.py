"""Source-hoof anchored 18-piece Panel/Interface research sewing tests.

Synthetic positive test is a GEOMETRIC FIXTURE, not the actual Stage6 sculpt;
trusted main Stage6 Blender workflow replays the real 25% source separately.
"""

from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

from plush_pattern_lab.patterns.stage6_lower_mother_toile import (
    build_source_hoof_lower_toile,
)
from plush_pattern_lab.patterns.stage6_research_assembly_svg import (
    render_research_assembly_svg,
)
from plush_pattern_lab.patterns.stage6_research_panel_interface import (
    SCHEMA,
    _insert_pair,
    _one_research_component,
    build_stage6_research_assembly,
)
from plush_pattern_lab.patterns.stage6_upper_mother_toile import (
    build_upper_mother_from_lower,
)
from plush_pattern_lab.validation.stage6_lower_mother_toile_qc import (
    EXPECTED_SOURCE_HOOF_PERIMETERS_MM,
)


def _synthetic_hoof_rings():
    rows = {}
    positions = {
        "FL": (-29.0, -34.0),
        "FR": (29.0, -34.0),
        "RL": (-29.0, 81.0),
        "RR": (29.0, 81.0),
    }
    for k, (role, (cx, cy)) in enumerate(positions.items()):
        theta = 2 * np.pi * np.arange(512) / 512
        original_length = EXPECTED_SOURCE_HOOF_PERIMETERS_MM[role]
        radius = original_length / (1024 * np.sin(np.pi / 512))
        xy = np.column_stack((cx + radius * np.cos(theta), cy + radius * np.sin(theta)))
        steps = np.linalg.norm(xy - np.roll(xy, -1, axis=0), axis=1)
        rows[role] = {
            "original_vertex_ids": np.arange(512 * k, 512 * (k + 1)),
            "original_xy_mm": xy,
            "source_edge_lengths_mm": steps,
            "source_perimeter_mm": float(steps.sum()),
            "source_centroid_xyz_mm": np.array([cx, cy, 20.0]),
        }
    return rows


def _synthetic_source_slices():
    rows = []
    slices = (
        (130, 28, 36, 93),
        (155, -43, 33, 33),
        (180, -50, 52, 37),
        (205, -47, 56, 36),
        (230, -47, 64, 22),
    )
    for z, cy, half_x, half_y in slices:
        theta = 2 * np.pi * np.arange(180) / 180
        x = half_x * np.cos(theta)
        y = cy + half_y * np.sin(theta)
        rows.extend(np.column_stack((x, y, np.full(180, z))).tolist())
    return np.asarray(rows, dtype=float)


def _trial():
    low = build_source_hoof_lower_toile(_synthetic_hoof_rings())
    upper = build_upper_mother_from_lower(low, _synthetic_source_slices())
    return low, upper


def test_existing_lower_plus_upper_forms_one_18_piece_32_interface_2d_graph():
    lower, upper = _trial()
    graph = build_stage6_research_assembly(lower, upper)
    assert graph["schema"] == SCHEMA
    assert len(graph["all_pieces"]) == 18
    assert len(graph["paired_stitch_interfaces"]) == 32
    assert graph["paired_interface_count"] == 32
    assert graph["print_sheet_count"] == 9
    assert graph["source_original_hoof_edge_count"] == 2048
    assert graph["assembly_is_one_connected_piece_graph"]
    assert {item["kind"] for item in graph["paired_stitch_interfaces"]} == {
        "hoof_yoke_to_sleeve",
        "synthetic_flat_sole_to_sleeve",
        "sleeve_self_close",
        "yoke_outer_to_lower_band",
        "band_vertical_side_join",
        "lower_band_to_upper_gore",
        "upper_gore_vertical_side_join",
        "upper_to_research_head_cap",
    }
    assert all(
        item["max_segment_disagreement_mm"] < 1e-4
        for item in graph["paired_stitch_interfaces"]
    )
    assert not graph["physical_toile_produced"]
    assert graph["factory_cut_patterns_approved"] == 0
    assert graph["P3_status"] == "in_progress"
    assert graph["P4_status"] == "not_started"
    assert "NOT approved patterns" in render_research_assembly_svg(graph)


@pytest.mark.parametrize(
    "tamper",
    ("hoof_vertex", "hoof_station", "upper_edge", "cap_edge", "factory", "four_bands"),
)
def test_source_id_segment_source_qa_and_factory_tampering_rejected(tamper):
    lower, upper = _trial()
    if tamper == "hoof_vertex":
        lower["original_source_hoofs"]["FL"]["source_vertex_ids"][3] += 1
    elif tamper == "hoof_station":
        lower["original_source_hoofs"]["FR"]["sleeve_stitch_station_x_mm"][50] += 2
    elif tamper == "upper_edge":
        upper["upper_gore_pieces"][0]["bottom_stitch_xy_mm"][2][0] += 2
    elif tamper == "cap_edge":
        upper["research_top_cap"]["quarter_source_surrogate_edge_indices"][1][3] = 99
    elif tamper == "factory":
        upper["industrial_cut_patterns_approved"] = 1
    else:
        lower["outer_quarter_bands"].pop()
    with pytest.raises((KeyError, ValueError, IndexError)):
        build_stage6_research_assembly(lower, upper)


def test_part_interface_duplicate_and_netline_mismatch_are_refused():
    pairs, claimed = [], set()
    _insert_pair(pairs, claimed, "P1.a", "P2.b", [1, 2], [1, 2], "trial", "source")
    assert len(pairs) == 1
    with pytest.raises(ValueError, match="more than once"):
        _insert_pair(pairs, claimed, "P1.a", "P3.c", [1], [1], "trial", "source")
    with pytest.raises(ValueError, match="segment by segment"):
        _insert_pair(pairs, claimed, "P4.a", "P5.b", [1], [2], "trial", "source")
    with pytest.raises(ValueError, match="nonfinite"):
        _insert_pair(
            pairs, claimed, "P4.a", "P5.b", [1], [float("nan")], "trial", "source"
        )


def test_disconnected_or_mislabeled_18_piece_sewing_graph_cannot_be_promoted():
    lower, upper = _trial()
    graph = build_stage6_research_assembly(lower, upper)
    altered = deepcopy(graph["paired_stitch_interfaces"])
    altered = [item for item in altered if "SOLE-" not in item["second"]]
    with pytest.raises(ValueError, match="do not form a connected"):
        _one_research_component(graph["all_pieces"], altered)
    wrong = deepcopy(graph)
    wrong["factory_cut_patterns_approved"] = 1
    with pytest.raises(ValueError):
        render_research_assembly_svg(wrong)
