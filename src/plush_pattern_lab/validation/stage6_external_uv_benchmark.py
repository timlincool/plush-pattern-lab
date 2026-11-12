"""Independent common metrics for existing LSCM vs free Blender ABF/Conformal.

All inputs are *the same* twelve true original Stage6 mesh disks. Blender
texture UV has NO physical size; apply the identical uniform relative-edge
least-squares scale used for the in-repo LSCM before comparing distortion.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict

import numpy as np

from plush_pattern_lab.validation.stage6_ear_slit_lscm import (
    _face_overlap_and_winding,
    _scale_free_gauge,
    _two_true_planar_seam_sides,
)

SCHEMA = "stage6-free-external-uv-same-source-apples-to-apples-v1"
NATIVE_SCHEMA = "stage6-free-blender-native-uv-abf-conformal-raw-v1"
ORIGINAL_SCHEMA = "stage6-ear-root-genuine-source-disk-lscm-research-v1"
METHODS = ("ANGLE_BASED", "CONFORMAL")
MAX_UV_VERTEX_DISAGREEMENT = 1e-5


def _identity(row):
    return (
        row["source_variant"],
        row.get("original_source_side", row.get("source_side")),
        row.get("source_slit_direction", row.get("slit_direction")),
    )


def _reference_original(source):
    if (
        source.get("schema") != ORIGINAL_SCHEMA
        or source.get("factory_cutting_patterns_approved") != 0
        or source.get("P3_status") != "in_progress"
        or source.get("P4_status") != "not_started"
    ):
        raise ValueError("original source Stage6 factory-gated input required")
    rows = source["candidate_2d_research_disks"]
    if len(rows) != 12 or len({_identity(row) for row in rows}) != 12:
        raise ValueError("must compare all twelve fixed real source disks")
    return {_identity(row): row for row in rows}


def _validate_native(native, source_hash, source):
    if (
        native.get("schema") != NATIVE_SCHEMA
        or native.get("blender_version") != "4.3.2"
        or native.get("source_study_sha256") != source_hash
        or native.get("source_blend_sha256")
        != source.get("original_public_blend_sha256")
        or native.get("methods") != list(METHODS)
        or native.get("third_party_commercial_service_used") is not False
        or native.get("cutting_patterns_approved") != 0
    ):
        raise ValueError("external native UV result not on same trusted Stage6 source")
    items = native["entries"]
    if (
        len(items) != 24
        or len({(_identity(item), item["method"]) for item in items}) != 24
    ):
        raise ValueError(
            "must include exactly twelve source disks x two native methods"
        )
    if any(item["method"] not in METHODS for item in items):
        raise ValueError("unrecognized Blender native solver")
    return items


def _disk_geometry(row):
    points = np.asarray(row["cut_disk_source_xyz_mm"], dtype=float)
    faces = np.asarray(row["cut_disk_original_source_triangle_indices"], dtype=np.int64)
    if (
        points.ndim != 2
        or points.shape[1] != 3
        or faces.ndim != 2
        or faces.shape[1] != 3
        or len(points) < 20
        or np.any(faces < 0)
        or np.any(faces >= len(points))
        or not np.isfinite(points).all()
    ):
        raise ValueError("invalid original source disk geometry")
    disk = {
        "source_xyz_mm": points,
        "disk_triangle_vertex_ids": faces,
        "slit_original_local_vertex_ids": row[
            "actual_slit_original_source_local_vertex_ids"
        ],
        "original_patch_vertex_id_per_disk_vertex": np.asarray(
            row["cut_disk_source_vertex_identity"], dtype=np.int64
        ),
        "real_source_3d_slit_length_mm": row["source_3d_cut_length_mm"],
    }
    return points, faces, disk


def _metrics(row, uv, method):
    if uv.ndim != 2 or uv.shape[1] != 2 or not np.isfinite(uv).all():
        raise ValueError("external native UV is nonfinite or malformed")
    points, faces, disk = _disk_geometry(row)
    if uv.shape != (len(points), 2) or not np.isfinite(uv).all():
        raise ValueError("native Blender UV not finite or not source-index aligned")
    planar, _, length_stats = _scale_free_gauge(points, faces, uv.copy())
    faces_stats = _face_overlap_and_winding(points, faces, planar)
    seam_stats = _two_true_planar_seam_sides(disk, planar)
    if not seam_stats[
        "original_source_cut_edge_has_exactly_two_oppositely_oriented_disk_sides"
    ]:
        raise ValueError("external UV broke real source seam identity")
    return {
        "method": method,
        "scaled_2d_p95_abs_edge_relative_error": length_stats[
            "scaled_2d_p95_abs_edge_relative_error"
        ],
        "scaled_2d_p50_abs_edge_relative_error": length_stats[
            "scaled_2d_p50_abs_edge_relative_error"
        ],
        "2d_two_sides_length_mismatch_fraction_of_source_3d": seam_stats[
            "scaled_planar_2d_two_sides_length_mismatch_fraction_of_source_3d"
        ],
        "2d_two_sides_length_mismatch_mm": seam_stats[
            "scaled_planar_2d_two_sides_length_mismatch_mm"
        ],
        "2d_max_per_source_seam_segment_length_difference_mm": seam_stats[
            "scaled_planar_2d_max_original_segment_pair_length_difference_mm"
        ],
        "inverted_or_collapsed_2d_source_faces": faces_stats[
            "reversed_or_collapsed_triangle_count"
        ],
        "overlapping_positive_area_face_pairs": faces_stats[
            "overlapping_positive_area_triangle_pair_count"
        ],
        "overlap_area_mm2": faces_stats["overlap_triangle_area_mm2"],
        "source_3d_real_netline_length_mm": row["source_3d_cut_length_mm"],
        "input_original_source_face_count": len(faces),
        "uniform_scale_from_native_uv_to_research_mm": length_stats[
            "uniform_isotropic_scale_from_minimum_squared_edge_relative_error"
        ],
        "passes_unverified_research_thresholds": (
            length_stats["scaled_2d_p95_abs_edge_relative_error"] <= 0.10
            and seam_stats[
                "scaled_planar_2d_two_sides_length_mismatch_fraction_of_source_3d"
            ]
            <= 0.03
            and faces_stats["reversed_or_collapsed_triangle_count"] == 0
            and faces_stats["overlapping_positive_area_triangle_pair_count"] == 0
        ),
        "these_thresholds_are_not_factory_criteria": True,
    }


def _original_method(row):
    length = row["uniform_scale_normalized_edge_diagnostics"]
    seam = row["true_source_seam_3d_vs_lscm_2d_pairing"]
    faces = row["original_source_planar_face_geometry_diagnostics"]
    return {
        "method": "EXISTING_LSCM",
        "scaled_2d_p95_abs_edge_relative_error": length[
            "scaled_2d_p95_abs_edge_relative_error"
        ],
        "2d_two_sides_length_mismatch_fraction_of_source_3d": seam[
            "scaled_planar_2d_two_sides_length_mismatch_fraction_of_source_3d"
        ],
        "inverted_or_collapsed_2d_source_faces": faces[
            "reversed_or_collapsed_triangle_count"
        ],
        "overlapping_positive_area_face_pairs": faces[
            "overlapping_positive_area_triangle_pair_count"
        ],
        "source_3d_real_netline_length_mm": row["source_3d_cut_length_mm"],
        "passes_unverified_research_thresholds": False,
        "these_thresholds_are_not_factory_criteria": True,
    }


def compare_native_to_existing(source, native, source_file_sha256):
    """Re-score external independent Blender UV against pinned old LSCM."""
    reference = _reference_original(source)
    native_entries = _validate_native(native, source_file_sha256, source)
    grouped = defaultdict(dict)
    for entry in native_entries:
        key = _identity(entry)
        if key not in reference:
            raise ValueError("external Blender UV candidate does not match source")
        if (
            entry.get("source_patch_sha256")
            != reference[key]["original_source_patch_sha256"]
            or entry.get("status") != "completed"
            or entry["vertex_count"] != len(reference[key]["cut_disk_source_xyz_mm"])
            or entry["triangle_count"]
            != len(reference[key]["cut_disk_original_source_triangle_indices"])
        ):
            raise ValueError("native result does not preserve source triangulation")
        grouped[key][entry["method"]] = entry
    rows = []
    improvements = {
        method: {
            "lower_p95_edge_error": 0,
            "lower_seam_mismatch": 0,
            "better_both": 0,
            "research_gates_passed": 0,
        }
        for method in METHODS
    }
    for key, source_row in reference.items():
        baseline = _original_method(source_row)
        options = []
        for method in METHODS:
            entry = grouped[key][method]
            if (
                entry["max_same_topological_vertex_uv_loop_disagreement"]
                > MAX_UV_VERTEX_DISAGREEMENT
            ):
                # A chart split invalidates the use of ONE UV per original disk vertex.
                raise ValueError("Blender UV added an unaccounted-for internal UV seam")
            uv = np.asarray(entry["uv_per_original_source_disk_vertex"], dtype=float)
            candidate = _metrics(source_row, uv, method)
            improvement = {
                "lower_p95_edge_error": (
                    candidate["scaled_2d_p95_abs_edge_relative_error"]
                    < baseline["scaled_2d_p95_abs_edge_relative_error"]
                ),
                "lower_seam_mismatch": (
                    candidate["2d_two_sides_length_mismatch_fraction_of_source_3d"]
                    < baseline["2d_two_sides_length_mismatch_fraction_of_source_3d"]
                ),
            }
            improvement["better_both"] = all(improvement.values())
            for label, passed in improvement.items():
                improvements[method][label] += int(passed)
            improvements[method]["research_gates_passed"] += int(
                candidate["passes_unverified_research_thresholds"]
            )
            candidate["compared_to_existing_lscm"] = improvement
            candidate["blender_runtime_seconds"] = entry["runtime_seconds"]
            options.append(candidate)
        rows.append(
            {
                "source_variant": key[0],
                "source_side": key[1],
                "original_source_slit": key[2],
                "existing_solver": baseline,
                "external_blender_solvers": options,
            }
        )
    return {
        "schema": SCHEMA,
        "source_original_3d_source_mesh_and_cut_ids_unchanged": True,
        "external_engine": "Blender 4.3.2 native unwrap (free, commercial use allowed)",
        "independently_tested_methods": list(METHODS),
        "total_source_disks": len(rows),
        "native_solver_cases": len(native_entries),
        "method_comparison_summary": improvements,
        "all_same_3d_inputs_tested_without_new_seam_selection": True,
        "full_same_metric_comparisons": rows,
        "no_commercial_closed_source_software_or_payment": True,
        "no_fabric_material_model_or_real_assembly_approved": True,
        "factory_cutting_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
    }


def fingerprint_source_bytes(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_comparison_svg(report):
    """Small scoreboard chart from measured values, no generated cut pattern."""
    if (
        report.get("schema") != SCHEMA
        or len(report.get("full_same_metric_comparisons", [])) != 12
    ):
        raise ValueError("expected all twelve source-disk comparisons")
    colors = {
        "EXISTING_LSCM": "#56677b",
        "ANGLE_BASED": "#256ea6",
        "CONFORMAL": "#bd7a28",
    }
    width, height = 1390, 850
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fcfcfa"/>',
        '<text x="24" y="36" font-family="sans-serif" font-size="21" '
        'fill="#1b3448">12 REAL Stage6 root disks | free external UV solver benchmark</text>',
        '<text x="24" y="58" font-family="sans-serif" font-size="13" '
        'fill="#ae3430">SOURCE-IDENTICAL RESEARCH ONLY / NO FACTORY PATTERNS</text>',
    ]
    rows = report["full_same_metric_comparisons"]
    headings = [
        ("P95 source-edge length error", "scaled_2d_p95_abs_edge_relative_error"),
        (
            "2D source cut side length mismatch",
            "2d_two_sides_length_mismatch_fraction_of_source_3d",
        ),
    ]
    for axis, (name, field) in enumerate(headings):
        x0 = 24 + axis * 694
        out.append(
            f'<text x="{x0}" y="103" font-family="sans-serif" font-size="15">'
            f"{name} (lower is better)</text>"
        )
        allvalues = [
            value[field]
            for row in rows
            for value in [row["existing_solver"], *row["external_blender_solvers"]]
        ]
        scale = 465 / max(max(allvalues), 0.01)
        for i, row in enumerate(rows):
            y = 136 + i * 53
            label = f"{row['source_variant'].split('_', 1)[0]} {row['source_side'][0]} {row['original_source_slit'][0:4]}"
            out.append(
                f'<text x="{x0}" y="{y + 23}" font-family="sans-serif" '
                f'font-size="11" fill="#41566a">{label}</text>'
            )
            for j, value in enumerate(
                [row["existing_solver"], *row["external_blender_solvers"]]
            ):
                ybase = y + j * 12
                bar = max(0.7, scale * value[field])
                out.append(
                    f'<rect x="{x0 + 132}" y="{ybase}" width="{bar:.2f}" height="9" '
                    f'fill="{colors[value["method"]]}"/>'
                )
    out.extend(
        [
            '<text x="26" y="827" font-family="sans-serif" font-size="12" '
            'fill="#526579">Grey: original in-repo LSCM | Blue: Blender ABF | '
            "Ochre: Blender Conformal. Metrics use SAME physical source triangles.</text>",
            "</svg>",
        ]
    )
    return "\n".join(out) + "\n"
