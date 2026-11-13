"""Verify a separately installed GPL Blender sewing SVG against original Stage6.

Never promote this raw ABF outline to a cutting pattern or supplier release.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from plush_pattern_lab.validation.stage6_s2s_svg import audit_stage6_external_svg


def _read(path):
    if not path.is_file() or path.is_symlink():
        raise ValueError("no unsigned, missing or symlinked research input allowed")
    return path.read_bytes()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--native", required=True, type=Path)
    parser.add_argument("--audit", required=True, type=Path)
    parser.add_argument("--svg", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise ValueError("never replace an existing external SVG audit")
    source_bytes, native_bytes, svg_bytes = (
        _read(args.source),
        _read(args.native),
        _read(args.svg),
    )
    result = audit_stage6_external_svg(
        json.loads(source_bytes),
        json.loads(native_bytes),
        json.loads(_read(args.audit)),
        svg_bytes,
        hashlib.sha256(source_bytes).hexdigest(),
        hashlib.sha256(native_bytes).hexdigest(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(
        "STAGE6_S2S_REAL_ABF_NETLINE_SOURCE_ID_AND_MM_AUDITED_NOT_FACTORY",
        json.dumps(
            {
                "original_edges": result["source_boundary_edge_count"],
                "perimeter_mm": result["svg_netline_perimeter_mm"],
                "factory_approved": False,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
