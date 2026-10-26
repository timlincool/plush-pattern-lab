"""Bounded normals of a synthetic ellipsoid; no physical fabric certification."""

from __future__ import annotations

import numpy as np


def ellipsoid_normal(
    point, equatorial_radius: float, polar_radius: float
) -> np.ndarray:
    """Unit outward gradient of (x²+y²)/R² + z²/H² = 1.

    Synthetic 3D initial placement only. This is not a constitutive material law
    or an attempt to infer an unknown target shape.
    """
    position = np.asarray(point, dtype=np.float64)
    if position.shape != (3,) or not np.isfinite(position).all():
        raise ValueError("Expected a finite 3D point")
    if not np.isfinite([equatorial_radius, polar_radius]).all():
        raise ValueError("Ellipsoid radii must be finite")
    if equatorial_radius <= 0 or polar_radius <= 0:
        raise ValueError("Ellipsoid radii must be positive")
    normal = position / np.array(
        [equatorial_radius**2, equatorial_radius**2, polar_radius**2]
    )
    magnitude = float(np.linalg.norm(normal))
    if not np.isfinite(magnitude) or magnitude <= 1e-12:
        raise ValueError("Ellipsoid outward normal undefined at this point")
    return normal / magnitude
