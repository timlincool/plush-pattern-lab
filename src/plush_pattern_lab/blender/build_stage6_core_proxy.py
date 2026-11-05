"""Create bounded, NON-DESTRUCTIVE Stage6 core-shell proxy research candidates.

Only the pinned public source may be opened, with Blender --disable-autoexec.
Candidate outputs are mesh-only PLY research artifacts; NEVER factory patterns.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from collections import Counter
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

from plush_pattern_lab.blender.audit_hoof_interfaces import (
    BODY,
    _boundary_successors,
    _walk_rings,
    build_report,
    sha256_file,
)
from plush_pattern_lab.blender.probe_stage6_core_shell import _face_components
from plush_pattern_lab.validation.core_shell_topology import (
    summarize_core_shell_topology,
)
from plush_pattern_lab.validation.manufacturing_proxy_quality import (
    register_original_hoof_seams,
    sampled_surface_distances_mm,
)

SOURCE_FACES = 466278
RATIOS = (0.50, 0.25)


def _boundary_records(mesh):
    """Preserve ordered original point IDs and actual world mm, no resampling."""
    mesh.verts.ensure_lookup_table()
    mesh.verts.index_update()
    rings = _walk_rings(_boundary_successors(mesh))
    return [
        {
            "vertex_ids": [vert for vert in ring],
            "xyz_mm": [
                list(np.asarray(mesh.verts[vert].co, dtype=np.float64) * 1000)
                for vert in ring
            ],
        }
        for ring in rings
    ]


def _count_mesh(mesh):
    """Apply the already-reviewed VEF manifold/connectedness checker."""
    face_sizes = Counter(str(len(face.verts)) for face in mesh.faces)
    incidence = {"0": 0, "1": 0, "2": 0, ">2": 0}
    for edge in mesh.edges:
        used = len(edge.link_faces)
        incidence[str(used) if used <= 2 else ">2"] += 1
    rings = _walk_rings(_boundary_successors(mesh))
    result = summarize_core_shell_topology(
        len(mesh.verts),
        len(mesh.edges),
        len(mesh.faces),
        dict(face_sizes),
        incidence,
        _face_components(mesh),
        [len(ring) for ring in rings],
    )
    result["loose_vertices"] = sum(not vert.link_edges for vert in mesh.verts)
    return result


def _protected_neighborhood(obj, source_rings):
    """Exclude all boundary vertices and TWO adjacent edge neighborhoods."""
    protected = {int(v) for ring in source_rings for v in ring["vertex_ids"]}
    mesh_edges = [tuple(edge.vertices) for edge in obj.data.edges]
    for _ in range(2):
        expanded = protected.copy()
        for a, b in mesh_edges:
            if a in protected or b in protected:
                expanded.update((a, b))
        protected = expanded
    interior = [
        vert.index for vert in obj.data.vertices if vert.index not in protected
    ]
    if len(interior) < 500 or len(protected) < 2048:
        raise ValueError("protected boundary neighborhood leaves no safe interior")
    return interior, len(protected)


def _evaluated_mesh(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    temporary = evaluated.to_mesh(preserve_all_data_layers=False, depsgraph=depsgraph)
    bm = bmesh.new()
    try:
        bm.from_mesh(temporary)
    finally:
        evaluated.to_mesh_clear()
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    bm.transform(obj.matrix_world)
    bm.normal_update()
    return bm


def _surface_samples(mesh, tree, count=1200):
    """Sample deterministic mesh vertices; distance is not exact Hausdorff."""
    mesh.verts.ensure_lookup_table()
    stride = max(1, len(mesh.verts) // count)
    results = []
    for index in range(0, len(mesh.verts), stride):
        hit = tree.find_nearest(mesh.verts[index].co)
        if hit is None or hit[0] is None:
            raise ValueError("nearest point search could not find a triangle")
        results.append(float(hit[3]) * 1000)
    return sampled_surface_distances_mm(results)


def _write_research_ply(path, mesh, sha):
    """Write just the derived proxy shell; no external materials/scripts/assets."""
    if path.exists() or path.is_symlink() or path.suffix != ".ply":
        raise ValueError("PLY output must be unused and use .ply extension")
    if any(len(face.verts) != 3 for face in mesh.faces):
        raise ValueError("research PLY requires triangular candidate faces")
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "ply\nformat binary_little_endian 1.0\n"
        "comment research_candidate_not_factory_pattern\n"
        f"comment verified_public_stage6_sha256 {sha}\n"
        f"element vertex {len(mesh.verts)}\n"
        "property float x\nproperty float y\nproperty float z\n"
        f"element face {len(mesh.faces)}\n"
        "property list uchar int vertex_indices\nend_header\n"
    )
    with path.open("xb") as stream:
        stream.write(header.encode("ascii"))
        for vertex in mesh.verts:
            x, y, z = vertex.co
            stream.write(struct.pack("<fff", x * 1000, y * 1000, z * 1000))
        for face in mesh.faces:
            stream.write(
                struct.pack("<Biii", 3, *(vert.index for vert in face.verts))
            )
    return path.stat().st_size


def _run_trial(source, ratio, interior, source_rings, original_bm, original_bvh, outdir, sha):
    """A cloned-only modifier experiment; any geometry issue rejects export."""
    proxy = source.copy()
    proxy.data = source.data.copy()
    proxy.name = f"RESEARCH_CORE_PROXY_RATIO_{ratio:.2f}"
    bpy.context.scene.collection.objects.link(proxy)
    bm = None
    try:
        for modifier in list(proxy.modifiers):
            proxy.modifiers.remove(modifier)
        for constraint in list(proxy.constraints):
            proxy.constraints.remove(constraint)
        group = proxy.vertex_groups.new(name="DECIMATE_ELIGIBLE_INTERIOR_ONLY")
        group.add(interior, 1.0, "REPLACE")
        modifier = proxy.modifiers.new("RESEARCH_DECIMATE", "DECIMATE")
        modifier.decimate_type = "COLLAPSE"
        modifier.vertex_group = group.name
        modifier.vertex_group_factor = 1.0
        modifier.invert_vertex_group = False
        modifier.ratio = ratio
        modifier.use_collapse_triangulate = True
        bm = _evaluated_mesh(proxy)
        result = {
            "requested_triangle_ratio": ratio,
            "actual_faces": len(bm.faces),
            "actual_vertices": len(bm.verts),
            "original_faces": SOURCE_FACES,
            "source_object_modified": False,
            "source_sha256": sha,
            "status": "RESEARCH_CANDIDATE_NOT_A_CUT_PATTERN",
            "proxy_exported": False,
            "accepted_for_pattern_cutting": False,
        }
        try:
            topo = _count_mesh(bm)
            identity = register_original_hoof_seams(source_rings, _boundary_records(bm))
            result["topology"] = topo
            result["hooves"] = identity
            good = (
                topo["candidate_for_non_destructive_proxy_experiment"]
                and topo["euler_characteristic"] == -2
                and topo["loose_vertices"] == 0
                and identity["all_original_seam_points_and_winding_preserved"]
                and len(bm.faces) < SOURCE_FACES
            )
        except ValueError as error:
            result["topology_or_interface_failure"] = str(error)
            good = False
        if good:
            proxy_bvh = BVHTree.FromBMesh(bm)
            result["original_to_proxy_sampled_surface_mm"] = _surface_samples(
                original_bm, proxy_bvh
            )
            result["proxy_to_original_sampled_surface_mm"] = _surface_samples(
                bm, original_bvh
            )
            filename = f"core_shell_proxy_ratio_{ratio:.2f}.ply"
            result["export_bytes"] = _write_research_ply(outdir / filename, bm, sha)
            result["research_proxy_file"] = filename
            result["proxy_exported"] = True
        else:
            result["rejection"] = "invalid exact boundaries or topology; no export"
        return result
    finally:
        if bm is not None:
            bm.free()
        mesh_data = proxy.data
        bpy.data.objects.remove(proxy, do_unlink=True)
        if mesh_data.users == 0:
            bpy.data.meshes.remove(mesh_data)


def evaluate_proxies(source_sha256, output_dir):
    """The original body and all 4 hoop joins must be proven before any trial."""
    checked = build_report(source_sha256)
    if not checked["all_geometry_interfaces_match"]:
        raise ValueError("original Stage6 four-hoof interface check failed")
    body = bpy.context.scene.objects.get(BODY)
    if body is None or body.type != "MESH":
        raise ValueError("verified Stage6 core shell is not available")
    pre = (len(body.data.vertices), len(body.data.edges), len(body.data.polygons))
    if pre[-1] != SOURCE_FACES:
        raise ValueError("fixed source core-shell topology unexpectedly changed")
    original_bm = bmesh.new()
    try:
        original_bm.from_mesh(body.data)
        original_bm.verts.ensure_lookup_table()
        original_bm.verts.index_update()
        original_bm.transform(body.matrix_world)
        original_bm.normal_update()
        source_rings = _boundary_records(original_bm)
        interior, protected_count = _protected_neighborhood(body, source_rings)
        original_bvh = BVHTree.FromBMesh(original_bm)
        trials = [
            _run_trial(
                body, ratio, interior, source_rings, original_bm,
                original_bvh, output_dir, source_sha256
            )
            for ratio in RATIOS
        ]
    finally:
        original_bm.free()
    post = (len(body.data.vertices), len(body.data.edges), len(body.data.polygons))
    if post != pre:
        raise ValueError("source object was changed by non-destructive experiment")
    return {
        "schema": "stage6-protected-core-shell-proxy-ab-v1",
        "status": "NONDESTRUCTIVE_3D_GEOMETRY_RESEARCH_NOT_FABRICATION",
        "source_sha256": source_sha256,
        "blender_version": bpy.app.version_string,
        "original_mesh_counts": dict(zip(("vertices", "edges", "faces"), pre)),
        "protected_2hop_neighborhood_vertices": protected_count,
        "eligible_interior_vertices": len(interior),
        "all_original_source_counts_unchanged": pre == post,
        "trials": trials,
        "approved_cut_patterns": 0,
        "complete_character_panels": False,
        "physical_sample_exists": False,
        "limitations": [
            "Research proxy shell does not include cloud layers, ears or hooves",
            "Vertex-to-surface samples are not continuous Hausdorff guarantees",
            "Geometric boundary preservation does not prove a sewable pattern",
            "No actual fabric, 2D rest panels, allowances or physical sewing",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--proxy-dir", type=Path, required=True)
    opts = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    if bpy.app.version[:3] != (4, 3, 2):
        raise ValueError("Blender 4.3.2 is required")
    if not opts.input.is_file() or opts.input.suffix != ".blend":
        raise ValueError("public source must be an existing Blender model")
    if opts.output.suffix != ".json" or opts.output.exists() or opts.output.is_symlink():
        raise ValueError("new JSON report path required")
    if opts.proxy_dir.exists() or opts.proxy_dir.is_symlink():
        raise ValueError("output candidate directory must not already exist")
    digest = sha256_file(opts.input)
    if digest != opts.source_sha256:
        raise ValueError("mismatched original Stage6 SHA; refuse to open file")
    bpy.ops.wm.open_mainfile(filepath=str(opts.input.resolve()), load_ui=False)
    opts.proxy_dir.mkdir(parents=True)
    result = evaluate_proxies(digest, opts.proxy_dir)
    opts.output.parent.mkdir(parents=True, exist_ok=True)
    opts.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        "STAGE6_NONDESTRUCTIVE_CORE_PROXY_AB",
        json.dumps(
            [
                {
                    "ratio": row["requested_triangle_ratio"],
                    "faces": row["actual_faces"],
                    "exported": row["proxy_exported"],
                    "seams": row.get("hooves", {}).get(
                        "all_original_seam_points_and_winding_preserved", False
                    ),
                    "error_source_to_proxy_p95_mm": row.get(
                        "original_to_proxy_sampled_surface_mm", {}
                    ).get("p95_mm"),
                    "error_source_to_proxy_max_mm": row.get(
                        "original_to_proxy_sampled_surface_mm", {}
                    ).get("max_mm"),
                    "rejection": row.get("rejection", ""),
                }
                for row in result["trials"]
            ]
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
