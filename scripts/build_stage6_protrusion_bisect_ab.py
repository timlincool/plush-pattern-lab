"""Source-only candidate cuts: exact original Stage6 rim, two original-edge routes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from plush_pattern_lab.validation.stage6_real_protrusion_bisect import (
    SOURCE_SCHEMA,
    build_real_protrusion_bisect_ab,
)

ORIGINAL_PROXY_SHA = "5b52e3fd09c83b19c5b9d95d6d8d859a147ff4deef90f1518f868d2e82e3a2dd"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-caps", required=True, type=Path)
    parser.add_argument("--source-summary", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise ValueError("refuse to overwrite source-seam research")
    if any(
        not p.is_file() or p.is_symlink()
        for p in (args.source_caps, args.source_summary)
    ):
        raise ValueError("missing original real source caps or summary")
    raw = args.source_caps.read_bytes()
    source = json.loads(raw)
    summary = json.loads(args.source_summary.read_bytes())
    if (
        source.get("schema") != SOURCE_SCHEMA
        or source.get("source_proxy_ply_sha256") != ORIGINAL_PROXY_SHA
        or summary.get("full_3d_source_caps_json_sha256")
        != hashlib.sha256(raw).hexdigest()
        or not summary.get("all_upper_lower_rims_3d_matched")
    ):
        raise ValueError("source real Stage6 3D cap/summary witness mismatch")
    report = build_real_protrusion_bisect_ab(source)
    report["same_run_real_3d_original_three_caps_sha256"] = hashlib.sha256(
        raw
    ).hexdigest()
    report["pinned_original_25_percent_proxy_sha256"] = ORIGINAL_PROXY_SHA
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, separators=(",", ":"), ensure_ascii=False) + "\n",
        encoding="utf8",
    )
    print(
        "STAGE6_REAL_ORIGINAL_SIDE_MERIDIAN_2ROUTES_4PANELS_EACH_RESEARCH",
        flush=True,
    )


if __name__ == "__main__":
    main()
