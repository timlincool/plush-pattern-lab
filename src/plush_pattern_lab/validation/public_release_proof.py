"""Pure integrity contract for the owner-approved Cloud Alpaca visual release.

This checks the exact published binary inventory. It does not attest to
manufacturing readiness or decide the rights of unrelated third-party files.
"""

from __future__ import annotations

import hashlib
import json
import re

REPO = "timlincool/plush-pattern-lab"
TAG = "cloud-alpaca-stage6-visuals-20261028"
ORIGINAL_MODEL_SHA = "791f4844bb87b9d2e7d10a21e01846d06cdf9c205153c6acf47cf7ab76b0f602"
BINARIES = {
    "cloud-alpaca-stage6.blend": (
        89853017,
        "38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a",
    ),
    "original-design.png": (
        1970766,
        "0ecf0fb619b1295dc7301af799b2b8ac2ab22fc8918ffca6378b5136ae164afa",
    ),
    "selected-D-appearance.png": (
        1299661,
        "33f9bf71b11ee9d4ca2e75e310900caefb840a872428de4caf200480eddd664b",
    ),
    "single-hoof-seam-comparison.png": (
        749341,
        "e1a6f22eecb48973ade1b20eda599ada1a47cf9d43700c32a5d38e3a9b8a65c4",
    ),
    "single-hoof-fleece-comparison.png": (
        732441,
        "284913c42c93a726611bcf36e7d09cb230d563caeba0d9bab9190d7d62c1708a",
    ),
}
SMALL_FILES = {"LICENSE-ASSETS-CC-BY-4.0.md", "visual-release-manifest.json"}
SUMS_FILE = "SHA256SUMS"
EXPECTED_FILES = set(BINARIES) | SMALL_FILES | {SUMS_FILE}
LINE = re.compile(r"([0-9a-f]{64})  ([A-Za-z0-9][A-Za-z0-9._-]*)\Z")


def digest(raw: bytes) -> str:
    """Compute the SHA-256 of a bounded in-memory metadata document."""
    return hashlib.sha256(raw).hexdigest()


def parse_checksum_file(raw: bytes) -> dict[str, str]:
    """Reject path traversal, duplicates, missing items and unsigned extras."""
    if len(raw) > 4096:
        raise ValueError("Unbounded checksum file")
    lines = raw.decode("utf-8").splitlines()
    checksums: dict[str, str] = {}
    for line in lines:
        match = LINE.fullmatch(line)
        if match is None or match[2] in checksums:
            raise ValueError("Invalid or repeated checksum entry")
        checksums[match[2]] = match[1]
    if set(checksums) != EXPECTED_FILES - {SUMS_FILE}:
        raise ValueError("Public Release inventory differs from expected visual files")
    for filename, (_, expected) in BINARIES.items():
        if checksums[filename] != expected:
            raise ValueError("Published visual checksum differs from pinned source")
    return checksums


def validate_manifest(raw: bytes) -> dict:
    """Check the published license, five binary identities, and excluded source ZIPs."""
    if len(raw) > 32768:
        raise ValueError("Unbounded Release manifest")
    document = json.loads(raw.decode("utf-8"))
    required = {
        "schema": "issue14-public-visual-release-v1",
        "tag": TAG,
        "status": "ORIGINAL_ARTWORK_AND_SAVED_STAGE6_ONLY",
        "license": "CC BY 4.0 for original artistic assets; MIT for owned source",
        "original_private_model_sha256": ORIGINAL_MODEL_SHA,
        "public_model_sha256": BINARIES["cloud-alpaca-stage6.blend"][1],
        "historical_six_zips": "NOT_INCLUDED_STRICT_REPRODUCTION_GATE_PENDING",
    }
    if any(document.get(key) != expected for key, expected in required.items()):
        raise ValueError("Public Release provenance or license contract mismatch")
    assets = document.get("assets")
    if not isinstance(assets, list) or len(assets) != 5:
        raise ValueError("Expected five binary assets")
    seen = set()
    for asset in assets:
        if not isinstance(asset, dict) or asset.get("name") not in BINARIES:
            raise ValueError("Unexpected asset record")
        name = asset["name"]
        if name in seen:
            raise ValueError("Duplicate Release asset record")
        seen.add(name)
        size, sha = BINARIES[name]
        expected_kind = (
            "sanitized_blender" if name.endswith(".blend") else "lossless_png"
        )
        if (asset.get("bytes"), asset.get("sha256"), asset.get("kind")) != (
            size,
            sha,
            expected_kind,
        ):
            raise ValueError("Release asset provenance mismatch")
    if seen != set(BINARIES):
        raise ValueError("Missing original visual asset")
    return document


def check_small_documents(
    sums: bytes, manifest: bytes, license_text: bytes
) -> dict[str, str]:
    """Verify small Release documents before accepting any binary download."""
    checksums = parse_checksum_file(sums)
    validate_manifest(manifest)
    if checksums["visual-release-manifest.json"] != digest(manifest):
        raise ValueError("Release manifest failed SHA-256")
    if checksums["LICENSE-ASSETS-CC-BY-4.0.md"] != digest(license_text):
        raise ValueError("Release license failed SHA-256")
    if b"Creative Commons Attribution 4.0" not in license_text:
        raise ValueError("CC BY 4.0 attribution license not present")
    return checksums
