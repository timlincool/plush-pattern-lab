"""Independent native B24 R1/R2 evaluated Cloth A/B: geometry, seams, strain."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial import cKDTree

SOURCE_SHA = "5b52e3fd09c83b19c5b9d95d6d8d859a147ff4deef90f1518f868d2e82e3a2dd"


def rebuild_mesh(path):
    with np.load(path, allow_pickle=False) as data:
        vertices = data["evaluated_blender_cloth_vertices_m"]
        rest = data["true_independent_flat_2d_rest_xy_m"]
        springs = data["original_sewing_spring_vertex_pairs"]
        counts = data["face_lengths"]
        packed = data["face_vertex_ids"]
    if vertices.shape != (2431, 3) or rest.shape != (2431, 2):
        raise ValueError("actual B24 mesh vertex counts changed")
    if springs.shape != (974, 2) or not np.isfinite(vertices).all():
        raise ValueError("changed physical sewing graph or invalid XYZ")
    triangles, material_edges = [], set()
    cursor = 0
    for count in counts:
        polygon = packed[cursor : cursor + int(count)]
        triangles.extend(
            (int(polygon[0]), int(polygon[i]), int(polygon[i + 1]))
            for i in range(1, int(count) - 1)
        )
        material_edges.update(
            tuple(sorted((int(a), int(b))))
            for a, b in zip(polygon, np.roll(polygon, -1))
        )
        cursor += int(count)
    if cursor != len(packed) or len(triangles) != 2950:
        raise ValueError("R2 original face topology mismatch")
    mesh = trimesh.Trimesh(vertices=vertices, faces=triangles, process=False)
    return mesh, rest, springs, np.asarray(sorted(material_edges), dtype=int)


def compare_surface(source, actual):
    a, _ = trimesh.sample.sample_surface(source, 15000, seed=33)
    b, _ = trimesh.sample.sample_surface(actual, 15000, seed=67)
    from_source = cKDTree(b).query(a)[0] * 1000
    from_actual = cKDTree(a).query(b)[0] * 1000
    return {
        "symmetric_mean_mm": float((from_source.mean() + from_actual.mean()) / 2),
        "source_to_actual_P95_mm": float(np.percentile(from_source, 95)),
        "actual_to_source_P95_mm": float(np.percentile(from_actual, 95)),
    }


def seam_strain(mesh, rest, springs, edges):
    verts = mesh.vertices
    gaps = np.linalg.norm(verts[springs[:, 0]] - verts[springs[:, 1]], axis=1) * 1000
    rest_length = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1)
    actual_length = np.linalg.norm(verts[edges[:, 0]] - verts[edges[:, 1]], axis=1)
    if not (rest_length > 1e-11).all():
        raise ValueError("zero-length R2 original 2D material edge")
    return {
        "mean_spring_gap_mm": float(gaps.mean()),
        "max_spring_gap_mm": float(gaps.max()),
        "absolute_rest_to_final_edge_error_P95_percent": float(
            np.percentile(abs(actual_length / rest_length - 1) * 100, 95)
        ),
    }


def audit(source, baseline, candidate, out):
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError("incorrect authentic Stage6 source PLY")
    original = trimesh.load(source, force="mesh")
    if len(original.faces) != 116568:
        raise ValueError("wrong Stage6 source proxy mesh")
    original.apply_scale(0.001)
    old, old_uv, old_pairs, old_edges = rebuild_mesh(baseline)
    new, new_uv, new_pairs, new_edges = rebuild_mesh(candidate)
    if not np.array_equal(old_pairs, new_pairs) or not np.array_equal(
        old_edges, new_edges
    ):
        raise ValueError("R2 changed the 974 sewing springs or source face graph")
    a = compare_surface(original, old)
    b = compare_surface(original, new)
    report = {
        "schema": "stage6-B24-R2-same-run-real-Blender-evaluated-ab-v1",
        "source_proxy_sha256": SOURCE_SHA,
        "actual_B24_R1_shape": a,
        "actual_B24_R2_shape": b,
        "actual_R1_physical": seam_strain(old, old_uv, old_pairs, old_edges),
        "actual_R2_physical": seam_strain(new, new_uv, new_pairs, new_edges),
        "R2_mean_shape_improved": bool(b["symmetric_mean_mm"] < a["symmetric_mean_mm"]),
        "R2_source_P95_improved": bool(
            b["source_to_actual_P95_mm"] < a["source_to_actual_P95_mm"]
        ),
        "source_ears_cloud_tail_unsewn": True,
        "collision_and_stuffing_unverified": True,
        "factory_patterns_approved": 0,
        "promote_to_P4": False,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "B24_R2_vs_R1_REAL_Blender_AB.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    new.export(out / "B24_R2_REAL_Blender_Cloth_frame40.glb")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("source", "baseline", "candidate", "out"):
        parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            audit(args.source, args.baseline, args.candidate, args.out),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
