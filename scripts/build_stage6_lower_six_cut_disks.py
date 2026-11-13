"""Locked Stage6 seven-rim original lower shell -> four 3D source disks.

No 2D cloth pattern, and no 3D topology alone authorizes factory cutting.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from propose_stage6_shell_panels import PROXY_SHA256, load_pinned_proxy

from plush_pattern_lab.validation.stage6_lower_six_cut_disks import (
    SCHEMA,
    build_lower_six_cut_disks,
)


def _raw(path):
    if not path.is_file() or path.is_symlink():
        raise ValueError("missing pinned Stage6 original source evidence")
    return path.read_bytes()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proxy", required=True, type=Path)
    parser.add_argument("--caps", required=True, type=Path)
    parser.add_argument("--four-zone", required=True, type=Path)
    parser.add_argument("--seven-ports", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if (
        args.output.suffix != ".json"
        or args.output.exists()
        or args.output.is_symlink()
        or hashlib.sha256(_raw(args.proxy)).hexdigest() != PROXY_SHA256
    ):
        raise ValueError("original Stage6 PLY changed or output would be replaced")
    cap_raw = _raw(args.caps)
    full_raw = _raw(args.four_zone)
    qa = json.loads(_raw(args.seven_ports))
    if (
        qa.get("same_run_original_three_caps_sha256")
        != hashlib.sha256(cap_raw).hexdigest()
        or qa.get("same_run_original_four_zone_sha256")
        != hashlib.sha256(full_raw).hexdigest()
        or qa.get("factory_cutting_patterns_approved") != 0
    ):
        raise ValueError("source seven-port/cap/four-zone SHA mismatch")
    xyz, faces = load_pinned_proxy(args.proxy)
    import trimesh  # noqa: PLC0415 - audited MIT 4.11.1 research source cut

    result = build_lower_six_cut_disks(
        xyz,
        faces,
        json.loads(cap_raw),
        json.loads(full_raw),
        qa,
        trimesh,
    )
    if result["schema"] != SCHEMA:
        raise ValueError("original Stage6 source disk schema drift")
    result["same_run_original_caps_sha256"] = hashlib.sha256(cap_raw).hexdigest()
    result["same_run_four_zone_sha256"] = hashlib.sha256(full_raw).hexdigest()
    result["same_run_seven_port_QA_sha256"] = hashlib.sha256(
        _raw(args.seven_ports)
    ).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf8",
    )
    print(
        "STAGE6_TRUE_LOWER_7RIM_4SOURCE_DISKS_6PAIRED_3D_PATHS_NO_CLOTH",
        [
            (
                zone["id"],
                [
                    round(seam["original_3d_netline_mm"], 4)
                    for seam in zone["original_source_3d_disk_seam_paths"]
                ],
            )
            for zone in result["source_topological_disks"]
        ],
        flush=True,
    )


if __name__ == "__main__":
    main()
