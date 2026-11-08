"""Independent upper-lower net-stitch pairing and anatomical-mismatch audit.

Numerical matching on a newly designed panel does not verify plush shape,
material relaxation, neck construction or embroidery positioning.
"""

from __future__ import annotations

import numpy as np
from shapely.geometry import Polygon

BAND_EDGES = 16
PANELS = 4
BOUNDED_NUMERIC_MM = 1e-4


def _distance_steps(value):
    p = np.asarray(value, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 2 or len(p) < 2:
        raise ValueError("missing finite explicit planar net-stitch polyline")
    if not np.isfinite(p).all():
        raise ValueError("nonfinite sewing stitch coordinates")
    return np.linalg.norm(np.diff(p, axis=0), axis=1)


def _body_interface(lower, upper, epsilon):
    rows = []
    for index, panel in enumerate(upper["upper_gore_pieces"]):
        base = lower["outer_quarter_bands"][index]
        if panel["id"] != f"UPPER-{index + 1}":
            raise ValueError("upper panel order does not match lower true-hoof band")
        if panel["paired_lower_band"] != base["id"]:
            raise ValueError("source band 16-edge identity changed")
        if panel["bottom_source_ring_edge_indices"] != base["source_ring_edge_indices"]:
            raise ValueError("source yoke segment IDs are not paired")
        expected = np.diff(np.asarray(base["stitch_bottom_station_x_mm"], dtype=float))
        observed = _distance_steps(panel["bottom_stitch_xy_mm"])
        if len(expected) != BAND_EDGES or len(observed) != BAND_EDGES:
            raise ValueError("source band/gore lower edge must have 16 parts")
        error = float(np.max(np.abs(expected - observed)))
        if error > epsilon:
            raise ValueError("band top edge has no exact paired upper-gore seam")
        rows.append(
            {
                "sewing_pair": f"BAND-{index + 1}.upper -> UPPER-{index + 1}.bottom",
                "source_lower_band_edge_indices": base["source_ring_edge_indices"],
                "max_net_stitch_segment_mismatch_mm": error,
                "paired_net_stitch_mm": float(observed.sum()),
            }
        )
    return rows


def _side_seams(upper, epsilon):
    pieces = upper["upper_gore_pieces"]
    expected = np.asarray(upper["common_panel_side_step_lengths_mm"], dtype=np.float64)
    rows = []
    for index in range(PANELS):
        right = _distance_steps(pieces[index]["right_stitch_xy_mm"])
        left = _distance_steps(pieces[(index + 1) % PANELS]["left_stitch_xy_mm"])
        if right.shape != (5,) or left.shape != (5,):
            raise ValueError("upper surrogate must have five indexed side sections")
        mismatch = float(np.max(np.abs(right - left)))
        source_error = float(
            max(np.max(np.abs(right - expected)), np.max(np.abs(left - expected)))
        )
        if mismatch > epsilon or source_error > epsilon:
            raise ValueError("new upper side seam is not paired segment by segment")
        rows.append(
            {
                "sewing_pair": f"UPPER-{index + 1}.right -> UPPER-{(index + 1) % PANELS + 1}.left",
                "shared_side_stitch_mm": float(right.sum()),
                "independent_2d_side_length_step_mismatch_mm": mismatch,
            }
        )
    return rows


def _cap(upper, epsilon):
    cap = upper["research_top_cap"]
    points = np.asarray(cap["stitch_ring_xy_mm"], dtype=np.float64)
    if points.shape != (64, 2):
        raise ValueError("unexpected top cap source-informed 64-edge seam")
    poly = Polygon(points)
    cut = Polygon(cap["cut_outline_xy_mm"])
    if not poly.is_valid or not cut.is_valid or not cut.covers(poly):
        raise ValueError("cap net stitch or allowance is not a valid fabric polygon")
    edge = np.linalg.norm(points - np.roll(points, -1, axis=0), axis=1)
    result = []
    for index, piece in enumerate(upper["upper_gore_pieces"]):
        ids = list(range(index * BAND_EDGES, (index + 1) * BAND_EDGES))
        if ids != cap["quarter_source_surrogate_edge_indices"][index]:
            raise ValueError("top cap 16-edge source-surrogate index reordering")
        boundary = _distance_steps(piece["upper_stitch_xy_mm"])
        if len(boundary) != BAND_EDGES:
            raise ValueError("top cap stitch pairing lost an edge")
        mismatch = float(np.max(np.abs(edge[ids] - boundary)))
        if mismatch > epsilon:
            raise ValueError("upper gore does not match the head top cap")
        result.append(
            {
                "sewing_pair": f"UPPER-{index + 1}.top -> TOP-CAP-TRIAL.edges-{ids[0]}..{ids[-1]}",
                "stitch_mm": float(edge[ids].sum()),
                "maximum_indexed_net_stitch_mismatch_mm": mismatch,
            }
        )
    return result


def audit_source_profile_upper_mother(upper, lower, *, tolerance=BOUNDED_NUMERIC_MM):
    if (
        upper.get("schema") != "stage6-source-profile-informed-upper-mother-toile-v1"
        or upper.get("status")
        != "NEW_4_GORE_AND_CAP_RESEARCH_NOT_ORIGINAL_SCULPT_PATTERN"
        or lower.get("schema") != "stage6-source-hoof-anchored-lower-mother-toile-v1"
        or upper.get("industrial_cut_patterns_approved") != 0
        or upper.get("new_upper_piece_count") != 5
        or upper.get("total_research_stitch_pieces") != 18
    ):
        raise ValueError("wrong source-linked upper-mother research version")
    if not 0 < tolerance <= 0.001:
        raise ValueError("numeric seam check must not be misrepresented as fabric")
    if len(upper.get("upper_gore_pieces", [])) != 4:
        raise ValueError("four formerly open band edges require four upper gores")
    if not upper["lower_13_piece_source_hoof_layout_preserved"]:
        raise ValueError("original source hoof identity must not change")
    for piece in upper["upper_gore_pieces"]:
        seam = Polygon(piece["stitch_outline_xy_mm"])
        cut = Polygon(piece["cut_outline_xy_mm"])
        if (
            not seam.is_valid
            or not cut.is_valid
            or seam.area <= 100
            or not cut.covers(seam)
        ):
            raise ValueError("upper body piece or allowance cannot be sewn flat")
    band = _body_interface(lower, upper, tolerance)
    side = _side_seams(upper, tolerance)
    top = _cap(upper, tolerance)
    jump = upper["max_source_observed_profile_center_step_mm"]
    misfit = upper["surrogate_meridian_3d_vs_2d"][
        "max_3d_surrogate_meridian_chord_minus_2d_seam_mm"
    ]
    if not np.isfinite([jump, misfit]).all():
        raise ValueError("missing numeric original source profile diagnostics")
    return {
        "schema": "stage6-upper-mother-source-band-and-cap-pairing-qa-v1",
        "four_real_lower_band_to_upper_source_stitch_relations": band,
        "four_independent_new_upper_side_seam_relations": side,
        "four_top_cap_indexed_16_edge_stitch_relations": top,
        "all_12_new_sewing_relations_matched_in_2d": True,
        "new_printable_upper_gore_count": 4,
        "new_printable_upper_cap_count": 1,
        "combined_research_piece_count": 18,
        "original_stage6_source_cross_section_center_jump_mm": jump,
        "neck_split_or_anatomical_articulation_review_required": jump > 50,
        "original_source_surrogate_meridian_length_mismatch_mm": misfit,
        "source_3d_meridian_lengths_not_preserved": True,
        "original_actual_3d_sculpt_stitch_curves_not_extracted": True,
        "actual_source_body_silhouette_not_certified": True,
        "source_hoof_real_3d_soles_still_not_flattened": True,
        "real_fabric_and_stuffing_tested": False,
        "cloud_face_ears_tail_and_drop_parts_assembled": False,
        "paper_pattern_form_closed_only_in_new_surrogate": True,
        "turning_ability_and_physical_stability_proved": False,
        "factory_cutting_approved": 0,
    }
