"""Synthetic visual inspection must preserve real Blender evidence and vetoes."""

import pytest

from plush_pattern_lab.validation.preview_evidence import verify_snapshot

BLEND_HASH = "a" * 64
TRIAL_HASH = "b" * 64


def valid_pair():
    simulation = {
        "status": "ACTUAL_CAPPED_CLOTH_SEWING_RESEARCH_ONLY",
        "panels": 12,
        "total_face_count": 1560,
        "vertices": 2390,
        "self_collision_enabled": False,
    }
    audit = {
        "status": "FINITE_ZERO_THICKNESS_TRIANGLE_INTERSECTION_SCREEN",
        "case_sha256": BLEND_HASH,
        "source_report_sha256": TRIAL_HASH,
        "triangle_count": 3120,
        "vertex_count": 2390,
        "research_trial_self_collision_enabled": False,
        "nonadjacent_other_pair_count": 1,
        "nonadjacent_seam_related_pair_count": 900,
        "nonadjacent_total_intersections": 901,
        "localization": {
            "counts": {"other": 1, "seam": 900, "shared": 10},
            "witnesses": {"other": [{"triangle_indices": [4, 257]}]},
        },
    }
    return simulation, audit


def inspect(pair):
    return verify_snapshot(*pair, blend_sha=BLEND_HASH, trial_sha=TRIAL_HASH)


def test_honest_research_preview_tracks_unresolved_contact():
    evidence = inspect(valid_pair())
    assert evidence["finite_nonseam_intersections"] == 1
    assert evidence["finite_seam_related_intersections"] == 900
    assert not evidence["research_contact_pass"]
    assert evidence["geometry_not_manufacturing_certified"]
    assert "NOT_REAL_PLUSH" in evidence["status"]


@pytest.mark.parametrize(
    "where,key,value",
    [
        ("audit", "case_sha256", "f" * 64),
        ("audit", "source_report_sha256", "0" * 64),
        ("audit", "nonadjacent_total_intersections", 0),
        ("audit", "nonadjacent_other_pair_count", -1),
        ("audit", "triangle_count", 1234),
        ("audit", "vertex_count", 200),
        ("audit", "research_trial_self_collision_enabled", True),
        ("audit", "localization", {}),
        ("sim", "panels", True),
        ("sim", "status", "FABRICATED_PRODUCTION_PASS"),
    ],
)
def test_reject_corrupt_or_fabricated_provenance(where, key, value):
    sim, audit = valid_pair()
    if where == "sim":
        sim[key] = value
    else:
        audit[key] = value
    with pytest.raises(ValueError):
        inspect((sim, audit))


def test_reject_out_of_bounds_witness():
    sim, audit = valid_pair()
    audit["localization"]["witnesses"]["other"][0]["triangle_indices"] = [4, 3120]
    with pytest.raises(ValueError, match="triangle index"):
        inspect((sim, audit))


def test_reject_missing_witness_not_just_green_count():
    sim, audit = valid_pair()
    audit["localization"]["witnesses"]["other"] = []
    with pytest.raises(ValueError, match="sample coverage"):
        inspect((sim, audit))


def test_real_free_no_danger_synthetic_no_witnesses():
    sim, audit = valid_pair()
    audit["nonadjacent_other_pair_count"] = 0
    audit["nonadjacent_seam_related_pair_count"] = 0
    audit["nonadjacent_total_intersections"] = 0
    audit["localization"]["counts"] = {"other": 0, "seam": 0}
    audit["localization"]["witnesses"]["other"] = []
    evidence = inspect((sim, audit))
    assert evidence["research_contact_pass"]
    assert evidence["geometry_not_manufacturing_certified"]
