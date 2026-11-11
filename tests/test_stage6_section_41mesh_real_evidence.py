"""Lock actual trusted Stage6 41-Mesh source section evidence without P4 claims."""

import json
from pathlib import Path

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/stage6_section_41mesh_20261111/summary.json"
PROGRESS = ROOT / "docs/PRODUCTION_PROGRESS.json"


def _real():
    return json.loads(EVIDENCE.read_text(encoding="utf8"))


def test_trusted_stage6_original_mesh_proximity_artifact_is_pinned():
    data = _real()
    trust = data["trusted_source_main"]
    assert data["source_original_blend_sha256"] == SOURCE_SHA256
    assert data["original_research_section_ring_count"] == {
        "125": 2,
        "230": 3,
        "245": 2,
    }
    assert trust["run_conclusion"] == "success"
    assert trust["run_id"] == 42947136279
    assert trust["artifact_id"] == 13822869393
    assert data["blender_version"] == "4.3.2"
    assert data["product_meshes_raycasted"] == 41
    assert data["independent_meshes_proximity_screened"] == 40
    assert data["not_raycasted_curve_and_hair_objects"] == 423
    assert len(trust["raw_artifact_zip_sha256"]) == 64
    assert len(trust["raw_full_41mesh_correspondence_json_sha256"]) == 64


def test_each_real_source_ring_retains_48_samples_and_raw_vertex_provenance():
    rows = _real()["per_loop_original_source_research"]
    assert [(x["z_mm"], x["loop_index_by_perimeter"]) for x in rows] == [
        (125, 0),
        (125, 1),
        (230, 0),
        (230, 1),
        (230, 2),
        (245, 0),
        (245, 1),
    ]
    for row in rows:
        counts = row["sample_classifications"]
        assert sum(counts.values()) == 48
        assert row["source_crossed_edges"] >= 48
        assert len(row["original_source_loop_sha256"]) == 64
        assert len(row["within_3mm_named_mesh_sample_counts"]) <= 40


def test_original_head_cloud_to_ear_observation_is_not_sewing_approval():
    data = _real()
    observations = data["per_loop_original_source_research"]
    rows = {(row["z_mm"], row["loop_index_by_perimeter"]): row for row in observations}
    center = rows[230, 0]["within_3mm_named_mesh_sample_counts"]
    left = rows[230, 1]["within_3mm_named_mesh_sample_counts"]
    right = rows[230, 2]["within_3mm_named_mesh_sample_counts"]
    assert center == {"Grey head cloud halo": 11, "Varied ivory forehead cloud": 8}
    assert left == {"Grey head cloud halo": 26}
    assert right == {"Varied ivory forehead cloud": 16}
    z245_l = rows[245, 0]["within_3mm_named_mesh_sample_counts"]
    z245_r = rows[245, 1]["within_3mm_named_mesh_sample_counts"]
    assert z245_l == {"Slender upright ivory ear -1": 35, "Pink inset ear -1": 26}
    assert z245_r == {"Slender upright ivory ear 1": 48, "Pink inset ear 1": 22}
    assert rows[245, 0]["sample_classifications"]["multiple"] == 25
    assert rows[245, 1]["sample_classifications"]["multiple"] == 22
    assert not data["anatomical_mesh_ownership_proven"]
    assert not data["design_front_side_back_top_signed_off"]
    assert not data["real_fabric_sewability_verified"]
    assert not data["physical_trial_done"]
    assert data["approved_manufacturer_cutting_patterns"] == 0


def test_real_mesh_evidence_does_not_advance_manufacturing_milestones():
    progress = json.loads(PROGRESS.read_text(encoding="utf8"))
    phase = {row["id"]: row for row in progress["phases"]}
    assert phase["P3"]["status"] == "in_progress"
    assert phase["P4"]["status"] == "not_started"
    assert not progress["overall"]["factory_sample_pack_ready"]
    assert EVIDENCE.relative_to(ROOT).as_posix() in {
        row["path"] for row in phase["P3"]["evidence"]
    }
