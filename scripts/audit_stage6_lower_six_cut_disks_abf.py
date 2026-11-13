"""Independent Stage6 seven-port lower ABF rejection and true 2D seam pairing.

Four actual 3D source disks + six copied 3D cutting paths. The 2D paper
pattern may still fail: this validator never overrides manufacturing gates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from plush_pattern_lab.validation.stage6_ear_slit_lscm import (
    _face_overlap_and_winding,
    _oriented_disk_boundary_edges,
    _scale_free_gauge,
)

SCHEMA = "stage6-true-lower-seven-ports-four-source-disks-ABF-seam-QA-v1"
SOURCE_SCHEMA = "stage6-seven-original-ports-six-source-interrim-disk-cuts-v1"
ABF_SCHEMA = "stage6-true-lower-seven-port-four-disks-native-Blender-ABF-v1"
ZONES = ("left_front", "left_rear", "right_front", "right_rear")
PAIRS = {"0:1": 126, "0:2": 321, "1:3": 233, "2:3": 121}


def _validate_zone(part, uv):
    xyz = np.asarray(part["source_3d_xyz_mm"], dtype=np.float64)
    faces = np.asarray(part["triangles_local_vertex_indices"], dtype=np.int64)
    source_id = np.asarray(
        part["original_lower_mesh_vertex_id_per_disk_vertex"], dtype=np.int64
    )
    flat = np.asarray(uv["uv_per_3d_cap_source_vertex"], dtype=np.float64)
    boundary = part["final_original_source_disk_rim_vertex_ids_in_order"]
    if (
        uv.get("source_cap_id") != part["id"]
        or uv.get("source_vertex_count") != len(xyz)
        or uv.get("source_triangle_count") != len(faces)
        or uv.get("original_cut_rim_edges") != len(boundary)
        or uv.get("maximum_split_UV_loop_disagreement", 1) > 1e-5
        or xyz.ndim != 2
        or xyz.shape[1] != 3
        or faces.ndim != 2
        or faces.shape[1] != 3
        or flat.shape != (len(xyz), 2)
        or len(source_id) != len(xyz)
        or np.any(source_id < 0)
        or np.any(faces < 0)
        or np.any(faces >= len(xyz))
        or not np.isfinite(flat).all()
        or not np.isfinite(xyz).all()
        or part.get("topological_Euler") != 1
    ):
        raise ValueError("ABF mismatch with real Stage6 original source disk")
    _, initial = np.unique(source_id, return_index=True)
    id_to_xyz = {int(source_id[i]): xyz[i] for i in initial}
    if any(not np.array_equal(point, id_to_xyz[int(v)])
           for point, v in zip(xyz, source_id)):
        raise ValueError("source 3D copied vertices have different XYZ")
    return xyz, faces, source_id, flat


def _actual_boundary_lengths(faces, xyz, mm, source_id):
    directed = _oriented_disk_boundary_edges(faces)
    result = defaultdict(list)
    for u, v in directed:
        a, b = int(source_id[u]), int(source_id[v])
        if a == b:
            raise ValueError("collapsed original Stage6 3D source rim edge")
        key = tuple(sorted((a, b)))
        result[key].append({
            "original_direction": (a, b),
            "planar_length_mm": float(np.linalg.norm(mm[u] - mm[v])),
            "source_3d_length_mm": float(np.linalg.norm(xyz[u] - xyz[v])),
        })
    return result


def _new_seams(part, boundary):
    results = []
    for original in part["original_source_3d_disk_seam_paths"]:
        vertices = original["original_3d_clipped_lower_source_vertex_ids"]
        physical = original["original_3d_netline_mm"]
        total_a, total_b, mismatch, measured = 0.0, 0.0, 0.0, 0.0
        for a, b in zip(vertices, vertices[1:]):
            pair = boundary[tuple(sorted((int(a), int(b))))]
            forward = [
                x for x in pair if x["original_direction"] == (a, b)
            ]
            backward = [
                x for x in pair if x["original_direction"] == (b, a)
            ]
            if len(pair) != 2 or len(forward) != 1 or len(backward) != 1:
                raise ValueError("one original 3D seam lacks opposite 2D copies")
            left, right = forward[0], backward[0]
            if abs(left["source_3d_length_mm"] - right["source_3d_length_mm"]) > 1e-8:
                raise ValueError("the 3D source seam changed between disk copies")
            total_a += left["planar_length_mm"]
            total_b += right["planar_length_mm"]
            measured += left["source_3d_length_mm"]
            mismatch += abs(left["planar_length_mm"] - right["planar_length_mm"])
        if abs(measured - physical) > 1e-7:
            raise ValueError("original Stage6 3D seam length was changed")
        results.append({
            "seam_role": original["seam_role"],
            "original_3d_netline_mm": physical,
            "original_source_edge_count": len(vertices) - 1,
            "first_2d_netline_mm": total_a,
            "second_2d_netline_mm": total_b,
            "two_2d_segmentwise_absolute_mismatch_fraction": mismatch / physical,
            "two_2d_sides_each_within_3pct_of_3d": (
                max(abs(total_a - physical), abs(total_b - physical)) / physical
                <= 0.03
            ),
            "paired_2d_netline_within_3pct": mismatch / physical <= 0.03,
            "not_a_fabric_sewing_approval": True,
        })
    return results


def _score_one(part, uv):
    xyz, faces, source_id, raw = _validate_zone(part, uv)
    mm, _, edge = _scale_free_gauge(xyz, faces, raw)
    surface = _face_overlap_and_winding(xyz, faces, mm)
    boundary = _actual_boundary_lengths(faces, xyz, mm, source_id)
    seams = _new_seams(part, boundary)
    acceptable = (
        edge["scaled_2d_p95_abs_edge_relative_error"] <= 0.1
        and surface["reversed_or_collapsed_triangle_count"] == 0
        and surface["overlapping_positive_area_triangle_pair_count"] == 0
        and all(
            s["paired_2d_netline_within_3pct"]
            and s["two_2d_sides_each_within_3pct_of_3d"]
            for s in seams
        )
    )
    return {
        "id": part["id"],
        "original_source_faces_count": len(faces),
        "real_3d_source_edge_to_native_ABF_2d_P95_relative_error": edge[
            "scaled_2d_p95_abs_edge_relative_error"
        ],
        "real_3d_source_edge_to_native_ABF_2d_P50_relative_error": edge[
            "scaled_2d_p50_abs_edge_relative_error"
        ],
        "flipped_or_collapsed_2d_triangles": surface[
            "reversed_or_collapsed_triangle_count"
        ],
        "overlapping_positive_area_2d_triangle_pairs": surface[
            "overlapping_positive_area_triangle_pair_count"
        ],
        "new_original_3d_source_cut_two_2d_sides": seams,
        "limited_individual_source_disk_ABF_gate_passed": acceptable,
        "industrial_cutting_pattern_approved": False,
    }, boundary


def _crosszone_sources(borders):
    groups = defaultdict(list)
    for zone, border in enumerate(borders):
        for key, occurrences in border.items():
            if len(occurrences) == 1:
                groups[key].append((zone, occurrences[0]))
            elif len(occurrences) != 2:
                raise ValueError("original lower source edge has too many copies")
    outcome = {}
    for key, entries in groups.items():
        if len(entries) != 2:
            continue
        (a, first), (b, second) = entries
        if a == b:
            raise ValueError("same disk cannot claim a crosszone source seam")
        pair = f"{min(a,b)}:{max(a,b)}"
        if pair not in PAIRS:
            raise ValueError("unexpected original lower Stage6 inter-zone contact")
        if abs(first["source_3d_length_mm"] - second["source_3d_length_mm"]) > 1e-8:
            raise ValueError("original Stage6 3D crosszone edge length mismatch")
        entry = outcome.setdefault(
            pair, {"edge_count": 0, "source_3d_mm": 0.0,
                   "two_2d_segmentwise_absolute_difference_mm": 0.0}
        )
        entry["edge_count"] += 1
        entry["source_3d_mm"] += first["source_3d_length_mm"]
        entry["two_2d_segmentwise_absolute_difference_mm"] += abs(
            first["planar_length_mm"] - second["planar_length_mm"]
        )
    if {pair: p["edge_count"] for pair, p in outcome.items()} != PAIRS:
        raise ValueError("original lower Stage6 source interzone seam edges omitted")
    for entry in outcome.values():
        entry["two_2d_mismatch_fraction"] = (
            entry["two_2d_segmentwise_absolute_difference_mm"]
            / entry["source_3d_mm"]
        )
        entry["original_two_2d_netlines_within_3pct"] = (
            entry["two_2d_mismatch_fraction"] <= 0.03
        )
    return outcome


def audit(source, native, source_sha):
    if (
        source.get("schema") != SOURCE_SCHEMA
        or source.get("source_3d_six_interrim_paths") != 6
        or source.get("factory_cutting_patterns_approved") != 0
        or [x["id"] for x in source.get("source_topological_disks", [])]
        != list(ZONES)
        or native.get("schema") != ABF_SCHEMA
        or native.get("source_six_cut_original_3D_disks_sha256") != source_sha
        or native.get("solver") != "ANGLE_BASED"
        or native.get("blender_version") != "4.3.2"
        or native.get("factory_cutting_patterns_approved") != 0
        or len(native.get("native_original_source_vertex_ABF_results", [])) != 4
    ):
        raise ValueError("untrusted original Stage6 source disk/ABF identity")
    scores = []
    borders = []
    rows = native["native_original_source_vertex_ABF_results"]
    for part, uv in zip(source["source_topological_disks"], rows):
        score, boundary = _score_one(part, uv)
        scores.append(score)
        borders.append(boundary)
    crosszone = _crosszone_sources(borders)
    return {
        "schema": SCHEMA,
        "source_original_lower_seven_port_six_disk_sha256": source_sha,
        "original_true_lower_source_triangles": source[
            "source_3d_total_original_lower_face_count"
        ],
        "source_four_real_disk_ABF_results": scores,
        "four_source_3d_original_zone_paired_2d_interface_results": crosszone,
        "all_four_disks_limited_ABF_gate_passed": all(
            x["limited_individual_source_disk_ABF_gate_passed"] for x in scores
        ),
        "all_crosszone_interfaces_paired_2d_within_3pct": all(
            x["original_two_2d_netlines_within_3pct"]
            for x in crosszone.values()
        ),
        "actual_three_upper_crown_cap_2d_mates_not_yet_verified": True,
        "original_four_hoof_fabric_cuff_2d_mates_not_yet_verified": True,
        "original_design_and_real_fabric_not_tested": True,
        "factory_cutting_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
    }


def _raw(path):
    if not path.is_file() or path.is_symlink():
        raise ValueError("original lower source disk or ABF output is missing")
    return path.read_bytes()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise ValueError("do not overwrite genuine Stage6 source research")
    raw = _raw(args.source)
    outcome = audit(
        json.loads(raw),
        json.loads(_raw(args.native)),
        hashlib.sha256(raw).hexdigest(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(outcome, ensure_ascii=False, indent=2) + "\n",
        encoding="utf8",
    )
    print(
        "STAGE6_LOWER_FOUR_TRUE_DISKS_NATIVE_ABF_RESEARCH_NOT_FACTORY",
        json.dumps({
            "disks": [
                {
                    "id": s["id"],
                    "P95": s[
                        "real_3d_source_edge_to_native_ABF_2d_P95_relative_error"
                    ],
                    "flipped": s["flipped_or_collapsed_2d_triangles"],
                    "overlap": s["overlapping_positive_area_2d_triangle_pairs"],
                }
                for s in outcome["source_four_real_disk_ABF_results"]
            ],
            "crosszone_2d_mismatch": {
                k: v["two_2d_mismatch_fraction"]
                for k, v in outcome[
                    "four_source_3d_original_zone_paired_2d_interface_results"
                ].items()
            },
            "factory_cutting": 0,
        }),
        flush=True,
    )


if __name__ == "__main__":
    main()
