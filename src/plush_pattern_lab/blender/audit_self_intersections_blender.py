"""Independent finite nonadjacent triangle-intersection screen on saved Blender meshes.

Uses Blender's BVHTree.overlap for triangle/triangle intersection candidates;
the Blender C implementation invokes isect_tri_tri_v3, but this is not a
formal guarantee for coplanar degeneracies, near contacts, or finite-thickness
fabric. No source model or candidate is modified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils.bvhtree import BVHTree

MAX_TRIANGLES = 12000
MAX_PAIRS = 100000
SNAPSHOT_NAME = "CAP_FINAL_SHAPE_NOT_MANUFACTURING"
CLOTH_NAME = "EXPERIMENT_EXPLICIT_CAP_SEWING_NOT_PRODUCTION"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_geometry(vertices, triangles, seam_edges=()):
    coords = [tuple(map(float, p)) for p in vertices]
    faces = [tuple(map(int, f)) for f in triangles]
    if not (4 <= len(coords) <= 30000 and 2 <= len(faces) <= MAX_TRIANGLES):
        raise ValueError("Geometry outside finite screen budget")
    if any(len(v) != 3 or any(not math.isfinite(x) for x in v) for v in coords):
        raise ValueError("Non-finite coordinate or wrong dimension")
    if any(
        len(t) != 3 or len(set(t)) != 3 or any(i < 0 or i >= len(coords) for i in t)
        for t in faces
    ):
        raise ValueError("Degenerate indexed triangle")
    neighbors = defaultdict(set)
    seam_list = [tuple(map(int, edge)) for edge in seam_edges]
    for u, v in seam_list:
        if u == v or min(u, v) < 0 or max(u, v) >= len(coords):
            raise ValueError("Invalid sewing pair")
        neighbors[u].add(v)
        neighbors[v].add(u)
    tree = BVHTree.FromPolygons(coords, faces, all_triangles=True, epsilon=0.0)
    raw = tree.overlap(tree)
    if len(raw) > MAX_PAIRS * 2:
        raise RuntimeError(
            "Raw intersection witness budget exceeded: do not silently truncate"
        )
    candidates = {tuple(sorted((i, j))) for i, j in raw if i != j}
    if len(candidates) > MAX_PAIRS:
        raise RuntimeError("Intersection witness budget exceeded")
    shared = seam_related = nonseam = 0
    seam_witnesses, nonseam_witnesses = [], []
    for i, j in sorted(candidates):
        f1, f2 = faces[i], faces[j]
        if set(f1) & set(f2):
            shared += 1
            continue
        near_seam = any(v in neighbors[u] for u in f1 for v in f2)
        if near_seam:
            seam_related += 1
            if len(seam_witnesses) < 20:
                seam_witnesses.append([i, j])
        else:
            nonseam += 1
            if len(nonseam_witnesses) < 20:
                nonseam_witnesses.append([i, j])
    return {
        "status": "FINITE_ZERO_THICKNESS_TRIANGLE_INTERSECTION_SCREEN",
        "vertex_count": len(coords),
        "triangle_count": len(faces),
        "sewing_identity_links": len(seam_list),
        "candidate_pairs_from_blender_bvh": len(candidates),
        "shared_vertex_pairs_excluded": shared,
        "nonadjacent_seam_related_pair_count": seam_related,
        "nonadjacent_other_pair_count": nonseam,
        "nonadjacent_total_intersections": seam_related + nonseam,
        "sample_seam_pairs": seam_witnesses,
        "sample_other_pairs": nonseam_witnesses,
        "zero_report_means": (
            "No intersection detected by Blender's finite triangle test for non-shared "
            "vertex pairs; not a certified collision-free stuffed plush."
        ),
        "limitations": [
            "Shared-vertex triangle pairs are excluded even if they fold across their common vertex",
            "Seam-related pairs are reported separately, not automatically accepted as safe",
            "No exact predicates for all coplanar, degenerate or nearly touching configurations",
            "No continuous-time tunneling or physical 1 mm cloth thickness check",
            "Geometry is duplicated stitched panels; not a physically welded/filled shell",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    for key in ("input", "case-report", "output"):
        parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    if (
        not args.input.is_file()
        or not args.case_report.is_file()
        or args.output.exists()
    ):
        raise RuntimeError("Saved source missing or target output already exists")
    expected = json.loads(args.case_report.read_text(encoding="utf8"))
    if expected.get("status") != "ACTUAL_CAPPED_CLOTH_SEWING_RESEARCH_ONLY":
        raise RuntimeError("Unrecognized saved Blender experiment report")
    bpy.ops.wm.open_mainfile(filepath=str(args.input.resolve()), load_ui=False)
    snap = bpy.data.objects.get(SNAPSHOT_NAME)
    source = bpy.data.objects.get(CLOTH_NAME)
    if snap is None or source is None or snap.type != "MESH" or source.type != "MESH":
        raise RuntimeError("Saved capped snapshot or pre-sewing source missing")
    if len(snap.data.vertices) != len(source.data.vertices):
        raise RuntimeError("Identity of cloth vertices changed")
    coords = [snap.matrix_world @ v.co for v in snap.data.vertices]
    snap.data.calc_loop_triangles()
    triangles = [
        tuple(int(i) for i in face.vertices) for face in snap.data.loop_triangles
    ]
    sewing_edges = [
        tuple(int(v) for v in edge.vertices)
        for edge in source.data.edges
        if edge.is_loose
    ]
    if len(sewing_edges) != expected.get("total_sewing_springs"):
        raise RuntimeError(
            f"Expected {expected.get('total_sewing_springs')} sewing links, got {len(sewing_edges)}"
        )
    report = audit_geometry(coords, triangles, sewing_edges)
    report.update(
        {
            "case_sha256": sha256(args.input),
            "source_report_sha256": sha256(args.case_report),
            "research_trial_self_collision_enabled": expected.get(
                "self_collision_enabled"
            ),
            "saved_blender_version": bpy.app.version_string,
            "numerical_evidence_only": True,
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(
        "NONADJACENT_TRIANGLE_SCREEN",
        json.dumps(
            {
                "triangles": report["triangle_count"],
                "seam_related": report["nonadjacent_seam_related_pair_count"],
                "other": report["nonadjacent_other_pair_count"],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
