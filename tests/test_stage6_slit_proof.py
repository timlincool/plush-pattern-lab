"""Pinned real Stage6 slit-unroll evidence; no manufactured cut claim."""

import json
from pathlib import Path

from plush_pattern_lab.validation.public_release_proof import MODEL_SHA256

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "experiments" / "stage6_slit_unroll_20261101" / "summary.json"


def test_measured_slit_unroll_proof_is_from_the_public_stage6():
    proof = json.loads(PROOF.read_text(encoding="utf-8"))
    assert proof["schema"] == "stage6-real-periodic-slit-unroll-evidence-v1"
    assert proof["source"]["sha256"] == MODEL_SHA256
    assert proof["source"]["trusted_workflow_run"].endswith("/41282869818")
    assert not proof["approved_cut_pattern"]
    assert proof["parameters"]["inner_seam_arclength_fixed"]
    assert len(proof["bands"]) == 8
    assert all(
        0 < item["p95_optimized"] < item["p95_initial"] for item in proof["bands"]
    )
    assert all(
        item["flips"] == 0
        and item["overlap_pairs"] == 0
        and item["slit_edges"] == 1
        and item["converged"]
        for item in proof["bands"]
    )
    assert proof["aggregate"]["p95_after_min"] > 0
    assert proof["aggregate"]["p95_after_max"] < 0.04
