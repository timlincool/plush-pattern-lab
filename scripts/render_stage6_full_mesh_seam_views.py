"""Make a research SVG from same-run real Blender 41-product-Mesh first hits.

Never turn the source-geometry visibility plot into a factory cutting outline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from propose_stage6_shell_panels import PROXY_SHA256, load_pinned_proxy

from plush_pattern_lab.patterns.full_scene_seam_visibility_svg import (
    render_product_mesh_five_view_svg,
)
from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proxy", type=Path, required=True)
    parser.add_argument("--visibility", type=Path, required=True)
    parser.add_argument("--historic-face", type=Path, required=True)
    parser.add_argument("--svg", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    args = parser.parse_args()
    if (
        not args.visibility.is_file()
        or not args.historic_face.is_file()
        or args.svg.suffix != ".svg"
        or args.metadata.suffix != ".json"
        or args.svg.resolve() == args.metadata.resolve()
    ):
        raise ValueError("expect distinct unused research SVG and metadata")
    if any(p.exists() or p.is_symlink() for p in (args.svg, args.metadata)):
        raise FileExistsError("refuse to overwrite source-linked visual evidence")
    detail = json.loads(args.visibility.read_text(encoding="utf8"))
    historic_bytes = args.historic_face.read_bytes()
    historic = json.loads(historic_bytes)
    if (
        detail.get("source_blend_sha256") != SOURCE_SHA256
        or detail.get("source_proxy_25_percent_sha256") != PROXY_SHA256
        or detail.get("historical_face_v14_sha256")
        != hashlib.sha256(historic_bytes).hexdigest()
        or detail.get("approved_for_manufacturer_cutting") is not False
    ):
        raise ValueError("source or historical face provenance is not fixed")
    xyz, _ = load_pinned_proxy(args.proxy)
    svg = render_product_mesh_five_view_svg(xyz, detail, historic).encode("utf8")
    visible = {
        "schema": "stage6-41-product-mesh-source-seam-5view-svg-reference-v1",
        "source_original_blend_sha256": SOURCE_SHA256,
        "source_proxy_sha256": PROXY_SHA256,
        "visibility_json_sha256": hashlib.sha256(
            args.visibility.read_bytes()
        ).hexdigest(),
        "historic_face_v14_sha256": hashlib.sha256(historic_bytes).hexdigest(),
        "svg_sha256": hashlib.sha256(svg).hexdigest(),
        "product_meshes_raw_geometry_raycasted": detail["product_meshes_raytested"],
        "view_names": [row["view"] for row in detail["view_results"]],
        "not_a_design_aligned_render": True,
        "not_a_cutting_pattern": True,
    }
    args.svg.parent.mkdir(parents=True, exist_ok=True)
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    args.svg.write_bytes(svg)
    args.metadata.write_text(
        json.dumps(visible, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(
        "STAGE6_COMPLETE_MESH_FIVE_VIEW_RESEARCH",
        json.dumps(
            {
                "product_meshes": visible["product_meshes_raw_geometry_raycasted"],
                "views": visible["view_names"],
                "svg_sha256": visible["svg_sha256"],
                "approved": False,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
