"""Persist two trusted Stage6 original source slab results, without P4 approval."""

import json
from pathlib import Path

from plush_pattern_lab.validation.component_inventory import SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments/stage6_source_slab_20261111/summary.json"


def _actual():
    return json.loads(EVIDENCE.read_text(encoding="utf8"))


def test_true_source_mesh_topology_proof_is_pinned_to_original_public_blend():
    x = _actual()
    assert x["source"]["public_stage6_original_blend_sha256"] == SOURCE_SHA256
    assert x["source"]["source_proxy_vertices"] == 59306
    assert x["source"]["source_proxy_triangles"] == 116568
    assert len(x["source"]["same_run_41_product_mesh_correspondence_sha256"]) == 64
    assert len(x["source"]["original_13_plane_contour_detail_sha256"]) == 64


def test_two_trusted_runs_have_identical_raw_slab_json_and_svg():
    x = _actual()
    a, b = x["real_blender_trusted_main_runs"]
    assert a["conclusion"] == b["conclusion"] == "success"
    assert {a["run_id"], b["run_id"]} == {42951036948, 42951246219}
    assert a["artifact_id"] != b["artifact_id"]
    assert a["artifact_zip_sha256"] != b["artifact_zip_sha256"]
    assert x["two_independent_trusted_runs_byte_identical_each_raw_research_file"]
    assert not x["two_full_artifact_zip_files_byte_identical"]
    assert all(len(value) == 64 for value in x["raw_research_files_sha256"].values())


def test_crown_branch_and_ear_side_continuity_do_not_authorize_cutting():
    x = _actual()
    spans = x["real_source_slabs"]
    assert len(spans) == 5
    triangle_counts = [s["open_slab_source_triangles"] for s in spans]
    assert triangle_counts == [5078, 3566, 7127, 9597, 4691]
    assert [s["connected_surface_components"] for s in spans] == [2, 1, 1, 1, 3]
    assert spans[3]["components"][0]["lower_loop_indices"] == [0]
    assert spans[3]["components"][0]["upper_loop_indices"] == [0, 1, 2]
    transitions = sorted(
        (tuple(c["lower_loop_indices"]), tuple(c["upper_loop_indices"]))
        for c in spans[4]["components"]
    )
    assert transitions == [((0,), ()), ((1,), (0,)), ((2,), (1,))]
    assert x["P3_status"] == "in_progress"
    assert x["P4_status"] == "not_started"
    assert x["approved_factory_cutting_patterns"] == 0
    assert not x["seam_allowance_verified"]
    assert not x["ear_root_manufacturing_seam_validated"]
