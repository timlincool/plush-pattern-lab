"""Pinned Stage6 left-front real 36,833-face annulus -> slit disk -> LSCM.

This command deliberately retains unsuccessful flattening experiments. No 1:1
cutting stencil is approved without valid UV geometry and physical fabric.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from plush_pattern_lab.patterns.full_panel_research_svg import (
    render_full_panel_research_svg,
)
from plush_pattern_lab.patterns.mesh_lscm_candidate import flatten_cut_panel
from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256
from plush_pattern_lab.validation.real_panel_slit import slit_real_panel
from propose_stage6_shell_panels import load_pinned_proxy

REAL_FACES = 36833
REAL_VERTICES = 18913
REAL_CUFF_EDGES = 512
RESEARCH_SPLIT_Y = 20.0


def _source_region(xyz, faces):
    center = xyz[faces].mean(axis=1)
    labels = (center[:, 0] >= 0).astype(np.int8) * 2
    labels += (center[:, 1] >= RESEARCH_SPLIT_Y).astype(np.int8)
    selected = np.flatnonzero(labels == 0)
    if len(selected) != REAL_FACES:
        raise ValueError("pinned Stage6 left-front face count has drifted")
    return selected


def evaluate_real_leftfront(points, faces, budget=8000):
    """Return a real but unapproved rest-shape test and reconstructible UV data."""
    selected = _source_region(points, faces)
    disk = slit_real_panel(points, faces, selected, REAL_CUFF_EDGES)
    if disk["original_annulus_vertices"] != REAL_VERTICES:
        raise ValueError("actual Stage6 left-front vertex identity has drifted")
    if disk["original_annulus_faces"] != REAL_FACES:
        raise ValueError("source Stage6 panel triangle count has drifted")
    quality, uv = flatten_cut_panel(disk, iteration_cap=budget)
    boundary = dict(quality["boundary"])
    edge_source_ids = boundary.pop("boundary_edge_source_vertex_ids")
    edge_uv_ids = boundary.pop("boundary_edge_uv_ids")
    quality["boundary"] = boundary
    report = {
        "schema": "stage6-leftfront-whole-panel-lscm-v1",
        "status": quality["status"],
        "source_original_model_sha256": SOURCE_SHA256,
        "region": "left_front",
        "region_id": 0,
        "source_3d_split_x_mm": 0,
        "source_3d_split_y_mm": RESEARCH_SPLIT_Y,
        "topology": {
            key: value
            for key, value in disk.items()
            if key in {
                "slit_path_length_3d_mm",
                "source_cuff_edges",
                "source_outer_seam_edges",
                "original_annulus_vertices",
                "original_annulus_faces",
                "cut_disk_vertices",
                "cut_disk_faces",
                "cut_disk_boundary_edges",
                "cut_disk_euler",
            }
        },
        "slit_path_original_vertex_ids": disk["slit_path_source_vertex_ids"].tolist(),
        "geometry_quality": quality,
        "original_3d_faces_unchanged": True,
        "net_cut_pattern_approved": False,
        "fabric_material_validated": False,
        "visual_design_seam_path_approved": False,
        "manufacturing_ready": False,
        "next_if_rejected": "Add a design-approved seam or dart; no tolerance relaxation",
    }
    detail = {
        "schema": "stage6-leftfront-face-linked-2d-uv-detail-v1",
        "source_original_model_sha256": SOURCE_SHA256,
        "source_face_id_by_panel_face": disk["source_face_ids"].tolist(),
        "source_vertex_id_by_uv_vertex": disk["source_vertex_ids"].tolist(),
        "cut_panel_face_uv_vertices": disk["faces"].tolist(),
        "cut_panel_vertex_uv_mm": np.round(uv, 8).tolist(),
        "boundary_original_3d_edge_source_ids": edge_source_ids,
        "boundary_cut_uv_edge_ids": edge_uv_ids,
        "slit_path_original_vertex_ids": report["slit_path_original_vertex_ids"],
        "approved_for_cutting": False,
    }
    svg = render_full_panel_research_svg(disk, uv, quality)
    return report, detail, svg


def _write_new(path, value):
    if path.exists() or path.is_symlink():
        raise FileExistsError("refuse to overwrite research evidence")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--detail", type=Path, required=True)
    parser.add_argument("--svg", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=8000)
    args = parser.parse_args()
    if args.source_sha256 != SOURCE_SHA256:
        raise ValueError("unexpected public source identity")
    for item, extension in (
        (args.summary, ".json"),
        (args.detail, ".json"),
        (args.svg, ".svg"),
    ):
        if item.suffix != extension or item.exists() or item.is_symlink():
            raise ValueError("only unused JSON/SVG paths accepted")
    if len({p.resolve() for p in (args.summary, args.detail, args.svg)}) != 3:
        raise ValueError("all research outputs require distinct paths")
    xyz, faces = load_pinned_proxy(args.input)
    report, detail, svg = evaluate_real_leftfront(xyz, faces, args.iterations)
    detail_bytes = (json.dumps(detail, ensure_ascii=False) + "\n").encode("utf8")
    report["detail_file_sha256"] = hashlib.sha256(detail_bytes).hexdigest()
    report["detail_file_name"] = args.detail.name
    _write_new(args.detail, detail_bytes)
    _write_new(args.svg, svg.encode("utf8"))
    _write_new(
        args.summary,
        (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf8"),
    )
    print(
        "STAGE6_REAL_LEFTFRONT_COMPLETE_PANEL_LSCM",
        json.dumps(
            {
                "status": report["status"],
                "triangle_faces": report["topology"]["original_annulus_faces"],
                "cut_vertices": report["topology"]["cut_disk_vertices"],
                "slit_3d_mm": report["topology"]["slit_path_length_3d_mm"],
                "uv_edge_error_p95": report["geometry_quality"]["strain_screen"][
                    "triangle_edge_relative_error"
                ]["p95"],
                "uv_flips": report["geometry_quality"]["strain_screen"][
                    "inverted_winding_triangles"
                ],
                "uv_overlaps": report["geometry_quality"]["global_2d_overlap"][
                    "overlapping_nonzero_area_triangle_pairs"
                ],
                "uv_overlap_truncated": report["geometry_quality"]["global_2d_overlap"][
                    "overlap_search_truncated"
                ],
                "approved_for_cutting": False,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
