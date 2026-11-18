"""R6 monotone side-lobe fabric bridge reusing R5 geometry and sewing tools.

The old 230 -> 240 -> 230 mm backtracking remains the rejected R5 control.
R6 only changes the 3D preposition and matching independent 2D fabric rest.
The four original Stage6 ear meshes are not physically sewn.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from research.stage6_b24_r5 import build_r5_side_lobes as base

R6_HEIGHTS_MM = (230.0, 231.0, 232.0, 235.0, 245.0)
R5_REJECTED_HEIGHTS_MM = (230.0, 240.0, 230.0, 235.0, 245.0)
R6_BRIDGE_FRACTION = 0.55


def bridge(arrays, faces, roles, springs, hole_ids, side, rings):
    """Rebuild R5's sewn topology without its descending-z foldback."""
    full = [
        rings[0],
        (1 - R6_BRIDGE_FRACTION) * rings[0] + R6_BRIDGE_FRACTION * rings[1],
        rings[1],
        rings[2],
        rings[3],
    ]
    heights = R6_HEIGHTS_MM
    if not np.all(np.diff(heights) > 0):
        raise ValueError("R6 fabric bridge has descending or duplicate height")
    all_ids = base._append_side_gores(
        arrays, faces, roles, springs, hole_ids, side, full, heights
    )
    for index, gore in enumerate(all_ids):
        following = all_ids[(index + 1) % 4]
        springs.extend(
            (int(a), int(b)) for a, b in zip(gore[:, -1], following[:, 0])
        )
    base._append_tip_wedges(
        arrays, faces, roles, springs, side, full, heights, all_ids
    )
    return {
        "side": "L" if side < 0 else "R",
        "gore_panels": 4,
        "vertices_per_gore": 45,
        "tip_wedge_panels": 4,
        "vertices_per_wedge": 10,
        "profile_z_mm": list(R6_HEIGHTS_MM),
        "original_source_sections_z_mm": list(base.SOURCE_LEVELS_MM),
        "synthetic_230mm_source_loop_raised_to_mm": 232.0,
        "actual_original_ear_Mesh_sewn": False,
    }


def generate(stage, source, output):
    """Export the separate R6 trial without mutating any prior R5 artifact."""
    out = Path(output)
    result = base.generate(stage, source, out, bridge_builder=bridge)
    staging = out / "R5_SOURCE_TWO_SIDE_LOBES_2D_REST_3D_PREPOSITION_NOT_SIMULATED.npz"
    digest = hashlib.sha256(staging.read_bytes()).hexdigest()
    if result["R5_stage_npz_SHA256"] != digest:
        raise ValueError("R6 stage hash does not match source-generated fabric")
    if not all(
        piece["profile_z_mm"] == list(R6_HEIGHTS_MM)
        for piece in result["side_lobe_panels"]
    ):
        raise ValueError("R6 right/left five-station heights changed")
    manifest = {
        "schema": "stage6-R6-monotone-lobe-no-backtracking-research-v1",
        "source_stage_sha256": digest,
        "underlying_reused_source_generator": "stage6_b24_r5.build_r5_side_lobes",
        "underlying_output_is_named_R5_for_solver_compatibility": True,
        "rejected_R5_nonmonotone_heights_mm": list(R5_REJECTED_HEIGHTS_MM),
        "R6_monotone_heights_mm": list(R6_HEIGHTS_MM),
        "R6_synthetic_bridge_factor": R6_BRIDGE_FRACTION,
        "source_original_235_and_245mm_z_preserved": True,
        "source_original_230mm_lobe_moved_up_2mm_for_clearance": True,
        "R3_original_986_springs_preserved": True,
        "R5_full_spring_identity_reused": True,
        "source_original_4_ear_meshes_sewn": 0,
        "native_Cloth_simulation_run": False,
        "factory_cutting_patterns_approved": 0,
    }
    path = out / "R6_MONOTONE_BRIDGE_PROVENANCE.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for item in ("stage", "source", "out"):
        parser.add_argument("--" + item, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(generate(args.stage, args.source, args.out), ensure_ascii=False))


if __name__ == "__main__":
    main()
