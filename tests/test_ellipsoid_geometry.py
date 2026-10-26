"""Synthetic ellipsoid normal vector should not insert a radial pole distortion."""

import numpy as np
import pytest

from plush_pattern_lab.patterns.ellipsoid_geometry import ellipsoid_normal


def test_equator_is_radial_and_pole_is_axial():
    assert ellipsoid_normal((0.055, 0, 0), 0.055, 0.07) == pytest.approx([1, 0, 0])
    assert ellipsoid_normal((0, 0, 0.07), 0.055, 0.07) == pytest.approx([0, 0, 1])


def test_near_pole_normal_uses_axial_component():
    theta = np.deg2rad(8.0)
    point = [0.055 * np.sin(theta), 0, 0.07 * np.cos(theta)]
    vector = ellipsoid_normal(point, 0.055, 0.07)
    assert np.linalg.norm(vector) == pytest.approx(1)
    assert vector[2] > 0.95
    assert vector[0] < 0.3


@pytest.mark.parametrize(
    "point, radius, height",
    [
        ([0, 0], 0.055, 0.07),
        ([0, 0, 0], 0.055, 0.07),
        ([float("nan"), 0, 0], 0.055, 0.07),
        ([0.055, 0, 0], 0, 0.07),
        ([0.055, 0, 0], 0.055, float("inf")),
    ],
)
def test_nonphysical_normals_fail_closed(point, radius, height):
    with pytest.raises(ValueError):
        ellipsoid_normal(point, radius, height)
