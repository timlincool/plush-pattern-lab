"""Independently reject or screen native ABF on genuine Stage6 short cut seams.

Reuse original Stage6 source vertex identity, exact original 3D triangles,
existing P95 gauge / triangle overlap and two-sided source seam auditing.
No mathematical research gate is a factory fabric certification.
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
    _two_true_planar_seam_sides,
)

SCHEMA = "stage6-original-high-protrusion-short-slit-ABF-source-seam-QA-v1"
SOURCE_SCHEMA = "stage6-original-ear-high-protrusion-short-open-slit-v1"
UV_SCHEMA = "stage6-original-high-protrusion-short-dart-native-blender-ABF-v1"
CAPS_SCHEMA = "stage6-genuine-source-z230-three-open-caps-v1"
ROUTES = ("Y_REAR_RIM_TO_TIP", "X_INNER_RIM_TO_TIP")
SIDES = ("left_high_protrusion", "right_high_protrusion")


def _paired_segmentwise_absolute_mismatch(disk, mm):
    faces = np.asarray(disk["disk_triangle_vertex_ids"], dtype=np.int64)
    identity = np.asarray(
        disk["original_patch_vertex_id_per_disk_vertex"], dtype=np.int64
    )
    original_path = disk["slit_original_local_vertex_ids"]
    edges = _oriented_disk_boundary_edges(faces)
    grouped = defaultdict(list)
    for a, b in edges:
        grouped[tuple(sorted((int(identity[a]), int(identity[b]))))].append((a, b))
    mismatches = []
    for a, b in zip(original_path[:-1], original_path[1:]):
        paired = grouped[tuple(sorted((a, b)))]
        forward = [row for row in paired if identity[row[0]] == a]
        reverse = [row for row in paired if identity[row[0]] == b]
        if len(paired) != 2 or len(forward) != 1 or len(reverse) != 1:
            raise ValueError("cut source seam does not have opposite 2D copies")
        length = [
            float(np.linalg.norm(mm[u] - mm[v]))
            for u, v in (forward[0], reverse[0])
        ]
        mismatches.append(abs(length[0] - length[1]))
    return float(sum(mismatches) / disk["real_source_3d_slit_length_mm"])


def _verify_original_geometry(disk, cap):
    original = np.asarray(cap["vertices_xyz_mm"], dtype=float)
    original_faces = np.asarray(cap["triangles_local_vertex_indices"], dtype=int)
    xyz = np.asarray(disk["source_xyz_mm"], dtype=float)
    faces = np.asarray(disk["disk_triangle_vertex_ids"], dtype=int)
    source_ids = np.asarray(
        disk["original_patch_vertex_id_per_disk_vertex"], dtype=int
    )
    path = np.asarray(disk["slit_original_local_vertex_ids"], dtype=int)
    if (
        original.ndim != 2
        or xyz.ndim != 2
        or xyz.shape[1] != 3
        or faces.shape != original_faces.shape
        or len(path) < 2
        or not np.isfinite(xyz).all()
        or np.any(source_ids < 0)
        or np.any(source_ids >= len(original))
        or np.any(faces < 0)
        or np.any(faces >= len(xyz))
        or len(xyz) != len(original) + len(path) - 1
        or not np.array_equal(source_ids[: len(original)], np.arange(len(original)))
        or not np.array_equal(source_ids[len(original) :], path[:-1])
        or not np.array_equal(xyz, original[source_ids])
        or not np.array_equal(source_ids[faces], original_faces)
        or disk.get("source_tip_vertex_not_duplicated") is not True
        or disk.get("topological_Euler") != 1
    ):
        raise ValueError("not exactly all original source triangles with short seam copies")
    physical = float(np.linalg.norm(np.diff(original[path], axis=0), axis=1).sum())
    if abs(physical - disk["real_source_3d_slit_length_mm"]) > 1e-8:
        raise ValueError("original source 3D short-seam length changed")
    return xyz, faces, path


def _one(disk, entry, original):
    if (
        entry.get("source_cap_id") != disk["id"]
        or entry.get("source_vertex_count") != len(disk["source_xyz_mm"])
        or entry.get("source_triangle_count") != len(disk["disk_triangle_vertex_ids"])
        or entry.get("original_cut_rim_edges") != disk["source_boundary_edges"]
        or entry.get("maximum_split_UV_loop_disagreement", 1) > 1e-5
    ):
        raise ValueError("native ABF does not index original 3D short-dart disk")
    xyz, faces, path = _verify_original_geometry(disk, original)
    uv = np.asarray(entry["uv_per_3d_cap_source_vertex"], dtype=np.float64)
    if uv.shape != (len(xyz), 2) or not np.isfinite(uv).all():
        raise ValueError("invalid native Blender ABF coordinates")
    mm, _, edge = _scale_free_gauge(xyz, faces, uv)
    topology = _face_overlap_and_winding(xyz, faces, mm)
    seam = _two_true_planar_seam_sides(disk, mm)
    mismatch = _paired_segmentwise_absolute_mismatch(disk, mm)
    original_len = disk["real_source_3d_slit_length_mm"]
    first = seam["scaled_planar_2d_first_source_netline_length_mm"]
    second = seam["scaled_planar_2d_second_source_netline_length_mm"]
    physical_diff = max(abs(first - original_len), abs(second - original_len))
    gates = {
        "original_3d_all_triangle_edge_P95_le_10_percent": (
            edge["scaled_2d_p95_abs_edge_relative_error"] <= 0.10
        ),
        "original_cut_2d_paired_segment_abs_diff_le_3_percent": mismatch <= 0.03,
        "two_2d_sides_each_within_3percent_of_3d_seam": (
            physical_diff / original_len <= 0.03
        ),
        "no_2d_triangle_flips": topology["reversed_or_collapsed_triangle_count"] == 0,
        "no_positive_area_2d_triangle_overlaps": (
            topology["overlapping_positive_area_triangle_pair_count"] == 0
        ),
    }
    return {
        "id": disk["id"],
        "route": disk["route"],
        "source_cap_id": disk["source_cap_id"],
        "original_source_triangle_count": len(faces),
        "original_3d_source_path_vertex_count": len(path),
        "source_3d_seam_mm": original_len,
        "original_cap_source_3d_full_meridian_mm": disk[
            "source_original_full_meridian_3d_mm"
        ],
        "scaled_2d_source_edge_P95_relative_error": edge[
            "scaled_2d_p95_abs_edge_relative_error"
        ],
        "scaled_2d_first_side_seam_mm": first,
        "scaled_2d_second_side_seam_mm": second,
        "scaled_2d_paired_segment_cumulative_abs_mismatch_fraction": mismatch,
        "max_one_2d_side_deviation_from_3d_source_fraction": (
            physical_diff / original_len
        ),
        "2d_flipped_or_collapsed_triangle_count": topology[
            "reversed_or_collapsed_triangle_count"
        ],
        "2d_positive_area_overlap_triangle_pairs": topology[
            "overlapping_positive_area_triangle_pair_count"
        ],
        "research_quality_checks": gates,
        "all_limited_research_checks_passed": all(gates.values()),
        "source_3d_triangle_geometry_or_original_face_order_modified": False,
        "factory_cutting_patterns_approved": 0,
    }


def audit(short, caps, native, short_sha, caps_sha):
    if (
        short.get("schema") != SOURCE_SCHEMA
        or short.get("same_run_caps_sha256") != caps_sha
        or short.get("factory_cutting_patterns_approved") != 0
        or short.get("P3_status") != "in_progress"
        or short.get("P4_status") != "not_started"
        or caps.get("schema") != CAPS_SCHEMA
        or caps.get("industrial_cutting_patterns_approved") != 0
        or native.get("schema") != UV_SCHEMA
        or native.get("same_run_source_short_slits_sha256") != short_sha
        or native.get("blender_version") != "4.3.2"
        or native.get("solver") != "ANGLE_BASED"
        or native.get("factory_cutting_patterns_approved") != 0
    ):
        raise ValueError("candidate ABF and original Stage6 3D source SHA mismatch")
    all_caps = {c["id"]: c for c in caps["upper_caps"]}
    disks = short["four_real_original_cap_short_slit_disks"]
    rows = native["entries"]
    if len(disks) != 4 or len(rows) != 4:
        raise ValueError("all four predeclared short source slits required")
    checked = []
    for index, (disk, uv) in enumerate(zip(disks, rows)):
        if (
            disk["route"] != ROUTES[index // 2]
            or disk["source_cap_id"] != SIDES[index % 2]
            or uv["route"] != disk["route"]
        ):
            raise ValueError("predeclared original short source seam order changed")
        checked.append(_one(disk, uv, all_caps[disk["source_cap_id"]]))
    return {
        "schema": SCHEMA,
        "source_original_genuine_caps_sha256": caps_sha,
        "source_short_open_slit_study_sha256": short_sha,
        "solver": "Blender4.3.2 native ANGLE_BASED",
        "quality_3d_source_face_and_2d_seam_checks": checked,
        "four_predeclared_short_slits_tested": len(checked),
        "both_rear_and_inner_original_3d_source_edges_tested": True,
        "all_four_limited_research_checks_passed": all(
            x["all_limited_research_checks_passed"] for x in checked
        ),
        "no_real_fabric_or_pile_hidden_seam_proven": True,
        "matching_lower_7rim_source_body_2d_seam_not_available": True,
        "factory_cutting_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
    }


def _read(path):
    if not path.is_file() or path.is_symlink():
        raise ValueError("missing original Stage6 source or ABF proof")
    return path.read_bytes()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--caps", required=True, type=Path)
    parser.add_argument("--native", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise ValueError("do not overwrite original prior research evidence")
    source_raw, caps_raw = _read(args.source), _read(args.caps)
    report = audit(
        json.loads(source_raw),
        json.loads(caps_raw),
        json.loads(_read(args.native)),
        hashlib.sha256(source_raw).hexdigest(),
        hashlib.sha256(caps_raw).hexdigest(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(
        "STAGE6_SHORT_REAR_INNER_NATIVE_ABF_3D_SOURCE_AND_TWO_2D_SEAM_QA",
        [
            {
                "route": x["route"],
                "side": x["source_cap_id"],
                "P95": x["scaled_2d_source_edge_P95_relative_error"],
                "paired_abs_mismatch": x[
                    "scaled_2d_paired_segment_cumulative_abs_mismatch_fraction"
                ],
                "factory_approved": False,
            }
            for x in report["quality_3d_source_face_and_2d_seam_checks"]
        ],
        flush=True,
    )


if __name__ == "__main__":
    main()
