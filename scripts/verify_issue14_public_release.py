"""Independently stream and SHA-256-verify the public Issue14 visual Release.

Downloads are anonymous HTTPS requests without gh, PAT, GitHub secrets or
access to the original private repository. Refuses unexpected content or hashes.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from importlib import import_module
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_proof = import_module("plush_pattern_lab.validation.public_release_proof")
BINARIES = _proof.BINARIES
REPO = _proof.REPO
SMALL_FILES = _proof.SMALL_FILES
SUMS_FILE = _proof.SUMS_FILE
TAG = _proof.TAG
check_small_documents = _proof.check_small_documents

MAX_SMALL_BYTES = 32768
READ_BYTES = 1024 * 1024


def release_url(filename: str) -> str:
    """Use only internally pinned ASCII names, never a user-supplied URL."""
    return f"https://github.com/{REPO}/releases/download/{TAG}/{filename}"


def read_small(filename: str) -> bytes:
    """Read bounded metadata while never attaching an authentication header."""
    request = urllib.request.Request(
        release_url(filename),
        headers={"User-Agent": "alpaca-anonymous-release-verifier"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        result = response.read(MAX_SMALL_BYTES + 1)
    if len(result) > MAX_SMALL_BYTES:
        raise ValueError(f"Unbounded metadata in {filename}")
    return result


def stream_binary(
    filename: str,
    expected_bytes: int,
    expected_sha: str,
    destination: Path | None,
) -> None:
    """Hash a public binary incrementally; optionally save to a new file only."""
    request = urllib.request.Request(
        release_url(filename),
        headers={"User-Agent": "alpaca-anonymous-release-verifier"},
    )
    digest = hashlib.sha256()
    consumed = 0
    with urllib.request.urlopen(request, timeout=90) as response:
        stream = destination.open("xb") if destination is not None else None
        try:
            while True:
                block = response.read(READ_BYTES)
                if not block:
                    break
                consumed += len(block)
                if consumed > expected_bytes:
                    raise ValueError("Public asset exceeds pinned size")
                digest.update(block)
                if stream is not None:
                    stream.write(block)
        finally:
            if stream is not None:
                stream.close()
    if consumed != expected_bytes or digest.hexdigest() != expected_sha:
        raise ValueError(f"Public SHA-256 or size mismatch: {filename}")
    print(
        f"ISSUE14_PUBLIC_BINARY_PASS {filename} bytes={consumed} sha256={expected_sha}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--download-dir", type=Path, help="Optional new, empty output directory"
    )
    args = parser.parse_args()
    print(f"ISSUE14_VERIFY_PUBLIC_RELEASE {REPO} tag={TAG} anonymous=true")
    sums = read_small(SUMS_FILE)
    manifest = read_small("visual-release-manifest.json")
    license_text = read_small("LICENSE-ASSETS-CC-BY-4.0.md")
    checksums = check_small_documents(sums, manifest, license_text)
    destination = args.download_dir
    if destination is not None:
        if destination.exists() or destination.is_symlink():
            raise ValueError("Output directory must not exist")
        destination.mkdir(parents=True)
        small = {
            SUMS_FILE: sums,
            "visual-release-manifest.json": manifest,
            "LICENSE-ASSETS-CC-BY-4.0.md": license_text,
        }
        if set(small) != SMALL_FILES | {SUMS_FILE}:
            raise ValueError("Unexpected metadata set")
        for filename, data in small.items():
            (destination / filename).write_bytes(data)
    for filename, (size, expected) in sorted(BINARIES.items()):
        if checksums[filename] != expected:
            raise ValueError("Published checksum does not match local source pin")
        target = destination / filename if destination is not None else None
        stream_binary(filename, size, expected, target)
    print(f"ISSUE14_PUBLIC_ANONYMOUS_SHA256_VERIFIED binary_assets={len(BINARIES)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, UnicodeError) as error:
        print(
            f"ISSUE14_PUBLIC_RELEASE_INVALID {type(error).__name__}: {error}",
            file=sys.stderr,
        )
        raise SystemExit(2) from error
