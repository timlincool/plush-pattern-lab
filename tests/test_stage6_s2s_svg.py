"""Synthetic contract tests: third-party SVG may not forge Stage6 source or scale."""

from __future__ import annotations

import hashlib
from copy import deepcopy

import pytest

from plush_pattern_lab.validation import stage6_s2s_svg as s2s

SOURCE_HASH = "a" * 64
NATIVE_HASH = "b" * 64
SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" width="20.0mm" '
    b'height="20.0mm" viewBox="0 0 20.0 20.0">'
    b'<defs><style>.seam{fill:none}</style></defs><g>'
    b'<path class="seam" d="M 2,18 12,18 12,8 2,8 2,18 "/>'
    b'</g></svg>'
)


def _fixture():
    src = {
        "source_variant": s2s.IDENTITY[0],
        "original_source_side": s2s.IDENTITY[1],
        "source_slit_direction": s2s.IDENTITY[2],
        "original_source_patch_sha256": "source-patch-locked",
        "cut_disk_source_xyz_mm": [
            [0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0]
        ],
        "cut_disk_original_source_triangle_indices": [[0, 1, 2], [0, 2, 3]],
    }
    source = {
        "schema": s2s.SOURCE_SCHEMA,
        "original_public_blend_sha256": s2s.SOURCE_SHA,
        "factory_cutting_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
        "candidate_2d_research_disks": [src],
    }
    native = {
        "schema": s2s.NATIVE_SCHEMA,
        "source_blend_sha256": s2s.SOURCE_SHA,
        "source_study_sha256": SOURCE_HASH,
        "blender_version": "4.3.2",
        "methods": ["ANGLE_BASED", "CONFORMAL"],
        "cutting_patterns_approved": 0,
        "third_party_commercial_service_used": False,
        "entries": [{
            "source_variant": s2s.IDENTITY[0],
            "source_side": s2s.IDENTITY[1],
            "slit_direction": s2s.IDENTITY[2],
            "source_patch_sha256": "source-patch-locked",
            "method": "ANGLE_BASED",
            "status": "completed",
            "max_same_topological_vertex_uv_loop_disagreement": 0,
            "vertex_count": 4,
            "triangle_count": 2,
            "uv_per_original_source_disk_vertex": [
                [.1, .1], [.6, .1], [.6, .6], [.1, .6]
            ],
        }],
    }
    audit = {
        "schema": s2s.AUDIT_SCHEMA,
        "same_run_source_study_sha256": SOURCE_HASH,
        "same_run_free_blender_native_raw_sha256": NATIVE_HASH,
        "factory_cutting_patterns_approved": 0,
        "P3_status": "in_progress",
        "P4_status": "not_started",
        "full_same_metric_comparisons": [{
            "source_variant": s2s.IDENTITY[0],
            "source_side": s2s.IDENTITY[1],
            "original_source_slit": s2s.IDENTITY[2],
            "external_blender_solvers": [{
                "method": "ANGLE_BASED",
                "uniform_scale_from_native_uv_to_research_mm": 20.,
                "scaled_2d_p95_abs_edge_relative_error": 0.16,
                "2d_two_sides_length_mismatch_fraction_of_source_3d": 0.02,
            }],
        }],
    }
    return source, native, audit


def test_external_s2s_proves_every_original_source_boundary_edge_in_mm():
    source, native, audit = _fixture()
    report = s2s.audit_stage6_external_svg(
        source, native, audit, SVG, SOURCE_HASH, NATIVE_HASH
    )
    assert report["schema"] == s2s.REPORT_SCHEMA
    assert report["method"] == "ANGLE_BASED"
    assert report["source_boundary_edge_count"] == 4
    assert report["all_svg_edges_match_original_ABF_source_cut"]
    assert report["svg_netline_perimeter_mm"] == pytest.approx(40.)
    assert report["external_svg_sha256"] == hashlib.sha256(SVG).hexdigest()
    assert not report["svg_contains_seam_allowance"]
    assert report["factory_cutting_patterns_approved"] == 0
    assert report["P4_status"] == "not_started"


@pytest.mark.parametrize(
    "fault",
    (
        "bad_source_sha", "bad_raw_sha", "changed_original_source",
        "fake_factory", "changed_cut_triangle", "wrong_source_patch",
        "uv_seam_split", "conformal_only", "wrong_method_identity",
        "clipped_uv", "bad_scale", "duplicated_source_entry",
    ),
)
def test_external_s2s_rejects_source_metrics_or_method_forgery(fault):
    source, native, audit = _fixture()
    if fault == "bad_source_sha":
        native["source_study_sha256"] = "wrong"
    elif fault == "bad_raw_sha":
        audit["same_run_free_blender_native_raw_sha256"] = "wrong"
    elif fault == "changed_original_source":
        source["original_public_blend_sha256"] = "wrong"
    elif fault == "fake_factory":
        audit["factory_cutting_patterns_approved"] = 1
    elif fault == "changed_cut_triangle":
        native["entries"][0]["triangle_count"] = 3
    elif fault == "wrong_source_patch":
        native["entries"][0]["source_patch_sha256"] = "wrong"
    elif fault == "uv_seam_split":
        native["entries"][0][
            "max_same_topological_vertex_uv_loop_disagreement"
        ] = 0.2
    elif fault == "conformal_only":
        native["entries"][0]["method"] = "CONFORMAL"
    elif fault == "wrong_method_identity":
        native["entries"][0]["source_side"] = "right"
    elif fault == "clipped_uv":
        native["entries"][0]["uv_per_original_source_disk_vertex"][1][0] = 1.3
    elif fault == "bad_scale":
        audit["full_same_metric_comparisons"][0][
            "external_blender_solvers"
        ][0]["uniform_scale_from_native_uv_to_research_mm"] = float("nan")
    else:
        source["candidate_2d_research_disks"].append(
            deepcopy(source["candidate_2d_research_disks"][0])
        )
    with pytest.raises(ValueError):
        s2s.audit_stage6_external_svg(
            source, native, audit, SVG, SOURCE_HASH, NATIVE_HASH
        )


@pytest.mark.parametrize(
    "replacement",
    (
        b'width="20.0mm"', b'viewBox="0 0 20.0 20.0"',
        b'2,18 12,18 12,8 2,8 2,18',
        b'<path class="seam"', b'<g>',
    ),
)
def test_external_svg_negative_mutations_are_rejected(replacement):
    source, native, audit = _fixture()
    replacement_text = {
        b'width="20.0mm"': b'width="21.0mm"',
        b'viewBox="0 0 20.0 20.0"': b'viewBox="0 0 19.0 20.0"',
        b'2,18 12,18 12,8 2,8 2,18': b'2,18 12,18 12,8 2,8 4,18',
        b'<path class="seam"': b'<path class="danger"',
        b'<g>': b'<g><script>alert(1)</script>',
    }[replacement]
    with pytest.raises(ValueError):
        s2s.audit_stage6_external_svg(
            source, native, audit, SVG.replace(replacement, replacement_text),
            SOURCE_HASH, NATIVE_HASH,
        )


def test_external_svg_rejects_duplicate_or_wrong_source_boundary_edge():
    source, native, audit = _fixture()
    invalid = SVG.replace(b"12,8 2,8", b"12,8 12,18")
    with pytest.raises(ValueError):
        s2s.audit_stage6_external_svg(
            source, native, audit, invalid, SOURCE_HASH, NATIVE_HASH
        )


def test_external_svg_rejects_non_manifold_original_faces():
    source, native, audit = _fixture()
    source["candidate_2d_research_disks"][0][
        "cut_disk_original_source_triangle_indices"
    ] = [[0, 1, 2], [0, 1, 2], [0, 1, 2]]
    native["entries"][0]["triangle_count"] = 3
    with pytest.raises(ValueError):
        s2s.audit_stage6_external_svg(
            source, native, audit, SVG, SOURCE_HASH, NATIVE_HASH
        )
