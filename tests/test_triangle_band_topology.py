"""Tests for a real triangular annulus vs broken/nonmanifold face bands."""

import pytest

from plush_pattern_lab.validation.triangle_band_topology import (
    analyze_triangle_patch,
)

SEAM = [0, 1, 2, 3]
OUTER = [4, 5, 6, 7]
FACES = []
for i in range(4):
    j = (i + 1) % 4
    FACES.extend([(SEAM[i], SEAM[j], OUTER[j]), (SEAM[i], OUTER[j], OUTER[i])])


def test_two_boundary_connected_triangle_annulus_is_supported():
    report = analyze_triangle_patch(SEAM, FACES)
    assert report["candidate_triangular_annulus"]
    assert report["seam_vertices"] == 4
    assert report["triangles"] == 8
    assert report["total_vertices"] == 8
    assert report["outer_vertices"] == 4
    assert report["edges"] == 16
    assert report["euler_characteristic"] == 0
    assert report["seam_boundary_edges_exposed"] == 4
    assert report["outer_boundary_edges"] == 4
    assert report["boundary_loops"] == 2
    assert report["face_components"] == 1
    assert report["nonmanifold_edges"] == 0
    assert report["triangles_by_seam_vertex_count"] == {"1": 4, "2": 4}


def test_missing_face_is_not_a_closed_band():
    report = analyze_triangle_patch(SEAM, FACES[:-1])
    assert not report["candidate_triangular_annulus"]


def test_nonmanifold_duplicate_face_is_not_accepted():
    report = analyze_triangle_patch(SEAM, FACES + [FACES[0]])
    assert not report["candidate_triangular_annulus"]


def test_disconnected_extra_patch_is_not_accepted():
    report = analyze_triangle_patch(SEAM, FACES + [(20, 21, 22)])
    assert report["face_components"] == 2
    assert not report["candidate_triangular_annulus"]


@pytest.mark.parametrize(
    "seam,faces",
    [
        ([0, 0, 1, 2], FACES),
        ([0, 1, 2], FACES),
        (SEAM, []),
        (SEAM, [(0, 1, 1)]),
        (SEAM, [(0, 1, 5, 4)]),
    ],
)
def test_invalid_topology_refused(seam, faces):
    with pytest.raises(ValueError):
        analyze_triangle_patch(seam, faces)


def test_topology_is_not_flattening_or_material_approval():
    report = analyze_triangle_patch(SEAM, FACES)
    assert "no surface flattening" in report["limitations"]
    assert "cut" not in report
    assert "strain" not in report
