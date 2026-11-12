"""Reusable Panel/Interface-inspired assembly contract for EXISTING 18-piece toile.

The geometry and nine A4 sheets already exist. This module adds explicit
stitch-partner identities, indexed netline checks and one sewing order. It is
an independent in-repo design, NOT copied GarmentCode implementation.

Digital seam equalities only: 13+5 research surrogates remain unfit to the
original Stage6 neck/head; no tested materials, stuffing or factory authority.
"""

from __future__ import annotations

from collections import deque

import numpy as np

from plush_pattern_lab.validation.stage6_lower_mother_toile_qc import (
    inspect_source_lower_toile,
)
from plush_pattern_lab.validation.stage6_upper_mother_toile_qc import (
    audit_source_profile_upper_mother,
)

SCHEMA = "stage6-18piece-panel-interface-research-assembly-v1"
ROLES = ("FL", "FR", "RL", "RR")
TOLERANCE_MM = 1e-4
SOURCE_SHA = "38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a"


def _open_segments(points):
    xy = np.asarray(points, dtype=float)
    if (
        xy.ndim != 2
        or xy.shape[1] != 2
        or len(xy) < 2
        or not np.isfinite(xy).all()
    ):
        raise ValueError("missing finite 2D research netline")
    values = np.linalg.norm(np.diff(xy, axis=0), axis=1)
    if np.any(values <= 0):
        raise ValueError("zero-length 2D research sewing segment")
    return values


def _ring_segments(points):
    xy = np.asarray(points, dtype=float)
    if (
        xy.ndim != 2
        or xy.shape[1] != 2
        or len(xy) < 3
        or not np.isfinite(xy).all()
    ):
        raise ValueError("missing original projected hoof source ring")
    values = np.linalg.norm(xy - np.roll(xy, -1, axis=0), axis=1)
    if np.any(values <= 0):
        raise ValueError("non-simple source ring edge in research assembly")
    return values


def _station_segments(stations):
    data = np.asarray(stations, dtype=float)
    if data.ndim != 1 or len(data) < 2 or not np.isfinite(data).all():
        raise ValueError("missing source-indexed netline station lengths")
    values = np.diff(data)
    if np.any(values <= 0):
        raise ValueError("source-indexed netline steps must all be positive")
    return values


def _part_inventory():
    pieces = [
        {
            "id": "YOKE-01",
            "role": "four_hoof_ventral_test_yoke",
            "quantity": 1,
            "source_grade": "new_2d_surrogate_source_hoop_holes_only",
            "paper": "lower_mother_toile_research/sheet-01.svg",
        }
    ]
    for name in ROLES:
        pieces.extend(
            [
                {
                    "id": f"LEG-{name}",
                    "role": "straight_hoof_sleeve_trial",
                    "quantity": 1,
                    "source_grade": "source_hoof_512_segment_perimeter_but_synthetic_height",
                    "paper": "lower_mother_toile_research/sheet-02.svg",
                },
                {
                    "id": f"SOLE-{name}",
                    "role": "flat_provisional_sole_not_real_rounded_hoof",
                    "quantity": 1,
                    "source_grade": "same_source_hoof_XY_ring_flat_disc_surrogate",
                    "paper": "lower_mother_toile_research/sheet-03.svg",
                },
            ]
        )
    for i in range(1, 5):
        pieces.extend(
            [
                {
                    "id": f"BAND-{i}",
                    "role": "lower_body_outer_quarter_band",
                    "quantity": 1,
                    "source_grade": "new_surrogate_from_yoke_outer_64_segments",
                    "paper": "lower_mother_toile_research/sheet-04.svg",
                },
                {
                    "id": f"UPPER-{i}",
                    "role": "lofted_upper_body_head_neck_gore_trial",
                    "quantity": 1,
                    "source_grade": "new_source_envelope_informed_2d_surrogate",
                    "paper": f"upper_mother_toile_research/upper-sheet-0{i}.svg",
                },
            ]
        )
    pieces.append(
        {
            "id": "TOP-CAP-TRIAL",
            "role": "provisional_head_top_cap",
            "quantity": 1,
            "source_grade": "new_cap_surrogate_no_ear_or_cloud_mounts",
            "paper": "upper_mother_toile_research/upper-sheet-05.svg",
        }
    )
    return pieces


def _insert_pair(pairs, claimed, left, right, lhs, rhs, kind, source_id):
    a, b = np.asarray(lhs, dtype=float), np.asarray(rhs, dtype=float)
    if a.ndim != 1 or b.ndim != 1 or a.shape != b.shape or len(a) < 1:
        raise ValueError("original panel interfaces have incompatible stations")
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("panel/interface contains nonfinite netline length")
    if np.any(a <= 0) or np.any(b <= 0):
        raise ValueError("panel/interface contains zero or negative netline segment")
    mismatch = float(np.max(np.abs(a - b)))
    if mismatch > TOLERANCE_MM:
        raise ValueError("research seam partners do not match segment by segment")
    if left in claimed or right in claimed or left == right:
        raise ValueError("a paper pattern interface was attached more than once")
    claimed.update((left, right))
    pairs.append(
        {
            "id": f"S{len(pairs) + 1:02d}",
            "kind": kind,
            "first": left,
            "second": right,
            "segment_count": len(a),
            "first_2d_netline_mm": float(a.sum()),
            "second_2d_netline_mm": float(b.sum()),
            "max_segment_disagreement_mm": mismatch,
            "source_reference": source_id,
            "fabric_face_orientation_proven": False,
            "physical_stitching_proven": False,
        }
    )


def _hoof_seams(lower, pairs, claimed):
    for name in ROLES:
        hoof = lower["original_source_hoofs"][name]
        source = _ring_segments(hoof["source_stitch_ring_xy_mm"])
        stations = _station_segments(hoof["sleeve_stitch_station_x_mm"])
        if len(source) != 512 or len(stations) != 512:
            raise ValueError("original Stage6 hoof source identity not preserved")
        identity = hoof["source_3d_source_id_and_projected_xy_sha256"]
        _insert_pair(
            pairs,
            claimed,
            f"YOKE-01.hole-{name}",
            f"LEG-{name}.top",
            source,
            stations,
            "hoof_yoke_to_sleeve",
            identity,
        )
        _insert_pair(
            pairs,
            claimed,
            f"LEG-{name}.bottom",
            f"SOLE-{name}.rim",
            stations,
            source,
            "synthetic_flat_sole_to_sleeve",
            identity,
        )
        h = [float(hoof["sleeve_height_mm"])]
        _insert_pair(
            pairs,
            claimed,
            f"LEG-{name}.side-left",
            f"LEG-{name}.side-right",
            h,
            h,
            "sleeve_self_close",
            f"new_straight_sleeve_{name}",
        )


def _outer_band_seams(lower, pairs, claimed):
    outer = _ring_segments(lower["yoke"]["outer_stitch_xy_mm"])
    if len(outer) != 64:
        raise ValueError("original lower yoke research outer identity changed")
    bands = lower["outer_quarter_bands"]
    for index, band in enumerate(bands):
        if (
            band["id"] != f"BAND-{index + 1}"
            or band["source_ring_edge_indices"]
            != list(range(index * 16, (index + 1) * 16))
        ):
            raise ValueError("surrogate yoke 64 index station order changed")
        _insert_pair(
            pairs,
            claimed,
            f"YOKE-01.outer-{index + 1}",
            f"BAND-{index + 1}.bottom",
            outer[index * 16 : (index + 1) * 16],
            _station_segments(band["stitch_bottom_station_x_mm"]),
            "yoke_outer_to_lower_band",
            f"surrogate_yoke_outer_16_indexed_edges_{index + 1}",
        )
        next_band = (index + 1) % 4 + 1
        side = [float(band["stitch_rectangle_xy_mm"][2][1])]
        neighbor = [
            float(bands[next_band - 1]["stitch_rectangle_xy_mm"][2][1])
        ]
        _insert_pair(
            pairs,
            claimed,
            f"BAND-{index + 1}.right",
            f"BAND-{next_band}.left",
            side,
            neighbor,
            "band_vertical_side_join",
            "new_synthetic_vertical_band_edge",
        )


def _upper_band_seams(lower, upper, pairs, claimed):
    for index, panel in enumerate(upper["upper_gore_pieces"]):
        band = lower["outer_quarter_bands"][index]
        if (
            panel["id"] != f"UPPER-{index + 1}"
            or panel["paired_lower_band"] != band["id"]
            or panel["bottom_source_ring_edge_indices"]
            != band["source_ring_edge_indices"]
        ):
            raise ValueError("upper panel broke true-indexed lower band relationship")
        _insert_pair(
            pairs,
            claimed,
            f"BAND-{index + 1}.top",
            f"UPPER-{index + 1}.bottom",
            _station_segments(band["stitch_bottom_station_x_mm"]),
            _open_segments(panel["bottom_stitch_xy_mm"]),
            "lower_band_to_upper_gore",
            f"source_yoke_outer_surrogate_indexed_16_{index + 1}",
        )
        neighbor = (index + 1) % 4 + 1
        _insert_pair(
            pairs,
            claimed,
            f"UPPER-{index + 1}.right",
            f"UPPER-{neighbor}.left",
            _open_segments(panel["right_stitch_xy_mm"]),
            _open_segments(
                upper["upper_gore_pieces"][neighbor - 1]["left_stitch_xy_mm"]
            ),
            "upper_gore_vertical_side_join",
            "new_synthetic_six_stations_five_intervals",
        )


def _cap_seams(upper, pairs, claimed):
    cap = upper["research_top_cap"]
    source = _ring_segments(cap["stitch_ring_xy_mm"])
    if len(source) != 64:
        raise ValueError("source-informed top cap must contain exactly 64 edges")
    for index, panel in enumerate(upper["upper_gore_pieces"]):
        offset = index * 16
        if cap["quarter_source_surrogate_edge_indices"][index] != list(
            range(offset, offset + 16)
        ):
            raise ValueError("top cap source-informed edge IDs were reordered")
        _insert_pair(
            pairs,
            claimed,
            f"UPPER-{index + 1}.top",
            f"TOP-CAP-TRIAL.quarter-{index + 1}",
            _open_segments(panel["upper_stitch_xy_mm"]),
            source[offset : offset + 16],
            "upper_to_research_head_cap",
            f"synthetic_top_cap_16_indices_{index + 1}",
        )


def _one_research_component(pieces, pairs):
    nodes = {item["id"] for item in pieces}
    adjacency = {name: set() for name in nodes}
    for edge in pairs:
        a, b = edge["first"].split(".")[0], edge["second"].split(".")[0]
        if a not in nodes or b not in nodes:
            raise ValueError("sewing interface refers to an unknown actual paper piece")
        adjacency[a].add(b)
        adjacency[b].add(a)
    seen, queue = set(), deque(["YOKE-01"])
    while queue:
        node = queue.popleft()
        if node not in seen:
            seen.add(node)
            queue.extend(adjacency[node] - seen)
    if seen != nodes:
        raise ValueError("eighteen research pieces do not form a connected graph")
    return True


def _assembly_stages():
    return [
        {
            "step": 1,
            "operation": "print_and_check_9_A4_100_percent_scale",
            "required_evidence": "all_sheets_show_10x10mm_calibration",
        },
        {"step": 2, "operation": "close_four_leg_sleeves"},
        {"step": 3, "operation": "join_four_FLAT_research_soles"},
        {"step": 4, "operation": "sew_four_leg_sleeves_to_YOKE_source_hoof_holes"},
        {"step": 5, "operation": "join_four_lower_outer_band_side_edges"},
        {
            "step": 6,
            "operation": "join_YOKE_outer_to_four_BAND_bottoms",
            "warning": "leave_42_49mm_research_return_gap_on_BAND_3",
        },
        {"step": 7, "operation": "join_each_BAND_top_to_UPPER_bottom"},
        {"step": 8, "operation": "join_four_upper_gore_side_seams"},
        {"step": 9, "operation": "join_TOP_CAP_TRIAL_to_four_UPPER_top_arcs"},
        {
            "step": 10,
            "operation": "PHYSICAL_TEST_REQUIRED_turn_stuff_and_close_gap",
            "complete": False,
        },
    ]


def build_stage6_research_assembly(lower, upper):
    """One connected 18-piece *research* sewing graph with 32 paired interfaces."""
    low = inspect_source_lower_toile(lower)
    high = audit_source_profile_upper_mother(upper, lower)
    if (
        low["factory_patterns_approved"] != 0
        or high["factory_cutting_approved"] != 0
        or not high["all_12_new_sewing_relations_matched_in_2d"]
        or not high["source_3d_meridian_lengths_not_preserved"]
    ):
        raise ValueError("unapproved full-body surrogate or source discrepancy")
    pairs, seen = [], set()
    _hoof_seams(lower, pairs, seen)
    _outer_band_seams(lower, pairs, seen)
    _upper_band_seams(lower, upper, pairs, seen)
    _cap_seams(upper, pairs, seen)
    inventory = _part_inventory()
    if len(inventory) != 18 or len(pairs) != 32 or len(seen) != 64:
        raise ValueError("full research assembly lost a sewing relation")
    _one_research_component(inventory, pairs)
    if not all(pair["max_segment_disagreement_mm"] <= TOLERANCE_MM for pair in pairs):
        raise ValueError("unmatched research 2D netline")
    return {
        "schema": SCHEMA,
        "source_public_stage6_blend_sha256": SOURCE_SHA,
        "provenance": "four_real_source_hoof_rings_plus_new_18piece_research_surrogate",
        "units": "mm",
        "stitch_tolerance_mm": TOLERANCE_MM,
        "all_pieces": inventory,
        "paired_stitch_interfaces": pairs,
        "print_sheet_count": 9,
        "total_research_pieces": 18,
        "paired_interface_count": 32,
        "source_original_hoof_edge_count": 2048,
        "source_hole_roles": list(ROLES),
        "assembly_is_one_connected_piece_graph": True,
        "assembly_stages": _assembly_stages(),
        "draft_turning_gap_mm": low["proposed_return_gap_mm"],
        "critical_original_source_neck_center_jump_mm": high[
            "original_stage6_source_cross_section_center_jump_mm"
        ],
        "original_3d_meridian_vs_surrogate_2d_mismatch_mm": high[
            "original_source_surrogate_meridian_length_mismatch_mm"
        ],
        "flat_sole_is_NOT_original_rounded_hoof": True,
        "upper_four_gore_shape_is_NOT_original_stage6_head_neck": True,
        "ears_clouds_tail_face_drops_straps_NOT_attached": True,
        "fabric_thickness_grain_stretch_and_stuffing_NOT_tested": True,
        "digitally_matched_netlines_are_NOT_wearable_or_factory_certificate": True,
        "physical_toile_produced": False,
        "factory_cut_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
    }
