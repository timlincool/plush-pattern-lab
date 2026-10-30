"""Numerical negative controls for a 3D seam triangle-band projection."""

import numpy as np
import pytest

from plush_pattern_lab.validation.triangle_band_projection import (
    projection_screen,
)

SEAM = [0, 1, 2, 3]
FACE = []
for i in range(4):
    j = (i + 1) % 4
    FACE.extend([(i, j, j + 4), (i, j + 4, i + 4)])
INNER = np.array(
    [[-5.0, -5.0, 0.0], [5.0, -5.0, 0.0],
     [5.0, 5.0, 0.0], [-5.0, 5.0, 0.0]]
)
OUTER = np.array(
    [[-10.0, -10.0, 0.0], [10.0, -10.0, 0.0],
     [10.0, 10.0, 0.0], [-10.0, 10.0, 0.0]]
)


def test_true_planar_annulus_has_negligible_projection_error():
    data = projection_screen(np.vstack([INNER, OUTER]), FACE, SEAM)
    assert data["triangle_count"] == 8
    assert data["seam_vertices"] == 4
    assert data["edge_relative_loss"]["max"] < 1e-12
    assert data["collapsed_projected_triangles"] == 0
    assert data["seam_plane_max_deviation_mm"] == pytest.approx(0)
    assert not data["piece_rest_shape_solved"]


def test_vertical_mesh_band_projection_collapses_surface():
    outer = INNER.copy()
    outer[:, 2] += 8
    data = projection_screen(np.vstack([INNER, outer]), FACE, SEAM)
    assert data["collapsed_projected_triangles"] > 0
    assert data["edge_relative_loss"]["max"] > 0.9
    assert data["projected_area_ratio"]["p05"] < 1e-6
    assert data["degenerate_3d_triangles"] == 0
    assert not data["piece_rest_shape_solved"]


@pytest.mark.parametrize(
    "bad_mesh,bad_faces,bad_seam",
    [
        (np.full((8, 3), float("nan")), FACE, SEAM),
        (np.zeros((8, 2)), FACE, SEAM),
        (np.vstack([INNER, OUTER]), [(0, 1, 8)], SEAM),
        (np.vstack([INNER, OUTER]), [(0, 0, 1)], SEAM),
        (np.vstack([INNER, OUTER]), [(0, 1, 2, 3)], SEAM),
        (np.vstack([INNER, OUTER]), FACE, [0, 0, 2, 3]),
        (np.vstack([INNER, OUTER]), FACE, [0, 1, 2, 8]),
    ],
)
def test_invalid_geometry_must_not_be_silently_repaired(
    bad_mesh, bad_faces, bad_seam
):
    with pytest.raises(ValueError):
        projection_screen(bad_mesh, bad_faces, bad_seam)


def test_output_is_diagnostics_not_a_cuttable_pattern():
    data = projection_screen(np.vstack([INNER, OUTER]), FACE, SEAM)
    assert data["fit_method"].endswith("not_intrinsic_unfolding")
    assert "cut_outline" not in data
    assert "seam_allowance" not in data
