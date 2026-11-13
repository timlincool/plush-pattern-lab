"""Build four source-locked Stage6 3D short seam candidates, without UV.

Original left/right source caps, original 3D X/Y meridians and all raw faces
are untouched. Outputs source vertex correspondence for later Blender ABF.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from plush_pattern_lab.validation.stage6_protrusion_short_dart import build_short_darts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-caps", type=Path, required=True)
    parser.add_argument("--source-full-bisect", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (
        args.output.suffix != ".json"
        or args.output.exists()
        or args.output.is_symlink()
        or any(
            not p.is_file() or p.is_symlink()
            for p in (args.source_caps, args.source_full_bisect)
        )
    ):
        raise ValueError("source data missing or prior trial output would be changed")
    raw_caps = args.source_caps.read_bytes()
    raw_full = args.source_full_bisect.read_bytes()
    report = build_short_darts(
        json.loads(raw_caps),
        json.loads(raw_full),
        hashlib.sha256(raw_caps).hexdigest(),
    )
    report["same_run_original_full_meridians_sha256"] = hashlib.sha256(
        raw_full
    ).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf8",
    )
    print(
        "STAGE6_TWO_SHORT_REAR_INNER_SOURCE_RIM_TO_TIP_SLITS_PER_SIDE",
        [
            (x["id"], len(x["slit_path_original_cap_vertex_ids"]))
            for x in report["four_real_original_cap_short_slit_disks"]
        ],
        flush=True,
    )


if __name__ == "__main__":
    main()
