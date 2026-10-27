"""Static review of six locally verified model archives (without execution)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from plush_pattern_lab.validation.archive_integrity import audit_one, load_manifest
from plush_pattern_lab.validation.archive_static import inspect_archive

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive-dir", type=Path,
        default=ROOT / "local-assets" / "legacy-release-v25"
    )
    parser.add_argument(
        "--report", type=Path,
        default=ROOT / "local-output" / "legacy-static-review.json"
    )
    args = parser.parse_args()
    manifest = load_manifest(
        ROOT / "design/archive-v25/release-integrity-manifest.json"
    )
    if args.report.exists() or args.report.is_symlink():
        raise ValueError("Refusing to overwrite review history")
    results = []
    for asset in manifest["assets"]:
        integrity = audit_one(args.archive_dir, asset)
        if not integrity["status"].startswith("INTEGRITY_VERIFIED"):
            raise ValueError(f"Integrity must pass before inspecting {asset['name']}")
        result = inspect_archive(args.archive_dir / asset["name"])
        result["asset"] = asset["name"]
        results.append(result)
    report = {
        "schema": "plush-archive-static-review-v1",
        "status": "STATIC_REVIEW_REQUIRED_NOT_PUBLICATION_AUTHORIZED",
        "scanned_archives": len(results),
        "results": results,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("ARCHIVE_STATIC_REVIEW", json.dumps({
        "archives": len(results),
        "scripts": sum(x["scripts_inspected"] for x in results),
        "arrays": sum(x["numeric_arrays_checked"] for x in results),
        "findings": sum(len(x["risk_findings"]) for x in results),
        "status": report["status"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
