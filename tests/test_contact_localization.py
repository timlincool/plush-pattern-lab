"""Proof that contact localization preserves the conservative original veto."""

from __future__ import annotations

import pytest

from plush_pattern_lab.validation.contact_localization import (
    describe_contacts,
    polygon_identities,
)


def test_layout_maps_panel_rows_and_two_caps():
    # Two panels are not supported; emulate N=6 with 8 quad faces per panel.
    polygon_ids = [i for i in range(60) for _ in range(2)]
    names, zones = polygon_identities(
        polygon_ids, panels=6, gore_faces=48, face_count=60
    )
    assert len(names) == len(zones) == 120
    assert (names[0], zones[0]) == ("P01", "upper_join")
    assert (names[14], zones[14]) == ("P01", "lower_join")
    assert (names[16], zones[16]) == ("P02", "upper_join")
    assert (names[96], zones[96]) == ("UPPER", "upper_cap")
    assert (names[118], zones[118]) == ("LOWER", "lower_cap")


@pytest.mark.parametrize("bad", [
    {"panels": 5, "gore_faces": 80, "face_count": 90},
    {"panels": 6, "gore_faces": 47, "face_count": 59},
    {"panels": 6, "gore_faces": 48, "face_count": 61},
])
def test_invalid_face_layout_refused(bad):
    with pytest.raises(ValueError):
        polygon_identities([0] * (bad["face_count"] * 2), **bad)


def test_invalid_triangle_polygon_index_refused():
    with pytest.raises(ValueError, match="Invalid"):
        polygon_identities([0] * 119 + [True], panels=6, gore_faces=48, face_count=60)


def test_region_and_two_zones_preserve_counts():
    coords = [
        (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0), (1.0, 0.0, 1.0), (0.0, 1.0, 1.0),
        (2.0, 0.0, 0.0), (3.0, 0.0, 0.0), (2.0, 1.0, 0.0),
    ]
    faces = [(0, 1, 2), (3, 4, 5), (0, 6, 7), (6, 7, 8)]
    names = ["P01", "P02", "P01", "UPPER"]
    zones = ["lower_join", "lower_join", "body", "upper_cap"]
    hits = {(0, 1), (0, 2), (1, 3)}
    result = describe_contacts(hits, coords, faces, {}, names, zones)
    assert result["counts"] == {"shared": 1, "seam": 0, "other": 2}
    assert result["witnesses"]["other"][0]["triangle_indices"] == [0, 1]
    assert result["witnesses"]["other"][0]["panel_names"] == ["P01", "P02"]
    assert result["witnesses"]["other"][0]["triangle_centroids_mm"][0] == [
        333.33333, 333.33333, 0.0
    ]
    assert any(row["region_pair"] == ["P01", "P02"] for row in result["by_panel_pair"])
    assert result["witness_sample_limited"] == {"seam": False, "other": False}


def test_seam_identity_remains_counted_not_deleted():
    coords = [(float(i), 0, 0) for i in range(8)]
    faces = [(0, 1, 2), (3, 4, 5)]
    neighbors = {0: {3}, 1: set(), 2: set()}
    report = describe_contacts({(0, 1)}, coords, faces, neighbors,
                               ["P01", "P02"], ["upper_join", "upper_join"])
    assert report["counts"]["seam"] == 1
    assert report["counts"]["other"] == 0
    assert report["witnesses"]["seam"][0]["triangle_indices"] == [0, 1]


@pytest.mark.parametrize("pairs", [{(1, 0)}, {(0, 9)}])
def test_invalid_pair_ids_are_rejected(pairs):
    with pytest.raises(ValueError, match="Invalid"):
        describe_contacts(pairs, [(0, 0, 0)] * 9, [(0, 1, 2), (3, 4, 5)],
                          {}, ["P01", "P02"], ["upper_join", "upper_join"])
