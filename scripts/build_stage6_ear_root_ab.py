"""Pinned Stage6 source Z230/Z235 ear-root A/B; research evidence only."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from propose_stage6_shell_panels import PROXY_SHA256, load_pinned_proxy

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256
from plush_pattern_lab.validation.stage6_ear_root_ab import (
    SCHEMA,
    compare_real_ear_root_ab,
)
from plush_pattern_lab.validation.stage6_ear_root_ab_svg import (
    render_root_ab_svg,
)


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inputs(args):
    sources = (
        args.section_summary,
        args.section_detail,
        args.source_slab,
        args.previous_41mesh,
    )
    targets = (args.output, args.svg)
    if (
        args.source_sha256 != SOURCE_SHA256
        or any(not path.is_file() or path.is_symlink() for path in sources)
        or args.output.suffix != ".json"
        or args.svg.suffix != ".svg"
        or args.output.resolve() == args.svg.resolve()
        or any(path.exists() or path.is_symlink() for path in targets)
    ):
        raise ValueError("untrusted source or output overwrites protected research")
    summary = json.loads(args.section_summary.read_text(encoding="utf8"))
    detail = json.loads(args.section_detail.read_text(encoding="utf8"))
    slab = json.loads(args.source_slab.read_text(encoding="utf8"))
    prior = json.loads(args.previous_41mesh.read_text(encoding="utf8"))
    detail_sha = _sha(args.section_detail)
    prior_sha = _sha(args.previous_41mesh)
    if (
        summary.get("schema") != "stage6-real-sculpt-contour-vs-split-A-B-trial-qa-v1"
        or summary.get("original_public_blend_sha256") != SOURCE_SHA256
        or summary.get("source_25percent_proxy_ply_sha256") != PROXY_SHA256
        or summary.get("full_original_source_contour_detail_sha256") != detail_sha
        or summary.get("factory_cutting_approved") != 0
        or slab.get("schema")
        != "stage6-actual-source-mesh-five-slab-head-ear-continuity-v1"
        or slab.get("same_run_section_detail_sha256") != detail_sha
        or slab.get("same_run_41_mesh_correspondence_sha256") != prior_sha
        or slab.get("factory_cutting_patterns_approved") != 0
        or prior.get("source_original_blend_sha256") != SOURCE_SHA256
        or prior.get("same_run_true_source_detail_sha256") != detail_sha
        or prior.get("raw_product_mesh_objects_checked") != 41
        or prior.get("factory_cutting_patterns_approved") != 0
    ):
        raise ValueError("cross-run or unsupported public Stage6 source evidence")
    return detail


def _validate_research(qa):
    if qa["schema"] != SCHEMA or qa["source_230_to_235_open_slab_triangles"] != 2708:
        raise ValueError("actual Stage6 Z230 to Z235 source slab changed")
    if qa["manufacturing_cutting_approved"] != 0:
        raise ValueError("source contour cannot be an approved cutting pattern")
    if [c["source_plane_z_mm"] for c in qa["candidate_options"]] != [230, 235]:
        raise ValueError("unexpected source ear root A/B variants")
    for option in qa["candidate_options"]:
        if (
            option["left_right_reflected_boundary_hausdorff_mm"] >= 0.5
            or [row["side"] for row in option["source_side_loops"]]
            != ["left", "right"]
            or not all(
                row["xy_minor_bbox_under_two_research_6mm_allowances"]
                for row in option["source_side_loops"]
            )
        ):
            raise ValueError("source ring symmetry, identity, or width risk changed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proxy", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--section-summary", type=Path, required=True)
    parser.add_argument("--section-detail", type=Path, required=True)
    parser.add_argument("--source-slab", type=Path, required=True)
    parser.add_argument("--previous-41mesh", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--svg", type=Path, required=True)
    args = parser.parse_args()
    detail = _inputs(args)
    vertices, faces = load_pinned_proxy(args.proxy)
    qa = compare_real_ear_root_ab(vertices, faces, detail)
    _validate_research(qa)
    atlas = render_root_ab_svg(qa)
    qa.update(
        {
            "original_public_stage6_blend_sha256": SOURCE_SHA256,
            "source_25pct_proxy_ply_sha256": PROXY_SHA256,
            "same_run_section_detail_sha256": _sha(args.section_detail),
            "same_run_section_summary_sha256": _sha(args.section_summary),
            "same_run_source_slab_sha256": _sha(args.source_slab),
            "same_run_41_mesh_correspondence_sha256": _sha(args.previous_41mesh),
            "source_ab_svg_sha256": hashlib.sha256(atlas.encode("utf8")).hexdigest(),
        }
    )
    for path in (args.output, args.svg):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.svg.write_text(atlas, encoding="utf8")
    args.output.write_text(
        json.dumps(qa, ensure_ascii=False, indent=2) + "\n",
        encoding="utf8",
    )
    print(
        "STAGE6_REAL_SOURCE_EAR_ROOT_RING_AB_NOT_SEWABLE_PAPER_PATTERNS",
        json.dumps(
            {
                "candidate_rings": [
                    [
                        row["name"],
                        [round(x["source_3d_ring_perimeter_mm"], 3)
                         for x in row["source_side_loops"]],
                    ]
                    for row in qa["candidate_options"]
                ],
                "approved": False,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
