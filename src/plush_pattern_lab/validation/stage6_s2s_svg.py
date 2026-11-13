"""Audit external GPL sewing SVG against unchanged Stage6 ABF source boundaries.

This pure module never runs Blender or imports the third-party add-on.
It validates an exported RESEARCH netline, not a fabric cutting pattern.
"""

from __future__ import annotations

import hashlib
import math
import xml.etree.ElementTree as ET
from collections import Counter

import numpy as np

SOURCE_SHA = "38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a"
SOURCE_SCHEMA = "stage6-ear-root-genuine-source-disk-lscm-research-v1"
NATIVE_SCHEMA = "stage6-free-blender-native-uv-abf-conformal-raw-v1"
AUDIT_SCHEMA = "stage6-free-external-uv-same-source-apples-to-apples-v1"
REPORT_SCHEMA = "stage6-pinned-external-s2s-abf-svg-audit-v1"
ADDON_COMMIT = "919d031628264bb466840827a81f657133931de7"
IDENTITY = ("N15_sloped_source_band", "left", "lateral")
SVG_NS = "{http://www.w3.org/2000/svg}"


def select_source_abf(source, native, audit, source_sha, native_sha):
    """Find one predeclared original disk and its already-measured ABF UV."""
    if (
        source.get("schema") != SOURCE_SCHEMA
        or source.get("original_public_blend_sha256") != SOURCE_SHA
        or source.get("factory_cutting_patterns_approved") != 0
        or source.get("P3_status") != "in_progress"
        or source.get("P4_status") != "not_started"
        or native.get("schema") != NATIVE_SCHEMA
        or native.get("source_blend_sha256") != SOURCE_SHA
        or native.get("blender_version") != "4.3.2"
        or native.get("source_study_sha256") != source_sha
        or native.get("methods") != ["ANGLE_BASED", "CONFORMAL"]
        or native.get("cutting_patterns_approved") != 0
        or native.get("third_party_commercial_service_used") is not False
        or audit.get("schema") != AUDIT_SCHEMA
        or audit.get("same_run_source_study_sha256") != source_sha
        or audit.get("same_run_free_blender_native_raw_sha256") != native_sha
        or audit.get("factory_cutting_patterns_approved") != 0
        or audit.get("P3_status") != "in_progress"
        or audit.get("P4_status") != "not_started"
    ):
        raise ValueError("S2S exporter must use the same trusted Stage6 ABF inputs")
    source_rows = [
        row
        for row in source["candidate_2d_research_disks"]
        if (
            row["source_variant"],
            row["original_source_side"],
            row["source_slit_direction"],
        )
        == IDENTITY
    ]
    native_rows = [
        row
        for row in native["entries"]
        if (row["source_variant"], row["source_side"], row["slit_direction"])
        == IDENTITY
        and row["method"] == "ANGLE_BASED"
    ]
    audit_rows = [
        row
        for row in audit["full_same_metric_comparisons"]
        if (row["source_variant"], row["source_side"], row["original_source_slit"])
        == IDENTITY
    ]
    if not all(len(group) == 1 for group in (source_rows, native_rows, audit_rows)):
        raise ValueError("predeclared N15 left lateral source/ABF identity missing")
    src, uv, scored = source_rows[0], native_rows[0], audit_rows[0]
    choices = [
        row for row in scored["external_blender_solvers"]
        if row["method"] == "ANGLE_BASED"
    ]
    if (
        len(choices) != 1
        or uv.get("status") != "completed"
        or uv.get("source_patch_sha256") != src.get("original_source_patch_sha256")
        or uv.get("max_same_topological_vertex_uv_loop_disagreement", 1) > 1e-5
    ):
        raise ValueError("UV is not the original unsplit source-aligned Blender ABF")
    xyz = np.asarray(src["cut_disk_source_xyz_mm"], dtype=float)
    tri = np.asarray(src["cut_disk_original_source_triangle_indices"], dtype=int)
    xy = np.asarray(uv["uv_per_original_source_disk_vertex"], dtype=float)
    scale = float(choices[0]["uniform_scale_from_native_uv_to_research_mm"])
    if (
        xyz.ndim != 2 or xyz.shape[1] != 3
        or tri.ndim != 2 or tri.shape[1] != 3
        or xy.shape != (len(xyz), 2)
        or uv["vertex_count"] != len(xyz)
        or uv["triangle_count"] != len(tri)
        or not np.isfinite(xyz).all()
        or not np.isfinite(xy).all()
        or not math.isfinite(scale) or scale <= 0 or scale > 10000
        or np.any(tri < 0) or np.any(tri >= len(xyz))
        or np.any(xy < -1e-6) or np.any(xy > 1 + 1e-6)
    ):
        raise ValueError("invalid or clipped Blender UV / geometry / millimetre scale")
    return src, uv, choices[0]


def _boundary_edges(faces):
    counter = Counter()
    for a, b, c in faces:
        if len({int(a), int(b), int(c)}) != 3:
            raise ValueError("degenerate source face in SVG audit")
        for i, j in ((a, b), (b, c), (c, a)):
            counter[tuple(sorted((int(i), int(j))))] += 1
    if any(count > 2 for count in counter.values()):
        raise ValueError("non-manifold source disk not exportable")
    boundary = {key for key, count in counter.items() if count == 1}
    if len(boundary) < 3:
        raise ValueError("source disk does not expose a seam boundary")
    return boundary


def _netline_path(svg_bytes, scale):
    if (
        not svg_bytes or len(svg_bytes) > 2_000_000
        or b"<!DOCTYPE" in svg_bytes.upper()
        or b"<!ENTITY" in svg_bytes.upper()
    ):
        raise ValueError("invalid or active-content SVG")
    root = ET.fromstring(svg_bytes)
    if root.tag != SVG_NS + "svg":
        raise ValueError("expected SVG namespace")
    for field in ("width", "height"):
        value = root.get(field, "")
        if not value.endswith("mm") or not math.isclose(
            float(value[:-2]), scale, rel_tol=0, abs_tol=1e-5
        ):
            raise ValueError("SVG physical viewBox no longer matches ABF millimetres")
    box = [float(x) for x in root.get("viewBox", "").split()]
    if len(box) != 4 or not np.allclose(box, [0, 0, scale, scale], atol=1e-5):
        raise ValueError("SVG viewport silently scaled or translated")
    allowed = {SVG_NS + item for item in ("svg", "defs", "style", "g", "path")}
    if any(node.tag not in allowed for node in root.iter()):
        raise ValueError("unexpected elements or active content in addon SVG")
    paths = [node for node in root.iter() if node.tag == SVG_NS + "path"]
    if len(paths) != 1 or paths[0].get("class") != "seam":
        raise ValueError("expected exactly one external source sewing netline")
    raw = paths[0].get("d", "").replace(",", " ").split()
    if len(raw) < 9 or raw[0] != "M" or len(raw) % 2 != 1:
        raise ValueError("unrecognized sewing-path coordinates")
    coords = np.asarray([float(v) for v in raw[1:]], dtype=float).reshape(-1, 2)
    if (
        not np.isfinite(coords).all()
        or np.any(coords < -1e-3)
        or np.any(coords > scale + 1e-3)
        or np.linalg.norm(coords[0] - coords[-1]) > 1e-3
    ):
        raise ValueError("sewing path is clipped, open or non-finite")
    return coords


def audit_stage6_external_svg(source, native, audit, svg_bytes, source_sha, native_sha):
    """Verify every external outline segment equals an original ABF cut boundary."""
    src, uv, metrics = select_source_abf(source, native, audit, source_sha, native_sha)
    scale = float(metrics["uniform_scale_from_native_uv_to_research_mm"])
    faces = np.asarray(src["cut_disk_original_source_triangle_indices"], dtype=int)
    boundary = _boundary_edges(faces)
    vertex_ids = sorted({v for edge in boundary for v in edge})
    positions = np.asarray(uv["uv_per_original_source_disk_vertex"], dtype=float)
    # Blender S2S exporter writes x=u*scale, y=(1-v)*scale, with no seam allowance.
    expected = np.column_stack(
        (positions[vertex_ids, 0] * scale, (1 - positions[vertex_ids, 1]) * scale)
    )
    coords = _netline_path(svg_bytes, scale)
    if len(coords) != len(boundary) + 1:
        raise ValueError("addon SVG omitted or duplicated source boundary edges")
    distances = np.linalg.norm(
        coords[:-1, None, :] - expected[None, :, :], axis=2
    )
    nearest = np.argmin(distances, axis=1)
    if (
        np.max(distances[np.arange(len(nearest)), nearest]) > 1e-3
        or len(set(nearest.tolist())) != len(vertex_ids)
    ):
        raise ValueError("S2S outline is not source vertex-aligned at real millimetres")
    ids = [vertex_ids[int(i)] for i in nearest]
    actual_edges = {
        tuple(sorted((ids[i], ids[(i + 1) % len(ids)])))
        for i in range(len(ids))
    }
    if actual_edges != boundary:
        raise ValueError("external SVG changed source seam topology or length")
    length = float(np.linalg.norm(np.diff(coords, axis=0), axis=1).sum())
    return {
        "schema": REPORT_SCHEMA,
        "exporter": "artyredd/blender-seams-to-sewing-pattern",
        "external_addon_pinned_commit": ADDON_COMMIT,
        "method": "ANGLE_BASED",
        "source_variant": IDENTITY[0],
        "source_side": IDENTITY[1],
        "source_slit": IDENTITY[2],
        "source_blend_sha256": SOURCE_SHA,
        "same_run_source_study_sha256": source_sha,
        "same_run_native_uv_sha256": native_sha,
        "source_patch_sha256": src["original_source_patch_sha256"],
        "external_svg_sha256": hashlib.sha256(svg_bytes).hexdigest(),
        "source_boundary_edge_count": len(boundary),
        "all_svg_edges_match_original_ABF_source_cut": True,
        "physical_svg_millimetres_from_independent_ABF_gauge": scale,
        "svg_netline_perimeter_mm": length,
        "source_edge_P95_relative_error": metrics["scaled_2d_p95_abs_edge_relative_error"],
        "source_cut_two_side_length_mismatch_fraction": metrics[
            "2d_two_sides_length_mismatch_fraction_of_source_3d"
        ],
        "svg_contains_seam_allowance": False,
        "source_sculpt_geometry_modified": False,
        "factory_cutting_patterns_approved": 0,
        "physical_toile_produced": False,
        "P3_status": "in_progress",
        "P4_status": "not_started",
    }
