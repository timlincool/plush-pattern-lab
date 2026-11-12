"""Pin two trusted true Stage6 nonhorizontal source 3D seam experiments."""

import json
from pathlib import Path

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/stage6_nonhorizontal_ear_root_20261112/summary.json"
PROGRESS = ROOT / "docs/PRODUCTION_PROGRESS.json"


def _load():
    return json.loads(EVIDENCE.read_text(encoding="utf8"))


def test_original_stage6_two_replays_seven_identical_raw_sha_not_zips():
    report = _load()
    assert report["original_public_blend_sha256"] == SOURCE_SHA256
    assert report["original_proxy_vertex_count"] == 59306
    assert report["original_proxy_triangle_count"] == 116568
    assert report["trusted_python_ci"]["passed_tests"] == 624
    first, repeat = report["two_independent_trusted_main_blender_4_3_2_runs"]
    assert (first["run_id"], repeat["run_id"]) == (43190504878, 43190708654)
    assert first["conclusion"] == repeat["conclusion"] == "success"
    assert first["full_artifact_zip_sha256"] != repeat["full_artifact_zip_sha256"]
    hashes = report["seven_raw_files_sha256_matching_across_both_trusted_runs"]
    assert len(hashes) == 7
    assert all(len(value) == 64 for value in hashes.values())
    assert report["all_seven_original_research_files_byte_identical_twice"]
    assert not report["complete_action_artifact_zip_byte_identical"]


def test_original_real_source_four_sloping_patches_are_paired_but_narrow_at_rim():
    report = _load()
    variants = report["source_curved_3d_cut_research_variants"]
    assert [v["study"] for v in variants] == [
        "N15_sloped_source_band",
        "N17_sloped_source_band",
    ]
    assert [[p["source_patch_derived_triangles"] for p in v["sides"]] for v in variants] == [
        [1680, 1755],
        [1865, 1940],
    ]
    assert report["source_cut_component_counts_per_variant"] == {
        "below": 1,
        "root": 3,
        "above": 2,
    }
    for study in variants:
        assert study["source_area_reconstruction_abs_error_mm2"] < 1e-4
        assert [side["side"] for side in study["sides"]] == ["left", "right"]
        for patch in study["sides"]:
            assert patch["graph_width_min_p05_median_p95_max_mm"][0] > 12
            assert patch["upper_rim_xy_minor_mm"] < 12
            assert patch["lower_paired_seam_segments"] >= 100
            assert patch["upper_paired_seam_segments"] >= 70
            for key in (
                "source_patch_canonical_sha256",
                "lower_3d_seam_subtree_sha256",
                "upper_3d_seam_subtree_sha256",
            ):
                assert len(patch[key]) == 64
    assert report["all_four_band_source_graph_min_distances_over_12mm"]
    assert report["all_four_upper_original_ear_rims_xy_minor_under_12mm"]
    assert report["physical_world_seam_xyz_match_error_mm"] == 0


def test_true_3d_source_pairing_does_not_authorize_2d_cut_patterns():
    report = _load()
    progress = json.loads(PROGRESS.read_text(encoding="utf8"))
    phases = {p["id"]: p for p in progress["phases"]}
    assert phases["P3"]["status"] == report["P3_status"] == "in_progress"
    assert phases["P4"]["status"] == report["P4_status"] == "not_started"
    assert EVIDENCE.relative_to(ROOT).as_posix() in {
        entry["path"] for entry in phases["P3"]["evidence"]
    }
    assert not progress["overall"]["factory_sample_pack_ready"]
    assert report["factory_cutting_patterns_approved"] == 0
    assert not report["material_2d_rest_netlines_cut_allowances_verified"]
    assert not report["independent_ear_cloud_attachment_and_design_four_view_signed_off"]
    assert not report["real_fabric_test_or_factory_approval"]
    assert report["original_high_density_466k_faces_not_directly_cut"]
