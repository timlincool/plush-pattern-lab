"""Pinned Stage6 25% core PLY -> actual full-shell 3D four-zone seam graph.

Research segmentation only. Do not convert the top-view drawing to fabric cuts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from plush_pattern_lab.patterns.whole_shell_seam_map import (
    render_four_zone_seam_map,
)
from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256
from plush_pattern_lab.validation.whole_shell_partition import draft_four_zone_shell

PROXY_SHA256 = "5b52e3fd09c83b19c5b9d95d6d8d859a147ff4deef90f1518f868d2e82e3a2dd"
PROXY_BYTES = 2227384
VERTICES = 59306
FACES = 116568


def load_pinned_proxy(path):
    """Accept only the already-measured mesh-only binary PLY from public Stage6."""
    if not path.is_file() or path.is_symlink() or path.suffix != ".ply":
        raise ValueError("missing verified Stage6 research-only PLY")
    if path.stat().st_size != PROXY_BYTES:
        raise ValueError("wrong-size Stage6 PLY")
    if hashlib.sha256(path.read_bytes()).hexdigest() != PROXY_SHA256:
        raise ValueError("Stage6 proxy SHA-256 mismatch")
    with path.open("rb") as stream:
        header = b""
        while not header.endswith(b"end_header\n") and len(header) <= 4096:
            line = stream.readline()
            if not line:
                raise ValueError("truncated proxy PLY header")
            header += line
        metadata = header.decode("ascii")
        required = (
            "ply\nformat binary_little_endian 1.0\n",
            f"element vertex {VERTICES}\n",
            f"element face {FACES}\n",
            "property list uchar int vertex_indices\nend_header\n",
        )
        if any(key not in metadata for key in required):
            raise ValueError("untrusted PLY layout")
        points = np.fromfile(stream, dtype="<f4", count=VERTICES * 3)
        face_type = np.dtype([("n", "u1"), ("indices", "<i4", (3,))])
        records = np.fromfile(stream, dtype=face_type, count=FACES)
        if stream.read(1) or len(points) != VERTICES * 3 or len(records) != FACES:
            raise ValueError("truncated or excessive PLY content")
    if (records["n"] != 3).any():
        raise ValueError("research PLY contains nontriangle faces")
    return points.reshape(-1, 3).astype(np.float64), records["indices"]


def measure_splits(vertices, triangles):
    """Compare only two predeclared crosswise split locations with same source."""
    candidates = [
        draft_four_zone_shell(vertices, triangles, split_y_mm=cut)
        for cut in (20.0, 25.0)
    ]
    valid = [
        row
        for row in candidates
        if row["all_regions_single_connected_annuli_with_one_complete_hoof"]
    ]
    if not valid:
        raise ValueError("no valid four-zone topological split on real Stage6")
    selected = min(valid, key=lambda row: row["total_shared_3d_seam_length_mm"])
    return {
        "schema": "stage6-source-pinned-whole-shell-seam-plan-v1",
        "status": "3D_FOUR_ZONE_STRUCTURAL_RESEARCH_NO_CUT_PATTERN",
        "source_original_model_sha256": SOURCE_SHA256,
        "proxy_ply_sha256": PROXY_SHA256,
        "proxy_faces": FACES,
        "split_y_candidates_mm": [20.0, 25.0],
        "scenarios": candidates,
        "shorter_3d_seam_graph_study_y_mm": selected["split_y_mm"],
        "shortest_seam_is_not_verified_assembly_or_cost_optimum": True,
        "fabric_cut_pattern_approved": False,
        "real_2d_net_seams": False,
        "factory_approved": False,
        "limitations": [
            "3D topology / exact shared mesh edges only, not sewn fabric net lengths",
            "Four regions each still require a well-designed radial slit or more panels",
            "Four-way seam junctions and finite-stuffing/seam allowances unresolved",
            "No verified correct face placement or supplier material specification",
        ],
    }, selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--svg", type=Path, required=True)
    args = parser.parse_args()
    if args.source_sha256 != SOURCE_SHA256:
        raise ValueError("not the public Stage6 original source identity")
    if args.output.suffix != ".json" or args.svg.suffix != ".svg":
        raise ValueError("report must be JSON and 3D top-view reference SVG")
    if args.output.resolve() == args.svg.resolve():
        raise ValueError("research report and drawing paths must be distinct")
    if any(path.exists() or path.is_symlink() for path in (args.output, args.svg)):
        raise FileExistsError("refuse to overwrite measured paper-pattern research")
    vertices, faces = load_pinned_proxy(args.input)
    report, selected = measure_splits(vertices, faces)
    image = render_four_zone_seam_map(vertices, selected)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.svg.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.svg.write_text(image, encoding="utf-8")
    print(
        "STAGE6_REAL_WHOLE_SHELL_FOUR_REGION_SEAM_GRAPH",
        json.dumps(
            {
                "selected_y_mm": selected["split_y_mm"],
                "candidate_ratios": [row["split_y_mm"] for row in report["scenarios"]],
                "regions": [
                    {
                        "name": row["name"],
                        "faces": row["face_count"],
                        "components": row["face_components_by_shared_edge"],
                        "cuff": row["source_hoof_boundary_edges"],
                        "boundary_loops": row["boundary_loop_count"],
                    }
                    for row in selected["regions"]
                ],
                "cut_edges": selected["total_shared_3d_seam_edges"],
                "seam_length_mm": selected["total_shared_3d_seam_length_mm"],
                "seam_junctions": selected["shared_seam_junction_vertices_over_two"],
                "manufacturing_cut_approved": False,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
