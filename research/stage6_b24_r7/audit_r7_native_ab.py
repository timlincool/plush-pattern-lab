"""Compare R6/R7 genuine Blender frame40 meshes against the real Stage6 shell.

Does not infer physical contact or manufacturing acceptance from shape alone.
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

SOURCE_SHA = "5b52e3fd09c83b19c5b9d95d6d8d859a147ff4deef90f1518f868d2e82e3a2dd"


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _rename_regions(metrics):
    for item in metrics.values():
        item["R6_mean_mm"] = item.pop("R3_mean_distance_mm")
        item["R7_mean_mm"] = item.pop("R5_mean_distance_mm")
        item["R6_p95_mm"] = item.pop("R3_p95_mm")
        item["R7_p95_mm"] = item.pop("R5_p95_mm")
        item["R7_improved"] = item.pop("R5_improved")
    return metrics


def evaluate(source, r6_snapshot, r7_snapshot, output):
    """Reject altered sewing topology; separately score shape and material."""
    path = Path(output)
    if path.exists():
        raise FileExistsError("refuse to overwrite actual R7 physical evidence")
    if _hash(source) != SOURCE_SHA:
        raise ValueError("Stage6 original proxy SHA changed")
    original = trimesh.load(source, force="mesh")
    if len(original.faces) != 116568:
        raise ValueError("not the true original Stage6 25% proxy")
    original.apply_scale(0.001)
    old, old_pairs, old_rest, old_edges = _actual_mesh(r6_snapshot)
    new, new_pairs, new_rest, new_edges = _actual_mesh(r7_snapshot)
    if len(old.vertices) != 3139 or len(new.vertices) != 3139:
        raise ValueError("R7 source 40-piece cloth topology changed")
    if old_pairs.shape != (1170, 2) or not np.array_equal(old_pairs, new_pairs):
        raise ValueError("R7 altered 1170 exact seam spring identities")
    original_shape = _geometry_distance(original, old)
    revised_shape = _geometry_distance(original, new)
    before = _physics_diagnostics(old, old_pairs, old_rest, old_edges)
    after = _physics_diagnostics(new, new_pairs, new_rest, new_edges)
    zones = _rename_regions(_side_surface_metrics(original, old, new))
    report = {
        "schema": "stage6-R7-root-lift-native-Blender40f-vs-R6-v1",
        "R6_snapshot_SHA256": _hash(r6_snapshot),
        "R7_snapshot_SHA256": _hash(r7_snapshot),
        "source_proxy_SHA256": SOURCE_SHA,
        "same_Blender_4_3_2_native_40frames": True,
        "original_1170_spring_IDs_preserved": True,
        "R6_shape": original_shape,
        "R7_shape": revised_shape,
        "R6_material": before,
        "R7_material": after,
        "upper_head_and_side_lobe_regions": zones,
        "R7_global_shape_improved": (
            revised_shape["symmetric_surface_sample_mean_mm"]
            < original_shape["symmetric_surface_sample_mean_mm"]
        ),
        "R7_material_p95_not_worse": (
            after["2d_rest_to_actual_3d_edge_relative_strain_p95_percent"]
            <= before["2d_rest_to_actual_3d_edge_relative_strain_p95_percent"]
        ),
        "nonadjacent_triangle_contact_not_checked_here": True,
        "no_filling_collision_or_real_original_ears_sewn": True,
        "factory_patterns_approved": 0,
        "P3": "in_progress",
        "P4": "not_started",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    new.export(path.parent / "R7_REAL_CLOTH_FRAME40_RESEARCH_ONLY.glb")
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("STAGE6_R7_TRUE_NATIVE_40F_AB", json.dumps(report))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "baseline", "candidate", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    evaluate(args.source, args.baseline, args.candidate, args.out)


if __name__ == "__main__":
    main()
