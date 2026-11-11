"""Trace authentic Stage6 source slab connectivity and 41Mesh provenance.

Only locked 25%-proxy triangle IDs and same-run true section/mesh evidence.
This does not generate sewing seams or manufacturing paper patterns.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from propose_stage6_shell_panels import PROXY_SHA256, load_pinned_proxy

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256
from plush_pattern_lab.validation.stage6_source_slab_continuity import (
    trace_true_source_slab,
)
from plush_pattern_lab.validation.stage6_source_slab_timeline import (
    render_source_slab_timeline,
)

REAL_SOURCE_BANDS = ((125, 135), (135, 145), (180, 205), (205, 230), (230, 245))
EXPECTED_SOURCE_TRIANGLES = (5078, 3566, 7127, 9597, 4691)
EXPECTED_SLAB_COMPONENTS = (2, 1, 1, 1, 3)


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inputs(args):
    sources = (args.section_summary, args.section_detail, args.correspondence)
    outputs = (args.output, args.svg)
    if args.source_sha256 != SOURCE_SHA256:
        raise ValueError("original public Stage6 source SHA is required")
    if (
        any(not p.is_file() or p.is_symlink() for p in sources)
        or args.output.suffix != ".json"
        or args.svg.suffix != ".svg"
        or args.output.resolve() == args.svg.resolve()
        or any(p.exists() or p.is_symlink() for p in outputs)
    ):
        raise ValueError("invalid, untrusted or already existing research input/output")
    summary = json.loads(args.section_summary.read_text(encoding="utf8"))
    detail = json.loads(args.section_detail.read_text(encoding="utf8"))
    prior = json.loads(args.correspondence.read_text(encoding="utf8"))
    if (
        summary.get("original_public_blend_sha256") != SOURCE_SHA256
        or summary.get("source_25percent_proxy_ply_sha256") != PROXY_SHA256
        or summary.get("full_original_source_contour_detail_sha256")
        != _sha(args.section_detail)
        or summary.get("factory_cutting_approved") != 0
        or prior.get("schema")
        != "stage6-original-section-41-product-mesh-proximity-5view-v1"
        or prior.get("source_original_blend_sha256") != SOURCE_SHA256
        or prior.get("same_run_true_source_detail_sha256")
        != _sha(args.section_detail)
        or prior.get("raw_product_mesh_objects_checked") != 41
        or prior.get("factory_cutting_patterns_approved") != 0
    ):
        raise ValueError("cross-experiment or corrupted original source evidence")
    return detail


def _locked_real_anatomy(reports):
    if (
        tuple(r["source_triangle_count_in_open_slab"] for r in reports)
        != EXPECTED_SOURCE_TRIANGLES
        or tuple(r["source_surface_component_count_in_open_slab"] for r in reports)
        != EXPECTED_SLAB_COMPONENTS
    ):
        raise ValueError("locked original Stage6 source band component anatomy changed")
    branch = reports[3]
    crown = reports[4]
    if (
        len(branch["surface_components"]) != 1
        or branch["surface_components"][0]["lower_loop_indices"] != [0]
        or branch["surface_components"][0]["upper_loop_indices"] != [0, 1, 2]
        or sorted(
            (tuple(c["lower_loop_indices"]), tuple(c["upper_loop_indices"]))
            for c in crown["surface_components"]
        ) != [((0,), ()), ((1,), (0,)), ((2,), (1,))]
    ):
        raise ValueError("Stage6 branching / crown cap source continuity changed")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proxy", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--section-summary", type=Path, required=True)
    parser.add_argument("--section-detail", type=Path, required=True)
    parser.add_argument("--correspondence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--svg", type=Path, required=True)
    args = parser.parse_args()
    detail = _inputs(args)
    xyz, tri = load_pinned_proxy(args.proxy)
    reports = [
        trace_true_source_slab(xyz, tri, detail, lower, upper)
        for lower, upper in REAL_SOURCE_BANDS
    ]
    _locked_real_anatomy(reports)
    atlas = render_source_slab_timeline(reports)
    evidence = {
        "schema": "stage6-actual-source-mesh-five-slab-head-ear-continuity-v1",
        "original_public_blend_sha256": SOURCE_SHA256,
        "original_source_proxy_sha256": PROXY_SHA256,
        "same_run_section_summary_sha256": _sha(args.section_summary),
        "same_run_section_detail_sha256": _sha(args.section_detail),
        "same_run_41_mesh_correspondence_sha256": _sha(args.correspondence),
        "source_face_count": len(tri),
        "actual_original_triangle_slab_reports": reports,
        "timeline_svg_sha256": hashlib.sha256(atlas.encode("utf8")).hexdigest(),
        "branching_is_source_surface_geometry_not_a_sewing_seam": True,
        "fabric_and_designed_ear_root_not_tested": True,
        "factory_cutting_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
    }
    for path in (args.output, args.svg):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.svg.write_text(atlas, encoding="utf8")
    args.output.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(
        "STAGE6_REAL_HEAD_EAR_BRANCH_AND_CAP_TOPOLOGY_NOT_MANUFACTURING_SEAM",
        json.dumps(
            {
                "slabs": [
                    [r["lower_plane_z_mm"], r["upper_plane_z_mm"],
                     r["source_surface_component_count_in_open_slab"]]
                    for r in reports
                ],
                "factory_approved": False,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
