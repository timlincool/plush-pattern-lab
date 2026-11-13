"""Compare installed FreeCAD flatmesh with already-verified Blender ABF fairly.

No new UV solver, custom relaxation, fabric assumptions or pattern generation.
The existing source-indexed metric evaluator is reused for FreeCAD output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path

import numpy as np

from plush_pattern_lab.validation.stage6_external_uv_benchmark import _metrics
from run_stage6_freecad_flatmesh import SCHEMA, SOLVER, SOURCE_SHA, source_disks

REPORT_SCHEMA = "stage6-freecad-flatmesh-vs-native-blender-abf-research-v1"
ABF_SCHEMA = "stage6-free-blender-native-uv-abf-conformal-raw-v1"
AUDIT_SCHEMA = "stage6-free-external-uv-same-source-apples-to-apples-v1"


def _key(item):
    return (
        item["source_variant"],
        item.get("original_source_side", item.get("source_side")),
        item.get("source_slit_direction", item.get("slit_direction")),
    )


def _index(rows):
    indexed = {_key(row): row for row in rows}
    if len(indexed) != 12 or len(rows) != 12:
        raise ValueError("twelve unique original Stage6 N15/N17 source disks required")
    return indexed


def _validate(source, flat, native, audit, source_digest, native_digest):
    if (
        flat.get("schema") != SCHEMA
        or flat.get("method") != SOLVER
        or flat.get("source_study_sha256") != source_digest
        or flat.get("source_blend_sha256") != SOURCE_SHA
        or flat.get("factory_cutting_patterns_approved") != 0
        or native.get("schema") != ABF_SCHEMA
        or native.get("source_study_sha256") != source_digest
        or native.get("source_blend_sha256") != SOURCE_SHA
        or native.get("methods") != ["ANGLE_BASED", "CONFORMAL"]
        or native.get("cutting_patterns_approved") != 0
        or audit.get("schema") != AUDIT_SCHEMA
        or audit.get("same_run_source_study_sha256") != source_digest
        or audit.get("same_run_free_blender_native_raw_sha256") != native_digest
        or audit.get("factory_cutting_patterns_approved") != 0
    ):
        raise ValueError("FreeCAD and ABF results are not from the same Stage6 source")
    originals = _index(source_disks(source))
    flat_rows = _index(flat["entries"])
    abf_rows = [
        entry for entry in native["entries"] if entry["method"] == "ANGLE_BASED"
    ]
    abf = _index(abf_rows)
    baseline_rows = [
        {**row, "source_side": row["source_side"],
         "slit_direction": row["original_source_slit"]}
        for row in audit["full_same_metric_comparisons"]
    ]
    measured = _index(baseline_rows)
    return originals, flat_rows, abf, measured


def compare(source, flat, native, audit, source_digest, native_digest):
    originals, proposed, abf, baseline = _validate(
        source, flat, native, audit, source_digest, native_digest
    )
    rows = []
    for key, original in originals.items():
        fc = proposed[key]
        bl = abf[key]
        old = baseline[key]
        expected_vertices = len(original["cut_disk_source_xyz_mm"])
        expected_faces = len(original["cut_disk_original_source_triangle_indices"])
        if (
            fc.get("status") != "completed"
            or bl.get("status") != "completed"
            or fc.get("source_patch_sha256")
            != original["original_source_patch_sha256"]
            or bl.get("source_patch_sha256")
            != original["original_source_patch_sha256"]
            or fc.get("source_vertex_count") != expected_vertices
            or fc.get("source_triangle_count") != expected_faces
            or bl.get("vertex_count") != expected_vertices
            or bl.get("triangle_count") != expected_faces
        ):
            raise ValueError("candidate changed original Stage6 triangle/vertex identity")
        geom = np.asarray(fc["uv_per_original_source_disk_vertex"], dtype=float)
        trial = _metrics(original, geom, SOLVER)
        a = [x for x in old["external_blender_solvers"] if x["method"] == "ANGLE_BASED"]
        if len(a) != 1:
            raise ValueError("verified native Blender ABF baseline missing")
        blender = a[0]
        edge = "scaled_2d_p95_abs_edge_relative_error"
        seam = "2d_two_sides_length_mismatch_fraction_of_source_3d"
        rows.append({
            "source_variant": key[0],
            "side": key[1],
            "slit_direction": key[2],
            "original_source_patch_sha256": original["original_source_patch_sha256"],
            "freecad_native_seconds": fc["solver_seconds"],
            "freecad": trial,
            "blender_ABF": blender,
            "freecad_better_P95": trial[edge] < blender[edge],
            "freecad_better_two_sided_seam": trial[seam] < blender[seam],
            "freecad_meets_research_gate": trial["passes_unverified_research_thresholds"],
        })
    edge = "scaled_2d_p95_abs_edge_relative_error"
    seam = "2d_two_sides_length_mismatch_fraction_of_source_3d"
    return {
        "schema": REPORT_SCHEMA,
        "source_original_stage6_sha256": SOURCE_SHA,
        "source_study_sha256": source_digest,
        "blender_native_raw_sha256": native_digest,
        "solver": SOLVER,
        "independent_common_metric_evaluator": "_metrics/stage6_external_uv_benchmark",
        "same_original_source_faces_and_cut_edges_for_every_pair": True,
        "cases": rows,
        "count": len(rows),
        "freecad_P95_median": statistics.median(x["freecad"][edge] for x in rows),
        "ABF_P95_median": statistics.median(x["blender_ABF"][edge] for x in rows),
        "freecad_two_side_seam_diff_median": statistics.median(
            x["freecad"][seam] for x in rows
        ),
        "ABF_two_side_seam_diff_median": statistics.median(
            x["blender_ABF"][seam] for x in rows
        ),
        "freecad_better_P95_cases": sum(x["freecad_better_P95"] for x in rows),
        "freecad_better_seam_cases": sum(
            x["freecad_better_two_sided_seam"] for x in rows
        ),
        "freecad_research_gate_passed": sum(
            x["freecad_meets_research_gate"] for x in rows
        ),
        "real_fabric_not_tested": True,
        "factory_cutting_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
    }


def _load(path):
    if not path.is_file() or path.is_symlink():
        raise ValueError("missing unsigned same-run source")
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--native", required=True, type=Path)
    parser.add_argument("--audit", required=True, type=Path)
    parser.add_argument("--freecad", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise ValueError("do not overwrite earlier FreeCAD research")
    source, digest = _load(args.source)
    native, native_digest = _load(args.native)
    audit, _ = _load(args.audit)
    flat, _ = _load(args.freecad)
    result = compare(source, flat, native, audit, digest, native_digest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print("STAGE6_FREECAD_VS_ABF_REAL_SAME_SOURCE_RESEARCH", json.dumps({
        "count": result["count"],
        "freecad_better_P95_cases": result["freecad_better_P95_cases"],
        "freecad_better_seam_cases": result["freecad_better_seam_cases"],
        "factory_approved": False,
    }), flush=True)


if __name__ == "__main__":
    main()
