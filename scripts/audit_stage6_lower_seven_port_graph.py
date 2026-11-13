"""Verify original Stage6 7-rim lower source joins and draw real 3D seam atlas.

The SVG is a physical-millimetre *top projection*, not a fabric rest pattern.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from propose_stage6_shell_panels import load_pinned_proxy

from plush_pattern_lab.patterns.stage6_lower_seven_port_svg import (
    render_seven_real_rims_a4,
)
from plush_pattern_lab.validation.stage6_lower_seven_port_graph import (
    audit_original_seven_port_shell,
)

CAPS_SUMMARY_SCHEMA = "stage6-real-source-z230-three-cap-3d-topology-audit-v1"


def _source_inputs(args):
    files = (args.proxy, args.caps, args.caps_summary, args.four_zone)
    outputs = (args.output, args.svg_y20, args.svg_y25)
    if (
        any(not path.is_file() or path.is_symlink() for path in files)
        or any(path.exists() or path.is_symlink() for path in outputs)
        or len({path.resolve() for path in outputs}) != 3
        or args.output.suffix != ".json"
        or args.svg_y20.suffix != ".svg"
        or args.svg_y25.suffix != ".svg"
    ):
        raise ValueError("locked original source missing or would overwrite evidence")
    caps_raw = args.caps.read_bytes()
    four_raw = args.four_zone.read_bytes()
    summary = json.loads(args.caps_summary.read_bytes())
    if (
        summary.get("schema") != CAPS_SUMMARY_SCHEMA
        or summary.get("full_3d_source_caps_json_sha256")
        != hashlib.sha256(caps_raw).hexdigest()
        or not summary.get("all_upper_lower_rims_3d_matched")
        or not summary.get("original_four_hoof_source_boundaries_4x512_retained")
        or summary.get("factory_cutting_patterns_approved") != 0
    ):
        raise ValueError("source upper/lower cap proof and same-run data mismatch")
    return json.loads(caps_raw), json.loads(four_raw), caps_raw, four_raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proxy", required=True, type=Path)
    parser.add_argument("--caps", required=True, type=Path)
    parser.add_argument("--caps-summary", required=True, type=Path)
    parser.add_argument("--four-zone", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--svg-y20", required=True, type=Path)
    parser.add_argument("--svg-y25", required=True, type=Path)
    args = parser.parse_args()
    caps, four, caps_raw, four_raw = _source_inputs(args)
    source, triangles = load_pinned_proxy(args.proxy)
    import trimesh  # noqa: PLC0415 - pinned optional MIT research dependency

    report = audit_original_seven_port_shell(source, triangles, caps, four, trimesh)
    images = [
        render_seven_real_rims_a4(source, triangles, caps, report, split, trimesh)
        for split in (20.0, 25.0)
    ]
    report["same_run_original_three_caps_sha256"] = hashlib.sha256(caps_raw).hexdigest()
    report["same_run_original_four_zone_sha256"] = hashlib.sha256(four_raw).hexdigest()
    report["true_3D_XY_top_view_svg_sha256"] = [
        hashlib.sha256(svg.encode("utf8")).hexdigest() for svg in images
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for path in (args.svg_y20, args.svg_y25):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.svg_y20.write_text(images[0], encoding="utf8")
    args.svg_y25.write_text(images[1], encoding="utf8")
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf8",
    )
    print(
        "STAGE6_REAL_LOWER_SEVEN_RIMS_HEAD_AND_FOUR_HOOF_3D_PAIRED_NOT_CLOTH",
        [
            {
                "Y": x["split_y_mm"],
                "loops": [
                    y["source_3D_boundary_loops"]
                    for y in x["lower_four_zone_source_patches"]
                ],
                "extra_topological_cuts": x[
                    "minimum_additional_topological_opening_cuts_to_four_disks"
                ],
            }
            for x in report["source_four_zone_comparisons"]
        ],
        flush=True,
    )


if __name__ == "__main__":
    main()
