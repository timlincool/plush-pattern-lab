"""Machine-checkable Stage6 source-to-proxy seam identity and shape metrics.

This is a research geometry gate, not approved garment cutting geometry.
All coordinates are world-space millimetres. Source vertex indices are
mapped one-to-one to candidate indices without resampling or nearest guessing.
"""

from __future__ import annotations

import numpy as np

from plush_pattern_lab.validation.boundary_match import (
    cyclic_match_mm,
    unique_centroid_mapping,
)

RING_COUNT = 4
RING_VERTICES = 512
SEAM_MAX_GAP_MM = 0.0001


def _ring_record(item):
    ids = np.asarray(item["vertex_ids"])
    coords = np.asarray(item["xyz_mm"], dtype=np.float64)
    if ids.shape != (RING_VERTICES,) or not np.issubdtype(ids.dtype, np.integer):
        raise ValueError("ring needs 512 integral original vertex identities")
    if len(np.unique(ids)) != RING_VERTICES or (ids < 0).any():
        raise ValueError("ring has invalid repeated or negative vertex identities")
    if coords.shape != (RING_VERTICES, 3) or not np.isfinite(coords).all():
        raise ValueError("ring must contain 512 finite 3D points in millimetres")
    if np.any(np.linalg.norm(coords - np.roll(coords, 1, axis=0), axis=1) <= 0):
        raise ValueError("ring has a zero-length directed edge")
    return ids, coords


def register_original_hoof_seams(source_rings, proxy_rings):
    """Require four equal oriented rings; preserve explicit old→new vertex IDs."""
    if len(source_rings) != RING_COUNT or len(proxy_rings) != RING_COUNT:
        raise ValueError("exactly four original and candidate hoof openings required")
    originals = [_ring_record(row) for row in source_rings]
    candidates = [_ring_record(row) for row in proxy_rings]
    mapping = unique_centroid_mapping(
        [coords for _, coords in originals],
        [coords for _, coords in candidates],
    )
    results = []
    for candidate_index, (source_index, _) in enumerate(mapping):
        old_ids, old_xyz = originals[source_index]
        new_ids, new_xyz = candidates[candidate_index]
        match = cyclic_match_mm(old_xyz, new_xyz)
        good = (
            match["max_gap_mm"] <= SEAM_MAX_GAP_MM
            and match["rms_gap_mm"] <= SEAM_MAX_GAP_MM
            and not match["reversed_boundary_winding"]
        )
        result = {
            "source_ring_index": int(source_index),
            "proxy_ring_index": int(candidate_index),
            "vertex_count": RING_VERTICES,
            "max_gap_mm": match["max_gap_mm"],
            "rms_gap_mm": match["rms_gap_mm"],
            "matching_direction_preserved": not match["reversed_boundary_winding"],
            "exact_world_geometry_accepted": bool(good),
        }
        if good:
            ordered = np.roll(new_ids, match["cyclic_shift"])
            result["original_to_proxy_vertex_id"] = [
                [int(old), int(new)] for old, new in zip(old_ids, ordered)
            ]
        results.append(result)
    return {
        "expected_original_ring_count": RING_COUNT,
        "expected_original_hoof_seam_vertices": RING_VERTICES * RING_COUNT,
        "all_original_seam_points_and_winding_preserved": all(
            row["exact_world_geometry_accepted"] for row in results
        ),
        "registrations": sorted(results, key=lambda row: row["source_ring_index"]),
        "source_to_proxy_vertex_identity_is_explicit": all(
            "original_to_proxy_vertex_id" in row for row in results
        ),
    }


def sampled_surface_distances_mm(distances):
    """Report deterministic nearest-surface sample error without claiming Hausdorff."""
    arr = np.asarray(distances, dtype=np.float64)
    if arr.ndim != 1 or not 1 <= len(arr) <= 10000:
        raise ValueError("bounded 1D surface sample distances required")
    if not np.isfinite(arr).all() or np.any(arr < 0):
        raise ValueError("non-finite or negative surface distance")
    return {
        "sample_count": len(arr),
        "mean_mm": float(arr.mean()),
        "p95_mm": float(np.quantile(arr, 0.95)),
        "max_mm": float(arr.max()),
        "rms_mm": float(np.sqrt(np.mean(arr * arr))),
        "sampling_note": (
            "Deterministic sampled vertex-to-nearest-triangle distances, "
            "not exact Hausdorff or a production fit tolerance"
        ),
    }
