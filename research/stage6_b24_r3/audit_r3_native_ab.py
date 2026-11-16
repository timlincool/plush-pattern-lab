"""Independent original Stage6 vs actual R2/R3 cloth A/B geometry research QA.

Neither a finite nearest-surface distance nor low seam gap certifies contact,
material stretch, filling or factory-ready sewing patterns.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial import cKDTree


def _actual_mesh(path):
    with np.load(path, allow_pickle=False) as stage:
        verts = stage["evaluated_blender_cloth_vertices_m"].copy()
        rest = stage["true_independent_flat_2d_rest_xy_m"].copy()
        springs = stage["original_sewing_spring_vertex_pairs"].copy()
        lengths = stage["face_lengths"].copy()
        ids = stage["face_vertex_ids"].copy()
    if not np.isfinite(verts).all() or len(verts) != len(rest):
        raise ValueError("invalid original evaluated cloth geometry")
    faces = []
    edge_count = Counter()
    cursor = 0
    for size in lengths:
        polygon = ids[cursor : cursor + int(size)]
        faces.extend(
            (int(polygon[0]), int(polygon[k]), int(polygon[k + 1]))
            for k in range(1, int(size) - 1)
        )
        edge_count.update(
            tuple(sorted((int(a), int(b))))
            for a, b in zip(polygon, np.roll(polygon, -1))
        )
        cursor += int(size)
    if cursor != len(ids) or any(n > 2 for n in edge_count.values()):
        raise ValueError("invalid source surface edge incidence")
    mesh = trimesh.Trimesh(vertices=verts, faces=np.asarray(faces), process=False)
    edges = np.asarray(list(edge_count), dtype=int)
    return mesh, springs, rest, edges


def _geometry_distance(target, observed):
    truth, _ = trimesh.sample.sample_surface(target, 15000, seed=33)
    model, _ = trimesh.sample.sample_surface(observed, 15000, seed=67)
    outward = cKDTree(model).query(truth)[0] * 1000
    inward = cKDTree(truth).query(model)[0] * 1000
    return {
        "symmetric_surface_sample_mean_mm": float((outward.mean() + inward.mean()) / 2),
        "source_to_actual_sample_p95_mm": float(np.percentile(outward, 95)),
        "actual_to_source_sample_p95_mm": float(np.percentile(inward, 95)),
    }


def _physics_diagnostics(mesh, pairs, rest, surface_edges):
    v = mesh.vertices
    seam = np.linalg.norm(v[pairs[:, 0]] - v[pairs[:, 1]], axis=1) * 1000
    physical = np.linalg.norm(v[surface_edges[:, 0]] - v[surface_edges[:, 1]], axis=1)
    material = np.linalg.norm(rest[surface_edges[:, 0]] - rest[surface_edges[:, 1]], axis=1)
    if not np.isfinite(physical).all() or (material <= 1e-11).any():
        raise ValueError("non-finite or collapsed material edge")
    strain = abs(physical / material - 1) * 100
    return {
        "evaluated_3d_vertices": len(v),
        "sewing_springs": len(pairs),
        "final_mean_sewing_gap_mm": float(seam.mean()),
        "final_max_sewing_gap_mm": float(seam.max()),
        "2d_rest_to_actual_3d_edge_relative_strain_p95_percent": float(
            np.percentile(strain, 95)
        ),
        "2d_rest_to_actual_3d_edge_relative_strain_max_percent": float(strain.max()),
    }


def verify(source, baseline, candidate, output):
    if Path(output).exists():
        raise FileExistsError("no overwriting original R3 study result")
    target = trimesh.load(source, force="mesh")
    if len(target.faces) != 116568:
        raise ValueError("wrong real Stage6 25percent source mesh")
    target.apply_scale(0.001)
    before, springs_old, flat_old, edges_old = _actual_mesh(baseline)
    after, springs_new, flat_new, edges_new = _actual_mesh(candidate)
    if len(before.vertices) != 2431 or len(after.vertices) != 2635:
        raise ValueError("true old R2 and new R3 vertex identity changed")
    if not np.array_equal(springs_new[:974], springs_old):
        raise ValueError("old native source-connected sewing springs not preserved")
    old_shape = _geometry_distance(target, before)
    new_shape = _geometry_distance(target, after)
    old_material = _physics_diagnostics(before, springs_old, flat_old, edges_old)
    new_material = _physics_diagnostics(after, springs_new, flat_new, edges_new)
    report = {
        "schema": "stage6-R3-versus-R2-true-Blender-evaluated-same-run-AB-v1",
        "source": "genuine fixed Stage6 25percent proxy, measured against solver meshes",
        "shape_metric": "15k seeded surface points each; KDTree sample nearest; millimeters",
        "R2_true_physical_shape": old_shape,
        "R3_true_physical_shape": new_shape,
        "R2_spring_and_material": old_material,
        "R3_spring_and_material": new_material,
        "R3_mean_shape_improved": bool(
            new_shape["symmetric_surface_sample_mean_mm"]
            < old_shape["symmetric_surface_sample_mean_mm"]
        ),
        "R3_source_to_actual_p95_improved": bool(
            new_shape["source_to_actual_sample_p95_mm"]
            < old_shape["source_to_actual_sample_p95_mm"]
        ),
        "R3_material_strain_p95_not_worse": bool(
            new_material["2d_rest_to_actual_3d_edge_relative_strain_p95_percent"]
            <= old_material["2d_rest_to_actual_3d_edge_relative_strain_p95_percent"]
        ),
        "physical_cloth_self_intersection_tested": False,
        "physical_pressure_fill_tested": False,
        "original_cloud_ear_tail_ornaments_sewn": False,
        "factory_cutting_patterns_approved": 0,
        "P3": "in_progress",
        "P4": "not_started",
    }
    after.export(Path(output).parent / "R3_REAL_40FRAME_CLOTH_NOT_A_FACTORY_TOY.glb")
    Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("STAGE6_R3_ACTUAL_PHYSICAL_AB", json.dumps(report))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "baseline", "candidate", "out"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    verify(args.source, args.baseline, args.candidate, args.out)


if __name__ == "__main__":
    main()