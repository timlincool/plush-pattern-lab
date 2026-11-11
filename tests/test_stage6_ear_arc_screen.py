"""Fail-closed Stage6 source quadrant arc, five-view and non-sewability tests."""

from __future__ import annotations

import hashlib
import json
import math
import struct
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from plush_pattern_lab.validation.stage6_ear_arc_screen import (
    ORIGINAL_SHA,
    PROXY_SHA,
    SCHEMA,
    compare_source_quadrant_arcs,
)
from plush_pattern_lab.validation.stage6_ear_arc_svg import (
    render_stage6_arc_screen_svg,
)


def _ring(side):
    n = 96
    center = -55 if side == "left" else 55
    xy = [
        [
            center + 7 * math.cos(i * math.tau / n),
            -44 + 5 * math.sin(i * math.tau / n),
        ]
        for i in range(n)
    ]
    edges = [[i, i + 1] for i in range(n)]
    raw = b"".join(struct.pack("<qq", *pair) for pair in edges)
    raw += b"".join(struct.pack("<dd", *point) for point in xy)
    length = sum(
        math.dist(point, xy[(i + 1) % n]) for i, point in enumerate(xy)
    )
    return {
        "side": side,
        "source_contour_sha256": hashlib.sha256(raw).hexdigest(),
        "original_proxy_crossed_edge_count": n,
        "source_3d_ring_perimeter_mm": length,
        "source_centroid_xy_mm": [center, -44],
        "xy_minor_bbox_under_two_research_6mm_allowances": True,
        "full_interpolated_original_source_xy_mm": xy,
        "full_crossed_original_proxy_vertex_id_pairs": edges,
    }


def _observed(ring, z):
    xy = ring["full_interpolated_original_source_xy_mm"]
    edges = ring["full_crossed_original_proxy_vertex_id_pairs"]
    samples = []
    for i in range(48):
        idx = i * len(xy) // 48
        category = (
            "near_original_body_first_surface"
            if i % 3 == 0
            else "occluded_by_another_product_mesh"
        )
        samples.append(
            {
                "source_edge_ordinal": idx,
                "source_vertex_id_pair": edges[idx],
                "source_xyz_mm": [*xy[idx], z],
                "physical_attachment_or_ear_identity_proven": False,
                "nearby_raw_meshes_within_6mm": [
                    {"mesh": "Grey head cloud halo", "distance_mm": 1.5}
                ]
                if i % 4 == 0
                else [],
                "five_view_first_hit": {
                    view: {"classification": category}
                    for view in ("front", "back", "left", "right", "top")
                },
            }
        )
    return {
        "side": ring["side"],
        "source_contour_sha256": ring["source_contour_sha256"],
        "source_edge_samples_observed": 48,
        "original_source_crossed_edge_count": len(xy),
        "surface_mesh_occlusion_not_a_hidden_sewing_seam": True,
        "physical_ear_root_not_approved": True,
        "original_source_edge_samples": samples,
    }


def _inputs():
    source_options, visibility_options = [], []
    for name, z in (("A_lower_root_ring", 230), ("B_higher_root_ring", 235)):
        sides = [_ring(s) for s in ("left", "right")]
        source_options.append(
            {"name": name, "source_plane_z_mm": z, "source_side_loops": sides}
        )
        visibility_options.append(
            {
                "name": name,
                "source_z_mm": z,
                "sides": [_observed(side, z) for side in sides],
            }
        )
    return (
        {
            "schema": "stage6-original-source-ear-root-two-height-ring-ab-v1",
            "original_public_stage6_blend_sha256": ORIGINAL_SHA,
            "source_25pct_proxy_ply_sha256": PROXY_SHA,
            "manufacturing_cutting_approved": 0,
            "candidate_options": source_options,
        },
        {
            "schema": "stage6-original-source-ear-root-ab-41mesh-five-view-v1",
            "original_public_blend_sha256": ORIGINAL_SHA,
            "raw_product_meshes_raycasted": 41,
            "original_fur_curves_not_tested": 423,
            "manufacturing_seam_or_dart_approved": False,
            "P4_started": False,
            "options": visibility_options,
        },
    )


def test_all_four_quadrants_source_ids_and_unpaired_seam_endpoints():
    study, visibility = _inputs()
    report = compare_source_quadrant_arcs(study, visibility)
    assert report["schema"] == SCHEMA
    assert report["studied_quadrants"] == [
        "medial",
        "lateral",
        "posterior",
        "anterior",
    ]
    arcs = [
        arc
        for option in report["option_results"]
        for side in option["sides"]
        for arc in side["quadrant_arc_hypotheses"]
    ]
    assert len(arcs) == 16
    assert all(arc["sample_count"] == 12 for arc in arcs)
    assert all(arc["original_arc_endpoints_unpaired"] == 2 for arc in arcs)
    assert all(arc["source_original_plane_arc_length_mm"] > 0 for arc in arcs)
    assert all(not arc["approved_as_hidden_seam"] for arc in arcs)
    assert report["approved_factory_cutting_patterns"] == 0
    assert report["P3_status"] == "in_progress"
    assert report["P4_status"] == "not_started"
    svg = render_stage6_arc_screen_svg(report, study)
    assert "NOT CUTTING PATTERNS" in svg
    assert svg.count("<polyline ") == 16


@pytest.mark.parametrize(
    "kind",
    [
        "sha",
        "study_approved",
        "visibility_approved",
        "wrong_mesh_count",
        "wrong_z",
        "wrong_side",
        "missing_view",
        "wrong_classification",
        "wrong_sample_id",
        "wrong_sample_xyz",
        "interior_xy_tamper",
        "negative_mesh_distance",
        "too_many_samples",
        "fake_covered_proof",
    ],
)
def test_tampering_and_false_fabrication_claims_fail_closed(kind):
    study, visibility = _inputs()
    source = study["candidate_options"][0]["source_side_loops"][0]
    seen = visibility["options"][0]["sides"][0]
    sample = seen["original_source_edge_samples"][0]
    if kind == "sha":
        source["source_contour_sha256"] = "0" * 64
    elif kind == "study_approved":
        study["manufacturing_cutting_approved"] = 1
    elif kind == "visibility_approved":
        visibility["manufacturing_seam_or_dart_approved"] = True
    elif kind == "wrong_mesh_count":
        visibility["raw_product_meshes_raycasted"] = 40
    elif kind == "wrong_z":
        visibility["options"][0]["source_z_mm"] = 235
    elif kind == "wrong_side":
        seen["side"] = "right"
    elif kind == "missing_view":
        sample["five_view_first_hit"].pop("back")
    elif kind == "wrong_classification":
        sample["five_view_first_hit"]["back"]["classification"] = "factory_approved"
    elif kind == "wrong_sample_id":
        sample["source_vertex_id_pair"] = [123, 456]
    elif kind == "wrong_sample_xyz":
        sample["source_xyz_mm"][0] += 1
    elif kind == "interior_xy_tamper":
        source["full_interpolated_original_source_xy_mm"][1][0] += 1
    elif kind == "negative_mesh_distance":
        sample["nearby_raw_meshes_within_6mm"][0]["distance_mm"] = -1
    elif kind == "too_many_samples":
        seen["original_source_edge_samples"].append(deepcopy(sample))
    else:
        sample["physical_attachment_or_ear_identity_proven"] = True
    with pytest.raises(ValueError):
        compare_source_quadrant_arcs(study, visibility)


def test_original_source_quadrants_do_not_depend_on_which_mesh_is_occluding():
    study, visibility = _inputs()
    before = compare_source_quadrant_arcs(study, visibility)
    changed = deepcopy(visibility)
    for option in changed["options"]:
        for side in option["sides"]:
            for sample in side["original_source_edge_samples"]:
                for row in sample["five_view_first_hit"].values():
                    row["classification"] = "self_occluded_by_original_body"
    after = compare_source_quadrant_arcs(study, changed)
    for first, second in zip(before["option_results"], after["option_results"]):
        for left, right in zip(first["sides"], second["sides"]):
            assert [
                arc["source_sample_indices_in_order"]
                for arc in left["quadrant_arc_hypotheses"]
            ] == [
                arc["source_sample_indices_in_order"]
                for arc in right["quadrant_arc_hypotheses"]
            ]


def test_same_run_cli_hash_and_no_evidence_overwrite(tmp_path):
    study, visibility = _inputs()
    source, raw = tmp_path / "source.json", tmp_path / "visibility.json"
    source.write_text(json.dumps(study))
    visibility["same_run_ear_root_study_sha256"] = hashlib.sha256(
        source.read_bytes()
    ).hexdigest()
    raw.write_text(json.dumps(visibility))
    script = Path(__file__).resolve().parents[1] / "scripts/audit_stage6_ear_root_arcs.py"
    output, svg = tmp_path / "result.json", tmp_path / "result.svg"
    argv = [
        sys.executable,
        str(script),
        "--study",
        str(source),
        "--visibility",
        str(raw),
        "--output",
        str(output),
        "--svg",
        str(svg),
    ]
    good = subprocess.run(argv, capture_output=True, text=True, check=False)
    assert good.returncode == 0, good.stderr
    assert output.exists() and svg.exists()
    assert "NOT CUTTING PATTERNS" in svg.read_text()
    again = subprocess.run(argv, capture_output=True, text=True, check=False)
    assert again.returncode != 0
    assert "overwrite" in again.stderr
    output.unlink()
    svg.unlink()
    visibility["same_run_ear_root_study_sha256"] = "f" * 64
    raw.write_text(json.dumps(visibility))
    bad = subprocess.run(argv, capture_output=True, text=True, check=False)
    assert bad.returncode != 0
    assert "cross-run" in bad.stderr
