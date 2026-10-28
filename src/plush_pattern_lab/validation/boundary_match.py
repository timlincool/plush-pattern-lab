"""纯数值闭合缝环匹配：验证形状、周长、反向绕序与一对一对应。

输入坐标统一为毫米。坐标吻合只能说明三维几何接口成立，
不表示已经展平二维裁片、缝合、填棉或通过安全检查。
"""

import numpy as np

MAX_RING_VERTICES = 4096


def as_ring_mm(points):
    """拒绝退化、非有限、错误单位维度与过大输入。"""
    ring = np.asarray(points, dtype=np.float64)
    if ring.ndim != 2 or ring.shape[1] != 3:
        raise ValueError("闭合缝环必须是 N×3 毫米坐标")
    if not 3 <= len(ring) <= MAX_RING_VERTICES or not np.isfinite(ring).all():
        raise ValueError("缝环顶点数量或数值不合法")
    lengths = np.linalg.norm(ring - np.roll(ring, 1, axis=0), axis=1)
    if np.any(lengths <= 0):
        raise ValueError("缝环包含连续重复点或零长度边")
    return ring


def perimeter_mm(points):
    """计算闭合环的三维边长总和，不以平面投影代替。"""
    ring = as_ring_mm(points)
    return float(np.linalg.norm(ring - np.roll(ring, 1, axis=0), axis=1).sum())


def cyclic_match_mm(source, target):
    """枚举起点和正反方向，寻找均方误差最小的一一顶点对应。"""
    body, hoof = as_ring_mm(source), as_ring_mm(target)
    if len(body) != len(hoof):
        raise ValueError("两条环的采样点数不同，禁止自行重采样")
    best = None
    for is_reversed in (False, True):
        ordered = hoof[::-1] if is_reversed else hoof
        for offset in range(len(body)):
            gaps = np.linalg.norm(body - np.roll(ordered, offset, axis=0), axis=1)
            rms = float(np.sqrt(np.mean(gaps * gaps)))
            maximum = float(gaps.max())
            if best is None or (rms, maximum) < (
                best["rms_gap_mm"],
                best["max_gap_mm"],
            ):
                best = {
                    "rms_gap_mm": rms,
                    "max_gap_mm": maximum,
                    "reversed_boundary_winding": is_reversed,
                    "cyclic_shift": offset,
                    "vertex_count": len(body),
                }
    return best


def unique_centroid_mapping(body_rings, hoof_rings):
    """四蹄分别选择最近的主体开口，并拒绝一个开口匹配多只蹄。"""
    if not body_rings or len(body_rings) != len(hoof_rings):
        raise ValueError("主体环与蹄环必须非空且数量相同")
    bodies = [as_ring_mm(x) for x in body_rings]
    targets = [as_ring_mm(x) for x in hoof_rings]
    body_centers = [ring.mean(axis=0) for ring in bodies]
    used = set()
    matched = []
    for hoof in targets:
        center = hoof.mean(axis=0)
        gaps = [float(np.linalg.norm(center - p)) for p in body_centers]
        selected = int(np.argmin(gaps))
        if selected in used:
            raise ValueError("蹄部到主体环无法建立唯一映射")
        used.add(selected)
        matched.append((selected, gaps[selected]))
    return matched


def verify_mating_loops(body, hoof, tolerance_mm=0.0001):
    """严守世界坐标和方向，不通过则由调用者明确拒绝晋升。"""
    if not 0 < tolerance_mm <= 0.01:
        raise ValueError("不允许放宽几何判定容差")
    match = cyclic_match_mm(body, hoof)
    source_length = perimeter_mm(body)
    target_length = perimeter_mm(hoof)
    delta = abs(source_length - target_length)
    return {
        **match,
        "body_perimeter_mm": source_length,
        "hoof_perimeter_mm": target_length,
        "perimeter_delta_mm": delta,
        "tolerance_mm": tolerance_mm,
        "world_boundary_geometry_match": (
            match["max_gap_mm"] <= tolerance_mm
            and delta <= tolerance_mm
            and match["reversed_boundary_winding"]
        ),
    }
