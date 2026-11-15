"""Export every genuine Stage6 product MESH for full-character visual assembly.

This is a read-only visual scene export, not a cut-pattern or sewn attachment.
All 41 product meshes retain actual original world-space vertex coordinates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np

SOURCE_SHA = "38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a"


def _digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _registry(path):
    j = json.loads(Path(path).read_text(encoding="utf8"))
    if j.get("source_sha256") != SOURCE_SHA or len(j.get("component_rows", [])) != 42:
        raise ValueError("42-source-mesh registry or source SHA changed")
    rows = j["component_rows"]
    valid = [r for r in rows if not r["non_product_scene_asset"]]
    if len(valid) != 41 or len({r["source_mesh"] for r in valid}) != 41:
        raise ValueError("expected original 41 uniquely identified product meshes")
    return {r["source_mesh"]: r for r in valid}


def _triangulate(mesh):
    faces = []
    for poly in mesh.polygons:
        corners = list(poly.vertices)
        if len(corners) < 3:
            raise ValueError("degenerate source face")
        faces.extend(
            (corners[0], corners[k], corners[k + 1])
            for k in range(1, len(corners) - 1)
        )
    return np.asarray(faces, dtype=np.int32).reshape(-1, 3)


def _source_mesh(obj):
    mesh = obj.data
    coords = np.asarray(
        [tuple(obj.matrix_world @ v.co) for v in mesh.vertices], dtype=np.float32
    ).reshape(-1, 3)
    triangles = _triangulate(mesh)
    if len(coords) < 3 or len(triangles) == 0 or not np.isfinite(coords).all():
        raise ValueError("invalid source mesh vertex coordinates")
    if np.max(np.abs(coords)) > 10 or triangles.max() >= len(coords):
        raise ValueError("source geometry outside meter-scale product bounds")
    return coords, triangles


def _export_source(input_file, registry_path, output):
    if bpy.app.version[:3] != (4, 3, 2):
        raise ValueError("pinned Blender 4.3.2 required")
    for p in (input_file, registry_path):
        if not Path(p).is_file() or Path(p).is_symlink():
            raise ValueError("missing or symlink source input")
    if _digest(input_file) != SOURCE_SHA:
        raise ValueError("original Stage6 SHA mismatch")
    if Path(output).exists() and any(Path(output).iterdir()):
        raise ValueError("refuse to replace earlier visual proof")
    role_by_name = _registry(registry_path)
    bpy.ops.wm.open_mainfile(filepath=str(Path(input_file).resolve()), load_ui=False)
    observed = {o.name: o for o in bpy.data.objects if o.type == "MESH"}
    if len(observed) != 42 or not role_by_name.keys() <= observed.keys():
        raise ValueError("original 42 MESH scene no longer matches registry")
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    arrays, catalog = {}, []
    for idx, name in enumerate(sorted(role_by_name)):
        obj = observed[name]
        verts, faces = _source_mesh(obj)
        key = f"mesh_{idx:02d}"
        arrays[key + "_vertices_m"] = verts
        arrays[key + "_triangles"] = faces
        entry = role_by_name[name]
        catalog.append({
            "id": key,
            "name": name,
            "category": entry["scene_group"],
            "original_source_polygons": len(obj.data.polygons),
            "vertices": len(verts),
            "triangles": len(faces),
            "bounds_m": [verts.min(axis=0).tolist(), verts.max(axis=0).tolist()],
            "geometry_is_original_source_mesh": True,
            "physical_attachment_to_R2_sewn": False,
        })
    binary = out / "STAGE6_41_ORIGINAL_PRODUCT_MESHES_UNSEWN.npz"
    np.savez_compressed(binary, **arrays)
    curves = [o for o in bpy.data.objects if o.type in {"CURVE", "CURVES"}]
    report = {
        "schema": "stage6-41-original-product-mesh-visual-assembly-v1",
        "original_blend_sha256": SOURCE_SHA,
        "registry_sha256": _digest(registry_path),
        "mesh_archive_sha256": _digest(binary),
        "blender": bpy.app.version_string,
        "original_scene_mesh_count": len(observed),
        "product_mesh_count": len(catalog),
        "visual_curves_not_exported": len(curves),
        "original_product_mesh_names_and_roles": catalog,
        "source_coordinates": "world XYZ meters, no recentering and no AI geometry",
        "material": "color by role in offline viewer; source shader not baked",
        "modifier_mesh_not_evaluated": True,
        "physical_R2_to_overlay_attachments_proven": False,
        "factory_cut_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
    }
    (out / "STAGE6_41_original_mesh_manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print("STAGE6_FULL_VISUAL_41_MESH_EXPORTED",
          json.dumps({"original_meshes": len(catalog), "curves_not_exported": len(curves),
                      "total_triangles": sum(x["triangles"] for x in catalog),
                      "archive_sha256": report["mesh_archive_sha256"]}), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--registry", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    a = p.parse_args(argv)
    _export_source(a.input, a.registry, a.out)


if __name__ == "__main__":
    main()
