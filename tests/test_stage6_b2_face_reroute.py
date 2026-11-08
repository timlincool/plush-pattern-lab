"""Guard two anatomically bounded Stage6 source reroute experiments."""

import numpy as np
import pytest

from plush_pattern_lab.validation.stage6_b_face_reroute import (
    RESEARCH_ROUTES,
    _allowed_mesh_edges,
    _candidate_targets,
    _old_source_paths,
    _source_edge_shortest,
    reroute_original_b_high2,
)


def test_two_reroute_targets_do_not_allow_historic_nose_endpoint():
    points = np.asarray(
        [
            [-0.86, -68.28, 150.52],
            [-0.90, -19.57, 222.70],
            [-0.93, -86.34, 190.23],
        ]
    )
    boundary = np.arange(3)
    c = _candidate_targets(points, boundary, RESEARCH_ROUTES[0])
    d = _candidate_targets(points, boundary, RESEARCH_ROUTES[1])
    assert c.tolist() == [0]
    assert d.tolist() == [1]
    assert 2 not in c and 2 not in d


def test_shortest_source_mesh_path_must_follow_actual_original_edge_ids():
    coords = np.asarray([[0, 0, 0], [0, 1, 0], [0, 2, 0], [1, 2, 0]])
    edges = np.asarray([[0, 1], [1, 2], [1, 3]])
    path = _source_edge_shortest(coords, edges, 0, np.asarray([2]))
    assert path.tolist() == [0, 1, 2]
    assert np.all(np.linalg.norm(np.diff(coords[path], axis=0), axis=1) > 0)
    with pytest.raises(ValueError):
        _source_edge_shortest(coords, edges[:1], 0, np.asarray([3]))


def test_source_face_high_region_is_hard_excluded_even_if_boundary_is_a_target():
    coords = np.asarray(
        [
            [-45, -32, 20],
            [-0.9, -86, 190],
            [-0.8, -85, 185],
            [-44, -30, 20],
            [-40, -25, 50],
        ]
    )
    edges = np.asarray([[0, 2], [2, 1], [3, 4]])
    cuff = np.empty((0, 2), dtype=int)
    outer = np.asarray([[1, 2]])
    with pytest.raises(ValueError, match="facial exclusion"):
        _allowed_mesh_edges(
            coords, edges, cuff, outer, [np.array([3, 4])],
            np.asarray([1]), 0
        )


def test_trusted_old_source_path_ids_and_length_must_match_original_xyz():
    xyz = np.column_stack((np.arange(10), np.zeros(10), np.zeros(10)))
    ids = np.array([0, 1, 3, 5, 7, 9])
    raw = [
        {"original_source_vertex_ids": [0, 1], "source_3d_length_mm": 1.0},
        {"original_source_vertex_ids": [3, 5], "source_3d_length_mm": 2.0},
        {"original_source_vertex_ids": [7, 9], "source_3d_length_mm": 2.0},
    ]
    assert len(_old_source_paths(ids, xyz, raw)) == 3
    raw[2]["source_3d_length_mm"] = 400
    with pytest.raises(ValueError, match="length changed"):
        _old_source_paths(ids, xyz, raw)
    raw[2]["source_3d_length_mm"] = 2.0
    raw[2]["original_source_vertex_ids"] = [7, 8]
    with pytest.raises(ValueError):
        _old_source_paths(ids, xyz, raw)


def test_incompatible_source_region_cannot_be_promoted_to_real_reroute():
    points = np.zeros((6, 3))
    faces = np.array([[0, 1, 2], [3, 4, 5]], dtype=int)
    with pytest.raises(ValueError):
        reroute_original_b_high2(points, faces, np.array([0]), [])


@pytest.mark.parametrize(
    "mode",
    [
        ("bad", 150.0, -20.0, -5.0),
        ("none", 250.0, -78.0, -65.0),
    ],
)
def test_missing_anatomical_source_boundary_stops_instead_of_guessing(mode):
    coords = np.asarray([[-0.9, -69, 150], [-0.9, -19, 220]])
    if mode[0] == "bad":
        mode = (mode[0], mode[1], mode[2], mode[3])
    with pytest.raises(ValueError):
        _candidate_targets(coords, np.arange(2), mode)
