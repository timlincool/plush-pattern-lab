"""Real four-hole B24 research yoke constrained triangulation regression."""

import numpy as np
import pytest

from research.stage6_b24_source_yoke_cdt import build


def _source():
    theta = 2 * np.pi * np.arange(64) / 64
    outer = np.column_stack((90 * np.cos(theta), 110 * np.sin(theta)))
    holes = {}
    for name, cx, cy in [
        ("FL", -42, -45),
        ("FR", 42, -45),
        ("RL", -42, 45),
        ("RR", 42, 45),
    ]:
        fine = 2 * np.pi * np.arange(512) / 512
        holes[name] = np.column_stack(
            (cx + 12 * np.cos(fine), cy + 12 * np.sin(fine))
        ).tolist()
    return {
        "schema": "stage6-source-hoof-anchored-lower-mother-toile-v1",
        "approved_industrial_paper_patterns": 0,
        "yoke": {
            "outer_stitch_xy_mm": outer.tolist(),
            "source_hoof_holes_stitch_xy_mm": holes,
        },
    }


def test_unchanged_five_source_boundaries_preserved_in_2d():
    result = build(_source(), "same-run-lower-sha")
    assert result["schema"] == "stage6-b24-four-hoof-hole-constrained-yoke-mesh-v1"
    assert result["source_lower_mother_json_sha256"] == "same-run-lower-sha"
    assert len(result["triangles_local_original_yoke_vertex_ids"]) == 326
    assert result["original_stitch_loop_boundary_edges"] == 320
    assert result["additional_steiner_vertices"] == 0
    assert result["factory_cutting_patterns_approved"] == 0


def test_original_yoke_with_invalid_overlapping_leg_holes_is_rejected():
    source = _source()
    source["yoke"]["source_hoof_holes_stitch_xy_mm"]["FR"] = source["yoke"][
        "source_hoof_holes_stitch_xy_mm"
    ]["FL"]
    with pytest.raises(ValueError):
        build(source, "same-run-lower-sha")


def test_refuses_fake_factory_approval_or_original_source_type():
    source = _source()
    source["approved_industrial_paper_patterns"] = 1
    with pytest.raises(ValueError):
        build(source, "sha")
    source["approved_industrial_paper_patterns"] = 0
    source["schema"] = "fake-source"
    with pytest.raises(ValueError):
        build(source, "sha")
