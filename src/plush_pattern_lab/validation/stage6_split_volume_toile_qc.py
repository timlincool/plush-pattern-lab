"""Independent numerical stitch audit for the two disconnected anatomy trials.

Matched planar boundary lengths are not a source-sculpt fit or fabric approval.
"""

from __future__ import annotations

import numpy as np
from shapely.geometry import Polygon

QUARTER = 16


def _steps(pts, *, ring=False):
    p = np.asarray(pts, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 2 or not np.isfinite(p).all():
        raise ValueError("nonfinite or malformed 2D stitch source coordinates")
    if ring:
        p = np.vstack((p, p[0]))
    if len(p) < 2:
        raise ValueError("source indexed stitch line is empty")
    return np.linalg.norm(np.diff(p, axis=0), axis=1)


def _band_to_torso(lower, trial, tolerance):
    pairs = []
    for i, row in enumerate(trial["torso_gore_pieces"]):
        band = lower["outer_quarter_bands"][i]
        if row["id"] != f"TORSO-{i + 1}":
            raise ValueError("body mother source panel ID sequence changed")
        if row["source_surrogate_16_ring_edge_ids"] != band["source_ring_edge_indices"]:
            raise ValueError("original four-quarters lower hoof yoke ring changed")
        actual = _steps(row["lower_stitch_xy_mm"])
        expected = np.diff(np.asarray(band["stitch_bottom_station_x_mm"]))
        if actual.shape != (16,) or np.max(np.abs(actual - expected)) > tolerance:
            raise ValueError("real-source lower BAND upper edge does not fit torso lower")
        pairs.append(
            {"pair": f"BAND-{i + 1}.top :: TORSO-{i + 1}.bottom",
             "mm": float(actual.sum()),
             "max_segment_difference_mm": float(np.max(np.abs(actual - expected)))}
        )
    return pairs


def _four_gore_sides(trial, role, tolerance):
    pieces = trial["torso_gore_pieces"] if role == "TORSO" else trial["headneck_gore_pieces"]
    rows = []
    for i in range(4):
        right = _steps(pieces[i]["right_stitch_xy_mm"])
        left = _steps(pieces[(i + 1) % 4]["left_stitch_xy_mm"])
        if right.shape != left.shape or np.max(np.abs(right - left)) > tolerance:
            raise ValueError("body/head seam meridian cannot be sewn segment by segment")
        rows.append(
            {"pair": f"{role}-{i + 1}.right :: {role}-{(i + 1) % 4 + 1}.left",
             "mm": float(right.sum()),
             "indexed_segment_max_error_mm": float(np.max(np.abs(right - left)))}
        )
    return rows


def _cap_quarters(trial, role, cap, field, tolerance):
    ring = _steps(cap["outer_stitch_xy_mm"], ring=True)
    if ring.shape != (64,):
        raise ValueError("cannot stitch a cap without 64 indexed surrogate edges")
    pieces = trial["torso_gore_pieces"] if role == "TORSO" else trial["headneck_gore_pieces"]
    result = []
    for i, piece in enumerate(pieces):
        actual = _steps(piece[field])
        expected = ring[i * QUARTER : (i + 1) * QUARTER]
        if actual.shape != (QUARTER,) or np.max(np.abs(actual - expected)) > tolerance:
            raise ValueError("cap has no exact matching 16-edge mother stitch")
        result.append(
            {"pair": f"{piece['id']}.{field} :: {cap['id']}.quarter-{i + 1}",
             "length_mm": float(actual.sum()),
             "indexed_max_error_mm": float(np.max(np.abs(actual - expected)))}
        )
    return result


def _allowance_and_topology(trial, allowance):
    shoulder = trial["shoulder_cap"]
    outer = Polygon(shoulder["outer_stitch_xy_mm"])
    cut = Polygon(
        shoulder["cut_outer_xy_mm"], shoulder["cut_inner_holes_xy_mm"]
    )
    guide = Polygon(trial["neck_source_inspired_guide"]["ring_xy_mm"])
    if not outer.is_valid or not cut.is_valid or not cut.covers(outer.exterior):
        raise ValueError("invalid source-inspired shoulder cap cutting geometry")
    if not guide.is_valid or guide.area <= 30:
        raise ValueError("source neck port is not a valid simple stitch ring")
    if not outer.contains(guide):
        raise ValueError("neck root crosses torso cap outer sewing boundary")
    distance = float(outer.exterior.distance(guide))
    expected_holes = int(trial["name"].startswith("B_"))
    if len(shoulder["cut_inner_holes_xy_mm"]) != expected_holes:
        raise ValueError("closed shoulder vs open port A/B topology changed")
    if distance < (2 * allowance + 0.7 if expected_holes else allowance + 0.7):
        raise ValueError("neck port and shoulder cannot accommodate sewing allowances")
    return {
        "source_inspired_shoulder_cap_to_neck_root_2d_clearance_mm": distance,
        "inside_2d_sewing_ring_count": expected_holes,
        "closed_separate_option_vs_open_integrated_option_checked": True,
    }


def _neck_join(trial, tolerance):
    guide = _steps(trial["neck_source_inspired_guide"]["ring_xy_mm"], ring=True)
    root = np.concatenate([
        _steps(part["lower_stitch_xy_mm"]) for part in trial["headneck_gore_pieces"]
    ])
    if guide.shape != (64,) or root.shape != (64,):
        raise ValueError("head-neck root must retain 64 indexed source-inspired arcs")
    if float(np.max(np.abs(root - guide))) > tolerance:
        raise ValueError("neck panel bases do not match an actual source-inspired guide")
    shared = {
        "headneck_root_and_shoulder_guide_mm": float(guide.sum()),
        "maximum_segment_difference_mm": float(np.max(np.abs(root - guide))),
    }
    if trial["name"].startswith("A_"):
        closed = trial["head_bottom_cap_if_separate"]
        if closed is None or trial["neck_collar_if_integrated"] is not None:
            raise ValueError("separately stuffed head bottom should be closed")
        other = _steps(closed["outer_stitch_xy_mm"], ring=True)
        if len(closed["cut_inner_holes_xy_mm"]) or max(abs(guide - other)) > tolerance:
            raise ValueError("head closure disk doesn't match 64 root edges")
        shared["stitch_method"] = "external_hand_ladder_stitch_to_solid_shoulder_mark"
        shared["surface_join_is_not_a_cut_edge_seam_certified"] = True
    else:
        collar = trial["neck_collar_if_integrated"]
        if collar is None or trial["head_bottom_cap_if_separate"] is not None:
            raise ValueError("open neck port must use the 10mm collar sleeve")
        stations = np.diff(np.asarray(collar["lower_and_upper_stitch_station_x_mm"]))
        if stations.shape != (64,) or np.max(abs(stations - guide)) > tolerance:
            raise ValueError("collar has an unequal 64 segment seam")
        if abs(collar["height_mm"] - 10) > tolerance:
            raise ValueError("wrong physical offset between shoulder and neck root")
        shared["stitch_method"] = "cut_shoulder_hole_to_collar_to_headneck_root"
        shared["neck_opening_still_requires_physical_turning_test"] = True
    return shared


def audit_separated_stage6_toile(lower, study, *, tolerance_mm=1e-4):
    if (
        study.get("schema") != "stage6-separated-torso-headneck-mother-trial-ab-v1"
        or study.get("factory_cutting_patterns_approved") != 0
        or lower.get("schema") != "stage6-source-hoof-anchored-lower-mother-toile-v1"
        or lower.get("source_hoof_open_edges") != 2048
        or len(study.get("options", [])) != 2
        or not 0 < tolerance_mm <= 0.001
    ):
        raise ValueError("invalid signed research source or unauthorized factory status")
    results = []
    for trial in study["options"]:
        if (
            trial["new_plus_existing_research_pieces"] != 24
            or trial["new_pattern_pieces"] != 11
            or trial["industrial_cut_patterns_approved"] != 0
            or len(trial["torso_gore_pieces"]) != 4
            or len(trial["headneck_gore_pieces"]) != 4
        ):
            raise ValueError("head / torso separated research piece inventory changed")
        for row in (*trial["torso_gore_pieces"], *trial["headneck_gore_pieces"]):
            seam, cut = Polygon(row["stitch_polygon_xy_mm"]), Polygon(
                row["cut_polygon_xy_mm"]
            )
            if not seam.is_valid or not cut.is_valid or not cut.covers(seam):
                raise ValueError("some 2D research gore is self-crossed or clipped")
        band = _band_to_torso(lower, trial, tolerance_mm)
        torso_sides = _four_gore_sides(trial, "TORSO", tolerance_mm)
        head_sides = _four_gore_sides(trial, "HEADNECK", tolerance_mm)
        shoulder = _cap_quarters(
            trial, "TORSO", trial["shoulder_cap"], "upper_stitch_xy_mm", tolerance_mm
        )
        top = _cap_quarters(
            trial, "HEADNECK", trial["head_top_cap"], "upper_stitch_xy_mm", tolerance_mm
        )
        port = _allowance_and_topology(
            trial, float(lower["material_seam_allowance_is_unverified_mm"])
        )
        neck = _neck_join(trial, tolerance_mm)
        if trial["name"].startswith("A_"):
            if not neck["surface_join_is_not_a_cut_edge_seam_certified"]:
                raise ValueError("unvalidated external head attachment must remain flagged")
        elif not neck["neck_opening_still_requires_physical_turning_test"]:
            raise ValueError("internal collar assembly cannot assert stuffing success")
        else:
            pass
        results.append(
            {
                "candidate": trial["name"],
                "lower_band_to_torso_pairs": band,
                "torso_gore_vertical_pairs": torso_sides,
                "headneck_gore_vertical_pairs": head_sides,
                "torso_gore_to_shoulder_cap_pairs": shoulder,
                "headneck_gore_to_top_cap_pairs": top,
                "neck_connection": neck,
                "shoulder_port_2d_clearance": port,
                "sewing_relations_checked": 21,
                "all_new_mathematical_seam_lengths_paired": True,
                "surrogate_3d_source_gore_lengths_and_head_shape_not_approved": True,
                "source_root_polygon_repositioned_and_rescaled": True,
                "physical_fabric_sewing_test_completed": False,
                "industrial_cutting_approved": 0,
            }
        )
    if [row["candidate"] for row in results] != [
        "A_separate_stuffed_head", "B_integrated_neck_port"
    ]:
        raise ValueError("independent head and integrated neck variants must both exist")
    return {
        "schema": "stage6-two-anatomic-volumes-stitch-and-port-qc-v1",
        "two_distinct_manufacturing_trial_variants": results,
        "real_original_source_four_hoofs_unmodified": True,
        "old_lower_13_pieces_preserved": True,
        "upper_source_envelope_not_fitted": True,
        "original_face_ear_cloud_tail_drop_mounts_unresolved": True,
        "all_actual_material_or_stuffing_validation_missing": True,
        "approved_industrial_patterns": 0,
    }
