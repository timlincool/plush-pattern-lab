"""Negative controls: view-ray shape agreement does not establish sewing safety."""

import numpy as np
import pytest

from plush_pattern_lab.validation.proxy_view_quality import (
    check_winding_counts,
    compare_orthographic_hits,
)


def test_identical_masks_and_depths_give_exact_view_agreement():
    a = np.ones((12, 16))
    a[0, 0] = np.nan
    result = compare_orthographic_hits(a, a.copy())
    assert result["silhouette_iou"] == 1.0
    assert result["silhouette_mismatch_rays"] == 0
    assert result["first_hit_depth_mm"]["max"] == 0
    assert result["shared_visible_rays"] == 191


def test_missed_pixels_are_counted_separately_from_depth_displacement():
    a = np.ones((8, 8)) * 5
    b = np.ones((8, 8)) * 6
    a[0, 0] = np.nan
    b[1, 1] = np.nan
    measured = compare_orthographic_hits(a, b)
    assert measured["shared_visible_rays"] == 62
    assert measured["silhouette_mismatch_rays"] == 2
    assert measured["silhouette_iou"] == pytest.approx(62 / 64)
    assert measured["first_hit_depth_mm"]["max"] == 1.0


@pytest.mark.parametrize(
    "first,second",
    [
        (np.ones((8, 8)), np.ones((9, 8))),
        (np.ones(8), np.ones(8)),
        (np.ones((3, 8)), np.ones((3, 8))),
        (np.full((8, 8), float("nan")), np.full((8, 8), float("nan"))),
        (np.zeros((8, 8)), np.full((8, 8), float("nan"))),
        (np.full((8, 8), float("inf")), np.zeros((8, 8))),
    ],
)
def test_invalid_or_empty_views_are_refused(first, second):
    with pytest.raises(ValueError):
        compare_orthographic_hits(first, second)


def test_coherent_face_winding_does_not_claim_outward_normals():
    report = check_winding_counts(250, 0)
    assert report["coherent_face_winding"]
    assert report["outward_normals_proven"] is False
    wrong = check_winding_counts(250, 3)
    assert not wrong["coherent_face_winding"]


@pytest.mark.parametrize(
    "interior,bad",
    [(0, 0), (30, -1), (30, 31), (2.5, 0), (20, 0.5)],
)
def test_impossible_winding_census_is_rejected(interior, bad):
    with pytest.raises(ValueError):
        check_winding_counts(interior, bad)
