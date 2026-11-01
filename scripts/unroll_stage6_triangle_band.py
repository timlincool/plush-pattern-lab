"""Research-only Stage 6 3D triangle bands -> slit 2D candidate.

Only accepts temporary geometry extracted from the pinned public Stage6 model.
Run after Blender disabled-autoexec geometry extraction, not on untrusted PR code.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from plush_pattern_lab.patterns.seam_unroll_svg import draw_slit_unroll_svg
from plush_pattern_lab.validation.public_release_proof import MODEL_SHA256
from plush_pattern_lab.validation.seam_unroll_candidate import (
    unroll_triangular_band,
)

SCHEMA = "stage6-verified-local-triangle-bands-v1"
BODY = "PRIMARY continuous sculpt | new anatomy"
HOOFS = (
    "Rounded hoof base",
    "Rounded hoof base.001",
    "Rounded hoof base.002",
    "Rounded hoof base.003",
)


def _check_input(data):
    if data.get("schema") != SCHEMA or data.get("units") != "mm":
        raise ValueError("not a verified millimetre Stage6 geometry document")
    if data.get("source_sha256") != MODEL_SHA256:
        raise ValueError("unexpected public Stage6 model identity")
    patches = data.get("patches")
    if not isinstance(patches, list) or len(patches) != 8:
        raise ValueError("exactly eight Stage6 local surface rings are required")
    identities = [(p.get("object"), p.get("ring_index")) for p in patches]
    expected = {(BODY, i) for i in range(4)}
    expected.update((hoof, 0) for hoof in HOOFS)
    if len(set(identities)) != 8 or set(identities) != expected:
        raise ValueError("wrong Stage6 object/ring identity")
    for patch in patches:
        if len(patch["seam_ids"]) != 512 or len(patch["faces"]) != 768:
            raise ValueError("changed actual Stage6 local patch topology")
    return patches


def evaluate(data, budget):
    """Every result is a separate research candidate, never a cut approval."""
    patches = _check_input(data)
    records, polygons = [], []
    for patch in patches:
        score, uv = unroll_triangular_band(
            patch["vertices_mm"], patch["faces"], patch["seam_ids"], budget
        )
        records.append(
            {
                "object": patch["object"],
                "ring_index": patch["ring_index"],
                **score,
            }
        )
        polygons.append(uv)
    return {
        "schema": "stage6-eight-slit-unroll-candidates-v1",
        "source_sha256": MODEL_SHA256,
        "units": "mm",
        "status": "RESEARCH_CANDIDATES_NOT_CUT_PATTERNS",
        "all_original_seam_lengths_fixed": all(
            r["fixed_original_3d_seam_length"] for r in records
        ),
        "bands": records,
        "approved_for_cutting": False,
        "limitations": [
            "Slit seam is an imposed periodic arclength gauge, not measured fabric",
            "No pairwise body/hoof UV registration has been manufactured or sewn",
            "Even no overlaps and low edge error do not certify a plush toy",
        ],
    }, polygons


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--svg", type=Path, required=True)
    parser.add_argument("--budget", type=int, default=60)
    args = parser.parse_args()
    if not args.input.is_file() or args.input.stat().st_size > 8_000_000:
        raise ValueError("missing or unbounded Stage6 geometry")
    if args.output.suffix != ".json" or args.svg.suffix != ".svg":
        raise ValueError("output must be JSON and visual reference SVG")
    if args.output.resolve() == args.svg.resolve():
        raise ValueError("separate output paths required")
    if any(p.exists() or p.is_symlink() for p in (args.output, args.svg)):
        raise FileExistsError("refuse to overwrite research evidence")
    document = json.loads(args.input.read_text(encoding="utf-8"))
    result, layouts = evaluate(document, args.budget)
    svg = draw_slit_unroll_svg(result["bands"], layouts)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.svg.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.svg.write_text(svg, encoding="utf-8")
    print(
        "STAGE6_SLIT_UNROLL_RESEARCH",
        json.dumps(
            [
                {
                    "object": row["object"],
                    "ring_index": row["ring_index"],
                    "p95_initial": row["initial"]["p95_abs_edge_relative_error"],
                    "p95_optimized": row["optimized"]["p95_abs_edge_relative_error"],
                    "flips": row["optimized"][
                        "mixed_winding_or_collapsed_triangles"
                    ],
                    "overlap_pairs": row["overlap"]["overlapping_triangle_pairs"],
                    "slit_edges": row["cut_edges_count"],
                    "converged": row["solver"]["converged"],
                }
                for row in result["bands"]
            ]
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
