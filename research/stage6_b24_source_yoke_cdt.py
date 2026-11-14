"""Use GEOS/Shapely constrained Delaunay on genuine B24 research yoke with four holes.

A standalone 2D fabric polygon and its four original hoof ring samples, no new
mesh solver. The resulting 326 triangles MUST preserve all five 64-edge loops.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import Polygon

SCHEMA = "stage6-b24-four-hoof-hole-constrained-yoke-mesh-v1"
FOOTS = ("FL", "FR", "RL", "RR")


def build(lower, digest):
    yoke = lower["yoke"]
    outer = np.asarray(yoke["outer_stitch_xy_mm"], dtype=float)
    holes = [
        np.asarray(yoke["source_hoof_holes_stitch_xy_mm"][key], dtype=float)[::8]
        for key in FOOTS
    ]
    if (
        lower.get("schema") != "stage6-source-hoof-anchored-lower-mother-toile-v1"
        or lower.get("approved_industrial_paper_patterns") != 0
        or outer.shape != (64, 2)
        or any(x.shape != (64, 2) for x in holes)
        or not all(np.isfinite(x).all() for x in [outer, *holes])
        or not hasattr(shapely, "constrained_delaunay_triangles")
    ):
        raise ValueError("requires true research 4-hoof-hole polygon and Shapely CDT")
    polygon = Polygon(outer, holes)
    if not polygon.is_valid or polygon.area < 100:
        raise ValueError("original source-hoof four-hole research yoke is invalid")
    flat = np.vstack([outer, *holes])
    lookup = {tuple(np.round(p, 8)): i for i, p in enumerate(flat)}
    if len(lookup) != len(flat):
        raise ValueError("old B24 original hoop sample vertices overlap")
    triangles = []
    real_area = 0.0
    for patch in shapely.constrained_delaunay_triangles(polygon).geoms:
        if patch.geom_type != "Polygon" or len(patch.exterior.coords) != 4:
            raise ValueError("non-triangular constrained GEOS result")
        ring = list(patch.exterior.coords)[:-1]
        try:
            ids = tuple(lookup[tuple(np.round(point, 8))] for point in ring)
        except KeyError as exc:
            raise ValueError("Shapely CDT added a new manufactured vertex") from exc
        if len(set(ids)) != 3 or patch.area < 1e-9:
            raise ValueError("degenerate constrained yoke triangle")
        triangles.append(ids)
        real_area += patch.area
    count = Counter(
        tuple(sorted((u, v)))
        for triangle in triangles
        for u, v in zip(triangle, triangle[1:] + triangle[:1])
    )
    boundary = {key for key, visits in count.items() if visits == 1}
    reference = {
        tuple(sorted((offset + i, offset + (i + 1) % 64)))
        for offset in (0, 64, 128, 192, 256)
        for i in range(64)
    }
    if (
        len(triangles) != 326
        or boundary != reference
        or set(count.values()) - {1, 2}
        or abs(real_area - polygon.area) > 1e-6
    ):
        raise ValueError("CDT did not preserve five original stitching loops")
    return {
        "schema": SCHEMA,
        "source_lower_mother_json_sha256": digest,
        "open_source": "Shapely constrained_delaunay_triangles / GEOS",
        "source_2d_fabric_boundaries": 5,
        "original_source_yoke_outer_and_four_hoof_rings_64_edges_each": True,
        "original_stitch_loop_boundary_edges": 320,
        "source_original_yoke_area_mm2": float(polygon.area),
        "triangles_local_original_yoke_vertex_ids": triangles,
        "original_2d_yoke_vertices": 320,
        "additional_steiner_vertices": 0,
        "factory_cutting_patterns_approved": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lower", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if (
        not args.lower.is_file()
        or args.lower.is_symlink()
        or args.out.exists()
        or args.out.is_symlink()
    ):
        raise ValueError("missing original source or already existing yoke output")
    raw = args.lower.read_bytes()
    model = build(json.loads(raw), hashlib.sha256(raw).hexdigest())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(model, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf8",
    )
    print(
        "STAGE6_B24_ORIGINAL_2D_YOKE_FOUR_HOOF_HOLES_CDT_LOCKED",
        len(model["triangles_local_original_yoke_vertex_ids"]),
        flush=True,
    )


if __name__ == "__main__":
    main()
