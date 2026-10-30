"""Inspect the actual faces adjacent to Stage 6 hoof seam rings, read-only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np

from plush_pattern_lab.blender.audit_hoof_interfaces import (
    _boundary_successors,
    _source_objects,
    _walk_rings,
    build_report,
    sha256_file,
)
from plush_pattern_lab.validation.seam_band_topology import (
    face_profile,
    outer_ring_for_quads,
)
from plush_pattern_lab.validation.triangle_band_topology import (
    analyze_triangle_patch,
)


def inspect_object(obj):
    """Read only one face around each topological seam edge."""
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.verts.index_update()
        bm.faces.ensure_lookup_table()
        bm.faces.index_update()
        rings = _walk_rings(_boundary_successors(bm))
        lookup = {}
        for edge in bm.edges:
            if edge.is_boundary:
                key = frozenset(vert.index for vert in edge.verts)
                if len(edge.link_faces) != 1:
                    raise ValueError("boundary edge is not incident to one face")
                lookup[key] = tuple(v.index for v in edge.link_faces[0].verts)
        records = []
        for index, ring in enumerate(rings):
            pairs = zip(ring, ring[1:] + ring[:1])
            faces = [lookup[frozenset((a, b))] for a, b in pairs]
            report = face_profile(ring, faces)
            report["ring_index"] = index
            incident = {
                face.index: tuple(vert.index for vert in face.verts)
                for vertex in ring
                for face in bm.verts[vertex].link_faces
            }
            try:
                report["vertex_one_ring_patch"] = analyze_triangle_patch(
                    ring, list(incident.values())
                )
            except ValueError as error:
                report["vertex_one_ring_patch"] = {
                    "candidate_triangular_annulus": False,
                    "failure_reason": str(error),
                }
            if report["regular_quad_strip"]:
                outer = outer_ring_for_quads(ring, faces)
                radial = np.array(
                    [
                        float(
                            (
                                obj.matrix_world @ bm.verts[a].co
                                - obj.matrix_world @ bm.verts[b].co
                            ).length
                        )
                        * 1000
                        for a, b in zip(ring, outer)
                    ],
                    dtype=np.float64,
                )
                report["radial_edge_lengths_mm"] = {
                    "min": float(radial.min()),
                    "max": float(radial.max()),
                    "mean": float(radial.mean()),
                }
            records.append(report)
        return records
    finally:
        bm.free()


def generate_report(source_sha):
    """Verify the existing strict four-hoof geometry gate before surveying."""
    verified = build_report(source_sha)
    if not verified["all_geometry_interfaces_match"]:
        raise ValueError("Stage 6 four-hoof topology and orientation gate failed")
    objects = _source_objects()
    if len(objects) != 5:
        raise ValueError("missing body or four hoof objects")
    entries = [{"object": obj.name, "rings": inspect_object(obj)} for obj in objects]
    return {
        "schema": "stage6-adjacent-face-topology-v1",
        "status": "TOPOLOGY_SURVEY_ONLY_NO_FLATTENING",
        "source_sha256": source_sha,
        "blender": bpy.app.version_string,
        "objects": entries,
        "all_original_3d_seams_match": True,
        "all_first_face_bands_regular_quads": all(
            ring["regular_quad_strip"] for row in entries for ring in row["rings"]
        ),
        "all_vertex_one_ring_patches_triangular_annuli": all(
            ring["vertex_one_ring_patch"]["candidate_triangular_annulus"]
            for row in entries
            for ring in row["rings"]
        ),
        "limitations": [
            "Boundary-adjacent polygon census only; not a surface parameterization",
            "No 2D rest shape, cut boundary, allowance, fabric or stuffing evidence",
        ],
    }


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
        raise ValueError("input .blend does not exist")
    if args.output.suffix != ".json" or args.output.exists():
        raise ValueError("output must be an unused .json path")
    source_sha = sha256_file(args.input)
    if source_sha != args.source_sha256:
        raise ValueError("input source SHA-256 mismatch; refusing to open")
    bpy.ops.wm.open_mainfile(filepath=str(args.input.resolve()), load_ui=False)
    report = generate_report(source_sha)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        "STAGE6_ONE_RING_TOPOLOGY_SURVEY",
        json.dumps(
            {
                "all_regular_quads": report["all_first_face_bands_regular_quads"],
                "all_triangle_annuli": report["all_vertex_one_ring_patches_triangular_annuli"],
                "objects": [
                    {
                        "name": x["object"],
                        "rings": x["rings"],
                    }
                    for x in report["objects"]
                ],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
