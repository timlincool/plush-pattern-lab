"""Sparse LSCM diagnostic for a genuinely slitted original Stage6 root disk.

Free boundary LSCM has scale gauge freedom. Renormalize with an explicitly
recorded *uniform* least-squares edge scale before measuring any 2D strain.
This is NOT physically calibrated fabric rest-shape or a cutting template.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from scipy.sparse import coo_matrix, vstack
from scipy.sparse.linalg import lsqr
from scipy.spatial.distance import cdist
from shapely.geometry import Polygon
from shapely.strtree import STRtree

SCHEMA = "stage6-ear-root-genuine-source-disk-lscm-research-v1"
SCREEN_EDGE_P95_RELATIVE = 0.10
SCREEN_SEAM_PAIR_RELATIVE = 0.03
RESEARCH_DOUBLE_ALLOWANCE_MM = 12.0


def _local_triangle_cr_gradients(xyz, faces):
    positions = xyz[faces]
    edge_x = positions[:, 1] - positions[:, 0]
    edge_y = positions[:, 2] - positions[:, 0]
    base = np.linalg.norm(edge_x, axis=1)
    area_twice = np.linalg.norm(np.cross(edge_x, edge_y), axis=1)
    if np.min(base) <= 1e-9 or np.min(area_twice) <= 1e-9:
        raise ValueError("original source disk contains collapsed 3D triangle")
    horizontal = np.einsum("ij,ij->i", edge_x, edge_y) / base
    vertical = area_twice / base
    gx = np.column_stack((-vertical, vertical, np.zeros(len(base))))
    gy = np.column_stack((horizontal - base, -horizontal, base))
    area = area_twice / 2
    return gx / area_twice[:, None], gy / area_twice[:, None], area


def _lscm_research_matrix(faces, dx, dy, area, vertex_count):
    count = len(faces)
    row = np.repeat(np.arange(count), 3)
    corner = faces.ravel()
    indices = np.r_[2 * row, 2 * row, 2 * row + 1, 2 * row + 1]
    columns = np.r_[2 * corner, 2 * corner + 1, 2 * corner, 2 * corner + 1]
    weight = np.sqrt(area)[:, None]
    data = np.r_[
        (dx * weight).ravel(),
        (-dy * weight).ravel(),
        (dy * weight).ravel(),
        (dx * weight).ravel(),
    ]
    return coo_matrix(
        (data, (indices, columns)), shape=(2 * count, 2 * vertex_count)
    ).tocsr()


def _anchored_lscm(xyz, faces, lower):
    """Two fixed physical reference points remove translation/rotation/scale."""
    dx, dy, area = _local_triangle_cr_gradients(xyz, faces)
    matrix = _lscm_research_matrix(faces, dx, dy, area, len(xyz))
    first, second = int(lower[0]), int(lower[len(lower) // 2])
    distance = float(np.linalg.norm(xyz[second] - xyz[first]))
    if distance < 1e-5:
        raise ValueError("source LSCM pin anchors not geometrically separated")
    positions = [2 * first, 2 * first + 1, 2 * second, 2 * second + 1]
    weight = 1000.0
    gauge = coo_matrix(
        (np.full(4, weight), (np.arange(4), positions)),
        shape=(4, 2 * len(xyz)),
    ).tocsr()
    solved = lsqr(
        vstack((matrix, gauge)).tocsr(),
        np.r_[np.zeros(2 * len(faces)), [0, 0, weight * distance, 0]],
        atol=1e-10,
        btol=1e-10,
        iter_lim=2500,
    )
    if solved[1] not in (1, 2) or not np.isfinite(solved[0]).all():
        raise ValueError("source research LSCM sparse solve failed")
    return solved[0].reshape(-1, 2), {
        "solver_stop_code": int(solved[1]),
        "sparse_iterations": int(solved[2]),
        "residual_norm": float(solved[3]),
        "two_original_3d_anchor_indices": [first, second],
        "anchor_distance_in_actual_source_3d_mm": distance,
        "not_fabric_rest_shape_pinning": True,
    }


def _all_disk_edge_distances(points, faces, uv):
    sorted_edges = np.sort(
        np.concatenate((faces[:, (0, 1)], faces[:, (1, 2)], faces[:, (2, 0)])),
        axis=1,
    )
    edges = np.unique(sorted_edges, axis=0)
    physical = np.linalg.norm(points[edges[:, 0]] - points[edges[:, 1]], axis=1)
    flat = np.linalg.norm(uv[edges[:, 0]] - uv[edges[:, 1]], axis=1)
    if np.any(physical < 1e-9) or not np.isfinite(flat).all():
        raise ValueError("invalid original disk 3D edges or planar image")
    return edges, physical, flat


def _scale_free_gauge(points, faces, uv):
    """Normalize one similarity scale globally, NOT a material optimization."""
    edges, physical, flat = _all_disk_edge_distances(points, faces, uv)
    ratio = flat / physical
    factor = float(ratio.sum() / (ratio @ ratio))
    if not 0 < factor < 100 or not np.isfinite(factor):
        raise ValueError("invalid uniform 2D similarity gauge")
    scaled = uv * factor
    scaled -= scaled.min(axis=0)
    strain = np.abs(factor * ratio - 1)
    return (
        scaled,
        strain,
        {
            "uniform_isotropic_scale_from_minimum_squared_edge_relative_error": factor,
            "source_3d_unique_disk_edges": len(edges),
            "scaled_2d_p50_abs_edge_relative_error": float(np.median(strain)),
            "scaled_2d_p95_abs_edge_relative_error": float(np.quantile(strain, 0.95)),
            "scaled_2d_max_abs_edge_relative_error": float(strain.max()),
            "p95_above_10percent_research_screen": bool(
                np.quantile(strain, 0.95) > SCREEN_EDGE_P95_RELATIVE
            ),
            "uniform_scale_not_known_material_grain_or_stretch": True,
        },
    )


def _face_overlap_and_winding(points, faces, uv):
    xy = uv[faces]
    first, second = xy[:, 1] - xy[:, 0], xy[:, 2] - xy[:, 0]
    signed = 0.5 * (first[:, 0] * second[:, 1] - first[:, 1] * second[:, 0])
    majority = 1 if np.count_nonzero(signed > 0) >= len(signed) / 2 else -1
    flips = int(np.count_nonzero(signed * majority <= 1e-9))
    physical = points[faces]
    area3d = 0.5 * np.linalg.norm(
        np.cross(physical[:, 1] - physical[:, 0], physical[:, 2] - physical[:, 0]),
        axis=1,
    )
    polygons = [Polygon(triangle) for triangle in xy]
    if any(not polygon.is_valid for polygon in polygons):
        raise ValueError("source LSCM produced invalid individual triangle polygon")
    tree = STRtree(polygons)
    pairs, overlap_area = 0, 0.0
    for index, polygon in enumerate(polygons):
        for found in tree.query(polygon):
            other = int(found)
            if other <= index:
                continue
            area = polygon.intersection(polygons[other]).area
            if area > 1e-6:
                pairs += 1
                overlap_area += area
    return {
        "planar_2d_signed_face_orientation_majority": majority,
        "reversed_or_collapsed_triangle_count": flips,
        "overlapping_positive_area_triangle_pair_count": pairs,
        "overlap_triangle_area_mm2": float(overlap_area),
        "source_3d_face_area_total_mm2": float(area3d.sum()),
        "scaled_2d_signed_face_area_total_mm2": float(signed.sum()),
        "scaled_2d_absolute_face_area_total_mm2": float(np.abs(signed).sum()),
        "scaled_2d_to_source_3d_face_area_p05_ratio": float(
            np.quantile(np.abs(signed) / area3d, 0.05)
        ),
        "scaled_2d_to_source_3d_face_area_p95_ratio": float(
            np.quantile(np.abs(signed) / area3d, 0.95)
        ),
        "zero_overlap_not_physical_fabric_rest_shape_or_factory_approval": True,
    }


def _oriented_disk_boundary_edges(faces):
    raw = np.concatenate((faces[:, (0, 1)], faces[:, (1, 2)], faces[:, (2, 0)]), axis=0)
    sorted_edges = np.sort(raw, axis=1)
    _, index, counts = np.unique(
        sorted_edges, axis=0, return_inverse=True, return_counts=True
    )
    return raw[counts[index] == 1]


def _two_true_planar_seam_sides(disk, uv):
    path = disk["slit_original_local_vertex_ids"]
    source = disk["original_patch_vertex_id_per_disk_vertex"]
    boundary = _oriented_disk_boundary_edges(disk["disk_triangle_vertex_ids"])
    mapped = defaultdict(list)
    for a, b in boundary:
        original = tuple(sorted((int(source[a]), int(source[b]))))
        mapped[original].append((int(a), int(b)))
    left, right = [], []
    for a, b in zip(path[:-1], path[1:]):
        found = mapped[tuple(sorted((a, b)))]
        a_forward = [p for p in found if source[p[0]] == a and source[p[1]] == b]
        b_forward = [p for p in found if source[p[0]] == b and source[p[1]] == a]
        if len(found) != 2 or len(a_forward) != 1 or len(b_forward) != 1:
            raise ValueError("two physical source seam copies do not orient oppositely")
        left.append(float(np.linalg.norm(uv[a_forward[0][0]] - uv[a_forward[0][1]])))
        right.append(float(np.linalg.norm(uv[b_forward[0][0]] - uv[b_forward[0][1]])))
    expected = disk["real_source_3d_slit_length_mm"]
    physical_path = disk["source_xyz_mm"][path]
    actual = float(np.linalg.norm(np.diff(physical_path, axis=0), axis=1).sum())
    if abs(actual - expected) > 1e-8:
        raise ValueError("source slit physical 3D length changed during unroll")
    first, second = float(sum(left)), float(sum(right))
    differences = np.abs(np.asarray(left) - np.asarray(right))
    return {
        "original_paired_3d_seam_length_each_side_mm": expected,
        "scaled_planar_2d_first_source_netline_length_mm": first,
        "scaled_planar_2d_second_source_netline_length_mm": second,
        "scaled_planar_2d_two_sides_length_mismatch_mm": abs(first - second),
        "scaled_planar_2d_two_sides_length_mismatch_fraction_of_source_3d": (
            abs(first - second) / expected
        ),
        "scaled_planar_2d_max_original_segment_pair_length_difference_mm": float(
            differences.max()
        ),
        "scaled_planar_2d_p95_original_segment_pair_length_difference_mm": float(
            np.quantile(differences, 0.95)
        ),
        "original_source_cut_edge_has_exactly_two_oppositely_oriented_disk_sides": True,
        "2d_netline_pair_exceeds_3percent_research_screen": bool(
            abs(first - second) / expected > SCREEN_SEAM_PAIR_RELATIVE
        ),
        "2d_sewing_netlines_not_equal_to_matched_3d_source_seam": True,
    }


def _lower_upper_planar_clearance(disk, uv):
    source = disk["original_patch_vertex_id_per_disk_vertex"]
    lower = np.isin(source, disk["original_source_lower_boundary_vertex_ids"])
    upper = np.isin(source, disk["original_source_upper_boundary_vertex_ids"])
    if not np.any(lower) or not np.any(upper):
        raise ValueError("original source planar lower/upper borders not found")
    gap = float(cdist(uv[lower], uv[upper]).min())
    return {
        "scaled_2d_min_sampled_lower_upper_vertex_gap_mm": gap,
        "below_two_nominal_6mm_allowances_in_2d_vertex_screen": (
            gap < RESEARCH_DOUBLE_ALLOWANCE_MM
        ),
        "sampled_vertex_gap_is_not_true_continuous_offset_allowance": True,
    }


def evaluate_original_source_slit_disk(disk):
    """Record research UV and fail closed on malformed topology / source seams."""
    points = np.asarray(disk["source_xyz_mm"], dtype=np.float64)
    faces = np.asarray(disk["disk_triangle_vertex_ids"], dtype=np.int64)
    low = disk["original_source_lower_boundary_vertex_ids"]
    if (
        not disk["slit_disk_single_boundary"]
        or disk["slit_disk_euler_characteristic"] != 1
    ):
        raise ValueError("LSCM requires verified source topological disk")
    uv, solver = _anchored_lscm(points, faces, low)
    uv, strain, distortion = _scale_free_gauge(points, faces, uv)
    if not np.isfinite(uv).all() or not np.isfinite(strain).all():
        raise ValueError("source LSCM planar coordinates not finite")
    faces_diagnostics = _face_overlap_and_winding(points, faces, uv)
    seam = _two_true_planar_seam_sides(disk, uv)
    gap = _lower_upper_planar_clearance(disk, uv)
    return {
        "schema": SCHEMA,
        "source_variant": disk["source_study"],
        "original_source_side": disk["source_side"],
        "source_slit_direction": disk["slit_direction"],
        "source_3d_cut_length_mm": disk["real_source_3d_slit_length_mm"],
        "original_source_patch_sha256": disk["source_patch_sha256"],
        "original_root_source_area_mm2": disk["original_source_patch_area_mm2"],
        "cut_disk_original_face_count": disk["slit_disk_face_count"],
        "original_source_real_face_ids_per_disk_triangle": (
            disk["derived_source_face_id_per_disk_triangle"].tolist()
        ),
        "cut_disk_source_xyz_mm": points.tolist(),
        "cut_disk_source_vertex_identity": (
            disk["original_patch_vertex_id_per_disk_vertex"].tolist()
        ),
        "cut_disk_original_source_triangle_indices": faces.tolist(),
        "actual_slit_original_source_local_vertex_ids": (
            disk["slit_original_local_vertex_ids"]
        ),
        "real_2d_research_coordinates_mm": uv.tolist(),
        "sparse_lscm": solver,
        "uniform_scale_normalized_edge_diagnostics": distortion,
        "original_source_planar_face_geometry_diagnostics": faces_diagnostics,
        "true_source_seam_3d_vs_lscm_2d_pairing": seam,
        "two_seams_2d_6mm_allowance_vertex_screen": gap,
        "not_a_calibrated_material_rest_pattern": True,
        "not_a_factory_cutting_or_sewing_approval": True,
        "factory_cutting_patterns_approved": 0,
    }
