"""Anonymously verify the single public Stage 6 Blender Release asset.

The four original PNG references are verified separately inside Git.
No GitHub token, private repository or third-party Python package is needed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from importlib import import_module
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_proof = import_module("plush_pattern_lab.validation.public_release_proof")

READ_BYTES = 1024 * 1024


def release_metadata_url() -> str:
    return f"https://api.github.com/repos/{_proof.REPO}/releases/tags/{_proof.TAG}"


def read_release_metadata() -> None:
    """Validate actual public Release assets, not an untrusted checksum manifest."""
    request = urllib.request.Request(
        release_metadata_url(),
        headers={"User-Agent": "alpaca-anonymous-stage6-verifier"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        raw = response.read(_proof.MAX_METADATA_BYTES + 1)
    _proof.validate_release_metadata(raw)


def hash_stream(response, output, expected_bytes: int) -> tuple[int, str]:
    """Hash a remote stream with a hard byte ceiling and optional destination."""
    digest = hashlib.sha256()
    consumed = 0
    while block := response.read(READ_BYTES):
        consumed += len(block)
        if consumed > expected_bytes:
            raise ValueError("Stage 6 asset exceeds pinned size")
        digest.update(block)
        if output is not None:
            output.write(block)
    return consumed, digest.hexdigest()


def stream_binary(
    filename: str,
    expected_bytes: int,
    expected_sha: str,
    destination: Path | None,
) -> None:
    """Verify content and remove an incomplete download on failure."""
    if filename != _proof.MODEL_NAME or expected_bytes != _proof.MODEL_BYTES:
        raise ValueError("Only the pinned Stage 6 asset may be downloaded")
    if expected_sha != _proof.MODEL_SHA256:
        raise ValueError("Unrecognized Stage 6 source SHA")
    request = urllib.request.Request(
        _proof.release_asset_url(),
        headers={"User-Agent": "alpaca-anonymous-stage6-verifier"},
    )
    created = False
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            output = destination.open("xb") if destination is not None else None
            created = output is not None
            try:
                consumed, actual_sha = hash_stream(response, output, expected_bytes)
            finally:
                if output is not None:
                    output.close()
        if consumed != expected_bytes or actual_sha != expected_sha:
            raise ValueError("Stage 6 SHA-256 or size mismatch")
    except Exception:
        if created and destination is not None:
            destination.unlink(missing_ok=True)
        raise
    print(f"STAGE6_PUBLIC_SHA256_PASS bytes={consumed} sha256={expected_sha}")

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--download-dir",
        type=Path,
        help="Optional new output directory; never overwrite",
    )
    args = parser.parse_args()
    print(f"STAGE6_VERIFY {release_metadata_url()} anonymous=true")
    read_release_metadata()
    destination = args.download_dir
    if destination is not None:
        if destination.exists() or destination.is_symlink():
            raise ValueError("Output directory must not exist")
        destination.mkdir(parents=True)
    try:
        stream_binary(
            _proof.MODEL_NAME,
            _proof.MODEL_BYTES,
            _proof.MODEL_SHA256,
            destination / _proof.MODEL_NAME if destination is not None else None,
        )
    except Exception:
        if destination is not None:
            destination.rmdir()
        raise
    print("STAGE6_PUBLIC_ASSET_VERIFIED binary_assets=1")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as error:
        print(
            f"STAGE6_PUBLIC_ASSET_INVALID {type(error).__name__}: {error}",
            file=sys.stderr,
        )
        raise SystemExit(2) from error
