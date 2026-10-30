"""Adversarial tests: a boundary is not automatically a sewable one-ring strip."""

import pytest

from plush_pattern_lab.validation.seam_band_topology import (
    face_profile,
    outer_ring_for_quads,
)

SEAM = [0, 1, 2, 3]
FACES = [
    (0, 1, 5, 4),
    (1, 2, 6, 5),
    (2, 3, 7, 6),
    (3, 0, 4, 7),
]


def test_exact_quad_strip_has_unique_outer_ring():
    assert outer_ring_for_quads(SEAM, FACES) == [4, 5, 6, 7]
    report = face_profile(SEAM, FACES)
    assert report["regular_quad_strip"]
    assert report["adjacent_faces"] == 4
    assert report["outer_ring_vertices"] == 4
    assert report["polygon_vertex_counts"] == {"4": 4}


def test_reverse_faces_and_cyclic_rotations_are_valid():
    flipped = [tuple(reversed(face)) for face in FACES]
    assert outer_ring_for_quads(SEAM, flipped) == [4, 5, 6, 7]
    assert outer_ring_for_quads(SEAM[1:] + SEAM[:1], FACES[1:] + FACES[:1]) == [
        5,
        6,
        7,
        4,
    ]


@pytest.mark.parametrize(
    "faces",
    [
        [FACES[0][:-1], *FACES[1:]],
        [(0, 1, 1, 4), *FACES[1:]],
        [(0, 1, 5, 2), *FACES[1:]],
        [FACES[0], FACES[0], *FACES[2:]],
        [(0, 5, 1, 4), *FACES[1:]],
        [(0, 1, 5, 4), (1, 2, 6, 8), *FACES[2:]],
        [(0, 1, 5, 4), (1, 2, 6, 4), (2, 3, 7, 6), (3, 0, 4, 7)],
    ],
)
def test_reject_unsupported_face_band_without_guessing(faces):
    with pytest.raises(ValueError):
        outer_ring_for_quads(SEAM, faces)
    report = face_profile(SEAM, faces)
    assert not report["regular_quad_strip"]
    assert report["quad_strip_failure_reason"]


def test_reject_repeated_boundary_and_missing_face():
    with pytest.raises(ValueError):
        outer_ring_for_quads([0, 1, 1, 3], FACES)
    with pytest.raises(ValueError):
        outer_ring_for_quads(SEAM, FACES[:3])


def test_report_never_promotes_to_2d_cut_pattern():
    report = face_profile(SEAM, FACES)
    assert "not yet a surface flattening" in report["limitation"]
    assert not any(key in report for key in ("cut_outline", "seam_allowance"))
