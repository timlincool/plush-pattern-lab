"""Independently reject mismatched R4 2D netlines or distorted material edges."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

from research.stage6_b24_r3.audit_r3_matched_netlines import (
    _boundary_edges,
    _pair_correspondences,
)


def audit(stage):
    with np.load(stage, allow_pickle=False) as data:
        uv = data["true_independent_flat_2d_rest_xy_m"]
        initial = data["initial_3d_prepositioned_vertices_m"]
        sizes = data["face_lengths"]
        ids = data["face_vertex_ids"]
        pairs = data["original_sewing_spring_vertex_pairs"]
    if initial.shape != (2699, 3) or uv.shape != (2699, 2):
        raise ValueError("expected exact original R3 with 64 new crown points")
    if len(sizes) != 2054 or pairs.shape != (986, 2):
        raise ValueError("R4 face or 986-spring topology changed")
    bounds = _boundary_edges(sizes, ids)
    mismatches = []
    for a, b, c, d in _pair_correspondences(bounds, pairs):
        left = np.linalg.norm(uv[a] - uv[b])
        right = np.linalg.norm(uv[c] - uv[d])
        mismatches.append(abs(left - right) * 1000)
    if len(mismatches) != 940 or max(mismatches) > 0.0001:
        raise ValueError("R4 cannot maintain 940 exactly matched 2D net seams")
    edge_count = Counter()
    start = 0
    for size in sizes:
        face = ids[start : start + int(size)]
        edge_count.update(
            tuple(sorted((int(a), int(b)))) for a, b in zip(face, np.roll(face, -1))
        )
        start += int(size)
    if start != len(ids) or max(edge_count.values()) > 2:
        raise ValueError("R4 original source cloth surface is nonmanifold")
    edges = np.asarray(list(edge_count), dtype=int)
    flat = np.linalg.norm(uv[edges[:, 0]] - uv[edges[:, 1]], axis=1)
    real = np.linalg.norm(initial[edges[:, 0]] - initial[edges[:, 1]], axis=1)
    if (flat < 1e-11).any():
        raise ValueError("collapsed R4 material edge")
    strain = abs(real / flat - 1) * 100
    p95 = float(np.percentile(strain, 95))
    if p95 > 10.5 or strain.max() > 75:
        raise ValueError("R4 material preposition research gates not met")
    return {
        "schema": "stage6-r4-940-segment-material-QA-v1",
        "numerically_paired_stitch_edges": len(mismatches),
        "max_2d_paired_seam_difference_mm": float(max(mismatches)),
        "material_preposition_edge_strain_p95_pct": p95,
        "material_preposition_edge_strain_max_pct": float(strain.max()),
        "springs": len(pairs),
        "source_3d_high_side_protrusions_physically_sewn": False,
        "blender_physics_executed": False,
        "factory_approved_patterns": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError("refuse replacing existing R4 QA")
    report = audit(args.stage)
    args.out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf8",
    )
    print("R4_940_NETLINE_AND_MATERIAL_QA_PASS", json.dumps(report))


if __name__ == "__main__":
    main()
