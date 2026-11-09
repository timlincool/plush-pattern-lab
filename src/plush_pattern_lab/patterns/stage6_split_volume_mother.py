"""Independent torso / front head-neck trial volumes from the real Stage6 source.

Not an intrinsic UV unwrap. Two proposed assemblies use original source
cross-section *envelopes*, not original seam edges or validated fabric physics.
"""

from __future__ import annotations

import numpy as np
from shapely.geometry import Polygon

BODY_HEIGHTS_MM = (100.0, 115.0, 125.0, 135.0)
HEAD_HEIGHTS_MM = (145.0, 155.0, 180.0, 205.0, 230.0)
SOURCE_SLAB_HALF_MM = 3.0
OPTIONS = (
    ("A_separate_stuffed_head", 0.74, 7.0),
    ("B_integrated_neck_port", 0.64, 13.0),
)
RING_VERTICES = 64
QUARTER = 16
PORT_CENTER_XY_MM = (0.0, -18.0)
FABRIC_ALLOWANCE_STUDY_MM = 6.0
NECK_CONNECTOR_HEIGHT_MM = 10.0


def _observed_ring(source, z, original_ring):
    points = source[np.abs(source[:, 2] - z) <= SOURCE_SLAB_HALF_MM]
    if len(points) < 100:
        raise ValueError("missing trusted original head or rear torso source slice")
    q = np.quantile(points[:, :2], (0.01, 0.99), axis=0)
    low, high = q[0], q[1]
    if np.any(high - low <= 2.0):
        raise ValueError("original source slice is degenerate")
    base_low, base_high = original_ring.min(axis=0), original_ring.max(axis=0)
    center = (base_high + base_low) / 2
    ring = (original_ring - center) * ((high - low) / (base_high - base_low))
    ring += (high + low) / 2
    if not Polygon(ring).is_valid:
        raise ValueError("source envelope ring is not a valid mother candidate")
    return ring, {
        "source_z_mm": z,
        "source_vertex_count": len(points),
        "source_xy_quantile01_99_mm": q.tolist(),
        "source_center_xy_mm": ((high + low) / 2).tolist(),
        "only_a_source_envelope_not_a_true_stage6_section_loop": True,
    }


def _arc(ring, i):
    ids = (np.arange(QUARTER + 1) + i * QUARTER) % RING_VERTICES
    pair = ring[ids]
    step = np.linalg.norm(np.diff(pair, axis=0), axis=1)
    if len(step) != QUARTER or np.any(step <= 1e-9):
        raise ValueError("degenerate indexed 16-edge trial ring quarter")
    return np.r_[0.0, np.cumsum(step)], step


def _meridian_steps(rings, heights):
    xyz = np.stack(
        [np.column_stack((ring, np.full(RING_VERTICES, z))) for ring, z in zip(rings, heights)]
    )
    main_3d = np.linalg.norm(
        np.diff(xyz[:, [0, 16, 32, 48]], axis=0), axis=2
    )
    widths = np.asarray(
        [[_arc(ring, i)[0][-1] for i in range(4)] for ring in rings]
    )
    half_width_shifts = np.abs(np.diff(widths, axis=0)) / 2
    steps = np.maximum(main_3d.max(axis=1), half_width_shifts.max(axis=1))
    steps += 0.2
    return steps, {
        "four_original_envelope_meridians_xyz_chord_mm": main_3d.tolist(),
        "max_source_envelope_corner_chord_minus_2d_meridian_step_mm": float(
            np.max(np.abs(main_3d - steps[:, None]))
        ),
        "source_slice_corners_are_not_original_stage6_cut_edge_chains": True,
    }


def _gore(rings, heights, steps, i, role, allowance):
    stations = [_arc(row, i)[0] for row in rings]
    widths = np.asarray([row[-1] for row in stations])
    side_dy = np.sqrt(steps**2 - (np.diff(widths) / 2) ** 2)
    if np.any(side_dy <= 1e-5):
        raise ValueError("synthetic torso/head gore meridian collapsed")
    y = np.r_[0.0, np.cumsum(side_dy)]
    left = np.column_stack((-widths / 2, y))
    right = np.column_stack((widths / 2, y))
    bottom = np.column_stack((stations[0] - widths[0] / 2, np.zeros(17)))
    top = np.column_stack((stations[-1] - widths[-1] / 2, np.full(17, y[-1])))
    polygon_points = np.vstack((bottom, right[1:], top[-2::-1], left[-2:0:-1]))
    seam = Polygon(polygon_points)
    cut = seam.buffer(allowance, quad_segs=8)
    if not seam.is_valid or seam.area < 80 or not cut.is_valid:
        raise ValueError("source-informed independent volume gore self-crosses")
    return {
        "id": f"{role}-{i + 1}",
        "source_stations_z_mm": list(heights),
        "source_surrogate_16_ring_edge_ids": list(range(i * 16, (i + 1) * 16)),
        "lower_stitch_xy_mm": bottom.tolist(),
        "upper_stitch_xy_mm": top.tolist(),
        "left_stitch_xy_mm": left.tolist(),
        "right_stitch_xy_mm": right.tolist(),
        "stitch_polygon_xy_mm": np.asarray(seam.exterior.coords).tolist(),
        "cut_polygon_xy_mm": np.asarray(cut.exterior.coords).tolist(),
        "source_surface_not_flattened": True,
    }


def _cap(ring, allowance, label, port=None):
    outer = Polygon(ring)
    if not outer.is_valid or outer.area <= 100:
        raise ValueError("invalid torso or head source-inspired cap")
    cut = outer.buffer(allowance, quad_segs=8)
    holes = []
    if port is not None:
        inside = Polygon(port).buffer(-allowance, quad_segs=8)
        if inside.is_empty or inside.geom_type != "Polygon":
            raise ValueError("neck port cutting allowance collapses")
        cut = cut.difference(inside)
        holes.append(port.tolist())
    if not cut.is_valid or cut.geom_type != "Polygon" or len(cut.interiors) != len(holes):
        raise ValueError("invalid standalone shoulder cap cutting perimeter")
    return {
        "id": label,
        "outer_stitch_xy_mm": ring.tolist(),
        "cut_outer_xy_mm": np.asarray(cut.exterior.coords).tolist(),
        "cut_inner_holes_xy_mm": [
            np.asarray(inner.coords).tolist() for inner in cut.interiors
        ],
        "upper_head_opening_stitch_xy_mm": holes,
        "original_mesh_source_cut_surface": False,
    }


def _guide_and_port(body_top, original_head_root, root_meta, scale, clearance):
    p = Polygon(body_top)
    source = np.asarray(original_head_root)
    raw_center = source.mean(axis=0)
    target = np.asarray(PORT_CENTER_XY_MM)
    port = (source - raw_center) * scale + target
    ring = Polygon(port)
    if not p.buffer(-clearance).contains(ring):
        raise ValueError("source-informed neck port violates shoulder seam clearance")
    distances = np.linalg.norm(port - source, axis=1)
    return port, {
        "original_source_head_root_z_mm": HEAD_HEIGHTS_MM[0],
        "actual_source_head_root_bounds_xy_mm": root_meta["source_xy_quantile01_99_mm"],
        "new_port_center_xy_mm": list(PORT_CENTER_XY_MM),
        "explicit_source_head_root_xy_scale": scale,
        "max_source_head_root_to_2d_port_vertex_xy_shift_mm": float(distances.max()),
        "mean_source_head_root_to_2d_port_vertex_xy_shift_mm": float(distances.mean()),
        "minimum_body_cap_boundary_to_port_mm": float(p.exterior.distance(ring)),
        "neck_port_matches_actual_source_root_geometry": False,
    }


def _surface_guide_length(ring):
    step = np.linalg.norm(ring - np.roll(ring, -1, axis=0), axis=1)
    return {
        "ring_xy_mm": ring.tolist(),
        "indexed_64_segment_mm": step.tolist(),
        "perimeter_mm": float(step.sum()),
    }


def _collar(guide, allowance):
    lengths = _surface_guide_length(guide)
    total = lengths["perimeter_mm"]
    return {
        "id": "COLLAR-TRIAL",
        "height_mm": NECK_CONNECTOR_HEIGHT_MM,
        "lower_and_upper_stitch_station_x_mm": np.r_[0.0, np.cumsum(lengths["indexed_64_segment_mm"])].tolist(),
        "cut_rectangle_xy_mm": [
            [-allowance, -allowance],
            [total + allowance, -allowance],
            [total + allowance, NECK_CONNECTOR_HEIGHT_MM + allowance],
            [-allowance, NECK_CONNECTOR_HEIGHT_MM + allowance],
        ],
        "must_be_sewn_into_tube_before_attachment": True,
    }


def _one_variant(source, old_lower_ring, body_profiles, body_rows, option):
    name, factor, clearance = option
    base, root_info = _observed_ring(source, HEAD_HEIGHTS_MM[0], old_lower_ring)
    port, mismatch = _guide_and_port(
        body_profiles[-1], base, root_info, factor, clearance
    )
    head_profiles = [port]
    head_source = [root_info]
    for z in HEAD_HEIGHTS_MM[1:]:
        ring, info = _observed_ring(source, z, old_lower_ring)
        head_profiles.append(ring)
        head_source.append(info)
    body_steps, body_3d = _meridian_steps(body_profiles, BODY_HEIGHTS_MM)
    head_steps, head_3d = _meridian_steps(head_profiles, HEAD_HEIGHTS_MM)
    allowance = FABRIC_ALLOWANCE_STUDY_MM
    body = [
        _gore(body_profiles, BODY_HEIGHTS_MM, body_steps, i, "TORSO", allowance)
        for i in range(4)
    ]
    head = [
        _gore(head_profiles, HEAD_HEIGHTS_MM, head_steps, i, "HEADNECK", allowance)
        for i in range(4)
    ]
    shoulder = _cap(
        body_profiles[-1], allowance, "SHOULDER-CAP-TRIAL",
        port if name.startswith("B_") else None
    )
    head_top = _cap(head_profiles[-1], allowance, "HEAD-TOP-CAP-TRIAL")
    neck_base = None
    collar = None
    if name.startswith("A_"):
        neck_base = _cap(port, allowance, "CLOSED-NECK-BASE-TRIAL")
    else:
        collar = _collar(port, allowance)
    return {
        "name": name,
        "source_3d_reference_body_and_head_are_distinct_research_volumes": True,
        "source_neck_port_modification": mismatch,
        "body_rings_z_mm": list(BODY_HEIGHTS_MM),
        "head_rings_z_mm": list(HEAD_HEIGHTS_MM),
        "body_source_observations": body_rows,
        "head_source_observations": head_source,
        "body_synthetic_rings_xy_mm": [p.tolist() for p in body_profiles],
        "head_synthetic_rings_xy_mm": [p.tolist() for p in head_profiles],
        "body_meridian_step_mm": body_steps.tolist(),
        "head_meridian_step_mm": head_steps.tolist(),
        "body_original_source_envelope_deviation": body_3d,
        "head_original_source_envelope_deviation": head_3d,
        "torso_gore_pieces": body,
        "headneck_gore_pieces": head,
        "shoulder_cap": shoulder,
        "head_top_cap": head_top,
        "head_bottom_cap_if_separate": neck_base,
        "neck_collar_if_integrated": collar,
        "neck_source_inspired_guide": _surface_guide_length(port),
        "separate_head_is_stuffed_and_externally_attached": name.startswith("A_"),
        "integrated_neck_port_has_an_open_torso_to_head_passage": name.startswith("B_"),
        "new_pattern_pieces": 11,
        "existing_lower_hoof_anchored_pieces": 13,
        "new_plus_existing_research_pieces": 24,
        "original_real_sculpt_cutting_patterns_generated": False,
        "industrial_cut_patterns_approved": 0,
    }


def build_split_volume_mother_ab(lower, source_xyz):
    if (
        lower.get("schema") != "stage6-source-hoof-anchored-lower-mother-toile-v1"
        or lower.get("source_hoof_open_edges") != 2048
        or lower.get("piece_count") != 13
        or lower.get("approved_industrial_paper_patterns") != 0
    ):
        raise ValueError("verified original-hoof lower 13-piece trial required")
    source = np.asarray(source_xyz, dtype=np.float64)
    if source.ndim != 2 or source.shape[1] != 3 or not np.isfinite(source).all():
        raise ValueError("unverified real Stage6 source XYZ reference")
    base = np.asarray(lower["yoke"]["outer_stitch_xy_mm"], dtype=float)
    if base.shape != (64, 2) or not Polygon(base).is_valid:
        raise ValueError("lower body original hoop-anchored outer band has changed")
    profiles = [base]
    rows = []
    for z in BODY_HEIGHTS_MM[1:]:
        ring, observation = _observed_ring(source, z, base)
        profiles.append(ring)
        rows.append(observation)
    variants = [
        _one_variant(source, base, profiles, rows, setting)
        for setting in OPTIONS
    ]
    center_135 = np.asarray(rows[-1]["source_center_xy_mm"])
    center_145 = np.asarray(
        variants[0]["head_source_observations"][0]["source_center_xy_mm"]
    )
    return {
        "schema": "stage6-separated-torso-headneck-mother-trial-ab-v1",
        "status": "TWO_ANATOMICAL_SOURCE_ENVELOPE_TRIALS_NOT_FACTORY_PATTERNS",
        "original_4x512_source_hoof_ids_preserved_by_same_run_lower": True,
        "original_lower_13_piece_geometry_not_modified": True,
        "two_distinct_stuffed_vs_open_neck_join_methods": True,
        "true_source_shoulder_z_mm": BODY_HEIGHTS_MM[-1],
        "true_source_neck_root_z_mm": HEAD_HEIGHTS_MM[0],
        "shoulder_to_neck_root_z_gap_mm": HEAD_HEIGHTS_MM[0] - BODY_HEIGHTS_MM[-1],
        "real_source_135_to145_center_shift_xy_mm": float(
            np.linalg.norm(center_145 - center_135)
        ),
        "reference_only_source_top_z_mm": float(source[:, 2].max()),
        "research_head_top_cap_z_mm": HEAD_HEIGHTS_MM[-1],
        "source_3d_top_height_not_represented_mm": float(
            source[:, 2].max() - HEAD_HEIGHTS_MM[-1]
        ),
        "options": variants,
        "source_slice_envelope_is_not_original_mesh_cut_contour": True,
        "original_face_ears_tail_clouds_drops_unconnected": True,
        "material_and_stuffing_never_verified": True,
        "factory_cutting_patterns_approved": 0,
    }
