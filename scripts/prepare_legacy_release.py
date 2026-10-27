"""Stage and audit six historical Blender archives without publishing or execution.

Run locally with GitHub CLI authenticated to the owner's old private repository.
Nothing is deleted or overwritten, and no private asset is sent to public CI.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from plush_pattern_lab.validation.archive_integrity import (
    SOURCE,
    audit,
    load_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "design" / "archive-v25" / "release-integrity-manifest.json"


def fetch_missing(directory: Path, manifest: dict) -> None:
    if shutil.which("gh") is None:
        raise ValueError("GitHub CLI gh is not installed or not on PATH")
    directory.mkdir(parents=True, exist_ok=True)
    for entry in manifest["assets"]:
        target = directory / entry["name"]
        if target.is_symlink():
            raise ValueError("Refusing symlink archive target")
        if target.exists():
            continue
        command = [
            "gh",
            "release",
            "download",
            manifest["source_tag"],
            "-R",
            SOURCE,
            "-D",
            str(directory),
            "--pattern",
            entry["name"],
        ]
        subprocess.run(command, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive-dir", type=Path, default=ROOT / "local-assets" / "legacy-release-v25"
    )
    parser.add_argument(
        "--report", type=Path, default=ROOT / "local-output" / "legacy-asset-audit.json"
    )
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    try:
        manifest = load_manifest(MANIFEST)
        archive_dir = args.archive_dir.resolve()
        if args.archive_dir.is_symlink():
            raise ValueError("Archive root cannot be a symlink")
        if args.download:
            fetch_missing(archive_dir, manifest)
        report = audit(archive_dir, manifest)
        if args.report.is_symlink() or args.report.exists():
            raise ValueError("Refusing to overwrite prior audit report")
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"MIGRATION_AUDIT_BLOCKED: {type(exc).__name__}", file=sys.stderr)
        return 1
    print(
        "ARCHIVE_INTEGRITY_AUDIT",
        json.dumps(
            {
                "status": report["status"],
                "verified": report["verified"],
                "total": report["total"],
                "report": str(args.report),
            },
            ensure_ascii=False,
        ),
    )
    return 0 if report["verified"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
