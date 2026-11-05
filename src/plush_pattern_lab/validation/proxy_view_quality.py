"""Independent, bounded numeric checks for an actual 3D proxy's orthographic views.

A 2D silhouette ray mask and a first-hit depth comparison are screening tools,
not full-surface Hausdorff, cloth strain, or manufacturing fit certificates.
"""

from __future__ import annotations

import numpy as np


def compare_orthographic_hits(reference_mm, candidate_mm):
    """Same registered rays; NaN means the view ray did not hit the mesh."""
    original = np.asarray(reference_mm, dtype=np.float64)
    proxy = np.asarray(candidate_mm, dtype=np.float64)
    if original.shape != proxy.shape or original.ndim != 2:
        raise ValueError("both orthographic samples need equal 2D grids")
    if not 8 <= min(original.shape) <= max(original.shape) <= 512:
        raise ValueError("orthographic sample grid must be between 8 and 512")
    if np.isinf(original).any() or np.isinf(proxy).any():
        raise ValueError("invalid infinite ray distances")
    valid_a, valid_b = ~np.isnan(original), ~np.isnan(proxy)
    union = valid_a | valid_b
    shared = valid_a & valid_b
    if not union.any() or not shared.any():
        raise ValueError("no common visible surface in the comparison view")
    deviations = np.abs(original[shared] - proxy[shared])
    return {
        "grid_size": list(original.shape),
        "ray_count": int(original.size),
        "reference_visible_rays": int(valid_a.sum()),
        "proxy_visible_rays": int(valid_b.sum()),
        "shared_visible_rays": int(shared.sum()),
        "silhouette_mismatch_rays": int(np.logical_xor(valid_a, valid_b).sum()),
        "silhouette_iou": float(shared.sum() / union.sum()),
        "first_hit_depth_mm": {
            "mean": float(deviations.mean()),
            "p95": float(np.quantile(deviations, 0.95)),
            "max": float(deviations.max()),
        },
        "scope": "finite resolution orthographic first-hit rays, not full geometry",
    }


def check_winding_counts(interior_edges, inconsistent_edges):
    """Two incident face loops must traverse a manifold edge oppositely."""
    if not isinstance(interior_edges, int) or not isinstance(inconsistent_edges, int):
        raise ValueError("face winding measurements must be integers")
    if interior_edges <= 0 or not 0 <= inconsistent_edges <= interior_edges:
        raise ValueError("invalid face winding measurement")
    return {
        "two_face_edges": interior_edges,
        "opposite_directed_edge_failures": inconsistent_edges,
        "coherent_face_winding": inconsistent_edges == 0,
        "outward_normals_proven": False,
    }
