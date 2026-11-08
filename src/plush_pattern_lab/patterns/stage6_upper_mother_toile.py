"""Four upper torso trial gores and a cap, joined to the real-hoof lower toile.

The original Stage6 source supplies only cross-section *observations*.
The proposed torso loft and its planar stitch geometry are newly designed.
"""

from __future__ import annotations

import numpy as np
from shapely.geometry import Polygon

PROFILE_Z_MM = (100.0, 130.0, 155.0, 180.0, 205.0, 230.0)
SOURCE_SLICE_HALF_WIDTH_MM = 3.0
SOURCE_QUANTILES = (0.01, 0.99)
UPPER_PANEL_COUNT = 4
STITCH_EDGES_PER_BAND = 16


def _source_profile(source_xyz, ring):
    xyz = np.asarray(source_xyz, dtype=np.float64)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or not np.isfinite(xyz).all():
        raise ValueError("source Stage6 proxy must be finite 3D millimetres")
    base_lo, base_hi = ring.min(axis=0), ring.max(axis=0)
    extent = base_hi - base_lo
    if np.any(extent <= 1.0):
        raise ValueError("invalid original lower-mother outer source ring")
    base_center = (base_hi + base_lo) / 2
    rows = []
    profiles = [ring.copy()]
    for z_mm in PROFILE_Z_MM[1:]:
        sample = xyz[np.abs(xyz[:, 2] - z_mm) <= SOURCE_SLICE_HALF_WIDTH_MM]
        if len(sample) < 100:
            raise ValueError("missing original Stage6 upper body/head source slice")
        lo, hi = np.quantile(sample[:, :2], SOURCE_QUANTILES, axis=0)
        if np.any(hi - lo <= 2):
            raise ValueError("collapsed original source upper-body cross section")
        center = (lo + hi) / 2
        proposal = (ring - base_center) * ((hi - lo) / extent) + center
        if not Polygon(proposal).is_valid:
            raise ValueError("new cross-section proxy cannot form a single disk")
        profiles.append(proposal)
        rows.append(
            {
                "source_slab_z_mm": z_mm,
                "source_slab_half_window_mm": SOURCE_SLICE_HALF_WIDTH_MM,
                "source_vertex_count": len(sample),
                "source_1pct_99pct_bounds_xy_mm": [lo.tolist(), hi.tolist()],
                "source_envelope_center_xy_mm": center.tolist(),
                "proposed_one_ring_stitch_xy_mm": proposal.tolist(),
                "source_disconnected_components_not_checked": True,
            }
        )
    jump = [
        float(np.linalg.norm(np.diff(np.asarray([
            np.asarray(row["source_envelope_center_xy_mm"]) for row in rows
        ]), axis=0)[i]))
        for i in range(len(rows) - 1)
    ]
    return np.asarray(profiles), rows, jump


def _panel_arc(ring, index):
    start = index * STITCH_EDGES_PER_BAND
    ids = (np.arange(STITCH_EDGES_PER_BAND + 1) + start) % len(ring)
    points = ring[ids]
    steps = np.linalg.norm(np.diff(points, axis=0), axis=1)
    if np.any(steps <= 1e-8):
        raise ValueError("collapsed source-indexed torso band segment")
    return np.r_[0.0, np.cumsum(steps)], steps


def _ring_widths(rings):
    widths = []
    for row in rings:
        widths.append([_panel_arc(row, i)[0][-1] for i in range(UPPER_PANEL_COUNT)])
    return np.asarray(widths, dtype=np.float64)


def _balanced_seam_steps(widths):
    dz = np.diff(np.asarray(PROFILE_Z_MM))
    maximum_half_width_change = np.max(np.abs(np.diff(widths, axis=0)), axis=1) / 2
    return np.hypot(dz, maximum_half_width_change)


def _planar_panel(index, rings, side_segment_mm, seam_allowance_mm):
    stations = [_panel_arc(ring, index)[0] for ring in rings]
    widths = np.asarray([row[-1] for row in stations])
    dy = np.sqrt(
        np.maximum(side_segment_mm**2 - (np.diff(widths) / 2) ** 2, 0.0)
    )
    if np.any(dy <= 1e-5):
        raise ValueError("upper surrogate panel has collapsed meridian increment")
    longitudinal = np.r_[0.0, np.cumsum(dy)]
    left = np.column_stack((-widths / 2, longitudinal))
    right = np.column_stack((widths / 2, longitudinal))
    bottom = np.column_stack((stations[0] - widths[0] / 2, np.zeros(17)))
    upper = np.column_stack((stations[-1] - widths[-1] / 2, np.full(17, longitudinal[-1])))
    outline = np.vstack((bottom, right[1:], upper[-2::-1], left[-2:0:-1]))
    seam = Polygon(outline)
    if seam.geom_type != "Polygon" or not seam.is_valid or seam.area <= 100:
        raise ValueError("upper torso gore has invalid 2D stitch perimeter")
    cut = seam.buffer(seam_allowance_mm, quad_segs=12)
    if cut.geom_type != "Polygon" or not cut.is_valid:
        raise ValueError("upper mother gore allowance self-intersects")
    return {
        "id": f"UPPER-{index + 1}",
        "paired_lower_band": f"BAND-{index + 1}",
        "source_station_z_mm": list(PROFILE_Z_MM),
        "left_stitch_xy_mm": left.tolist(),
        "right_stitch_xy_mm": right.tolist(),
        "bottom_stitch_xy_mm": bottom.tolist(),
        "upper_stitch_xy_mm": upper.tolist(),
        "stitch_outline_xy_mm": np.asarray(seam.exterior.coords).tolist(),
        "cut_outline_xy_mm": np.asarray(cut.exterior.coords).tolist(),
        "station_horizontal_stitch_widths_mm": widths.tolist(),
        "bottom_source_ring_edge_indices": list(
            range(index * 16, (index + 1) * 16)
        ),
        "side_segment_design_lengths_mm": side_segment_mm.tolist(),
        "area_2d_net_mm2": float(seam.area),
        "source_original_surface_flattened": False,
    }


def _cap(ring, allowance):
    poly = Polygon(ring)
    if not poly.is_valid or poly.area <= 1:
        raise ValueError("upper source-informed research cap is invalid")
    cut = poly.buffer(allowance, quad_segs=12)
    if cut.geom_type != "Polygon" or not cut.is_valid:
        raise ValueError("upper cap cutting allowance invalid")
    return {
        "id": "TOP-CAP-TRIAL",
        "top_plane_z_mm": PROFILE_Z_MM[-1],
        "stitch_ring_xy_mm": ring.tolist(),
        "cut_outline_xy_mm": np.asarray(cut.exterior.coords).tolist(),
        "quarter_source_surrogate_edge_indices": [
            list(range(i * 16, (i + 1) * 16)) for i in range(4)
        ],
        "area_net_mm2": float(poly.area),
        "ears_and_hair_not_connected": True,
        "not_original_3d_source_head_cap": True,
    }


def _meridian_mismatch_mm(rings, design_segments):
    points = np.stack(
        [
            np.column_stack((ring, np.full(len(ring), z)))
            for ring, z in zip(rings, PROFILE_Z_MM)
        ]
    )
    source_chord = np.linalg.norm(
        np.diff(points[:, [0, 16, 32, 48]], axis=0), axis=2
    )
    return {
        "original_source_inspired_meridian_chord_mm": source_chord.tolist(),
        "new_2d_shared_meridian_step_mm": design_segments.tolist(),
        "max_3d_surrogate_meridian_chord_minus_2d_seam_mm": float(
            np.max(np.abs(source_chord - design_segments[:, None]))
        ),
        "3d_surrogate_meridians_not_preserved": True,
    }


def build_upper_mother_from_lower(lower, source_xyz):
    """Connect every lower open BAND top to one new upper gore plus a top cap."""
    if (
        lower.get("schema") != "stage6-source-hoof-anchored-lower-mother-toile-v1"
        or lower.get("approved_industrial_paper_patterns") != 0
        or lower.get("piece_count") != 13
        or lower.get("source_hoof_open_edges") != 2048
        or len(lower.get("outer_quarter_bands", [])) != 4
    ):
        raise ValueError("not the independently audited original-source lower toile")
    ring = np.asarray(lower["yoke"]["outer_stitch_xy_mm"], dtype=np.float64)
    if ring.shape != (64, 2) or not Polygon(ring).is_valid:
        raise ValueError("lower true-hoof yoke must have intact 64-edge outer ring")
    rings, source, jumps = _source_profile(source_xyz, ring)
    widths = _ring_widths(rings)
    segments = _balanced_seam_steps(widths)
    allowance = float(lower["material_seam_allowance_is_unverified_mm"])
    if not 3 <= allowance <= 8:
        raise ValueError("unsafe or unverified mother toile seam allowance")
    pieces = [
        _planar_panel(i, rings, segments, allowance) for i in range(4)
    ]
    cap = _cap(rings[-1], allowance)
    return {
        "schema": "stage6-source-profile-informed-upper-mother-toile-v1",
        "status": "NEW_4_GORE_AND_CAP_RESEARCH_NOT_ORIGINAL_SCULPT_PATTERN",
        "units": "mm",
        "lower_13_piece_source_hoof_layout_preserved": True,
        "source_proxy_used_only_as_envelope_reference": True,
        "source_profile_slab_measurements": source,
        "source_profile_z_mm": list(PROFILE_Z_MM),
        "original_lower_yoke_64_edge_stitch_ring_xy_mm": ring.tolist(),
        "source_3d_head_highest_vertex_z_mm": float(np.max(source_xyz[:, 2])),
        "max_source_observed_profile_center_step_mm": max(jumps),
        "source_profile_center_step_mm": jumps,
        "synthetic_stitch_rings_xy_mm": rings.tolist(),
        "common_panel_side_step_lengths_mm": segments.tolist(),
        "surrogate_meridian_3d_vs_2d": _meridian_mismatch_mm(rings, segments),
        "upper_gore_pieces": pieces,
        "research_top_cap": cap,
        "new_upper_piece_count": 5,
        "lower_existing_piece_count": 13,
        "total_research_stitch_pieces": 18,
        "four_lower_bands_upper_edges_pair_to_gore_lower_edges": True,
        "head_and_neck_needs_anatomical_split_review": True,
        "real_material_stretch_not_measured": True,
        "real_original_stage6_face_ears_cloud_tail_unconnected": True,
        "industrial_cut_patterns_approved": 0,
    }
