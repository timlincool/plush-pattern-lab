"""Good and hostile fixtures for anonymous Stage6 asset verification."""

from __future__ import annotations

import hashlib
import io
import json

import pytest

from plush_pattern_lab.validation import public_release_proof as proof
from scripts import verify_issue14_public_release as cli


def example_documents() -> tuple[bytes, bytes, bytes]:
    assets = [
        {
            "name": name,
            "bytes": size,
            "sha256": sha,
            "kind": "sanitized_blender" if name.endswith(".blend") else "lossless_png",
        }
        for name, (size, sha) in sorted(proof.BINARIES.items())
    ]
    manifest = {
        "schema": "issue14-public-visual-release-v1",
        "tag": proof.TAG,
        "status": "ORIGINAL_ARTWORK_AND_SAVED_STAGE6_ONLY",
        "license": "CC BY 4.0 for original artistic assets; MIT for owned source",
        "assets": assets,
        "original_private_model_sha256": proof.ORIGINAL_MODEL_SHA,
        "public_model_sha256": proof.BINARIES["cloud-alpaca-stage6.blend"][1],
        "historical_six_zips": "NOT_INCLUDED_STRICT_REPRODUCTION_GATE_PENDING",
    }
    manifest_bytes = (json.dumps(manifest) + "\n").encode()
    license_bytes = b"Creative Commons Attribution 4.0 International\n"
    sources = {
        "visual-release-manifest.json": manifest_bytes,
        "LICENSE-ASSETS-CC-BY-4.0.md": license_bytes,
    }
    checksums = {name: sha for name, (_, sha) in proof.BINARIES.items()}
    checksums.update({name: proof.digest(value) for name, value in sources.items()})
    sums = "".join(
        f"{sha}  {name}\n" for name, sha in sorted(checksums.items())
    ).encode()
    return sums, manifest_bytes, license_bytes


def test_complete_visual_release_proof():
    sums, manifest, license_text = example_documents()
    verified = proof.check_small_documents(sums, manifest, license_text)
    assert (
        verified["cloud-alpaca-stage6.blend"]
        == proof.BINARIES["cloud-alpaca-stage6.blend"][1]
    )
    assert len(verified) == 7


def test_missing_or_unlisted_release_asset_rejected():
    sums, _, _ = example_documents()
    with pytest.raises(ValueError):
        proof.parse_checksum_file(
            sums.replace(b"  original-design.png\n", b"  private-original.zip\n")
        )
    with pytest.raises(ValueError):
        proof.parse_checksum_file(sums + sums.splitlines(keepends=True)[0])


@pytest.mark.parametrize(
    "bad_name", [b"../private.zip", b"subdir/model.blend", b"../x", b"a\\b"]
)
def test_checksum_path_traversal_rejected(bad_name):
    sums, _, _ = example_documents()
    first, rest = sums.split(b"  ", 1)
    altered = first + b"  " + bad_name + b"\n" + rest.split(b"\n", 1)[1]
    with pytest.raises(ValueError):
        proof.parse_checksum_file(altered)


def test_wrong_model_sha_rejected():
    sums, _, _ = example_documents()
    expected = proof.BINARIES["cloud-alpaca-stage6.blend"][1].encode()
    with pytest.raises(ValueError):
        proof.parse_checksum_file(sums.replace(expected, b"0" * 64))


def test_wrong_manifest_license_and_unpublished_zip_rejected():
    sums, manifest, license_text = example_documents()
    with pytest.raises(ValueError):
        proof.check_small_documents(sums, manifest, license_text + b"changed")
    document = json.loads(manifest)
    document["historical_six_zips"] = "PUBLISHED_UNVERIFIED"
    with pytest.raises(ValueError):
        proof.validate_manifest(json.dumps(document).encode())


def test_manifest_rejects_extra_duplicate_and_missing_assets():
    _, manifest, _ = example_documents()
    for change in ("duplicate", "missing", "other"):
        data = json.loads(manifest)
        if change == "duplicate":
            data["assets"][1] = data["assets"][0]
        elif change == "missing":
            data["assets"].pop()
        else:
            data["assets"][1]["name"] = "private-script.py"
        with pytest.raises(ValueError):
            proof.validate_manifest(json.dumps(data).encode())


def test_anonymous_download_stream_and_hash(monkeypatch, tmp_path):
    original = b"test-asset\x00" * 123
    requested = []

    def fake_urlopen(request, timeout):
        requested.append(request)
        assert timeout == 90
        assert request.get_header("Authorization") is None
        return io.BytesIO(original)

    monkeypatch.setattr(cli.urllib.request, "urlopen", fake_urlopen)
    expected = hashlib.sha256(original).hexdigest()
    destination = tmp_path / "model.bin"
    cli.stream_binary("cloud-alpaca-stage6.blend", len(original), expected, destination)
    assert destination.read_bytes() == original
    assert len(requested) == 1
    assert requested[0].full_url.startswith(
        "https://github.com/timlincool/plush-pattern-lab/releases/download/"
    )
    with pytest.raises(FileExistsError):
        cli.stream_binary(
            "cloud-alpaca-stage6.blend", len(original), expected, destination
        )


def test_reject_stream_tamper(monkeypatch):
    monkeypatch.setattr(
        cli.urllib.request, "urlopen", lambda request, timeout: io.BytesIO(b"tampered")
    )
    with pytest.raises(ValueError, match="mismatch"):
        cli.stream_binary("cloud-alpaca-stage6.blend", 8, "0" * 64, None)
