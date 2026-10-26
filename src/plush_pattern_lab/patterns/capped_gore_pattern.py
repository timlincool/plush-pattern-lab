#!/usr/bin/env python3
"""Synthetic plush gores with explicit top/bottom cap pieces, no pole singularity.

Geometry-only *stitch-line* design. This does NOT claim virtual sewing was
executed or that a specific fabric can support the needed deformations.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon


def _cap_ring(half_width, panels, allowance_mm, top):
    """Construct and validate one independent top/bottom stitch cap."""
    width = float(half_width[0 if top else -1])
    radius = width / (2 * math.sin(math.pi / (2 * panels)))
    if radius <= 0:
        raise ValueError("Cap radius collapsed")
    angles = (np.arange(2 * panels) - 1) * math.pi / panels
    points = np.c_[radius * np.cos(angles), radius * np.sin(angles)]
    polygon = Polygon(points)
    allowance = polygon.buffer(allowance_mm, join_style=1, quad_segs=12)
    if not polygon.is_valid or polygon.area <= 0 or allowance.geom_type != "Polygon":
        raise ValueError("Cap shape invalid")
    edge_length = np.linalg.norm(np.roll(points, -1, axis=0) - points, axis=1)
    if np.max(np.abs(edge_length - width)) > 1e-8:
        raise ValueError("Cap and gore stitch segment mismatch")
    return {
        "stitch_ring_2d_mm": points.tolist(),
        "cut_outline_2d_mm": np.asarray(allowance.exterior.coords).tolist(),
        "stitch_perimeter_mm": float(edge_length.sum()),
        "cut_area_mm2": float(allowance.area),
        "net_area_mm2": float(polygon.area),
        "radius_mm": radius,
        "edge_length_max_mismatch_mm": float(np.max(abs(edge_length - width))),
        "end_gore_halfwidth_mm": width,
    }


def make(
    radius_mm=55.0,
    half_height_mm=70.0,
    panels=8,
    segments=64,
    pole_cut_deg=8.0,
    allowance_mm=6.0,
):
    if not (
        5 <= radius_mm <= 250
        and 10 <= half_height_mm <= 500
        and 6 <= panels <= 24
        and 24 <= segments <= 256
        and 2 <= pole_cut_deg <= 20
        and 0 <= allowance_mm <= 12
    ):
        raise ValueError("Outside bounded research parameters")
    theta0 = math.radians(pole_cut_deg)
    theta = np.linspace(theta0, math.pi - theta0, segments + 1)
    r = radius_mm * np.sin(theta)
    z = half_height_mm * np.cos(theta)
    ds = np.hypot(np.diff(r), np.diff(z))
    half_width = r * math.pi / panels
    dw = np.diff(half_width)
    squared = ds * ds - dw * dw
    if (squared < -1e-9).any():
        raise ValueError("2D meridian geometry cannot preserve segment lengths")
    y = np.r_[0.0, np.cumsum(np.sqrt(np.maximum(squared, 0.0)))]
    left = np.c_[-half_width, y]
    right = np.c_[half_width, y]
    seam = Polygon(np.r_[left, right[::-1]])
    if not seam.is_valid or seam.area <= 0 or seam.geom_type != "Polygon":
        raise ValueError("Self-intersecting or collapsed 2D gores")
    cut = seam.buffer(allowance_mm, join_style=1, quad_segs=12)
    if cut.geom_type != "Polygon" or not cut.is_valid:
        raise ValueError("Gore seam allowance invalid")

    top = _cap_ring(half_width, panels, allowance_mm, True)
    bottom = _cap_ring(half_width, panels, allowance_mm, False)
    joined = []
    length = float(ds.sum())
    for i in range(panels):
        joined.append(
            {
                "type": "longitudinal",
                "a": f"P{i:02d}.right",
                "b": f"P{(i + 1) % panels:02d}.left",
                "length_mm": length,
            }
        )
        indices = [(2 * i + j) % (2 * panels) for j in range(3)]
        # Explicit mapping of left, midpoint, right source vertices to cap.
        for position, part in (("upper", top), ("lower", bottom)):
            joined.append(
                {
                    "type": position,
                    "a": f"P{i:02d}.{position}",
                    "b": f"{position}_cap.ring",
                    "a_positions": ["left", "middle", "right"],
                    "b_vertex_indices": indices,
                    "stitch_length_mm": float(
                        half_width[0 if position == "upper" else -1] * 2
                    ),
                    "cap_stitch_length_mm": float(part["stitch_perimeter_mm"] / panels),
                }
            )
    seam_errors = [
        abs(j["stitch_length_mm"] - j["cap_stitch_length_mm"])
        for j in joined
        if j["type"] != "longitudinal"
    ]
    if max(seam_errors) > 1e-7:
        raise ValueError("Unpaired transverse seams")
    return {
        "schema": "synthetic-capped-plush-pattern-v1",
        "status": "NET_PATTERN_GEOMETRY_ONLY_NO_SEWING_OR_STUFFING_CERTIFICATION",
        "parameters": {
            "radius_mm": radius_mm,
            "half_height_mm": half_height_mm,
            "panels": panels,
            "segments": segments,
            "pole_cut_deg": pole_cut_deg,
            "allowance_mm": allowance_mm,
        },
        "geometry": {
            "theta_radians": theta.tolist(),
            "radial_mm": r.tolist(),
            "z_mm": z.tolist(),
            "latitude_reference_positions_are_predefined": True,
        },
        "gore": {
            "left_stitch_2d_mm": left.tolist(),
            "right_stitch_2d_mm": right.tolist(),
            "cut_outline_2d_mm": np.asarray(cut.exterior.coords).tolist(),
            "net_area_mm2": float(seam.area),
            "cut_area_mm2": float(cut.area),
            "longitudinal_stitch_length_mm": length,
            "grain_direction": [0, 1],
        },
        "caps": {"upper": top, "lower": bottom},
        "sewing_pairs": joined,
        "quality": {
            "max_cross_stitch_length_mismatch_mm": max(seam_errors),
            "number_of_distinct_net_pieces": panels + 2,
            "number_of_stitch_relations": len(joined),
            "first_and_last_ring_radii_positive": bool(min(r) > 0),
            "zero_area_poles_eliminated_by_truncation": True,
            "seam_length_verification_only": True,
            "flattening_strain_measured": False,
            "virtual_sewing_executed": False,
            "real_material_measured": False,
            "stuffing_modeled": False,
        },
        "limitations": [
            "The two round caps are geometry prototypes; fabric grain/darts not optimized",
            "Explicit 3D/2D seam mapping is not a tested sewing simulation",
            "Side seam length equality and cap arc equality are necessary but not sufficient",
            "Missing measured fabric, filling, collision and physical sample validation",
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--panels", type=int, default=8)
    p.add_argument("--pole-cut-deg", type=float, default=8)
    p.add_argument("--radius-mm", type=float, default=55)
    p.add_argument("--half-height-mm", type=float, default=70)
    p.add_argument("--allowance-mm", type=float, default=6)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError("Refuse to overwrite pattern")
    v = make(
        radius_mm=a.radius_mm,
        half_height_mm=a.half_height_mm,
        panels=a.panels,
        pole_cut_deg=a.pole_cut_deg,
        allowance_mm=a.allowance_mm,
    )
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(
        json.dumps(v, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(json.dumps(v["quality"], ensure_ascii=False))


if __name__ == "__main__":
    main()
