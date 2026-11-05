"""Trusted real Stage6 fairing A/B proof must remain a rejection, not a stencil."""

import json
from pathlib import Path

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/stage6_manufacturing_surface_ab_20261105/summary.json"
PROGRESS = ROOT / "docs/PRODUCTION_PROGRESS.json"


def test_real_stage6_fairing_ab_is_pinned_and_rejected():
    data = json.loads(EVIDENCE.read_text(encoding="utf8"))
    assert (
        data["schema"] == "stage6-real-leftfront-manufacturing-surface-ab-measured-v1"
    )
    assert data["public_original_stage6_blend_sha256"] == SOURCE_SHA256
    assert data["trusted_main_run_conclusion"] == "success"
    assert data["leftfront_original_faces"] == 36833
    assert data["locked_original_3d_source_vertices"] == 1024
    assert data["protected_25pct_proxy_ply_sha256"] == (
        "5b52e3fd09c83b19c5b9d95d6d8d859a147ff4deef90f1518f868d2e82e3a2dd"
    )
    measured = data["measured"]
    assert measured["original"]["uv_nonzero_area_overlap_triangle_pairs"] == 23672
    assert measured["A_light"]["uv_nonzero_area_overlap_triangle_pairs"] == 24178
    assert measured["B_strong"]["uv_nonzero_area_overlap_triangle_pairs"] == 24401
    assert all(
        measured[x]["three_d_geometry_screen_rejected"] for x in ("A_light", "B_strong")
    )
    assert not data["geometric_and_manufacturing_cut_approved"]


def test_project_progress_keeps_rejected_surface_away_from_factory():
    progress = json.loads(PROGRESS.read_text(encoding="utf8"))
    p3 = next(row for row in progress["phases"] if row["id"] == "P3")
    p4 = next(row for row in progress["phases"] if row["id"] == "P4")
    assert p3["status"] == "in_progress"
    assert p4["status"] == "not_started"
    assert not progress["overall"]["factory_sample_pack_ready"]
    assert not progress["overall"]["mass_production_ready"]
    assert any(
        row["path"] == EVIDENCE.relative_to(ROOT).as_posix() for row in p3["evidence"]
    )
    assert (
        progress["verified_baseline"]["stage6_leftfront_surface_fairing_real_2d_ab"][
            "approved_for_cutting"
        ]
        == 0
    )
