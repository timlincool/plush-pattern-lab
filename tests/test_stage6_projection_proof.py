"""Regression: public Stage6 triangle projection evidence has precise provenance."""

import json
from pathlib import Path

from plush_pattern_lab.validation import public_release_proof as proof

ROOT = Path(__file__).resolve().parents[1]


def test_stage6_triangle_projection_is_traceable_negative_control():
    path = ROOT / "experiments/stage6_hoof_seams_20261030/triangle_band_projection.json"
    report = json.loads(path.read_text(encoding="utf8"))
    assert report["schema"] == "stage6-real-triangle-plane-projection-proof-v1"
    assert report["status"].endswith("NOT_CUT_PATTERN")
    assert report["source"]["sha256"] == proof.MODEL_SHA256
    assert report["source"]["size_bytes"] == proof.MODEL_BYTES
    assert report["source"]["trusted_run_url"].endswith("/41080431215")
    assert len(report["rows"]) == 8
    for item in report["rows"]:
        topo = item["topology"]
        assert topo == {
            "seam_vertices": 512,
            "outer_vertices": 256,
            "triangles": 768,
            "connected_components": 1,
            "boundary_loops": 2,
            "euler": 0,
            "nonmanifold_edges": 0,
        }
        metric = item["projection"]
        assert 0 < metric["edge_relative_loss_mean"] < 1
        assert metric["edge_relative_loss_mean"] < metric["edge_relative_loss_p95"]
        assert metric["edge_relative_loss_p95"] <= metric["edge_relative_loss_max"]
        assert metric["projected_triangles_collapsed"] == 0
        assert metric["projected_triangles_negative"] == 0
        assert metric["projected_triangles_positive"] == 768
    assert any("Not an optimized" in note for note in report["limitations"])
