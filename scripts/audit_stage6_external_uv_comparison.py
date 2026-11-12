"""Score original Stage6 LSCM vs FREE external Blender native ABF/Conformal.

Only research JSON/SVG, never an industrial pattern or printer cut file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from plush_pattern_lab.validation.stage6_external_uv_benchmark import (
    SCHEMA,
    compare_native_to_existing,
    fingerprint_source_bytes,
    render_comparison_svg,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--svg", type=Path, required=True)
    args = parser.parse_args()
    paths = (args.source, args.native, args.output, args.svg)
    if (
        any(not item.is_file() or item.is_symlink() for item in paths[:2])
        or any(item.exists() or item.is_symlink() for item in paths[2:])
        or len({item.resolve() for item in paths}) != 4
        or args.output.suffix != ".json"
        or args.svg.suffix != ".svg"
    ):
        raise ValueError(
            "unverified source/native input or attempt to overwrite evidence"
        )
    source = json.loads(args.source.read_text(encoding="utf8"))
    native = json.loads(args.native.read_text(encoding="utf8"))
    report = compare_native_to_existing(
        source, native, fingerprint_source_bytes(args.source)
    )
    preview = render_comparison_svg(report)
    if report["schema"] != SCHEMA or report["factory_cutting_patterns_approved"] != 0:
        raise ValueError("no factory cutting promotion on a solver benchmark")
    report["same_run_source_study_sha256"] = fingerprint_source_bytes(args.source)
    report["same_run_free_blender_native_raw_sha256"] = fingerprint_source_bytes(
        args.native
    )
    report["research_svg_sha256"] = hashlib.sha256(preview.encode("utf8")).hexdigest()
    for path in paths[2:]:
        path.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    args.svg.write_text(preview, encoding="utf8")
    print(
        "STAGE6_FREE_BLENDER_NATIVE_UV_COMPARE_NOT_CUTTING",
        json.dumps(report["method_comparison_summary"], sort_keys=True),
        flush=True,
    )


if __name__ == "__main__":
    main()
