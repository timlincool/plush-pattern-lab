"""Reject false source, missing seam IDs, and fake ear-root manufacturing claims."""

from copy import deepcopy

import numpy as np
import pytest

from plush_pattern_lab.validation import stage6_ear_root_ab as root
from plush_pattern_lab.validation.stage6_ear_root_ab_svg import render_root_ab_svg


def _ring(cx, count=16):
    theta = np.arange(count, dtype=float) * 2 * np.pi / count
    xy = np.column_stack((cx + 6 * np.cos(theta), 6 * np.sin(theta)))
    perimeter = float(np.linalg.norm(np.roll(xy, -1, axis=0) - xy, axis=1).sum())
    return {
        "true_interpolated_contour_xy_mm": xy.tolist(),
        "crossed_original_mesh_vertex_id_edge_pairs": [
            [i, i + 1] for i in range(count)
        ],
        "contour_perimeter_mm": perimeter,
        "contour_centroid_xy_mm": [cx, 0.0],
        "original_source_edge_and_interpolated_xy_sha256": "a" * 64,
        "closed_loop": True,
        "simple_polygon": True,
    }


def _series():
    return {
        "sections": [
            {
                "plane_z_mm": z,
                "true_source_plane_intersection_component_count": n,
                "source_contours": [_ring(0)]
                if n == 1
                else [_ring(0), _ring(-40), _ring(40)],
            }
            for z, n in [(225.90, 1), (225.91, 3), (230, 3), (235, 3)]
        ]
    }


def _trace():
    return {
        "source_surface_component_count_in_open_slab": 3,
        "source_triangle_count_in_open_slab": 300,
        "surface_components": [
            {"source_surface_relation": "one_to_one_surface_continuation_not_seam"}
            for _ in range(3)
        ],
    }


def _wire(monkeypatch, series=None, slab=None):
    monkeypatch.setattr(
        root, "real_source_section_series", lambda *args, **kw: series or _series()
    )
    monkeypatch.setattr(
        root, "trace_true_source_slab", lambda *args, **kw: slab or _trace()
    )


def test_ab_preserves_source_ids_and_no_paper_pattern_promotions(monkeypatch):
    _wire(monkeypatch)
    report = root.compare_real_ear_root_ab(None, None)
    assert [row["source_plane_z_mm"] for row in report["candidate_options"]] == [
        230,
        235,
    ]
    assert all(
        len(row["source_side_loops"]) == 2 for row in report["candidate_options"]
    )
    assert all(
        len(side["four_arclength_reference_marks"]) == 4
        for row in report["candidate_options"]
        for side in row["source_side_loops"]
    )
    assert report["manufacturing_cutting_approved"] == 0
    assert report["P3_status"] == "in_progress"
    assert report["P4_status"] == "not_started"
    assert "NOT PATTERNS" in render_root_ab_svg(report)


def test_3d_source_quarter_marks_are_not_sewing_notches():
    marks = root._notch_positions(_ring(-40), 230)
    assert [m["fraction_of_closed_ring"] for m in marks] == [0, 0.25, 0.5, 0.75]
    assert all(len(m["source_intersection_edge_before"]) == 2 for m in marks)
    assert all(m["not_a_manufacturing_notch"] for m in marks)
    assert all(m["true_source_xyz_mm"][2] == 230 for m in marks)


@pytest.mark.parametrize(
    "mutation",
    ["count", "duplicate", "invalid_polygon", "missing_ids", "bad_length"],
)
def test_invalid_source_root_rings_fail_closed(monkeypatch, mutation):
    series = _series()
    section = series["sections"][2]
    if mutation == "count":
        section["true_source_plane_intersection_component_count"] = 2
    elif mutation == "duplicate":
        section["source_contours"][2] = _ring(-42)
    elif mutation == "invalid_polygon":
        section["source_contours"][2]["true_interpolated_contour_xy_mm"] = [
            [0, 0] for _ in range(16)
        ]
    elif mutation == "missing_ids":
        section["source_contours"][1]["crossed_original_mesh_vertex_id_edge_pairs"] = []
    else:
        section["source_contours"][1]["contour_perimeter_mm"] += 1
    _wire(monkeypatch, series=series)
    with pytest.raises(ValueError):
        root.compare_real_ear_root_ab(None, None)


def test_previous_trusted_z230_source_digest_must_match(monkeypatch):
    _wire(monkeypatch)
    original = {
        "schema": "stage6-true-triangle-plane-component-loops-v1",
        "factory_cutting_approved": 0,
        "sections": deepcopy(_series()["sections"]),
    }
    assert root.compare_real_ear_root_ab(None, None, original)
    original["sections"][2]["source_contours"][1][
        "original_source_edge_and_interpolated_xy_sha256"
    ] = "f" * 64
    with pytest.raises(ValueError, match="digest"):
        root.compare_real_ear_root_ab(None, None, original)


def test_source_slab_branching_cannot_be_assumed_continuous(monkeypatch):
    slab = _trace()
    slab["source_surface_component_count_in_open_slab"] = 1
    _wire(monkeypatch, slab=slab)
    with pytest.raises(ValueError, match="continue"):
        root.compare_real_ear_root_ab(None, None)


def test_svg_rejects_false_factory_approval(monkeypatch):
    _wire(monkeypatch)
    report = root.compare_real_ear_root_ab(None, None)
    report["manufacturing_cutting_approved"] = 1
    with pytest.raises(ValueError):
        render_root_ab_svg(report)


def test_side_sampling_protects_original_vertex_edge_ids(monkeypatch):
    _wire(monkeypatch)
    option = root.compare_real_ear_root_ab(None, None)["candidate_options"][0]
    left = option["source_side_loops"][0]
    samples = root.plan_side_source_samples(left, 230, max_samples=8)
    assert len(samples) == 8
    assert len({s["source_edge_ordinal"] for s in samples}) == 8
    assert all(s["source_xyz_mm"][2] == 230 for s in samples)
    altered = deepcopy(left)
    altered["full_crossed_original_proxy_vertex_id_pairs"].pop()
    with pytest.raises(ValueError):
        root.plan_side_source_samples(altered, 230)
