"""R7 source-linked root transition: lift before extending lateral head lobes.

Preserves R5/R6 40 panels and 1170 springs. No original ears are sewn.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from research.stage6_b24_r5 import build_r5_side_lobes as base

R7_LEVELS_MM = (230.0, 232.0, 234.0, 235.0, 245.0)
R7_FRACTIONS = (0.0, 0.12, 0.46, 1.0, 1.0)


def bridge(arrays, faces, roles, springs, hole_ids, side, rings):
    """Lift the root first, then sweep toward the original side lobe."""
    root = np.asarray(rings[0], dtype=float)
    source_at_230 = np.asarray(rings[1], dtype=float)
    full = [
        root,
        (1.0 - R7_FRACTIONS[1]) * root + R7_FRACTIONS[1] * source_at_230,
        (1.0 - R7_FRACTIONS[2]) * root + R7_FRACTIONS[2] * source_at_230,
        np.asarray(rings[2], dtype=float),
        np.asarray(rings[3], dtype=float),
    ]
    heights = R7_LEVELS_MM
    if any(b <= a for a, b in zip(heights, heights[1:])):
        raise ValueError("R7 non-monotone station in source root-to-ear transition")
    all_ids = base._append_side_gores(
        arrays, faces, roles, springs, hole_ids, side, full, heights
    )
    for i, gore in enumerate(all_ids):
        successor = all_ids[(i + 1) % len(all_ids)]
        springs.extend((int(a), int(b)) for a, b in zip(gore[:, -1], successor[:, 0]))
    base._append_tip_wedges(arrays, faces, roles, springs, side, full, heights, all_ids)
    return {
        "side": "L" if side < 0 else "R",
        "gore_panels": 4,
        "vertices_per_gore": 45,
        "tip_wedge_panels": 4,
        "vertices_per_wedge": 10,
        "profile_z_mm": list(heights),
        "source_high_lobe_real_z_sections_mm": list(base.SOURCE_LEVELS_MM),
        "source_230mm_loop_is_used_at_234mm_as_proxy": True,
        "original_real_ear_meshes_sewn": 0,
    }


def generate(stage, source, output):
    """Reuse trusted R5 panel construction and save a separate R7 candidate."""
    out = Path(output)
    report = base.generate(stage, source, out, bridge_builder=bridge)
    candidate = out / "R5_SOURCE_TWO_SIDE_LOBES_2D_REST_3D_PREPOSITION_NOT_SIMULATED.npz"
    digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
    if digest != report["R5_stage_npz_SHA256"]:
        raise ValueError("R7 3D/2D stage hash differs from audited generator")
    if len(report["side_lobe_panels"]) != 2 or any(
        x["profile_z_mm"] != list(R7_LEVELS_MM)
        for x in report["side_lobe_panels"]
    ):
        raise ValueError("R7 source panel identity changed")
    metadata = {
        "schema": "stage6-R7-ascending-ear-root-lift-research-v1",
        "source_stage_sha256": digest,
        "R7_profile_z_mm": list(R7_LEVELS_MM),
        "R7_root_to_true_230mm_lobe_fractions": list(R7_FRACTIONS),
        "source_235_245mm_z_preserved": True,
        "R3_986_springs_preserved": True,
        "R6_1170_springs_preserved": True,
        "true_original_4_ear_meshes_physically_sewn": False,
        "native_blender_evaluated_solver_not_yet_run": True,
        "factory_patterns_approved": 0,
    }
    (out / "R7_ROOT_TRANSITION_PROVENANCE.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("stage", "source", "out"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(generate(args.stage, args.source, args.out), ensure_ascii=False))


if __name__ == "__main__":
    main()
