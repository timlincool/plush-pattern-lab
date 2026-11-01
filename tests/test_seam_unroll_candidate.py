"""Counterexamples for slit annulus edge optimization and cut-pattern denial."""

import xml.etree.ElementTree as ET

import numpy as np
import pytest

from plush_pattern_lab.patterns.seam_unroll_svg import draw_slit_unroll_svg
from plush_pattern_lab.validation.public_release_proof import MODEL_SHA256
from plush_pattern_lab.validation.seam_unroll_candidate import (
    unroll_triangular_band,
)
from scripts.unroll_stage6_triangle_band import BODY, HOOFS, evaluate


def _mesh(mode="cylinder", count=64):
    theta = np.arange(count) * 2 * np.pi / count
    inner = np.column_stack(
        (10 * np.cos(theta), 10 * np.sin(theta), np.zeros(count))
    )
    nouter = count // 2
    phase = np.arange(nouter) * 2 * np.pi / nouter
    outer = np.column_stack(
        (10 * np.cos(phase), 10 * np.sin(phase), np.full(nouter, 5.0))
    )
    if mode == "plane":
        outer[:, :2] *= 1.5
        outer[:, 2] = 0.0
    if mode == "warped":
        outer[:, :2] *= 1.5
        outer[:, 2] = np.linspace(3.0, 6.0, nouter)
    faces = []
    for i in range(nouter):
        a, b, c = (2 * i) % count, (2 * i + 1) % count, (2 * i + 2) % count
        d, e = count + i, count + ((i + 1) % nouter)
        faces.extend(((a, d, b), (b, e, c), (b, d, e)))
    return np.vstack((inner, outer)), np.asarray(faces), np.arange(count)


def _sample(mode="cylinder"):
    xyz, faces, seam = _mesh(mode)
    return unroll_triangular_band(xyz, faces, seam, budget=60)


def test_cylinder_one_radial_cut_preserves_true_seam_and_no_overlap():
    result, corners = _sample()
    assert result["fixed_seam_vertex_count"] == 64
    assert result["cut_edges_count"] == 1
    assert result["overlap"]["overlapping_triangle_pairs"] == 0
    assert result["optimized"]["mixed_winding_or_collapsed_triangles"] == 0
    assert result["optimized"]["p95_abs_edge_relative_error"] < 0.002
    assert result["solver"]["converged"]
    assert corners.shape == (96, 3, 2)
    assert result["fixed_original_3d_seam_length"]
    assert not result["approved_cut_pattern"]


def test_warped_case_may_reduce_distortion_but_still_fail_overlap():
    report, _ = _sample("warped")
    before = report["initial"]["p95_abs_edge_relative_error"]
    after = report["optimized"]["p95_abs_edge_relative_error"]
    assert after < before
    assert report["overlap"]["overlapping_triangle_pairs"] > 0
    assert report["optimized"]["mixed_winding_or_collapsed_triangles"] > 0
    assert not report["approved_cut_pattern"]


def test_planar_annulus_is_not_automatically_improved_by_slitting():
    report, _ = _sample("plane")
    assert report["optimized"]["p95_abs_edge_relative_error"] > 0.3
    assert not report["approved_cut_pattern"]


@pytest.mark.parametrize(
    "case",
    (
        "nonfinite",
        "out_of_bounds",
        "duplicate_face",
        "duplicate_seam",
        "missing_faces",
        "small_budget",
    ),
)
def test_reject_untrusted_or_degenerate_geometry(case):
    xyz, faces, seam = _mesh()
    if case == "nonfinite":
        xyz[0, 2] = np.nan
    elif case == "out_of_bounds":
        faces[0, 0] = len(xyz)
    elif case == "duplicate_face":
        faces[0] = faces[1]
    elif case == "duplicate_seam":
        seam[0] = seam[1]
    elif case == "missing_faces":
        faces = faces[:1]
    with pytest.raises(ValueError):
        unroll_triangular_band(
            xyz, faces, seam, budget=3 if case == "small_budget" else 60
        )


def _eight_patches():
    xyz, faces, seam = _mesh()
    objects = [(BODY, index) for index in range(4)]
    objects.extend((name, 0) for name in HOOFS)
    return {
        "schema": "stage6-verified-local-triangle-bands-v1",
        "source_sha256": MODEL_SHA256,
        "units": "mm",
        "patches": [
            {
                "object": name,
                "ring_index": ring,
                "vertices_mm": xyz.tolist(),
                "faces": faces.tolist(),
                "seam_ids": seam.tolist(),
            }
            for name, ring in objects
        ],
    }


def test_cli_research_evaluation_and_svg_are_not_cut_patterns():
    doc = _eight_patches()
    report, layouts = evaluate(doc, budget=40)
    assert report["all_original_seam_lengths_fixed"]
    assert not report["approved_for_cutting"]
    assert len(report["bands"]) == 8
    svg = draw_slit_unroll_svg(report["bands"], layouts)
    root = ET.fromstring(svg)
    assert root.attrib["width"].endswith("mm")
    assert "NOT A CUT PATTERN" in svg
    assert len(root.findall(".//{http://www.w3.org/2000/svg}polygon")) == 768


def test_cli_rejects_bad_identity_and_missing_band():
    doc = _eight_patches()
    doc["source_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="identity"):
        evaluate(doc, budget=40)
    doc = _eight_patches()
    doc["patches"].pop()
    with pytest.raises(ValueError, match="eight"):
        evaluate(doc, budget=40)
