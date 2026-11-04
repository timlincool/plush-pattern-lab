"""Read-only full Stage6 main-shell topology before any low-poly pattern proxy.

This reads the pinned public Blender scene, never changes or saves source mesh.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import bmesh
import bpy

from plush_pattern_lab.blender.audit_hoof_interfaces import (
    BODY,
    _boundary_successors,
    _walk_rings,
    build_report,
    sha256_file,
)
from plush_pattern_lab.validation.core_shell_topology import (
    summarize_core_shell_topology,
)


def _face_components(mesh):
    mesh.faces.ensure_lookup_table()
    mesh.faces.index_update()
    remaining = {face.index for face in mesh.faces}
    count = 0
    while remaining:
        count += 1
        current = [mesh.faces[remaining.pop()]]
        while current:
            face = current.pop()
            for edge in face.edges:
                for neighbor in edge.link_faces:
                    if neighbor.index in remaining:
                        remaining.remove(neighbor.index)
                        current.append(neighbor)
    return count


def inspect_core_shell():
    body = bpy.context.scene.objects.get(BODY)
    if body is None or body.type != "MESH":
        raise ValueError("Stage6 verified main body is not a MESH object")
    bm = bmesh.new()
    try:
        bm.from_mesh(body.data)
        bm.verts.ensure_lookup_table()
        bm.verts.index_update()
        ring_sizes = [len(ring) for ring in _walk_rings(_boundary_successors(bm))]
        face_sizes = Counter(str(len(face.verts)) for face in bm.faces)
        incidences = {"0": 0, "1": 0, "2": 0, ">2": 0}
        for edge in bm.edges:
            count = len(edge.link_faces)
            incidences[str(count) if count <= 2 else ">2"] += 1
        report = summarize_core_shell_topology(
            len(bm.verts),
            len(bm.edges),
            len(bm.faces),
            dict(face_sizes),
            incidences,
            _face_components(bm),
            ring_sizes,
        )
        report["loose_vertices"] = sum(not v.link_edges for v in bm.verts)
        if report["loose_vertices"]:
            report["candidate_for_non_destructive_proxy_experiment"] = False
        return report
    finally:
        bm.free()


def extract_core_shell_report(source_sha256):
    original = build_report(source_sha256)
    if not original["all_geometry_interfaces_match"]:
        raise ValueError("strict four-hoof boundary matching has not passed")
    report = inspect_core_shell()
    report["source_sha256"] = source_sha256
    report["blender"] = bpy.app.version_string
    report["verified_body_hoof_3d_pair_count"] = len(original["interfaces"])
    report["whole_model_modified"] = False
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    if bpy.app.version[:3] != (4, 3, 2):
        raise ValueError("Blender 4.3.2 is required")
    if not args.input.is_file() or args.input.suffix != ".blend":
        raise ValueError("expected an existing public Stage6 Blender scene")
    if args.output.suffix != ".json" or args.output.exists():
        raise ValueError("refuse to overwrite an earlier JSON report")
    if args.output.is_symlink():
        raise ValueError("refuse to write into a linked output path")
    digest = sha256_file(args.input)
    if digest != args.source_sha256:
        raise ValueError("source SHA-256 mismatch; never open untrusted scene")
    bpy.ops.wm.open_mainfile(filepath=str(args.input.resolve()), load_ui=False)
    report = extract_core_shell_report(digest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        "STAGE6_REAL_CORE_SHELL_TOPOLOGY",
        json.dumps(
            {
                "vertices": report["vertices"],
                "edges": report["edges"],
                "faces": report["faces"],
                "face_components": report["face_components_by_shared_edge"],
                "boundary_loops": report["boundary_loop_vertex_counts"],
                "euler": report["euler_characteristic"],
                "edge_incidence": report["edge_incidence"],
                "proxy_candidate": report[
                    "candidate_for_non_destructive_proxy_experiment"
                ],
                "low_poly_created": False,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
