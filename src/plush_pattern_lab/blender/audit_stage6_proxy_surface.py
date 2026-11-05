"""Independently audit real Stage6 50/25% proxy PLYs against source Blender.

Reopens only the pinned public Stage6 with --disable-autoexec. The derived
mesh has no materials, scripts, or nontrusted file formats. Research only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from plush_pattern_lab.blender.audit_hoof_interfaces import (
    BODY,
    build_report,
    sha256_file,
)
from plush_pattern_lab.validation.proxy_view_quality import (
    check_winding_counts,
    compare_orthographic_hits,
)

RESOLUTION = 96
EXPECTED = (
    ("core_shell_proxy_ratio_0.50.ply", 117591, 233138,
     "22020a5631ccd6b171f242d6c5c9f9713e9b0d600a20f8a0fcf3b7c08149bd4f"),
    ("core_shell_proxy_ratio_0.25.ply", 59306, 116568,
     "5b52e3fd09c83b19c5b9d95d6d8d859a147ff4deef90f1518f868d2e82e3a2dd"),
)
VIEWS = (
    ("front", 1, 1, 0, 2),
    ("back", 1, -1, 0, 2),
    ("left", 0, 1, 1, 2),
    ("right", 0, -1, 1, 2),
    ("top", 2, -1, 0, 1),
)


def _read_exact_ply(path, vertices, faces, expected_sha):
    """Parse only the trusted binary triangle PLY schema already exported by us."""
    if not path.is_file() or path.is_symlink():
        raise ValueError("trusted derived proxy PLY is missing")
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        raise ValueError("derived proxy SHA-256 mismatches the measured model")
    with path.open("rb") as stream:
        head = b""
        while not head.endswith(b"end_header\n") and len(head) <= 4096:
            line = stream.readline()
            if not line:
                raise ValueError("PLY header is incomplete")
            head += line
        metadata = head.decode("ascii")
        required = (
            "ply\nformat binary_little_endian 1.0\n",
            f"element vertex {vertices}\n",
            f"element face {faces}\n",
            "property list uchar int vertex_indices\nend_header\n",
        )
        if any(token not in metadata for token in required):
            raise ValueError("PLY schema is not the recorded research triangle mesh")
        points = np.fromfile(stream, dtype="<f4", count=3 * vertices)
        face_type = np.dtype([("n", "u1"), ("indices", "<i4", (3,))])
        indices = np.fromfile(stream, dtype=face_type, count=faces)
        if stream.read(1) or len(points) != 3 * vertices or len(indices) != faces:
            raise ValueError("bad or trailing PLY bytes")
    points = points.reshape(-1, 3).astype(np.float64) / 1000
    triangles = indices["indices"]
    if not np.isfinite(points).all() or (indices["n"] != 3).any():
        raise ValueError("invalid PLY coordinates or triangle records")
    if (triangles < 0).any() or (triangles >= vertices).any():
        raise ValueError("out-of-range PLY triangle indices")
    return points, triangles


def _bmesh_from_ply(points, triangles):
    """Create a temporary mesh, never an object attached to the source scene."""
    mesh = bpy.data.meshes.new("TEMP_VERIFIED_STAGE6_PLY")
    bm = bmesh.new()
    try:
        mesh.from_pydata(points.tolist(), [], triangles.tolist())
        mesh.update()
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()
        bm.verts.index_update()
        bm.faces.ensure_lookup_table()
        bm.faces.index_update()
        bm.normal_update()
        return bm
    except Exception:
        bm.free()
        raise
    finally:
        bpy.data.meshes.remove(mesh)


def _edge_winding(mesh):
    incoherent, compared = 0, 0
    for edge in mesh.edges:
        if len(edge.link_loops) != 2:
            continue
        a, b = edge.link_loops
        compared += 1
        if a.vert == b.vert:
            incoherent += 1
    return check_winding_counts(compared, incoherent)


def _self_intersections(mesh, tree):
    """BVH overlapping triangles excluding every pair sharing any source vertex."""
    mesh.faces.ensure_lookup_table()
    mesh.faces.index_update()
    vertex_ids = [tuple(v.index for v in f.verts) for f in mesh.faces]
    count, witnesses = 0, []
    candidate_pairs = tree.overlap(tree)
    for i, j in candidate_pairs:
        if i >= j:
            continue
        a, b = vertex_ids[i], vertex_ids[j]
        if a[0] in b or a[1] in b or a[2] in b:
            continue
        count += 1
        if len(witnesses) < 12:
            witnesses.append([int(i), int(j)])
    return {
        "nonadjacent_triangle_intersection_pairs": count,
        "bounded_first_12_face_index_witnesses": witnesses,
        "bvh_reported_raw_pair_count": len(candidate_pairs),
        "shared_vertex_neighbors_excluded": True,
        "thick_fabric_contact_and_continuous_time_not_tested": True,
    }


def _bounds(mesh):
    points = np.asarray([tuple(v.co) for v in mesh.verts], dtype=np.float64)
    return np.stack((points.min(axis=0), points.max(axis=0)))


def _view_hits(tree, bounds, axis, sign, u, v):
    """The near-side FIRST hit depth in mm, not mere projected vertex positions."""
    grid = np.full((RESOLUTION, RESOLUTION), np.nan)
    edge_margin = 0.002
    begin = bounds[0, axis] - 0.01 if sign == 1 else bounds[1, axis] + 0.01
    direction = Vector([sign if idx == axis else 0 for idx in range(3)])
    distance = float(bounds[1, axis] - bounds[0, axis] + 0.02)
    columns = np.linspace(
        bounds[0, u] - edge_margin, bounds[1, u] + edge_margin, RESOLUTION
    )
    rows = np.linspace(
        bounds[0, v] - edge_margin, bounds[1, v] + edge_margin, RESOLUTION
    )
    ray = [0.0, 0.0, 0.0]
    ray[axis] = float(begin)
    for iy, ordinate in enumerate(rows):
        ray[v] = float(ordinate)
        for ix, abscissa in enumerate(columns):
            ray[u] = float(abscissa)
            _, _, _, hit_distance = tree.ray_cast(Vector(ray), direction, distance)
            if hit_distance is not None:
                grid[iy, ix] = float(hit_distance) * 1000
    return grid


def _png_bytes(rgb):
    """Create an actual five-view audit PNG with Python stdlib, no GUI/fonts."""
    height, width = rgb.shape[:2]
    header = b"\x89PNG\r\n\x1a\n"

    def chunk(kind, data):
        return (
            struct.pack(">I", len(data)) + kind + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    pixels = b"".join(b"\x00" + rgb[y].tobytes() for y in range(height))
    return (
        header
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(pixels, 6))
        + chunk(b"IEND", b"")
    )


def _mask_overlay(original, proxy):
    """White empty; charcoal shared, red only-source, blue only-candidate."""
    a, b = np.isfinite(original), np.isfinite(proxy)
    rgb = np.full((*a.shape, 3), 255, dtype=np.uint8)
    rgb[a & b] = (45, 65, 72)
    rgb[a & ~b] = (236, 73, 68)
    rgb[~a & b] = (48, 119, 223)
    return rgb


def evaluate_geometry(source_sha256, candidates, output_dir):
    """Independent face, BVH and registered orthographic-view audit."""
    body = bpy.context.scene.objects.get(BODY)
    if body is None or body.type != "MESH":
        raise ValueError("verified Stage6 original main shell missing")
    original = bmesh.new()
    try:
        original.from_mesh(body.data)
        original.transform(body.matrix_world)
        original.verts.ensure_lookup_table()
        original.faces.ensure_lookup_table()
        original.faces.index_update()
        original.normal_update()
        reference_bvh = BVHTree.FromBMesh(original)
        bounds = _bounds(original)
        samples = {
            name: _view_hits(reference_bvh, bounds, axis, sign, u, v)
            for name, axis, sign, u, v in VIEWS
        }
        reference_winding = _edge_winding(original)
        results = []
        for name, vertices, faces, digest in candidates:
            points, indices = _read_exact_ply(output_dir / name, vertices, faces, digest)
            candidate = _bmesh_from_ply(points, indices)
            try:
                bvh = BVHTree.FromBMesh(candidate)
                compare = {}
                overlays = []
                for view, axis, sign, u, v in VIEWS:
                    ray_grid = _view_hits(bvh, bounds, axis, sign, u, v)
                    compare[view] = compare_orthographic_hits(samples[view], ray_grid)
                    overlays.append(_mask_overlay(samples[view], ray_grid))
                picture = np.concatenate(overlays, axis=1)
                png = name.replace(".ply", "_five_views.png")
                (output_dir / png).write_bytes(_png_bytes(picture))
                extent = _bounds(candidate) * 1000
                reference_extent = bounds * 1000
                results.append(
                    {
                        "research_ply": name,
                        "research_ply_sha256": digest,
                        "vertices": vertices,
                        "faces": faces,
                        "face_winding": _edge_winding(candidate),
                        "nonadjacent_bvh": _self_intersections(candidate, bvh),
                        "bounds_max_abs_mm": float(
                            np.abs(extent - reference_extent).max()
                        ),
                        "orthographic_first_hit": compare,
                        "five_view_overlay_png": png,
                        "manufacturing_approved": False,
                    }
                )
            finally:
                candidate.free()
        return {
            "schema": "stage6-real-proxy-independent-geometry-screen-v1",
            "status": "INDEPENDENT_SCREEN_NOT_FABRIC_PRODUCTION_CERTIFICATION",
            "source_main_mesh_faces": len(original.faces),
            "reference_face_winding": reference_winding,
            "reference_nonadjacent_bvh": _self_intersections(original, reference_bvh),
            "view_grid_resolution": RESOLUTION,
            "view_order": [x[0] for x in VIEWS],
            "colors": {
                "white": "no surface either model",
                "charcoal": "source and proxy silhouette both present",
                "red": "source surface only",
                "blue": "proxy surface only",
            },
            "source_sha256": source_sha256,
            "results": results,
            "approved_cut_patterns": False,
            "manufacturing_production_ready": False,
            "limitations": [
                "BVH checks triangle intersections only, not finite fabric thickness",
                "Shared-vertex triangles excluded from nonadjacent count",
                "Five ray masks at finite resolution are not exact silhouette proof",
                "Depth measures are near-view first hits, not full Hausdorff",
                "Source is only the main shell, not the entire stuffed toy",
            ],
        }
    finally:
        original.free()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--proxy-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    if bpy.app.version[:3] != (4, 3, 2):
        raise ValueError("Blender 4.3.2 required")
    if not args.input.is_file() or args.input.suffix != ".blend":
        raise ValueError("missing trusted public Blender source")
    if args.output.suffix != ".json" or args.output.exists() or args.output.is_symlink():
        raise ValueError("refuse to overwrite geometric research results")
    if sha256_file(args.input) != args.source_sha256:
        raise ValueError("source SHA verification failed")
    if args.source_sha256 != "38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a":
        raise ValueError("unexpected public source identity")
    if not args.proxy_dir.is_dir() or args.proxy_dir.is_symlink():
        raise ValueError("derived proxy directory must exist")
    bpy.ops.wm.open_mainfile(filepath=str(args.input.resolve()), load_ui=False)
    check = build_report(args.source_sha256)
    if not check["all_geometry_interfaces_match"]:
        raise ValueError("original four-hoof 3D interface check failed")
    result = evaluate_geometry(args.source_sha256, EXPECTED, args.proxy_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        "STAGE6_INDEPENDENT_PROXY_SCREEN",
        json.dumps(
            [
                {
                    "model": item["research_ply"],
                    "winding_conflicts": item["face_winding"][
                        "opposite_directed_edge_failures"
                    ],
                    "nonadjacent_intersections": item["nonadjacent_bvh"][
                        "nonadjacent_triangle_intersection_pairs"
                    ],
                    "bound_delta_max_mm": item["bounds_max_abs_mm"],
                    "front_iou": item["orthographic_first_hit"]["front"][
                        "silhouette_iou"
                    ],
                    "front_p95_depth_mm": item["orthographic_first_hit"]["front"][
                        "first_hit_depth_mm"
                    ]["p95"],
                }
                for item in result["results"]
            ]
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
