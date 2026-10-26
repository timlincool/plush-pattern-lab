"""Exact, read-only verification of versioned Alpaca Release archives.

No extract(), import, exec, pickle or Blender execution. Inspection of binary
Blender resources and license remains a separate human-controlled step.
"""

from __future__ import annotations

import hashlib
import json
import re
import stat
import zipfile
from pathlib import Path, PurePosixPath

MAX_FILES = 2000
MAX_MEMBER_BYTES = 1024 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
CHUNK_BYTES = 1024 * 1024
TEXT_SUFFIXES = {".py", ".sh", ".md", ".txt", ".json", ".toml", ".yml", ".yaml", ".svg"}
SECRET = re.compile(
    rb"gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|"
    rb"sk-[A-Za-z0-9_-]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    re.IGNORECASE,
)
LOCAL_PATH = re.compile(rb"[A-Za-z]:\\Users\\[^\\\r\n]+|/home/[^/\r\n]+/|/Users/[^/\r\n]+/")
SHA = re.compile(r"[0-9a-f]{64}\Z")
SOURCE = "timlincool/cloud-alpaca-plush"
TARGET = "timlincool/plush-pattern-lab"


def load_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "plush-legacy-release-migration-v1":
        raise ValueError("Unrecognized release manifest schema")
    if data.get("source_repo") != SOURCE or data.get("public_repo") != TARGET:
        raise ValueError("Unexpected private-to-public repository routing")
    names = [entry.get("name") for entry in data.get("assets", [])]
    if len(names) != 6 or len(set(names)) != 6:
        raise ValueError("Expected precisely six selected source assets")
    for entry in data["assets"]:
        if not re.fullmatch(r"0[1-6]-[a-z0-9-]+\.zip", entry["name"]):
            raise ValueError("Unrecognized archive file name")
        if not SHA.fullmatch(entry.get("published_sha256", "")):
            raise ValueError("Missing published SHA-256")
        if not SHA.fullmatch(entry.get("source_sha256", "")):
            raise ValueError("Missing original source SHA-256")
        if len(entry.get("member_sha256", {})) != entry.get("member_count"):
            raise ValueError("Manifest member hashes/count disagree")
        if any(not SHA.fullmatch(value) for value in entry["member_sha256"].values()):
            raise ValueError("Invalid member SHA-256 in manifest")
    return data


def _sha256(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(CHUNK_BYTES), b""):
            sha.update(block)
    return sha.hexdigest()


def _safe_name(name: str) -> bool:
    if not name or name.startswith(("/", "\\")) or "\\" in name:
        return False
    if ":" in name or any(ord(ch) < 32 for ch in name):
        return False
    segments = name.rstrip("/").split("/")
    return all(segment not in ("", ".", "..") for segment in segments)


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    return stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK


def _audit_member(source: zipfile.ZipFile, info: zipfile.ZipInfo) -> tuple[str, list[str]]:
    digest = hashlib.sha256()
    flags: list[str] = []
    text_only = PurePosixPath(info.filename).suffix.lower() in TEXT_SUFFIXES
    overlap = b""
    with source.open(info, "r") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_BYTES), b""):
            digest.update(chunk)
            if not text_only:
                continue
            sample = overlap + chunk
            if SECRET.search(sample):
                flags.append("POSSIBLE_CREDENTIAL")
            if LOCAL_PATH.search(sample):
                flags.append("POSSIBLE_PERSONAL_ABSOLUTE_PATH")
            overlap = sample[-256:]
    return digest.hexdigest(), sorted(set(flags))


def _zip_members(archive: zipfile.ZipFile, expected: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    members = [info for info in archive.infolist() if not info.is_dir()]
    total = sum(info.file_size for info in members)
    if len(members) > MAX_FILES or total > MAX_TOTAL_BYTES:
        return ["Archive exceeds bounded size/count"], warnings
    names = [info.filename for info in members]
    if len(names) != len(set(name.casefold() for name in names)):
        errors.append("Duplicate or case-colliding archive entries")
    required = expected["member_sha256"]
    if set(names) != set(required):
        errors.append("Archive member inventory differs from signed release manifest")
    for info in members:
        if not _safe_name(info.filename) or _is_symlink(info):
            errors.append("Unsafe archive member path or symlink")
            continue
        if info.flag_bits & 1 or info.file_size > MAX_MEMBER_BYTES:
            errors.append("Encrypted or unbounded archive member")
            continue
        # Only read manifest-known paths. Do not execute or extract any archive.
        if info.filename not in required:
            continue
        digest, flags = _audit_member(archive, info)
        if digest != required[info.filename]:
            errors.append("Unexpected SHA-256 of archived member")
        if "POSSIBLE_CREDENTIAL" in flags:
            errors.append("Potential embedded secret in text archive member")
        if "POSSIBLE_PERSONAL_ABSOLUTE_PATH" in flags:
            warnings.append("Possible personal absolute path in text member")
        if PurePosixPath(info.filename).suffix.lower() in {".blend", ".npz", ".blend1"}:
            warnings.append("Binary Blender/array asset needs isolated content review")
    return sorted(set(errors)), sorted(set(warnings))


def audit_one(directory: Path, entry: dict) -> dict:
    name = entry["name"]
    path = directory / name
    result = {"name": name, "status": "BLOCKED", "errors": [], "warnings": []}
    if path.is_symlink() or not path.is_file():
        result["errors"] = ["Expected local ZIP is missing or a symlink"]
        return result
    if path.stat().st_size != entry["published_bytes"]:
        result["errors"] = ["Released archive file size mismatch"]
        return result
    if _sha256(path) != entry["published_sha256"]:
        result["errors"] = ["Released archive SHA-256 mismatch"]
        return result
    try:
        with zipfile.ZipFile(path) as archive:
            errors, warnings = _zip_members(archive, entry)
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile, EOFError) as exc:
        result["errors"] = [f"ZIP structure or CRC check failed: {type(exc).__name__}"]
        return result
    result["errors"] = errors
    result["warnings"] = warnings
    if not errors:
        result["status"] = "INTEGRITY_VERIFIED_NEEDS_CONTENT_AND_LICENSE_REVIEW"
    return result


def audit(directory: Path, manifest: dict) -> dict:
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Local archive directory is absent or symlinked")
    records = [audit_one(directory, entry) for entry in manifest["assets"]]
    verified = sum(row["status"].startswith("INTEGRITY_VERIFIED") for row in records)
    return {
        "schema": "alpaca-public-release-audit-v1",
        "status": "INTEGRITY_CHECKED_NOT_PUBLICATION_AUTHORIZED"
        if verified == 6 else "BLOCKED",
        "verified": verified,
        "total": 6,
        "public_release_uploaded": False,
        "requires": [
            "Isolated Blender embedded scripts and external library review",
            "Asset-by-asset ownership and CC0 or alternate license approval",
            "Blender 4.3.2 six-stage restore and save/reopen verification",
        ],
        "archives": records,
    }
