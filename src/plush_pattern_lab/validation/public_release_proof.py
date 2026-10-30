"""Pin the sole public Stage 6 Blender binary and validate its Release inventory.

The four sanitized PNG references already live in Git and must not be
repackaged in the Release. This is an integrity check, not a production gate.
"""

from __future__ import annotations

import json

REPO = "timlincool/plush-pattern-lab"
TAG = "cloud-alpaca-stage6-visuals-20261028"
MODEL_NAME = "cloud-alpaca-stage6.blend"
MODEL_BYTES = 89_853_017
MODEL_SHA256 = "38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a"
ORIGINAL_MODEL_SHA = "791f4844bb87b9d2e7d10a21e01846d06cdf9c205153c6acf47cf7ab76b0f602"
MAX_METADATA_BYTES = 131_072


def release_asset_url() -> str:
    """Return a fixed, public, unauthenticated GitHub Release asset URL."""
    return f"https://github.com/{REPO}/releases/download/{TAG}/{MODEL_NAME}"


def validate_release_metadata(raw: bytes) -> None:
    """Reject incomplete/draft Releases and any unexpected extra binary asset."""
    if len(raw) > MAX_METADATA_BYTES:
        raise ValueError("Release metadata exceeds size limit")
    doc = json.loads(raw.decode("utf-8"))
    if not isinstance(doc, dict) or doc.get("tag_name") != TAG:
        raise ValueError("Unexpected Release identity")
    if doc.get("draft") is not False:
        raise ValueError("Release is not published")
    assets = doc.get("assets")
    if not isinstance(assets, list) or len(assets) != 1:
        raise ValueError("Release must contain exactly one Stage 6 binary")
    asset = assets[0]
    if not isinstance(asset, dict) or (
        asset.get("name"),
        asset.get("size"),
        asset.get("state"),
        asset.get("browser_download_url"),
    ) != (MODEL_NAME, MODEL_BYTES, "uploaded", release_asset_url()):
        raise ValueError("Release Stage 6 asset identity or size mismatch")
