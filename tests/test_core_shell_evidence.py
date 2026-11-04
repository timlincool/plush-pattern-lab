"""Actual Stage6 source shell evidence is NOT approval of a low-poly pattern."""

import json
from pathlib import Path

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256
from plush_pattern_lab.validation.core_shell_topology import (
    summarize_core_shell_topology,
)

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/stage6_core_shell_20261104/topology.json"
PROGRESS = ROOT / "docs/PRODUCTION_PROGRESS.json"


def test_source_topology_matches_measured_blender_evidence():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["source_sha256"] == SOURCE_SHA256
    assert data["provenance"]["trusted_workflow_run"].endswith("/41774495231")
    assert data["vertices"] == 234161
    assert data["edges"] == 700441
    assert data["faces"] == 466278
    assert data["face_sizes"] == {"3": 466278}
    assert data["edge_incidence"] == {"0": 0, "1": 2048, "2": 698393, ">2": 0}
    assert data["boundary_loop_vertex_counts"] == [512] * 4
    assert data["face_components_by_shared_edge"] == 1
    assert data["loose_vertices"] == 0
    assert data["euler_characteristic"] == -2
    assert data["whole_model_modified"] is False


def test_original_math_recomputes_the_saved_3d_topology_proof():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    derived = summarize_core_shell_topology(
        data["vertices"],
        data["edges"],
        data["faces"],
        data["face_sizes"],
        data["edge_incidence"],
        data["face_components_by_shared_edge"],
        data["boundary_loop_vertex_counts"],
    )
    for key, value in derived.items():
        assert data[key] == value, key
    assert derived["candidate_for_non_destructive_proxy_experiment"]
    assert not derived["low_poly_proxy_created"]
    assert not derived["cutting_patterns_approved"]


def test_factory_p3_started_without_fake_fabrication_progress():
    progress = json.loads(PROGRESS.read_text(encoding="utf-8"))
    p3 = next(phase for phase in progress["phases"] if phase["id"] == "P3")
    assert p3["status"] == "in_progress"
    assert any(
        row["path"] == "experiments/stage6_core_shell_20261104/topology.json"
        for row in p3["evidence"]
    )
    proof = progress["verified_baseline"]["stage6_core_shell_topology"]
    assert proof["triangles"] == 466278
    assert proof["shared_edge_connected_components"] == 1
    assert not proof["low_poly_proxy_created"]
    assert proof["whole_role_sewing_patterns_approved"] == 0
    assert not progress["overall"]["factory_sample_pack_ready"]
