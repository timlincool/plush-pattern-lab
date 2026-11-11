"""Pin public Stage6 source-edge ear-dart tip research; no fabric cutting."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from propose_stage6_shell_panels import PROXY_SHA256, load_pinned_proxy

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256
from plush_pattern_lab.validation.stage6_dart_paths import (
    TIP_TARGETS_Z_MM,
    explore_source_ear_dart_endings,
)
from plush_pattern_lab.validation.stage6_dart_paths_svg import (
    render_dart_tip_comparison_svg,
)


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verified_sources(args):
    sources = (args.proxy, args.study, args.arc_screen, args.visibility)
    targets = (args.output, args.svg)
    if (
        args.source_sha256 != SOURCE_SHA256
        or any(not p.is_file() or p.is_symlink() for p in sources)
        or any(p.exists() or p.is_symlink() for p in targets)
        or len({p.resolve() for p in (*sources, *targets)}) != 6
        or args.output.suffix != ".json"
        or args.svg.suffix != ".svg"
        or _digest(args.proxy) != PROXY_SHA256
    ):
        raise ValueError("only original SHA-locked Stage6 research and new outputs")
    study = json.loads(args.study.read_text(encoding="utf8"))
    arc = json.loads(args.arc_screen.read_text(encoding="utf8"))
    visibility = json.loads(args.visibility.read_text(encoding="utf8"))
    if (
        study.get("original_public_stage6_blend_sha256") != SOURCE_SHA256
        or study.get("source_25pct_proxy_ply_sha256") != PROXY_SHA256
        or arc.get("input_original_blend_sha256") != SOURCE_SHA256
        or arc.get("same_run_ear_root_source_json_sha256") != _digest(args.study)
        or arc.get("same_run_original_41mesh_visibility_json_sha256")
        != _digest(args.visibility)
        or visibility.get("same_run_ear_root_study_sha256") != _digest(args.study)
        or visibility.get("raw_product_meshes_raycasted") != 41
        or arc.get("approved_factory_cutting_patterns") != 0
        or study.get("manufacturing_cutting_approved") != 0
    ):
        raise ValueError("cross-run or unsupported source contour and 41Mesh proof")
    return study, arc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proxy", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--arc-screen", type=Path, required=True)
    parser.add_argument("--visibility", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--svg", type=Path, required=True)
    args = parser.parse_args()
    study, screen = _verified_sources(args)
    xyz, triangles = load_pinned_proxy(args.proxy)
    report = explore_source_ear_dart_endings(xyz, triangles, screen, study)
    if (
        len(report["candidates"]) != 4
        or {row["tip_target_z_mm"] for row in report["candidates"]}
        != set(TIP_TARGETS_Z_MM)
        or any(
            not row["not_a_validated_two_sided_sewing_netline"]
            for row in report["candidates"]
        )
    ):
        raise ValueError("candidate route count or manufacturing rejection changed")
    svg = render_dart_tip_comparison_svg(report)
    report.update(
        {
            "public_original_stage6_blend_sha256": SOURCE_SHA256,
            "original_25percent_proxy_sha256": PROXY_SHA256,
            "same_run_source_study_sha256": _digest(args.study),
            "same_run_source_arc_screen_sha256": _digest(args.arc_screen),
            "same_run_source_41mesh_visibility_sha256": _digest(args.visibility),
            "svg_sha256": hashlib.sha256(svg.encode("utf8")).hexdigest(),
        }
    )
    for path in (args.output, args.svg):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    args.svg.write_text(svg, encoding="utf8")
    print(
        "STAGE6_SOURCE_MEDIAL_DART_ROUTING_RESEARCH_NOT_SEWING",
        json.dumps(
            [
                [
                    row["side"],
                    row["tip_target_z_mm"],
                    row["unconstrained_shortest_routes_meet_early_vertex_count"],
                    row["min_original_vertex_to_vertex_gap_beyond_tip_4mm_mm"],
                ]
                for row in report["candidates"]
            ]
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
