"""校验唯一公开开发仓库中的真实 PNG：内容、来源哈希、尺寸与敏感元数据。"""

from __future__ import annotations

import hashlib
import json
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE_DIR = ROOT / "design" / "reference-v25" / "images"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PRIVATE_METADATA_CHUNKS = {b"tEXt", b"zTXt", b"iTXt", b"eXIf"}


def _inspect_png(data: bytes) -> tuple[tuple[int, int], set[bytes]]:
    assert data.startswith(PNG_SIGNATURE)
    offset = len(PNG_SIGNATURE)
    dimensions = (0, 0)
    chunks: set[bytes] = set()
    seen_end = False

    while offset < len(data):
        assert offset + 12 <= len(data)
        length = struct.unpack_from(">I", data, offset)[0]
        chunk_type = data[offset + 4 : offset + 8]
        end = offset + 12 + length
        assert end <= len(data)

        payload = data[offset + 8 : offset + 8 + length]
        actual_crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
        expected_crc = struct.unpack_from(">I", data, offset + 8 + length)[0]
        assert actual_crc == expected_crc
        chunks.add(chunk_type)

        if chunk_type == b"IHDR":
            dimensions = struct.unpack_from(">II", payload)
        if chunk_type == b"IEND":
            seen_end = True
            assert length == 0
            assert end == len(data)
        offset = end

    assert seen_end
    return dimensions, chunks


def test_public_reference_image_inventory() -> None:
    manifest = json.loads((IMAGE_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert manifest["license"] == "CC BY 4.0"
    assert len(manifest["files"]) == 2

    for entry in manifest["files"]:
        path = IMAGE_DIR / entry["path"]
        assert path.parent == IMAGE_DIR
        raw = path.read_bytes()
        assert len(raw) == entry["size_bytes"]
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]

        git_blob = b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
        assert hashlib.sha1(git_blob).hexdigest() == entry["git_blob_sha1"]

        dimensions, chunks = _inspect_png(raw)
        assert dimensions == (entry["width"], entry["height"])
        assert chunks.isdisjoint(PRIVATE_METADATA_CHUNKS)
