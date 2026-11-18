"""Measure genuine R3 vs R5 evaluated cloth geometry, not visual preposition.

Geometric distance is sampled and may favor visual targets while still failing
material, penetration, stuffing, manufacturing, and attachment safety gates.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial import cKDTree

from research.stage6_b24_r3.audit_r3_native_ab import (
    _actual_mesh,
    _geometry_distance,
    _physics_diagnostics,
)


def _side_surface_metrics(target, baseline, candidate):
    truth, _ = trimesh.sample.sample_surface(target, 15000, seed=33)
    base, _ = trimesh.sample.sample_surface(baseline, 15000, seed=67)
    trial, _ = trimesh.sample.sample_surface(candidate, 15000, seed=67)
    masks = {
        "upper_head": truth[:, 2] >= 0.155,
        "actual_high_side_protrusions": (
            (truth[:, 2] >= 0.225) & (abs(truth[:, 0]) >= 0.045)
        ),
    }
    output = {}
    for name, selected in masks.items():
        sample = truth[selected]
        if len(sample) < 40:
            raise ValueError("too few true original Stage6 source side-head points")
        a = cKDTree(base).query(sample)[0] * 1000
        b = cKDTree(trial).query(sample)[0] * 1000
        output[name] = {
            "source_samples": len(sample),
            "R3_mean_distance_mm": float(a.mean()),
            "R5_mean_distance_mm": float(b.mean()),
            "R5_improved": bool(b.mean() < a.mean()),
            "R3_p95_mm": float(np.percentile(a, 95)),
            "R5_p95_mm": float(np.percentile(b, 95)),
        }
    return output


def verify(source, baseline, candidate, output):
    output = Path(output)
    if output.exists():
        raise FileExistsError("true R5 physics A/B cannot overwrite previous evidence")
    target = trimesh.load(source, force="mesh")
    if len(target.faces) != 116568:
        raise ValueError("wrong true Stage6 source triangle mesh")
    target.apply_scale(0.001)
    old, old_springs, old_rest, old_edges = _actual_mesh(baseline)
    new, springs, rest, edges = _actual_mesh(candidate)
    if len(old.vertices) != 2635 or len(new.vertices) != 3139:
        raise ValueError("R5 result is not an actual 40-panel frame40 mesh")
    if springs.shape != (1170, 2) or not np.array_equal(
        old_springs, springs[:986]
    ):
        raise ValueError("R5 did not preserve R3 original spring identity")
    if not np.isfinite(new.vertices).all():
        raise ValueError("R5 native cloth produced nonfinite geometry")
    before = _geometry_distance(target, old)
    after = _geometry_distance(target, new)
    before_material = _physics_diagnostics(old, old_springs, old_rest, old_edges)
    after_material = _physics_diagnostics(new, springs, rest, edges)
    side_metrics = _side_surface_metrics(target, old, new)
    report = {
        "schema": "stage6-R5-40-panel-native-Blender-vs-R3-source-head-AB-v1",
        "true_evaluated_R5_mesh_from_blender": True,
        "comparison": "same source mesh, same native Cloth settings and 40 frames",
        "R3_true_shape": before,
        "R5_true_shape": after,
        "R3_material_and_seams": before_material,
        "R5_material_and_seams": after_material,
        "real_source_head_and_side_protrusion_metrics": side_metrics,
        "R5_global_shape_improved": bool(
            after["symmetric_surface_sample_mean_mm"]
            < before["symmetric_surface_sample_mean_mm"]
        ),
        "R5_material_strain_P95_not_worse": bool(
            after_material["2d_rest_to_actual_3d_edge_relative_strain_p95_percent"]
            <= before_material["2d_rest_to_actual_3d_edge_relative_strain_p95_percent"]
        ),
        "source_4_ear_meshes_physically_sewn": 0,
        "self_collision_and_filling_tested": False,
        "factory_cutting_patterns_approved": 0,
        "P3": "in_progress", "P4": "not_started",
    }
    new.export(output.parent / "R5_TRUE_40FRAME_CLOTH_WITH_TWO_SOURCE_LOBE_RESEARCH.glb")
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("R5_REAL_BLENDER_SHAPE_AB", json.dumps(report))
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "baseline", "candidate", "out"):
        p.add_argument("--" + name, required=True, type=Path)
    args = p.parse_args()
    verify(args.source, args.baseline, args.candidate, args.out)


if __name__ == "__main__":
    main()
