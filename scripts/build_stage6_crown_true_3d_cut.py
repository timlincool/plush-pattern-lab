"""Use open-source trimesh to cut true Stage6 crown into three source-linked caps.

Only source SHA-locked 25% proxy and permanent original z230 witness are allowed.
Produces research 3D triangulations, not approved 2D paper cutting patterns.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from propose_stage6_shell_panels import load_pinned_proxy

from plush_pattern_lab.validation.stage6_true_crown_3d_caps import (
    SCHEMA,
    SOURCE_PLY_SHA256,
    WITNESS_SHA256,
    build_three_real_source_caps,
)


def _input(path, expected_sha):
    if not path.is_file() or path.is_symlink():
        raise ValueError("source input missing or symlinked")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_sha:
        raise ValueError("real source PLY / original contour witness changed")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proxy", type=Path, required=True)
    parser.add_argument("--witness", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    if (
        args.output.resolve() == args.summary.resolve()
        or any(p.exists() or p.is_symlink() for p in (args.output, args.summary))
        or args.output.suffix != ".json"
        or args.summary.suffix != ".json"
    ):
        raise ValueError("do not overwrite prior real original-source crown research")
    _input(args.proxy, SOURCE_PLY_SHA256)
    raw = _input(args.witness, WITNESS_SHA256)
    source, faces = load_pinned_proxy(args.proxy)
    import trimesh  # noqa: PLC0415 - only this separate MIT research dependency

    study = build_three_real_source_caps(source, faces, json.loads(raw), raw, trimesh)
    details = json.dumps(study, ensure_ascii=False, separators=(",", ":")) + "\n"
    if study["schema"] != SCHEMA:
        raise ValueError("unexpected source-linked 3D cap study schema")
    summary = {
        "schema": "stage6-real-source-z230-three-cap-3d-topology-audit-v1",
        "source_proxy_sha256": SOURCE_PLY_SHA256,
        "source_original_witness_sha256": WITNESS_SHA256,
        "full_3d_source_caps_json_sha256": hashlib.sha256(
            details.encode("utf8")
        ).hexdigest(),
        "caps": [
            {
                "id": c["id"],
                "original_rim_source_edge_count": c["source_boundary_edges"],
                "original_3d_seam_perimeter_mm": c["source_3d_rim_perimeter_mm"],
                "three_dimensional_cap_vertices": len(c["vertices_xyz_mm"]),
                "three_dimensional_cap_triangles": len(
                    c["triangles_local_vertex_indices"]
                ),
                "topological_Euler": c["source_topological_Euler"],
                "original_source_rim_SHA256": c["source_original_rim_edge_ids_sha256"],
            }
            for c in study["upper_caps"]
        ],
        "lower_surface": {
            k: v
            for k, v in study["lower_single_original_surface"].items()
            if k != "lower_head_cut_rims"
        },
        "all_upper_lower_rims_3d_matched": study[
            "upper_to_lower_source_netline_matched_at_1e_6_mm"
        ],
        "original_four_hoof_source_boundaries_4x512_retained": True,
        "original_source_geometry_was_not_replaced_or_approved": True,
        "not_a_two_sided_2d_seam_or_a_manufacturing_cut": True,
        "factory_cutting_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
    }
    for path in (args.output, args.summary):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(details, encoding="utf8")
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf8")
    print("STAGE6_TRUE_CROWN_3D_CAPS_3_AND_LOWER_FOUR_HOOFS", flush=True)


if __name__ == "__main__":
    main()
