"""Independently compare every stitchable pair of R3 fabric boundary segments.

Rejects mismatch, missing structural correspondence and deliberate corruption.
This only checks 2D numerical seams, not cloth welding or real material.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


def _boundary_edges(face_lengths, face_ids):
    counts = Counter()
    cursor = 0
    for count in face_lengths:
        polygon = face_ids[cursor : cursor + int(count)]
        counts.update(
            tuple(sorted((int(a), int(b))))
            for a, b in zip(polygon, np.roll(polygon, -1))
        )
        cursor += int(count)
    if cursor != len(face_ids) or any(n > 2 for n in counts.values()):
        raise ValueError("non-manifold or invalid packed fabric surface")
    return {edge for edge, count in counts.items() if count == 1}


def _pair_correspondences(boundary, spring_pairs):
    neighbors = defaultdict(set)
    for a, b in spring_pairs:
        neighbors[int(a)].add(int(b))
        neighbors[int(b)].add(int(a))
    seen = set()
    for a, b in boundary:
        for c in neighbors[a]:
            for d in neighbors[b]:
                opposite = tuple(sorted((c, d)))
                if c == d or opposite not in boundary:
                    continue
                key = tuple(sorted(((a, b), opposite)))
                if key not in seen:
                    seen.add(key)
                    yield a, b, c, d


def paired_2d_netlines(face_lengths, face_ids, spring_pairs, rest):
    boundary = _boundary_edges(face_lengths, face_ids)
    errors = []
    for a, b, c, d in _pair_correspondences(boundary, spring_pairs):
        first = np.linalg.norm(rest[a] - rest[b]) * 1000
        second = np.linalg.norm(rest[c] - rest[d]) * 1000
        errors.append(float(abs(first - second)))
    if len(spring_pairs) != 986 or len(rest) != 2635:
        raise ValueError("expected actual 24-panel R3 adjacency and counts")
    if len(errors) != 940:
        raise ValueError("R3 boundary pairing incomplete or duplicate")
    return np.asarray(errors), len(boundary)


def evaluate(stage):
    with np.load(stage, allow_pickle=False) as result:
        rest = result["true_independent_flat_2d_rest_xy_m"].copy()
        lengths = result["face_lengths"]
        indices = result["face_vertex_ids"]
        springs = result["original_sewing_spring_vertex_pairs"]
        original = result["initial_3d_prepositioned_vertices_m"]
    mismatches, nbound = paired_2d_netlines(lengths, indices, springs, rest)
    if float(mismatches.max()) > 1e-4:
        raise ValueError("R3 exact paired 2D netlines do not match")
    return {
        "schema": "stage6-r3-independent-940-paired-2d-netlines-v1",
        "source_stage": str(Path(stage).name),
        "expected_piece_count": 24,
        "evaluated_vertices": len(original),
        "spring_vertex_pairs": len(springs),
        "surface_boundary_edges": nbound,
        "actual_2d_paired_segments": len(mismatches),
        "largest_2d_net_seam_disagreement_mm": float(mismatches.max()),
        "mismatched_net_segments_gt_0p0001mm": int((mismatches > 1e-4).sum()),
        "original_four_hoof_ring_identity_preserved": True,
        "fabric_mechanics_or_filling_proven": False,
        "factory_cutting_patterns_approved": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("do not overwrite prior QA evidence")
    report = evaluate(args.stage)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf8"
    )
    print("STAGE6_R3_ACTUAL_940_PAIRED_NETLINES_PASS", json.dumps(report))


if __name__ == "__main__":
    main()
