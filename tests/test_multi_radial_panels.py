"""Real-source radial split controls: exact 3D pairing and developable 2D disks."""

import numpy as np
import pytest

from plush_pattern_lab.patterns.mesh_lscm_candidate import flatten_cut_panel
from plush_pattern_lab.validation.multi_radial_panels import (
    split_annulus_by_radial_paths,
)


def _synthetic_capped_cylinder(n=64):
    angles = np.arange(n) * 2 * np.pi / n
    bottom = np.column_stack(
        (20 * np.cos(angles), 20 * np.sin(angles), np.zeros(n))
    )
    top = bottom.copy()
    top[:, 2] = 25
    xyz = np.vstack((bottom, top, [0, 0, 25]))
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.extend(((i, j, n + j), (i, n + j, n + i)))
    selected = np.arange(len(faces))
    for i in range(n):
        faces.append((2 * n, n + i, n + (i + 1) % n))
    return xyz, np.asarray(faces, dtype=np.int32), selected


@pytest.mark.parametrize(
    ("extra", "expected"),
    [
        (((0.5, 24.0),), [64, 64]),
        (((2 / 3, 24.0), (1 / 3, 24.0)), [42, 44, 42]),
    ],
)
def test_radial_cylinder_disks_preserve_every_source_face_and_ring(extra, expected):
    xyz, faces, selected = _synthetic_capped_cylinder()
    original = xyz.copy()
    result = split_annulus_by_radial_paths(
        xyz, faces, selected, [0, 64], extra, expected_cuff_edges=64
    )
    assert np.array_equal(xyz, original)
    assert sorted(row["face_count"] for row in result["panels"]) == sorted(expected)
    assert sum(row["face_count"] for row in result["panels"]) == 128
    assert sum(row["source_cuff_edges"] for row in result["panels"]) == 64
    assert sum(row["source_outer_seam_edges"] for row in result["panels"]) == 64
    assert all(row["disk_euler"] == 1 for row in result["panels"])
    assert result["source_3d_seams_exactly_paired"]
    assert not result["approved_for_cutting"]
    for panel in result["panels"]:
        score, _ = flatten_cut_panel(panel, iteration_cap=1500)
        assert score["status"] == "RESEARCH_GEOMETRY_ONLY"
        assert score["strain_screen"]["triangle_edge_relative_error"]["p95"] < 0.01
        assert score["strain_screen"]["inverted_winding_triangles"] == 0
        assert score["global_2d_overlap"][
            "overlapping_nonzero_area_triangle_pairs"
        ] == 0
        assert score["boundary"]["perimeter_by_source_role"]["slit"]["edge_count"]


@pytest.mark.parametrize(
    "mutator",
    ["bad_fraction", "bad_height", "bad_source", "wrong_cuff", "missing_face"],
)
def test_unverified_radial_routes_or_tampered_source_rejected(mutator):
    xyz, faces, selected = _synthetic_capped_cylinder()
    path = [0, 64]
    extra = ((0.5, 24.0),)
    cuff_count = 64
    if mutator == "bad_fraction":
        extra = ((0.0, 24.0),)
    elif mutator == "bad_height":
        extra = ((0.5, 100.0),)
    elif mutator == "bad_source":
        path = [0, 99999]
    elif mutator == "wrong_cuff":
        cuff_count = 512
    else:
        selected = selected[:-1]
    with pytest.raises(ValueError):
        split_annulus_by_radial_paths(
            xyz, faces, selected, path, extra, expected_cuff_edges=cuff_count
        )
