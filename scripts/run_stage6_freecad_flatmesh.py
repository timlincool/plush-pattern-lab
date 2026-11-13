# SPDX-License-Identifier: LGPL-2.1-or-later
"""Isolated adapter for FreeCAD's compiled flatmesh.FaceUnwrapper.

The solver comes from the installed, unmodified FreeCAD C++/pybind11 library.
Input: the exact twelve Stage6 real source disks already used by Blender ABF.
Not a fabric rest pattern or an authorization to cut/produce the plush toy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

SCHEMA = "stage6-freecad-flatmesh-original-source-raw-v1"
SOURCE_SCHEMA = "stage6-ear-root-genuine-source-disk-lscm-research-v1"
SOURCE_SHA = "38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a"
SOLVER = "FREECAD_FLATMESH_LSCM_RELAX_10_0_95"


def source_disks(raw):
    if (
        raw.get("schema") != SOURCE_SCHEMA
        or raw.get("original_public_blend_sha256") != SOURCE_SHA
        or raw.get("factory_cutting_patterns_approved") != 0
        or raw.get("P3_status") != "in_progress"
        or raw.get("P4_status") != "not_started"
    ):
        raise ValueError("expected locked Stage6 original P3 research source")
    disks = raw.get("candidate_2d_research_disks")
    if not isinstance(disks, list) or len(disks) != 12:
        raise ValueError("all twelve identical original source disks required")
    identities = [
        (x["source_variant"], x["original_source_side"], x["source_slit_direction"])
        for x in disks
    ]
    if len(set(identities)) != 12:
        raise ValueError("duplicate or missing original Stage6 disk identities")
    return disks


def _geometry(item):
    xyz = np.asarray(item["cut_disk_source_xyz_mm"], dtype=np.float64)
    tri = np.asarray(item["cut_disk_original_source_triangle_indices"], dtype=np.int64)
    if (
        xyz.ndim != 2
        or xyz.shape[1] != 3
        or tri.ndim != 2
        or tri.shape[1] != 3
        or len(xyz) < 20
        or len(tri) < 30
        or not np.isfinite(xyz).all()
        or np.any(tri < 0)
        or np.any(tri >= len(xyz))
        or np.any(tri[:, 0] == tri[:, 1])
        or np.any(tri[:, 1] == tri[:, 2])
        or np.any(tri[:, 2] == tri[:, 0])
    ):
        raise ValueError("source triangles are invalid or not index-aligned")
    return xyz, tri


def _solve(item, flatmesh_module):
    xyz, tri = _geometry(item)
    started = time.perf_counter()
    solver = flatmesh_module.FaceUnwrapper(xyz, tri)
    solver.findFlatNodes(10, 0.95)
    uv = np.asarray(solver.ze_nodes, dtype=np.float64)
    seconds = time.perf_counter() - started
    if uv.shape != (len(xyz), 2) or not np.isfinite(uv).all():
        raise ValueError("FreeCAD returned non-finite or non-source-aligned UV")
    if np.max(np.ptp(uv, axis=0)) <= 1e-10:
        raise ValueError("FreeCAD returned a collapsed two-dimensional pattern")
    return uv, seconds


def run_study(source, flatmesh_module, source_digest):
    disks = source_disks(source)
    if not callable(getattr(flatmesh_module, "FaceUnwrapper", None)):
        raise ValueError("compiled FreeCAD flatmesh.FaceUnwrapper is unavailable")
    rows = []
    for item in disks:
        identity = {
            "source_variant": item["source_variant"],
            "source_side": item["original_source_side"],
            "slit_direction": item["source_slit_direction"],
            "source_patch_sha256": item["original_source_patch_sha256"],
        }
        try:
            uv, seconds = _solve(item, flatmesh_module)
            result = {
                "status": "completed",
                "source_vertex_count": len(uv),
                "source_triangle_count": len(
                    item["cut_disk_original_source_triangle_indices"]
                ),
                "uv_per_original_source_disk_vertex": uv.tolist(),
                "solver_seconds": round(seconds, 5),
            }
        except (RuntimeError, ValueError, TypeError) as exc:
            result = {"status": "solver_failed", "error_type": type(exc).__name__}
        rows.append({**identity, **result})
    return {
        "schema": SCHEMA,
        "method": SOLVER,
        "source_study_sha256": source_digest,
        "source_blend_sha256": SOURCE_SHA,
        "freecad_algorithm": "FaceUnwrapper.lscm() plus 10 relax(0.95) rounds",
        "freecad_source_license": "LGPL-2.1-or-later",
        "external_compiled_freecad_not_vendored": True,
        "all_original_source_triangles_unchanged": True,
        "entries": rows,
        "research_only_not_material_rest_shape": True,
        "fabric_tested": False,
        "factory_cutting_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    if (
        not args.source.is_file()
        or args.source.is_symlink()
        or args.output.exists()
        or args.output.is_symlink()
    ):
        raise ValueError("requires same-run Stage6 source and untouched output path")
    import flatmesh  # noqa: PLC0415 - a separately installed native FreeCAD module

    original = args.source.read_bytes()
    report = run_study(
        json.loads(original), flatmesh, hashlib.sha256(original).hexdigest()
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    if any(row["status"] != "completed" for row in report["entries"]):
        raise ValueError("incomplete real source FreeCAD study; saved failed cases")
    print("STAGE6_FREECAD_FLATMESH_12_REAL_SOURCE_DISKS_RESEARCH_ONLY", flush=True)


if __name__ == "__main__":
    main()
