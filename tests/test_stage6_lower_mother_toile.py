"""Stage6 hoof-anchored lower-body research toile: source and fabrication canaries."""

from __future__ import annotations

import copy
import math
from xml.etree import ElementTree

import numpy as np
import pytest

from plush_pattern_lab.patterns.stage6_lower_mother_toile import (
    build_source_hoof_lower_toile,
    extract_original_hoof_rings,
)
from plush_pattern_lab.patterns.stage6_lower_mother_toile_svg import (
    render_lower_mother_toile_a4,
)
from plush_pattern_lab.validation.stage6_lower_mother_toile_qc import (
    EXPECTED_SOURCE_HOOF_PERIMETERS_MM,
    inspect_source_lower_toile,
)


def _synthetic_four_hoof_caps(n=512):
    centers = {
        "FL": (-29.0, -34.0),
        "FR": (29.0, -34.0),
        "RL": (-29.0, 81.0),
        "RR": (29.0, 81.0),
    }
    xyz, faces = [], []
    for identity, center in centers.items():
        perimeter = EXPECTED_SOURCE_HOOF_PERIMETERS_MM[identity]
        radius = perimeter / (2 * n * math.sin(math.pi / n))
        angle = 2 * math.pi * np.arange(n) / n
        xy = np.column_stack(
            (
                center[0] + radius * np.cos(angle),
                center[1] + radius * np.sin(angle),
            )
        )
        base = len(xyz)
        xyz.extend(np.column_stack((xy, np.full(n, 20.0))).tolist())
        xyz.append([center[0], center[1], 20.0])
        for i in range(n):
            faces.append([base + i, base + (i + 1) % n, base + n])
    return np.asarray(xyz), np.asarray(faces)


def _spec():
    vertices, faces = _synthetic_four_hoof_caps()
    rings = extract_original_hoof_rings(vertices, faces)
    return build_source_hoof_lower_toile(rings)


def test_four_source_hoof_rings_have_distinct_actual_512_edge_identities():
    xyz, f = _synthetic_four_hoof_caps()
    rings = extract_original_hoof_rings(xyz, f)
    assert set(rings) == {"FL", "FR", "RL", "RR"}
    assert [len(rings[x]["original_vertex_ids"]) for x in rings] == [512] * 4
    assert [rings[x]["source_centroid_xyz_mm"][0] for x in ("FL", "FR")] == pytest.approx(
        [-29, 29], abs=1e-5
    )
    assert [rings[x]["source_centroid_xyz_mm"][1] for x in ("RL", "RR")] == pytest.approx(
        [81, 81], abs=1e-5
    )


def test_source_hoof_yoke_has_four_real_size_stitch_holes_and_13_pieces():
    spec = _spec()
    report = inspect_source_lower_toile(spec)
    assert spec["piece_count"] == 13
    assert spec["source_hoof_open_edges"] == 2048
    assert spec["yoke"]["upper_body_shell_seam_unpaired"]
    assert report["four_original_source_hoof_rings_and_all_2048_source_edges_preserved"]
    assert report["four_source_hoofs_to_sleeve_to_flat_test_sole_paired_per_segment"]
    assert report["all_64_new_outer_yoke_edges_pair_with_four_printable_bands"]
    assert report["unpaired_upper_band_edges"] == 4
    assert report["proposed_return_gap_mm"] > 25
    assert report["factory_patterns_approved"] == 0


def test_source_hoof_panel_a4_sheets_are_true_mm_and_not_print_scaled():
    pages = render_lower_mother_toile_a4(_spec())
    assert sorted(pages) == [f"sheet-{x:02d}.svg" for x in range(1, 5)]
    for body in pages.values():
        root = ElementTree.fromstring(body)
        assert root.attrib["width"] == "210mm"
        assert root.attrib["height"] == "297mm"
        assert root.attrib["viewBox"] == "0 0 210 297"
        assert "10 x 10 mm calibration square" in body
        assert "NOT FACTORY APPROVED" in body
    assert "data-part=\"VENTRAL-YOKE\"" in pages["sheet-01.svg"]
    assert pages["sheet-02.svg"].count('data-part="LEG-') == 4
    assert pages["sheet-03.svg"].count('data-part="TEST-SOLE-') == 4
    assert pages["sheet-04.svg"].count('data-part="BAND-') == 4
    assert 'class="gap"' in pages["sheet-04.svg"]


def test_each_hoof_source_notch_is_same_vertex_identity_on_yoke_and_leg():
    spec = _spec()
    for identity, ring in spec["original_source_hoofs"].items():
        stations = np.asarray(ring["sleeve_stitch_station_x_mm"])
        points = np.asarray(ring["source_stitch_ring_xy_mm"])
        segments = np.linalg.norm(points - np.roll(points, -1, axis=0), axis=1)
        for index in (0, 128, 256, 384):
            assert stations[index] == pytest.approx(float(segments[:index].sum()))
        assert identity in ("FL", "FR", "RL", "RR")


@pytest.mark.parametrize(
    "tamper",
    ["sleeve_step", "source_id", "port_cut", "outer_band", "turning", "status"],
)
def test_changed_source_fabric_connections_or_false_approval_are_rejected(tamper):
    spec = copy.deepcopy(_spec())
    if tamper == "sleeve_step":
        spec["original_source_hoofs"]["FL"]["sleeve_stitch_station_x_mm"][128] += 2
    elif tamper == "source_id":
        spec["original_source_hoofs"]["FL"]["source_vertex_ids"][50] = 9999
    elif tamper == "port_cut":
        spec["yoke"]["inner_cut_holes_xy_mm"][0] = [[0, 0], [1, 0], [0, 1]]
    elif tamper == "outer_band":
        spec["outer_quarter_bands"][0]["stitch_bottom_station_x_mm"][8] += 1
    elif tamper == "turning":
        spec["turning_gap_research"]["band_id"] = "BAND-2"
    else:
        spec["approved_industrial_paper_patterns"] = 1
    with pytest.raises(ValueError):
        inspect_source_lower_toile(spec)


def test_original_source_boundary_missing_one_of_four_hoof_rings_refused():
    xyz, faces = _synthetic_four_hoof_caps()
    with pytest.raises(ValueError):
        extract_original_hoof_rings(xyz, faces[:-512])


@pytest.mark.parametrize("change", ["wrong_z", "degenerate_face", "extra_face"])
def test_source_mesh_hoof_boundary_cannot_be_substituted(change):
    xyz, faces = _synthetic_four_hoof_caps(n=32)
    if change == "wrong_z":
        xyz[0, 2] = 21.0
    elif change == "degenerate_face":
        faces[0] = [0, 0, 0]
    else:
        faces = np.vstack((faces, faces[:1]))
    with pytest.raises(ValueError):
        extract_original_hoof_rings(xyz, faces, expected_edges=32)


def test_relocated_yoke_or_test_sole_cannot_claim_original_body_sculpt():
    spec = _spec()
    assert spec["new_ventral_yoke_is_not_original_body_surface"]
    assert spec["real_hoof_base_3d_mesh_not_flattened"]
    assert spec["head_neck_upper_body_ears_tail_clouds_not_connected"]
    assert spec["physical_fabric_test_not_done"] is not False
    with pytest.raises(ValueError):
        build_source_hoof_lower_toile({}, seam_allowance_mm=6)
