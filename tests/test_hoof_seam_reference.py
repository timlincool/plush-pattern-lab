"""Stage6 四蹄真实接缝参考：弧长对位、投影畸变和刻意反例。"""

import xml.etree.ElementTree as ET

import numpy as np
import pytest

from plush_pattern_lab.patterns.hoof_seam_reference import (
    STATUS,
    build_reference,
    draw_reference_svg,
)


def shapes(points=32, warped=False):
    t = np.arange(points) * np.pi * 2 / points
    rings = []
    for i in range(4):
        z = 0.7 * np.sin(3 * t) if warped else np.zeros(points)
        rings.append(
            np.column_stack((12 * np.cos(t) + 110 * i, 9 * np.sin(t), z + i * 4))
        )
    return rings


def example(warped=False):
    bodies = shapes(warped=warped)
    hoofs = [np.roll(bodies[i][::-1], 7, axis=0) for i in (2, 0, 3, 1)]
    return bodies, hoofs


def build(bodies=None, hoofs=None):
    if bodies is None or hoofs is None:
        bodies, hoofs = example()
    return build_reference(bodies, hoofs, [f"hoof-{i}" for i in range(4)], "a" * 64)


def test_reference_has_exact_opposing_vertex_pairings_and_arc_length():
    report = build()
    assert report["status"] == STATUS
    assert report["quality"]["matched_interfaces"] == 4
    assert not report["quality"]["surface_flattened"]
    assert not report["quality"]["seam_allowance_defined"]
    assert not report["quality"]["approved_cut_patterns"]
    assert [r["body_ring_index"] for r in report["hoofs"]] == [2, 0, 3, 1]
    bodies, hoofs = example()
    for i, row in enumerate(report["hoofs"]):
        assert row["matching"]["world_boundary_geometry_match"]
        assert row["matching"]["reversed_boundary_winding"]
        assert row["max_matched_segment_length_delta_mm"] < 1e-9
        assert len(row["body_to_hoof_ring_ordinals"]) == 32
        assert sorted(row["body_to_hoof_ring_ordinals"]) == list(range(32))
        for notch in row["notches"]:
            source = bodies[row["body_ring_index"]][notch["body_ring_ordinal"]]
            target = hoofs[i][notch["hoof_ring_ordinal"]]
            np.testing.assert_allclose(source, target, rtol=0, atol=1e-12)
        assert [n["id"] for n in row["notches"]] == ["Q0", "Q1", "Q2", "Q3"]
        assert row["projection_diagnostics"][
            "projection_length_loss_mm"
        ] == pytest.approx(0, abs=1e-8)


def test_source_cycle_rotation_keeps_notch_identity():
    body, hoofs = example(warped=True)
    original = build(body, hoofs)
    rotated = build([np.roll(b, 5, axis=0) for b in body], hoofs)
    for first, second in zip(original["hoofs"], rotated["hoofs"]):
        np.testing.assert_allclose(
            first["projected_reference_ring_2d_mm"],
            second["projected_reference_ring_2d_mm"],
            rtol=0,
            atol=1e-10,
        )
        assert [n["arc_length_3d_mm"] for n in first["notches"]] == pytest.approx(
            [n["arc_length_3d_mm"] for n in second["notches"]], abs=1e-10
        )


def test_nonplanar_reference_reports_not_hides_projection_shrinkage():
    body, hoofs = example(warped=True)
    report = build(body, hoofs)
    for row in report["hoofs"]:
        q = row["projection_diagnostics"]
        assert q["max_out_of_plane_mm"] > 0.1
        assert q["out_of_plane_rms_mm"] > 0.1
        assert q["projection_length_loss_mm"] > 0.1
        assert q["perimeter_3d_mm"] > q["perimeter_2d_projected_mm"]
        assert q["max_projected_edge_shortfall_ratio"] > 0.001
        assert not q["projection_is_true_surface_flattening"]


def test_unchanged_winding_must_fail():
    bodies = shapes()
    with pytest.raises(ValueError, match="方向守卫"):
        build(bodies, [x.copy() for x in bodies])


def test_3d_offset_is_not_silently_fixed():
    bodies, hoofs = example()
    hoofs[0] = hoofs[0].copy()
    hoofs[0][:, 2] += 0.002
    with pytest.raises(ValueError, match="守卫"):
        build(bodies, hoofs)


def test_mismatched_topology_is_not_resampled():
    bodies, hoofs = example()
    hoofs[0] = hoofs[0][::2]
    with pytest.raises(ValueError, match="禁止插值"):
        build(bodies, hoofs)


def test_wrong_sha_and_missing_four_hoofs_are_rejected():
    body, hoofs = example()
    with pytest.raises(ValueError, match="SHA-256"):
        build_reference(body, hoofs, ["a"] * 4, "bad")
    with pytest.raises(ValueError, match="四只蹄"):
        build_reference(body[:3], hoofs[:3], ["a"] * 3, "a" * 64)


def test_nonfinite_or_collapsed_input_rejected():
    bodies, hoofs = example()
    bodies[0] = bodies[0].copy()
    bodies[0][0, 1] = np.nan
    with pytest.raises(ValueError):
        build(bodies, hoofs)


def test_svg_is_valid_1_to_1_reference_not_cut_outline():
    svg = draw_reference_svg(build())
    root = ET.fromstring(svg)
    assert root.attrib["width"].endswith("mm")
    assert root.attrib["height"].endswith("mm")
    assert (
        len(
            root.findall(
                "{http://www.w3.org/2000/svg}g/{http://www.w3.org/2000/svg}polygon"
            )
        )
        == 4
    )
    assert "NOT A CUT PATTERN" in svg
    assert "seam allowance" in svg
    assert "Q0" in svg and "Q3" in svg


def test_svg_rejects_untrusted_or_nonfinite_geometry():
    report = build()
    report["schema"] = "untrusted"
    with pytest.raises(ValueError):
        draw_reference_svg(report)
    report = build()
    report["hoofs"][0]["projected_reference_ring_2d_mm"][0][0] = np.inf
    with pytest.raises(ValueError):
        draw_reference_svg(report)
