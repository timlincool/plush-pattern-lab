"""Independent length, hole topology, allowance and opening QA for lower toile.

A geometrically valid half-toile is not a finished character or a material
certificate. The projected original hoof rims are NOT source torso seams.
"""

from __future__ import annotations

import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union

ORDER = ("FL", "FR", "RL", "RR")
EXPECTED_SOURCE_HOOF_PERIMETERS_MM = {
    "FL": 101.640317,
    "FR": 93.309140,
    "RL": 119.100288,
    "RR": 119.100290,
}


def _ring_edges(points):
    array = np.asarray(points, dtype=np.float64)
    if array.ndim != 2 or array.shape[1] != 2 or len(array) < 12:
        raise ValueError("research stitched hoof ring is malformed")
    if not np.isfinite(array).all():
        raise ValueError("nonfinite 2D source stitch points")
    return np.linalg.norm(array - np.roll(array, -1, axis=0), axis=1)


def _hoof_pairs(spec, tolerance_mm):
    rows = []
    ids = set()
    for label in ORDER:
        p = spec["original_source_hoofs"][label]
        edge = _ring_edges(p["source_stitch_ring_xy_mm"])
        stations = np.asarray(p["sleeve_stitch_station_x_mm"], dtype=float)
        source = p["source_vertex_ids"]
        if len(source) != 512 or len(set(source)) != 512:
            raise ValueError("original 512-edge hoop identities were not preserved")
        if set(source) & ids:
            raise ValueError("original four hoof source vertex rings overlap")
        ids.update(source)
        if stations.shape != (513,) or not np.isfinite(stations).all():
            raise ValueError("missing source-indexed upper/lower sleeve stitch stations")
        error = float(np.max(np.abs(np.diff(stations) - edge)))
        mismatch = abs(float(edge.sum()) - p["source_original_hoof_perimeter_mm"])
        mismatch += abs(float(stations[-1] - stations[0]) - float(edge.sum()))
        if error > tolerance_mm or mismatch > tolerance_mm:
            raise ValueError("real source 3D hoof boundary and sleeve stitches diverged")
        target = EXPECTED_SOURCE_HOOF_PERIMETERS_MM[label]
        if abs(float(edge.sum()) - target) > 0.003:
            raise ValueError("original real Stage6 source hoof perimeter changed")
        rows.append(
            {
                "hoof": label,
                "source_edge_ids_count": len(source),
                "source_3d_ring_perimeter_mm": p["source_original_hoof_perimeter_mm"],
                "yoke_to_sleeve_and_sole_top_bottom_step_error_mm": error,
                "toe_cap_is_a_synthetic_flat_test_piece": True,
            }
        )
    return rows


def _yoke_holes(spec, allowance):
    yoke = spec["yoke"]
    outer = Polygon(yoke["outer_stitch_xy_mm"])
    holes = {
        key: Polygon(spec["original_source_hoofs"][key]["source_stitch_ring_xy_mm"])
        for key in ORDER
    }
    cut_outer = Polygon(yoke["outer_cut_xy_mm"])
    cut_holes = [Polygon(data) for data in yoke["inner_cut_holes_xy_mm"]]
    if not outer.is_valid or not cut_outer.is_valid or len(cut_holes) != 4:
        raise ValueError("non-simple lower mother outer/cut boundaries")
    if any(not p.is_valid or p.is_empty for p in (*holes.values(), *cut_holes)):
        raise ValueError("invalid source hoof stitch hole or allowance inset")
    if not cut_outer.contains(outer):
        raise ValueError("cut must enclose full outside yoke stitch seam")
    if not all(holes[key].covers(cut_holes[i]) for i, key in enumerate(ORDER)):
        raise ValueError("four source hoop cut holes are not inset toward the hole")
    if any(outer.exterior.distance(hole) <= 2 * allowance for hole in holes.values()):
        raise ValueError("insufficient belly bridge between source hoof and outer stitch")
    cut = cut_outer.difference(unary_union(cut_holes))
    if not cut.is_valid or cut.geom_type != "Polygon" or len(cut.interiors) != 4:
        raise ValueError("lower yoke cut must contain exactly four real source holes")
    return outer, holes, cut


def _outer_band_pairs(spec, outer, tolerance):
    points = np.asarray(spec["yoke"]["outer_stitch_xy_mm"], dtype=np.float64)
    steps = _ring_edges(points)
    bands = spec["outer_quarter_bands"]
    if len(points) != 64 or len(bands) != 4:
        raise ValueError("expected four bounded quarter-band interfaces")
    results = []
    used = []
    for i, band in enumerate(bands):
        if band["id"] != f"BAND-{i + 1}":
            raise ValueError("wrong 2D outer band assembly order")
        expected_ids = list(range(i * 16, (i + 1) * 16))
        if band["source_ring_edge_indices"] != expected_ids:
            raise ValueError("yoke outer seam panel markers were reordered")
        stations = np.asarray(band["stitch_bottom_station_x_mm"], dtype=np.float64)
        if stations.shape != (17,) or not np.isfinite(stations).all():
            raise ValueError("unmatched source-linked outer band seam stations")
        error = float(np.max(np.abs(np.diff(stations) - steps[expected_ids])))
        if error > tolerance:
            raise ValueError("yoke outer and lower band stitch segment lengths disagree")
        used.extend(expected_ids)
        if not band["open_upper_edge_not_paired_to_body"]:
            raise ValueError("cannot claim finished outer torso shell")
        results.append(
            {
                "band": band["id"],
                "source_outer_stitch_edges": len(expected_ids),
                "yoke_to_band_stitch_mm": float(steps[expected_ids].sum()),
                "maximum_segment_length_mismatch_mm": error,
            }
        )
    if sorted(used) != list(range(64)):
        raise ValueError("not all original mother yoke outer edges have a partner")
    if abs(sum(b["yoke_to_band_stitch_mm"] for b in results) - outer.length) > tolerance:
        raise ValueError("unpaired new outer yoke circumference")
    return results


def inspect_source_lower_toile(spec, *, tolerance_mm=1e-4):
    if (
        spec.get("schema") != "stage6-source-hoof-anchored-lower-mother-toile-v1"
        or spec.get("status")
        != "GEOMETRIC_TEST_TOILE_NOT_APPROVED_STAGE6_CUTTING_PATTERN"
        or spec.get("piece_count") != 13
        or spec.get("source_hoof_open_edges") != 2048
        or spec.get("source_hoof_boundary_z_mm") != 20
        or spec.get("approved_industrial_paper_patterns") != 0
    ):
        raise ValueError("untrusted original source-anchored lower-toile contract")
    allowance = float(spec["material_seam_allowance_is_unverified_mm"])
    if not 3 <= allowance <= 8 or not 0 < tolerance_mm <= 0.001:
        raise ValueError("invalid stitch margin or test epsilon")
    hoofs = _hoof_pairs(spec, tolerance_mm)
    outer, _, cut = _yoke_holes(spec, allowance)
    bands = _outer_band_pairs(spec, outer, tolerance_mm)
    turning = spec["turning_gap_research"]
    if turning["band_id"] != "BAND-3" or turning[
        "bottom_band_seam_interval_fraction"
    ] != [0.35, 0.65]:
        raise ValueError("unrecognized source-notched provisional turning opening")
    turning_mm = bands[2]["yoke_to_band_stitch_mm"] * 0.30
    if turning_mm < 25:
        raise ValueError("trial return opening too narrow to handle safely")
    if not (
        spec["new_ventral_yoke_is_not_original_body_surface"]
        and spec["real_hoof_base_3d_mesh_not_flattened"]
        and spec["head_neck_upper_body_ears_tail_clouds_not_connected"]
    ):
        raise ValueError("mother shell trial overstates true Stage6 manufacturing")
    return {
        "schema": "stage6-lower-mother-toile-seam-audit-v1",
        "source_hoofs": hoofs,
        "outer_quarter_bands": bands,
        "four_original_source_hoof_rings_and_all_2048_source_edges_preserved": True,
        "four_source_hoofs_to_sleeve_to_flat_test_sole_paired_per_segment": True,
        "all_64_new_outer_yoke_edges_pair_with_four_printable_bands": True,
        "outer_band_vertical_stitches_geometrically_equal_height": True,
        "sleeve_side_stitches_geometrically_equal_height": True,
        "proposed_return_gap_mm": turning_mm,
        "yoke_four_hole_cut_area_mm2": cut.area,
        "unpaired_upper_band_edges": 4,
        "real_source_hoof_source_plane_z_mm": 20,
        "new_yoke_is_relocated_hypothesis_z_mm": 60,
        "full_character_or_3d_body_silhouette_matched": False,
        "real_hoof_cap_flattening_validated": False,
        "physical_fabric_and_material_tested": False,
        "factory_patterns_approved": 0,
    }
