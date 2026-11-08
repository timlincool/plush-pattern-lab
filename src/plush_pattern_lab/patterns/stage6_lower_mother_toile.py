"""Source-anchored lower-body 13-piece toile, NOT a Stage6 cutting pattern.

Four original hoof rings are planar and exact, but the new ventral yoke,
straight leg sleeves, flat test soles and upper bands are DESIGN SURROGATES.
Only sewing length and paper geometry are checked; no material/fit approval.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from shapely.geometry import LineString, MultiPoint, Polygon
from shapely.ops import unary_union

PIECE_IDS = ("FL", "FR", "RL", "RR")
SOURCE_HOOF_PLANE_Z_MM = 20.0
RESEARCH_YOKE_Z_MM = 60.0
DEFAULT_ALLOWANCE_MM = 6.0
DEFAULT_YOKE_MARGIN_MM = 18.0
BAND_STITCH_EDGES = 16


def _checked_mesh(xyz, faces):
    vertices = np.asarray(xyz, dtype=np.float64)
    tri = np.asarray(faces)
    if (
        vertices.ndim != 2
        or vertices.shape[1] != 3
        or not np.isfinite(vertices).all()
    ):
        raise ValueError("expected actual finite Stage6 millimetre vertices")
    if (
        tri.ndim != 2
        or tri.shape[1] != 3
        or not np.issubdtype(tri.dtype, np.integer)
        or not len(tri)
    ):
        raise ValueError("expected nonempty original source triangle indices")
    if np.any(tri < 0) or np.any(tri >= len(vertices)):
        raise ValueError("untrusted original mesh face index")
    return vertices, tri.astype(np.int64)


def _original_open_boundary(faces):
    pairs = np.concatenate(
        (faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]])
    )
    unique, counts = np.unique(
        np.sort(pairs, axis=1), axis=0, return_counts=True
    )
    if np.any(counts > 2) or not np.any(counts == 1):
        raise ValueError("nonmanifold original hoof boundary")
    return unique[counts == 1]


def _one_ring(start, adjacent, visited):
    prior, current, ids = -1, start, []
    while current not in visited:
        visited.add(current)
        ids.append(current)
        nxt = sorted(index for index in adjacent[current] if index != prior)
        if len(nxt) != 1 and prior != -1:
            raise ValueError("source boundary walk forked")
        prior, current = current, nxt[0]
        if len(ids) > len(adjacent):
            raise ValueError("original source cycle never closed")
    if current != start or len(ids) < 12:
        raise ValueError("source boundary does not close a simple ring")
    return np.asarray(ids, dtype=np.int64)


def _source_ring(ids, xyz, expected_edges):
    if len(ids) != expected_edges:
        raise ValueError("original hoof source ring has unexpected edge count")
    p = xyz[ids]
    if (
        np.max(np.abs(p[:, 2] - SOURCE_HOOF_PLANE_Z_MM)) > 0.002
        or not np.isfinite(p).all()
    ):
        raise ValueError("hoof source ring not planar at original Z=20mm")
    ring = Polygon(p[:, :2])
    if not ring.is_valid or ring.area < 100:
        raise ValueError("original hoof source ring is not a valid fabric boundary")
    if not ring.exterior.is_ccw:
        ids = np.r_[ids[0], ids[:0:-1]]
    xy = xyz[ids, :2]
    lengths = np.linalg.norm(xy - np.roll(xy, -1, axis=0), axis=1)
    if np.min(lengths) <= 1e-6:
        raise ValueError("original hoof source ring has degenerate stitch edges")
    return {
        "original_vertex_ids": ids,
        "original_xy_mm": xy,
        "source_edge_lengths_mm": lengths,
        "source_perimeter_mm": float(lengths.sum()),
        "source_centroid_xyz_mm": xyz[ids].mean(axis=0),
    }


def extract_original_hoof_rings(xyz, faces, *, expected_edges=512):
    """Validate and order four exact planar original open source boundary loops."""
    points, tri = _checked_mesh(xyz, faces)
    boundary = _original_open_boundary(tri)
    if len(boundary) != 4 * expected_edges:
        raise ValueError("expected exactly four untouched original hoof openings")
    adjacent = defaultdict(list)
    for a, b in boundary:
        adjacent[int(a)].append(int(b))
        adjacent[int(b)].append(int(a))
    if any(len(v) != 2 for v in adjacent.values()):
        raise ValueError("branched original source hoof boundary")
    visited, rows = set(), []
    for start in sorted(adjacent):
        if start not in visited:
            rows.append(_source_ring(_one_ring(start, adjacent, visited), points, expected_edges))
    if len(rows) != 4 or len(visited) != 4 * expected_edges:
        raise ValueError("source hoof openings are not four independent rings")
    rows.sort(
        key=lambda item: (
            item["source_centroid_xyz_mm"][1],
            item["source_centroid_xyz_mm"][0],
        )
    )
    if not (
        rows[0]["source_centroid_xyz_mm"][0] < 0
        and rows[1]["source_centroid_xyz_mm"][0] > 0
        and rows[2]["source_centroid_xyz_mm"][0] < 0
        and rows[3]["source_centroid_xyz_mm"][0] > 0
    ):
        raise ValueError("original front-left/right rear-left/right identity changed")
    return dict(zip(PIECE_IDS, rows))


def _outline(coords):
    vertices = np.asarray(coords, dtype=np.float64)
    if vertices.ndim != 2 or vertices.shape[1] != 2 or not np.isfinite(vertices).all():
        raise ValueError("invalid yoke seam XY geometry")
    poly = Polygon(vertices)
    if not poly.is_valid or poly.area <= 1:
        raise ValueError("collapsed or self-crossed manufacturing toile geometry")
    return poly


def _quarter_bands(outer_ring, height_mm):
    poly = np.vstack((outer_ring, outer_ring[0]))
    segment_length = np.linalg.norm(np.diff(poly, axis=0), axis=1)
    bands = []
    for i in range(4):
        local = segment_length[i * BAND_STITCH_EDGES : (i + 1) * BAND_STITCH_EDGES]
        x = np.r_[0.0, np.cumsum(local)]
        bands.append(
            {
                "id": f"BAND-{i + 1}",
                "source_ring_edge_indices": list(
                    range(i * BAND_STITCH_EDGES, (i + 1) * BAND_STITCH_EDGES)
                ),
                "yoke_outer_section_stitch_mm": float(local.sum()),
                "stitch_bottom_station_x_mm": x.tolist(),
                "stitch_rectangle_xy_mm": [
                    [0, 0], [float(x[-1]), 0],
                    [float(x[-1]), height_mm], [0, height_mm],
                ],
                "open_upper_edge_not_paired_to_body": True,
            }
        )
    return bands


def _toe_and_sleeve(ring, identity, height_mm):
    stations = np.r_[0.0, np.cumsum(ring["source_edge_lengths_mm"])]
    return {
        "id": identity,
        "source_vertex_ids": ring["original_vertex_ids"].tolist(),
        "source_stitch_ring_xy_mm": ring["original_xy_mm"].tolist(),
        "source_original_center_xyz_mm": ring["source_centroid_xyz_mm"].tolist(),
        "source_original_3d_z_mm": SOURCE_HOOF_PLANE_Z_MM,
        "source_original_hoof_edges": len(ring["original_vertex_ids"]),
        "source_original_hoof_perimeter_mm": ring["source_perimeter_mm"],
        "sleeve_stitch_station_x_mm": stations.tolist(),
        "sleeve_height_mm": height_mm,
        "toe_is_synthetic_flat_disc_not_original_3d_hoof_cap": True,
        "sleeve_yoke_top_is_a_relocated_research_interface": True,
    }


def _yoke_polygon(rings, margin_mm):
    points = np.vstack([ring["original_xy_mm"] for ring in rings.values()])
    hull = MultiPoint(points).convex_hull
    boundary = hull.buffer(margin_mm, join_style=1, quad_segs=16)
    if boundary.geom_type != "Polygon":
        raise ValueError("source foothold outer hull is not one manufacturable panel")
    line = LineString(boundary.exterior.coords)
    perimeter = line.length
    ring = np.asarray(
        [
            line.interpolate(perimeter * i / (4 * BAND_STITCH_EDGES)).coords[0]
            for i in range(4 * BAND_STITCH_EDGES)
        ],
        dtype=np.float64,
    )
    outside = _outline(ring)
    holes = [_outline(item["original_xy_mm"]) for item in rings.values()]
    net = Polygon(outside.exterior.coords, [hole.exterior.coords for hole in holes])
    if not net.is_valid or len(net.interiors) != 4:
        raise ValueError("original four source holes no longer fit proposed yoke")
    distance = min(outside.exterior.distance(hole) for hole in holes)
    return outside, holes, distance


def build_source_hoof_lower_toile(
    rings, *, seam_allowance_mm=6.0, yoke_margin_mm=18.0, height_mm=40.0
):
    """Return true four source-hoof ring seams plus a NEW lower mother assembly."""
    if (
        not 3 <= seam_allowance_mm <= 8
        or not 12 <= yoke_margin_mm <= 30
        or not 20 <= height_mm <= 65
        or set(rings) != set(PIECE_IDS)
    ):
        raise ValueError("unsafe lower-toile materials or missing source hoof roles")
    outside, holes, clearance = _yoke_polygon(rings, yoke_margin_mm)
    if clearance < 2 * seam_allowance_mm + 1:
        raise ValueError("insufficient fabric bridge at source hoof port")
    if any(
        holes[i].distance(holes[j]) < 2 * seam_allowance_mm + 1
        for i in range(4)
        for j in range(i + 1, 4)
    ):
        raise ValueError("four leg port seam allowances are too close")
    cut_holes = [hole.buffer(-seam_allowance_mm) for hole in holes]
    if any(
        hole.is_empty or hole.geom_type != "Polygon" or hole.area < 5
        for hole in cut_holes
    ):
        raise ValueError("cutting seam allowance would collapse a leg hole")
    outer_cut = outside.buffer(seam_allowance_mm, quad_segs=12)
    cut = outer_cut.difference(unary_union(cut_holes))
    if not cut.is_valid or cut.geom_type != "Polygon" or len(cut.interiors) != 4:
        raise ValueError("four-holed lower yoke cutting outline self-intersects")
    outer_ring = np.asarray(outside.exterior.coords[:-1], dtype=float)
    bands = _quarter_bands(outer_ring, height_mm)
    items = {
        name: _toe_and_sleeve(ring, name, height_mm)
        for name, ring in rings.items()
    }
    source_edges = sum(item["source_original_hoof_edges"] for item in items.values())
    return {
        "schema": "stage6-source-hoof-anchored-lower-mother-toile-v1",
        "status": "GEOMETRIC_TEST_TOILE_NOT_APPROVED_STAGE6_CUTTING_PATTERN",
        "units": "mm",
        "source_hoof_boundary_z_mm": SOURCE_HOOF_PLANE_Z_MM,
        "relocated_research_yoke_z_mm": RESEARCH_YOKE_Z_MM,
        "material_seam_allowance_is_unverified_mm": seam_allowance_mm,
        "source_hoof_open_edges": source_edges,
        "original_source_hoofs": items,
        "yoke": {
            "source_hoof_holes_stitch_xy_mm": {
                key: item["source_stitch_ring_xy_mm"]
                for key, item in items.items()
            },
            "outer_stitch_xy_mm": outer_ring.tolist(),
            "outer_cut_xy_mm": np.asarray(outer_cut.exterior.coords).tolist(),
            "inner_cut_holes_xy_mm": [
                np.asarray(hole.exterior.coords).tolist() for hole in cut_holes
            ],
            "minimum_source_hole_to_outer_stitch_clearance_mm": clearance,
            "outer_stitch_perimeter_mm": float(outside.length),
            "upper_body_shell_seam_unpaired": True,
        },
        "outer_quarter_bands": bands,
        "piece_count": 13,
        "piece_roles": {
            "ventral_yoke": 1, "four_leg_sleeves": 4,
            "four_synthetic_flat_hoof_soles": 4, "four_upper_outer_bands": 4,
        },
        "turning_gap_research": {
            "band_id": "BAND-3",
            "bottom_band_seam_interval_fraction": [0.35, 0.65],
            "physically_stuffed_complete_shell_not_yet_possible": True,
        },
        "source_3d_hoof_geometry_unmodified": True,
        "new_ventral_yoke_is_not_original_body_surface": True,
        "real_hoof_base_3d_mesh_not_flattened": True,
        "physical_fabric_test_not_done": True,
        "head_neck_upper_body_ears_tail_clouds_not_connected": True,
        "approved_industrial_paper_patterns": 0,
    }
