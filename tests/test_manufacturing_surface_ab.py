"""Synthetic controls for immutable seam positions and bounded 3D fairing."""

import numpy as np
import pytest

from plush_pattern_lab.validation.manufacturing_surface_ab import (
    _surface_screen,
    fair_manufacturing_surface,
)


def _fan():
    points = np.array(
        [
            [-1, -1, 0],
            [1, -1, 0],
            [1, 1, 0],
            [-1, 1, 0],
            [0, 0, 1],
        ],
        dtype=np.float64,
    )
    faces = np.array([[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]])
    return points, faces, np.arange(4, dtype=np.int64)


def test_boundary_frozen_and_displacement_cap_applied_without_changing_source():
    points, faces, boundary = _fan()
    untouched = points.copy()
    candidate, score = fair_manufacturing_surface(
        points, faces, boundary, steps=6, alpha=0.35, max_shift_mm=0.1
    )
    assert np.array_equal(points, untouched)
    assert np.array_equal(candidate[boundary], points[boundary])
    assert score["moved_interior_vertices"] == 1
    assert score["vertex_displacement_max_mm"] == pytest.approx(0.1)
    assert score["max_protected_vertex_drift_mm"] == 0
    assert score["face_orientation_reversals"] == 0
    assert score["all_protected_3d_seam_points_exact"]
    assert not score["approved_for_sewing_or_cutting"]


def test_stable_planar_surface_remains_unchanged_if_all_vertices_protected():
    points, faces, boundary = _fan()
    candidate, score = fair_manufacturing_surface(
        points, faces, np.arange(len(points)), steps=2,
        alpha=0.15, max_shift_mm=0.1
    )
    assert np.array_equal(candidate, points)
    assert score["vertex_displacement_max_mm"] == 0
    assert score["moved_interior_vertices"] == 0


def test_screen_detects_a_genuine_triangle_orientation_reversal():
    points, faces, boundary = _fan()
    out = points.copy()
    out[4, :2] = [3, 0]
    score = _surface_screen(points, out, faces, boundary)
    assert score["face_orientation_reversals"] >= 1


@pytest.mark.parametrize(
    "defect",
    ["nan", "bad_face", "bad_lock", "duplicate_lock", "step", "alpha", "cap"],
)
def test_untrusted_geometry_and_unbounded_movement_rejected(defect):
    points, faces, protected = _fan()
    settings = {"steps": 3, "alpha": 0.2, "max_shift_mm": 0.2}
    if defect == "nan":
        points[4, 2] = np.nan
    elif defect == "bad_face":
        faces[0, 0] = 999
    elif defect == "bad_lock":
        protected = np.asarray([-1], dtype=np.int64)
    elif defect == "duplicate_lock":
        protected = np.asarray([0, 0], dtype=np.int64)
    elif defect == "step":
        settings["steps"] = 100
    elif defect == "alpha":
        settings["alpha"] = -1.0
    else:
        settings["max_shift_mm"] = 10.0
    with pytest.raises(ValueError):
        fair_manufacturing_surface(points, faces, protected, **settings)
