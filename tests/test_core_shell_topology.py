"""Counterexamples for real Stage6 main-shell topology and proxy caution."""

import pytest

from plush_pattern_lab.validation.core_shell_topology import (
    summarize_core_shell_topology,
)

FACE_SIZES = {"3": 1000}
INCIDENCE = {"0": 0, "1": 2048, "2": 476, ">2": 0}
LOOPS = [512, 512, 512, 512]


def _report(**changes):
    values = {
        "vertices": 1522,
        "edges": 2524,
        "faces": 1000,
        "face_sizes": FACE_SIZES,
        "edge_incidence": INCIDENCE,
        "face_components": 1,
        "boundary_loop_sizes": LOOPS,
    }
    values.update(changes)
    return summarize_core_shell_topology(**values)


def test_four_boundary_genus_zero_mesh_is_only_proxy_input_candidate():
    report = _report()
    assert report["euler_characteristic"] == -2
    assert report["genus_candidate_if_orientable"] == 0
    assert report["manifold_edges_only"]
    assert report["four_512_edge_openings_verified"]
    assert report["candidate_for_non_destructive_proxy_experiment"]
    assert not report["low_poly_proxy_created"]
    assert not report["cutting_patterns_approved"]


def test_wrong_boundary_size_is_not_a_proxy_candidate():
    report = _report(boundary_loop_sizes=[511, 513, 512, 512])
    assert not report["four_512_edge_openings_verified"]
    assert not report["candidate_for_non_destructive_proxy_experiment"]


def test_disconnected_face_shell_must_not_be_approved():
    report = _report(face_components=2)
    assert report["face_components_by_shared_edge"] == 2
    assert not report["candidate_for_non_destructive_proxy_experiment"]


def test_nonmanifold_or_loose_edge_is_rejected_for_proxy():
    for bad in (
        {"0": 0, "1": 2048, "2": 475, ">2": 1},
        {"0": 1, "1": 2048, "2": 475, ">2": 0},
    ):
        result = _report(edge_incidence=bad)
        assert not result["manifold_edges_only"]
        assert not result["candidate_for_non_destructive_proxy_experiment"]


@pytest.mark.parametrize(
    "kwargs",
    (
        {"vertices": 0},
        {"face_sizes": {"3": 999}},
        {"edge_incidence": {"0": 0, "1": 2048, "2": 475}},
        {"edge_incidence": {"0": -1, "1": 2048, "2": 477, ">2": 0}},
        {"face_components": 0},
        {"boundary_loop_sizes": [512, 512, 512]},
        {"boundary_loop_sizes": [512, 512, 512, 0]},
    ),
)
def test_invalid_topology_counts_fail_closed(kwargs):
    with pytest.raises(ValueError):
        _report(**kwargs)
