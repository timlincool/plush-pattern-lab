"""Same-run Stage6 source partial-arc audit from trusted 41Mesh evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from plush_pattern_lab.validation.stage6_ear_arc_screen import (
    compare_source_quadrant_arcs,
)
from plush_pattern_lab.validation.stage6_ear_arc_svg import (
    render_stage6_arc_screen_svg,
)


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", required=True, type=Path)
    parser.add_argument("--visibility", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--svg", required=True, type=Path)
    args = parser.parse_args()
    sources = (args.study, args.visibility)
    outputs = (args.output, args.svg)
    if (
        any(not path.is_file() or path.is_symlink() for path in sources)
        or any(path.exists() or path.is_symlink() for path in outputs)
        or len({path.resolve() for path in (*sources, *outputs)}) != 4
        or args.output.suffix != ".json"
        or args.svg.suffix != ".svg"
    ):
        raise ValueError("source missing or original research output overwrite denied")
    study = json.loads(args.study.read_text(encoding="utf8"))
    visibility = json.loads(args.visibility.read_text(encoding="utf8"))
    if visibility.get("same_run_ear_root_study_sha256") != _sha(args.study):
        raise ValueError("cross-run original source and 41Mesh evidence mismatch")
    report = compare_source_quadrant_arcs(study, visibility)
    atlas = render_stage6_arc_screen_svg(report, study)
    report["same_run_ear_root_source_json_sha256"] = _sha(args.study)
    report["same_run_original_41mesh_visibility_json_sha256"] = _sha(args.visibility)
    report["arc_review_svg_sha256"] = hashlib.sha256(atlas.encode("utf8")).hexdigest()
    for output in outputs:
        output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf8",
    )
    args.svg.write_text(atlas, encoding="utf8")
    print(
        "STAGE6_FOUR_SOURCE_QUADRANT_ARCS_NOT_SEWABLE_PATTERN",
        json.dumps(
            [
                {
                    "option": option["name"],
                    "medial_12_samples": [
                        {
                            "side": side["side"],
                            "near_body_first_hits_in_four_views": sum(
                                item["near_original_body_first_surface"]
                                for item in side["quadrant_arc_hypotheses"][0][
                                    "per_view_12point_first_hit"
                                ].values()
                            ),
                        }
                        for side in option["sides"]
                    ],
                }
                for option in report["option_results"]
            ]
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
