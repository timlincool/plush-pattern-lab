"""Positive and adversarial tests for the Stage 6 single-binary Release gate."""

from __future__ import annotations

import hashlib
import io
import json

import pytest

from plush_pattern_lab.validation import public_release_proof as proof
from scripts import verify_issue14_public_release as cli


def release_metadata() -> bytes:
    return json.dumps(
        {
            "tag_name": proof.TAG,
            "draft": False,
            "assets": [
                {
                    "name": proof.MODEL_NAME,
                    "size": proof.MODEL_BYTES,
                    "state": "uploaded",
                    "browser_download_url": proof.release_asset_url(),
                }
            ],
        }
    ).encode()


def test_exactly_one_public_stage6_model_accepted():
    proof.validate_release_metadata(release_metadata())
    assert proof.release_asset_url().startswith(
        "https://github.com/timlincool/plush-pattern-lab/releases/download/"
    )


@pytest.mark.parametrize(
    "change",
    [
        "wrong_tag",
        "draft",
        "missing",
        "extra",
        "wrong_name",
        "wrong_size",
        "pending",
        "wrong_url",
    ],
)
def test_invalid_release_metadata_is_rejected(change):
    doc = json.loads(release_metadata())
    if change == "wrong_tag":
        doc["tag_name"] = "untrusted"
    elif change == "draft":
        doc["draft"] = True
    elif change == "missing":
        doc["assets"] = []
    elif change == "extra":
        doc["assets"].append({"name": "private.zip"})
    elif change == "wrong_name":
        doc["assets"][0]["name"] = "old-model.blend"
    elif change == "wrong_size":
        doc["assets"][0]["size"] += 1
    elif change == "pending":
        doc["assets"][0]["state"] = "new"
    else:
        doc["assets"][0]["browser_download_url"] = "https://other.example/model.blend"
    with pytest.raises(ValueError):
        proof.validate_release_metadata(json.dumps(doc).encode())


def test_invalid_or_excessive_metadata_rejected():
    with pytest.raises(ValueError):
        proof.validate_release_metadata(b"[]")
    with pytest.raises(ValueError):
        proof.validate_release_metadata(b"{}" + b" " * proof.MAX_METADATA_BYTES)


def test_anonymous_metadata_request(monkeypatch):
    requests = []

    def fake_urlopen(request, timeout):
        requests.append(request)
        assert timeout == 45
        return io.BytesIO(release_metadata())

    monkeypatch.setattr(cli.urllib.request, "urlopen", fake_urlopen)
    cli.read_release_metadata()
    assert len(requests) == 1
    assert requests[0].full_url == cli.release_metadata_url()
    assert requests[0].get_header("Authorization") is None


def test_anonymous_stream_success_and_no_overwrite(monkeypatch, tmp_path):
    content = b"verified-model"
    monkeypatch.setattr(proof, "MODEL_BYTES", len(content))
    monkeypatch.setattr(proof, "MODEL_SHA256", hashlib.sha256(content).hexdigest())
    requests = []

    def fake_urlopen(request, timeout):
        requests.append(request)
        assert timeout == 90
        return io.BytesIO(content)

    monkeypatch.setattr(cli.urllib.request, "urlopen", fake_urlopen)
    target = tmp_path / "stage6.blend"
    cli.stream_binary(proof.MODEL_NAME, len(content), proof.MODEL_SHA256, target)
    assert target.read_bytes() == content
    assert requests[0].get_header("Authorization") is None
    with pytest.raises(FileExistsError):
        cli.stream_binary(proof.MODEL_NAME, len(content), proof.MODEL_SHA256, target)
    assert target.read_bytes() == content


@pytest.mark.parametrize("content", [b"tampered", b"oversized payload"])
def test_tampered_or_oversized_download_is_cleaned(monkeypatch, tmp_path, content):
    expected = b"original"
    monkeypatch.setattr(proof, "MODEL_BYTES", len(expected))
    monkeypatch.setattr(proof, "MODEL_SHA256", hashlib.sha256(expected).hexdigest())
    monkeypatch.setattr(
        cli.urllib.request, "urlopen", lambda request, timeout: io.BytesIO(content)
    )
    target = tmp_path / "stage6.blend"
    with pytest.raises(ValueError):
        cli.stream_binary(proof.MODEL_NAME, len(expected), proof.MODEL_SHA256, target)
    assert not target.exists()


def test_refuses_unpinned_binary(monkeypatch):
    with pytest.raises(ValueError):
        cli.stream_binary("other.blend", proof.MODEL_BYTES, proof.MODEL_SHA256, None)
    with pytest.raises(ValueError):
        cli.stream_binary(proof.MODEL_NAME, proof.MODEL_BYTES, "0" * 64, None)
