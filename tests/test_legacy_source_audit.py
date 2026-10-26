"""Provenance of scanned (not yet published) legacy Alpaca release sources."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "design" / "archive-v25" / "audit-proof.json"


def _proof():
    return json.loads(PROOF.read_text(encoding="utf-8"))


def test_release_audit_is_complete_and_does_not_claim_public_upload():
    result = _proof()
    assert result["source_audit_run"] == 40310679635
    assert result["verification"]["archive_sha256_verified"] == 6
    assert result["verification"]["zip_members_verified"] == 252
    assert result["verification"]["archive_errors"] == 0
    assert not result["verification"]["publicly_published"]


def test_original_blender_security_claim_is_explicitly_scoped():
    scene = _proof()["blender_preflight"]
    assert scene["status"] == "PASS_SCOPE_LIMITED"
    assert scene["version"] == "4.3.2"
    assert scene["scene_objects"] == 465
    assert scene["embedded_scripts"] == scene["external_blender_libraries"] == 0
    assert scene["findings"] == 0
    assert _proof()["release_status"].startswith("UNPUBLISHED")


def test_images_have_verified_source_git_blobs_and_one_metadata_cleanup():
    files = _proof()["image_candidates"]
    assert len(files) == 4
    assert [i["metadata_stripped"] for i in files] == [False, True, False, False]
    assert all(len(i["git_blob_sha1"]) == 40 for i in files)
    assert files[0]["name"] == "original-design.png"
    assert files[1]["prepared_sha256"] != files[1]["source_sha256"]
