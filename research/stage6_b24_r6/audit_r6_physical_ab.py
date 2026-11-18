"""Compare actual R5 and R6 Blender frame40 mesh with original Stage6 source.

All displayed results use genuine evaluated Cloth vertices, never R6 staging.
The 4 original ear meshes, self-collision and stuffing are not certified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from research.stage6_b24_r3.audit_r3_native_ab import (
    _actual_mesh,
    _geometry_distance,
    _physics_diagnostics,
)
from research.stage6_b24_r5.audit_r5_real_ab import _side_surface_metrics


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _rename_head_metrics(results):
    for row in results.values():
        old_mean = row.pop("R3_mean_distance_mm")
        new_mean = row.pop("R5_mean_distance_mm")
        old_p95 = row.pop("R3_p95_mm")
        new_p95 = row.pop("R5_p95_mm")
        row["R5_mean_distance_mm"] = old_mean
        row["R6_mean_distance_mm"] = new_mean
        row["R5_p95_mm"] = old_p95
        row["R6_p95_mm"] = new_p95
        row["R6_improved"] = row.pop("R5_improved")
    return results


def verify(source, baseline, candidate, output):
    """Separate true geometry improvement from seam and material risks."""
    output = Path(output)
    if output.exists():
        raise FileExistsError("R6 cannot overwrite a previous physical result")
    target = trimesh.load(source, force="mesh")
    if len(target.faces) != 116568:
        raise ValueError("wrong true Stage6 source triangle mesh")
    target.apply_scale(0.001)
    before, springs_old, rest_old, edges_old = _actual_mesh(baseline)
    after, springs_new, rest_new, edges_new = _actual_mesh(candidate)
    if len(before.vertices) != len(after.vertices) or len(after.vertices) != 3139:
        raise ValueError("R6 40-piece candidate topology differs from R5")
    if not np.array_equal(springs_old, springs_new):
        raise ValueError("R6 did not preserve the 1170 native sewing springs")
    if not np.isfinite(after.vertices).all():
        raise ValueError("R6 Blender Cloth vertices are invalid")
    old_shape = _geometry_distance(target, before)
    new_shape = _geometry_distance(target, after)
    old_material = _physics_diagnostics(
        before, springs_old, rest_old, edges_old
    )
    new_material = _physics_diagnostics(
        after, springs_new, rest_new, edges_new
    )
    high = _rename_head_metrics(
        _side_surface_metrics(target, before, after)
    )
    report = {
        "schema": "stage6-R6-monotone-native40f-vs-R5-physical-AB-v1",
        "R5_real_cloth_npz_SHA256": _sha(baseline),
        "R6_real_cloth_npz_SHA256": _sha(candidate),
        "source_Stage6_proxy_PLY_SHA256": _sha(source),
        "same_native_Blender_Cloth_40_frames": True,
        "same_1170_sewing_spring_identity": True,
        "R5_actual_shape": old_shape,
        "R6_actual_shape": new_shape,
        "R5_real_material": old_material,
        "R6_real_material": new_material,
        "source_head_and_high_lobes": high,
        "global_shape_mean_improved": (
            new_shape["symmetric_surface_sample_mean_mm"]
            < old_shape["symmetric_surface_sample_mean_mm"]
        ),
        "material_P95_not_worse": (
            new_material["2d_rest_to_actual_3d_edge_relative_strain_p95_percent"]
            <= old_material["2d_rest_to_actual_3d_edge_relative_strain_p95_percent"]
        ),
        "physical_nonadjacent_self_contact_gate_checked": False,
        "actual_original_Stage6_ear_Mesh_sewn": 0,
        "factory_cut_patterns_approved": 0,
        "P3": "in_progress",
        "P4": "not_started",
    }
    after.export(output.parent / "R6_MONOTONE_REAL_BLENDER_FRAME40_UNAPPROVED.glb")
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print("STAGE6_R6_REAL_FRAME40_VS_R5", json.dumps(report))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "baseline", "candidate", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    verify(args.source, args.baseline, args.candidate, args.out)


if __name__ == "__main__":
    main()
