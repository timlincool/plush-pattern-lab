"""Adversarial verification for quarantined legacy Blender Release archives."""

from __future__ import annotations

import hashlib
import json
import stat
import zipfile
from pathlib import Path

import pytest

from plush_pattern_lab.validation.archive_integrity import (
    _safe_name,
    audit,
    audit_one,
    load_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "design/archive-v25/release-integrity-manifest.json"


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fake_archive(root: Path, members: dict[str, bytes]) -> dict:
    archive = root / "01-baseline-v25.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as target:
        for name, value in members.items():
            target.writestr(name, value)
    return {
        "name": archive.name,
        "published_bytes": archive.stat().st_size,
        "published_sha256": _hash(archive.read_bytes()),
        "source_sha256": "f" * 64,
        "member_count": len(members),
        "member_sha256": {name: _hash(data) for name, data in members.items()},
    }


def test_six_source_release_archives_and_published_hashes_are_frozen():
    m = load_manifest(MANIFEST)
    assert m["source_repo"] == "timlincool/cloud-alpaca-plush"
    assert [x["name"][:2] for x in m["assets"]] == ["01", "02", "03", "04", "05", "06"]
    assert sum(e["member_count"] for e in m["assets"]) == 252
    assert all(len(e["member_sha256"]) == e["member_count"] for e in m["assets"])
    # Original archives 03..06 were repacked with documentation normalization.
    assert all(e["source_sha256"] != e["published_sha256"] for e in m["assets"][2:])


def test_manifest_refuses_route_or_wrong_sha(tmp_path):
    m = load_manifest(MANIFEST)
    m["public_repo"] = "attacker/unknown"
    file = tmp_path / "manifest.json"
    file.write_text(json.dumps(m))
    with pytest.raises(ValueError, match="routing"):
        load_manifest(file)
    m["public_repo"] = "timlincool/plush-pattern-lab"
    m["assets"][0]["published_sha256"] = "bad"
    file.write_text(json.dumps(m))
    with pytest.raises(ValueError, match="published SHA"):
        load_manifest(file)


def test_verified_synthetic_zip_never_claims_publication(tmp_path):
    asset = _fake_archive(tmp_path, {"README.md": b"safe original reference"})
    result = audit_one(tmp_path, asset)
    assert result["status"] == "INTEGRITY_VERIFIED_NEEDS_CONTENT_AND_LICENSE_REVIEW"
    assert result["errors"] == []
    assert result["warnings"] == []
    full = audit(tmp_path, {"assets": [asset] * 6})
    assert not full["public_release_uploaded"]


def test_tamper_of_outer_zip_is_blocked(tmp_path):
    asset = _fake_archive(tmp_path, {"design.json": b'{"format":"v1"}'})
    archive = tmp_path / asset["name"]
    poisoned = bytearray(archive.read_bytes())
    poisoned[-10] ^= 1  # Same file size: prove digest check, not just length.
    archive.write_bytes(poisoned)
    result = audit_one(tmp_path, asset)
    assert result["status"] == "BLOCKED"
    assert "SHA-256" in result["errors"][0]


def test_member_provenance_is_checked_even_if_outer_hash_matches(tmp_path):
    asset = _fake_archive(tmp_path, {"README.md": b"unexpected contents"})
    asset["member_sha256"]["README.md"] = "a" * 64
    result = audit_one(tmp_path, asset)
    assert result["status"] == "BLOCKED"
    assert "archived member" in result["errors"][0]


@pytest.mark.parametrize(
    "name",
    [
        "../escape.txt",
        "src/../../escape",
        "/etc/passwd",
        r"C:\Users\secret.txt",
        "folder//file.txt",
        "folder/./file.txt",
        "folder\\escape.txt",
        "folder/token:\nhidden",
    ],
)
def test_zip_path_is_never_allowed(name):
    assert not _safe_name(name)


def test_zip_slip_and_case_collisions_are_blocked(tmp_path):
    unsafe = _fake_archive(tmp_path, {"../../outside.py": b"print('bad')"})
    assert audit_one(tmp_path, unsafe)["status"] == "BLOCKED"
    collision = _fake_archive(tmp_path, {"Head.py": b"x=1\n", "head.py": b"y=2\n"})
    assert audit_one(tmp_path, collision)["status"] == "BLOCKED"


def test_embedded_secret_is_rejected_without_printing_actual_value(tmp_path):
    token = b"ghp_" + b"x" * 40
    archive = _fake_archive(tmp_path, {"secrets.py": b"API='" + token + b"' \n"})
    result = audit_one(tmp_path, archive)
    assert result["status"] == "BLOCKED"
    assert any("Potential embedded secret" in error for error in result["errors"])
    assert token.decode() not in json.dumps(result)


def test_binary_blend_remains_pending_independent_review(tmp_path):
    archive = _fake_archive(tmp_path, {"mesh.blend": b"BLENDER fake binary"})
    result = audit_one(tmp_path, archive)
    assert result["status"] == "INTEGRITY_VERIFIED_NEEDS_CONTENT_AND_LICENSE_REVIEW"
    assert (
        "Binary Blender/array asset needs isolated content review" in result["warnings"]
    )


def test_refuses_zip_symlink_member(tmp_path):
    target = tmp_path / "01-baseline-v25.zip"
    with zipfile.ZipFile(target, "w") as z:
        item = zipfile.ZipInfo("evil.py")
        item.create_system = 3
        item.external_attr = (stat.S_IFLNK | 0o777) << 16
        z.writestr(item, "target.txt")
    asset = {
        "name": target.name,
        "published_bytes": target.stat().st_size,
        "published_sha256": _hash(target.read_bytes()),
        "member_sha256": {"evil.py": _hash(b"target.txt")},
        "member_count": 1,
    }
    assert audit_one(tmp_path, asset)["status"] == "BLOCKED"


def test_missing_and_symlink_archives_are_blocked(tmp_path):
    asset = _fake_archive(tmp_path, {"README.md": b"safe"})
    (tmp_path / asset["name"]).unlink()
    assert audit_one(tmp_path, asset)["status"] == "BLOCKED"
    (tmp_path / asset["name"]).symlink_to(tmp_path / "target.zip")
    assert audit_one(tmp_path, asset)["status"] == "BLOCKED"
