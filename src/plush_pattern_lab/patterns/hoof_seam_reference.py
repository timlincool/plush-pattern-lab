"""Stage 6 四蹄接缝的弧长对位标尺与二维投影参考；不是裁片展平。"""

from __future__ import annotations

import re
from html import escape

import numpy as np

from plush_pattern_lab.validation.boundary_match import (
    as_ring_mm,
    unique_centroid_mapping,
    verify_mating_loops,
)

STATUS = "STAGE6_HOOF_SEAM_REFERENCE_NOT_CUT_PATTERN"


def _canonical_body_ring(ring):
    """依世界坐标的最高 Z、最小 X/Y 选择已有顶点，绝不重采样。"""
    start = int(np.lexsort((ring[:, 1], ring[:, 0], -ring[:, 2]))[0])
    return np.roll(ring, -start, axis=0), start


def _flat_reference(ring):
    """最小二乘拟合平面，只供投影误差诊断，不宣称等距展开。"""
    delta = ring - ring.mean(axis=0)
    _, singular, basis = np.linalg.svd(delta, full_matrices=False)
    if singular[1] <= 1e-9:
        raise ValueError("边界几何接近共线，无法建立二维参考平面")
    normal = basis[-1]
    winding = np.cross(delta, np.roll(delta, -1, axis=0)).sum(axis=0)
    if np.linalg.norm(winding) <= 1e-9:
        raise ValueError("边界投影的有向面积退化")
    if np.dot(normal, winding) < 0:
        normal = -normal
    radial = delta - np.outer(delta @ normal, normal)
    anchor = radial[0]
    if np.linalg.norm(anchor) <= 1e-9:
        anchor = radial[int(np.argmax(np.linalg.norm(radial, axis=1)))]
    u = anchor / np.linalg.norm(anchor)
    v = np.cross(normal, u)
    flat = np.column_stack((delta @ u, delta @ v))
    edges_3d = np.linalg.norm(np.roll(ring, -1, axis=0) - ring, axis=1)
    edges_2d = np.linalg.norm(np.roll(flat, -1, axis=0) - flat, axis=1)
    if np.any(edges_2d <= 1e-9):
        raise ValueError("投影缝线存在零长度边；不可用于二维参考")
    residual = delta @ normal
    return flat, {
        "out_of_plane_rms_mm": float(np.sqrt(np.mean(residual**2))),
        "max_out_of_plane_mm": float(np.max(np.abs(residual))),
        "perimeter_3d_mm": float(edges_3d.sum()),
        "perimeter_2d_projected_mm": float(edges_2d.sum()),
        "projection_length_loss_mm": float(edges_3d.sum() - edges_2d.sum()),
        "max_projected_edge_shortfall_ratio": float(
            np.max(np.maximum(0.0, 1.0 - edges_2d / edges_3d))
        ),
        "projection_is_true_surface_flattening": False,
    }


def _notches(body, flat, body_indices, hoof_indices):
    edges = np.linalg.norm(np.roll(body, -1, axis=0) - body, axis=1)
    stations = np.r_[0.0, np.cumsum(edges[:-1])]
    total = float(edges.sum())
    positions = [
        int(np.argmin(abs(stations - fraction * total)))
        for fraction in (0, 0.25, 0.5, 0.75)
    ]
    if len(set(positions)) != 4:
        raise ValueError("对位标记落到重复顶点，环长度分布异常")
    return (
        [
            {
                "id": f"Q{idx}",
                "target_fraction": idx / 4,
                "arc_length_3d_mm": float(stations[point]),
                "body_ring_ordinal": int(body_indices[point]),
                "hoof_ring_ordinal": int(hoof_indices[point]),
                "projected_point_2d_mm": flat[point].tolist(),
            }
            for idx, point in enumerate(positions)
        ],
        stations,
    )


def _single_reference(body_raw, hoof_raw, hoof_name, body_index, center_gap):
    match = verify_mating_loops(body_raw, hoof_raw)
    if not match["world_boundary_geometry_match"]:
        raise ValueError(f"蹄部接口未通过原三维几何和方向守卫：{hoof_name}")
    body, start = _canonical_body_ring(body_raw)
    n = len(body)
    reversed_hoof = hoof_raw[::-1]
    shifted = np.roll(reversed_hoof, match["cyclic_shift"], axis=0)
    paired_hoof = np.roll(shifted, -start, axis=0)
    hoof_ordinals = np.roll(
        np.roll(np.arange(n - 1, -1, -1), match["cyclic_shift"]),
        -start,
    )
    body_ordinals = np.roll(np.arange(n), -start)
    flat, projection = _flat_reference(body)
    notches, stations = _notches(body, flat, body_ordinals, hoof_ordinals)
    body_edges = np.linalg.norm(np.roll(body, -1, axis=0) - body, axis=1)
    hoof_edges = np.linalg.norm(np.roll(paired_hoof, -1, axis=0) - paired_hoof, axis=1)
    return {
        "hoof": hoof_name,
        "body_ring_index": body_index,
        "centroid_gap_mm": center_gap,
        "vertex_count": n,
        "matching": match,
        "canonical_start_body_ordinal": start,
        "body_to_hoof_ring_ordinals": hoof_ordinals.tolist(),
        "max_matched_segment_length_delta_mm": float(
            np.max(np.abs(body_edges - hoof_edges))
        ),
        "notches": notches,
        "arc_length_stations_3d_mm": stations.tolist(),
        "projected_reference_ring_2d_mm": flat.tolist(),
        "projection_diagnostics": projection,
    }


def build_reference(body_rings, hoof_rings, hoof_names, source_sha256):
    """四蹄配对并记录 3D 真弧长与非等距 2D 投影，无制造放行。"""
    if not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
        raise ValueError("源模型 SHA-256 必须为 64 位小写十六进制")
    if len(body_rings) != 4 or len(hoof_rings) != 4 or len(hoof_names) != 4:
        raise ValueError("Stage 6 应有恰好四只蹄和四个主体洞口")
    bodies = [as_ring_mm(r) for r in body_rings]
    hoofs = [as_ring_mm(r) for r in hoof_rings]
    if any(len(r) != len(hoofs[0]) for r in (*bodies, *hoofs)):
        raise ValueError("四组接缝采样点数不同，禁止插值冒充原网格")
    locations = unique_centroid_mapping(bodies, hoofs)
    records = [
        _single_reference(bodies[index], hoof, name, index, gap)
        for hoof, name, (index, gap) in zip(hoofs, hoof_names, locations)
    ]
    return {
        "schema": "stage6-hoof-seam-reference-v1",
        "status": STATUS,
        "source_sha256": source_sha256,
        "units": "mm",
        "ring_ordinal_definition": "Topological ring order, NOT Blender mesh vertex id",
        "hoofs": records,
        "quality": {
            "matched_interfaces": len(records),
            "all_3d_geometry_interfaces_match": all(
                r["matching"]["world_boundary_geometry_match"] for r in records
            ),
            "surface_flattened": False,
            "seam_allowance_defined": False,
            "physical_material_measured": False,
            "approved_cut_patterns": False,
        },
        "limitations": [
            "2D contour is best-fit plane projection; NOT a surface-flattened net seam",
            "Arc-length stations use exact 3D polygonal edge lengths without resampling",
            "Q0..Q3 are geometry registration marks, not anatomical or cutting notches",
            "No seam allowances, face flattening, grain direction or manufacturability proof",
        ],
    }


def _validated_charts(report):
    if report.get("schema") != "stage6-hoof-seam-reference-v1":
        raise ValueError("只接受已配对的 Stage 6 接缝参考")
    if len(report["hoofs"]) != 4:
        raise ValueError("SVG 必须显示恰好四只蹄")
    charts = []
    for row in report["hoofs"]:
        points = np.asarray(row["projected_reference_ring_2d_mm"], dtype=float)
        if points.ndim != 2 or points.shape[1] != 2 or not 3 <= len(points) <= 4096:
            raise ValueError("无效的二维参考点")
        if not np.isfinite(points).all():
            raise ValueError("投影点非有限")
        minimum = points.min(axis=0)
        charts.append((points - minimum, points.max(axis=0) - minimum, row, minimum))
    return charts


def _draw_chart(i, chart, cell_w, cell_h, gauge_start, pad=18.0):
    points, _extent, row, minimum = chart
    ox, oy = (i % 2) * cell_w + pad, (i // 2) * cell_h + pad + 9
    coords = " ".join(f"{x:.3f},{y:.3f}" for x, y in points + (ox, oy))
    output = [f'<polygon points="{coords}"/>']
    for notch in row["notches"]:
        x, y = np.asarray(notch["projected_point_2d_mm"]) - minimum + (ox, oy)
        output.append(
            f'<circle cx="{x:.3f}" cy="{y:.3f}" r="0.9" fill="#c35235" stroke="none"/>'
        )
        output.append(
            f'<text x="{x + 1.5:.3f}" y="{y - 1.5:.3f}" fill="#8c3b2c" stroke="none" font-size="2.8">{notch["id"]}</text>'
        )
    diagnostic = row["projection_diagnostics"]
    loss = diagnostic["projection_length_loss_mm"]
    label = escape(str(row["hoof"]))
    output.append(
        f'<text x="{ox:.2f}" y="{oy - 5:.2f}" fill="#172c39" stroke="none" font-size="3.3">{label} | projected loss {loss:.3f}mm</text>'
    )
    base = gauge_start + i * 13.0 + 7
    finish = pad + diagnostic["perimeter_3d_mm"]
    output.extend(
        [
            f'<line x1="{pad:.3f}" y1="{base:.3f}" x2="{finish:.3f}" y2="{base:.3f}" stroke="#206c83" stroke-width="0.35"/>',
            f'<text x="{pad:.3f}" y="{base - 3:.3f}" fill="#172c39" stroke="none" font-size="2.8">H{i + 1} 3D arc gauge {diagnostic["perimeter_3d_mm"]:.3f} mm</text>',
        ]
    )
    for notch in row["notches"]:
        x = pad + notch["arc_length_3d_mm"]
        output.append(
            f'<line x1="{x:.3f}" y1="{base - 1.5:.3f}" x2="{x:.3f}" y2="{base + 1.5:.3f}" stroke="#c35235" stroke-width="0.45"/>'
        )
    return output


def draw_reference_svg(report):
    """1:1 平面投影与三维弧长标尺；不输出裁切布片。"""
    charts = _validated_charts(report)
    pad = 18.0
    max_w = max(float(extent[0]) for _, extent, _, _ in charts)
    max_h = max(float(extent[1]) for _, extent, _, _ in charts)
    cell_w, cell_h = max_w + 2 * pad, max_h + 2 * pad + 14
    gauge_start = cell_h * 2 + 13
    max_perimeter = max(
        float(row["projection_diagnostics"]["perimeter_3d_mm"])
        for _, _, row, _ in charts
    )
    width = max(cell_w * 2, max_perimeter + 2 * pad)
    height = gauge_start + 13.0 * 4 + 14
    output = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.3f}mm" height="{height:.3f}mm" viewBox="0 0 {width:.3f} {height:.3f}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<g fill="none" stroke="#206c83" stroke-width="0.35">',
    ]
    for i, chart in enumerate(charts):
        output.extend(_draw_chart(i, chart, cell_w, cell_h, gauge_start))
    output.extend(
        [
            "</g>",
            f'<text x="8" y="{height - 9:.2f}" font-size="3.4">1:1 mm | planar projection is NOT A CUT PATTERN</text>',
            f'<text x="8" y="{height - 4:.2f}" font-size="3.1">3D arc-length gauge, Q0-Q3 registration only; no seam allowance</text>',
            "</svg>",
        ]
    )
    return "\n".join(output) + "\n"
