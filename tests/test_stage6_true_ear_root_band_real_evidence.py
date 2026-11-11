"""Pin two actual Stage6 original-source 3D ear-root seam runs and veto paper."""

import json
from pathlib import Path

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/stage6_true_ear_root_band_20261111/summary.json"
PROGRESS = ROOT / "docs/PRODUCTION_PROGRESS.json"


def _actual():
    return json.loads(EVIDENCE.read_text(encoding="utf8"))


def test_two_real_stage6_runs_exactly_repeat_source_3d_cut_and_six_files():
    report = _actual()
    assert report["source_original_public_blend_sha256"] == SOURCE_SHA256
    assert report["source_original_proxy_vertices"] == 59306
    assert report["source_original_proxy_triangles"] == 116568
    assert report["trusted_python_ci"]["tests_passed"] == 613
    a, b = report["two_independent_trusted_stage6_blender_4_3_2_runs"]
    assert (a["run_id"], b["run_id"]) == (42980311292, 42980617110)
    assert a["conclusion"] == b["conclusion"] == "success"
    assert a["artifact_zip_sha256"] != b["artifact_zip_sha256"]
    six = report[
        "six_original_raw_research_file_sha256_exactly_identical_across_two_trusted_runs"
    ]
    assert len(six) == 6
    assert all(len(value) == 64 for value in six.values())
    assert report["six_raw_research_files_exact_byte_identical_twice"]
    assert not report["complete_action_zip_byte_identical"]


def test_original_source_3d_paired_netlines_are_exact_but_root_band_too_narrow():
    report = _actual()
    patches = report["root_patch_research"]
    assert [x["side"] for x in patches] == ["left", "right"]
    triangle_counts = [
        x["original_3d_ear_root_band"]["derived_triangle_faces"] for x in patches
    ]
    assert triangle_counts == [829, 879]
    euler = [x["original_3d_ear_root_band"]["euler_characteristic"] for x in patches]
    assert euler == [0, 0]
    assert all(
        x["original_3d_ear_root_band"]["closed_source_boundary_loops"] == 2
        for x in patches
    )
    lower_counts = [
        x["body_to_root_true_3d_paired_seam"]["source_triangle_crossing_segments"]
        for x in patches
    ]
    assert lower_counts == [113, 112]
    upper_counts = [
        x["root_to_upper_source_ear_true_3d_paired_seam"][
            "source_triangle_crossing_segments"
        ]
        for x in patches
    ]
    assert upper_counts == [110, 117]
    for patch in patches:
        for key in (
            "body_to_root_true_3d_paired_seam",
            "root_to_upper_source_ear_true_3d_paired_seam",
        ):
            seam = patch[key]
            assert seam["paired_edge_xyz_max_abs_error_mm"] == 0
            assert seam["opposite_face_edge_winding"]
            assert len(seam["canonical_subtree_sha256"]) == 64
        assert (
            patch["source_triangle_surface_graph_min_p05_median_p95_max_width_mm"][0]
            < 6
        )
        assert (
            patch["fraction_upper_seam_source_vertices_with_graph_path_under_12mm"]
            == 1.0
        )
    assert report["source_surface_area_reconstruction_abs_error_mm2"] == 0
    assert not report[
        "candidate_5mm_high_ear_root_band_suitable_for_two_nominal_6mm_2d_allowances"
    ]


def test_true_source_3d_seams_do_not_advance_factory_stage():
    report = _actual()
    progress = json.loads(PROGRESS.read_text(encoding="utf8"))
    phases = {row["id"]: row for row in progress["phases"]}
    assert phases["P3"]["status"] == report["P3_status"] == "in_progress"
    assert phases["P4"]["status"] == report["P4_status"] == "not_started"
    assert EVIDENCE.relative_to(ROOT).as_posix() in {
        row["path"] for row in phases["P3"]["evidence"]
    }
    assert not progress["overall"]["factory_sample_pack_ready"]
    assert report["manufacturer_cutting_patterns_approved"] == 0
    assert report["measured_3d_paired_seams_are_not_material_2d_rest_netlines"]
    assert report["material_stretch_thread_grain_and_turnout_unverified"]
    assert not report["physical_fabric_sample_done"]
    assert report["full_density_original_stage6_466k_face_direct_cut_not_done"]
