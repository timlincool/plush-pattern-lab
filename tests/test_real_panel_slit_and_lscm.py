"""True annulus-to-disk and LSCM tests with a physically developable cylinder."""

import xml.etree.ElementTree as ET

import numpy as np
import pytest

from plush_pattern_lab.patterns.full_panel_research_svg import (
    render_full_panel_research_svg,
)
from plush_pattern_lab.patterns.mesh_lscm_candidate import flatten_cut_panel
from plush_pattern_lab.validation.real_panel_slit import _edges, slit_real_panel


def _cylinder(count=64):
    """Triangulated cylinder with original lower cuff open and upper disk cap."""
    t = np.arange(count) * (2 * np.pi / count)
    bottom = np.column_stack(
        (20 * np.cos(t), 20 * np.sin(t), np.zeros(count))
    )
    top = bottom.copy()
    top[:, 2] = 25
    vertices = np.vstack((bottom, top, [0, 0, 25]))
    faces = []
    for i in range(count):
        j = (i + 1) % count
        faces.extend(((i, j, count + j), (i, count + j, count + i)))
    panel_ids = np.arange(len(faces))
    for i in range(count):
        j = (i + 1) % count
        faces.append((count + count, count + i, count + j))
    return vertices, np.asarray(faces), panel_ids


def _cut():
    xyz, faces, panel = _cylinder()
    return slit_real_panel(xyz, faces, panel, expected_cuff_edges=64)


def test_real_cylindrical_annulus_becomes_exactly_one_disk():
    result = _cut()
    assert result["source_cuff_edges"] == 64
    assert result["source_outer_seam_edges"] == 64
    assert result["original_annulus_faces"] == 128
    assert result["original_annulus_vertices"] == 128
    assert result["cut_disk_vertices"] == 130
    assert result["cut_disk_faces"] == 128
    assert result["cut_disk_boundary_edges"] == 130
    assert result["cut_disk_euler"] == 1
    assert len(result["slit_path_source_vertex_ids"]) == 2
    assert result["slit_path_length_3d_mm"] == pytest.approx(25)
    assert not result["fabric_cut_pattern_approved"]


def test_cylinder_conformal_unroll_has_correct_real_mm_net_seams():
    disk = _cut()
    score, uv = flatten_cut_panel(disk, iteration_cap=1000)
    assert score["status"] == "RESEARCH_GEOMETRY_ONLY"
    assert score["solver"]["converged_before_cap"]
    assert score["strain_screen"]["triangle_edge_relative_error"]["p95"] < 0.001
    assert score["strain_screen"]["inverted_winding_triangles"] == 0
    assert score["global_2d_overlap"]["overlapping_nonzero_area_triangle_pairs"] == 0
    assert not score["global_2d_overlap"]["overlap_search_truncated"]
    seam = score["boundary"]["perimeter_by_source_role"]
    assert seam["hoof"]["edge_count"] == 64
    assert seam["outer"]["edge_count"] == 64
    assert seam["slit"]["edge_count"] == 2
    assert seam["hoof"]["p95_edge_relative_error"] < 0.001
    assert not score["approved_cutting_pattern"]
    assert not score["factory_grain_or_seam_allowance_exists"]
    svg = render_full_panel_research_svg(disk, uv, score)
    assert ET.fromstring(svg).attrib["width"].endswith("mm")
    assert "NOT A CUTTING TEMPLATE" in svg


@pytest.mark.parametrize("failure", ["bad_cuff", "missing_panel", "bad_face", "repeat"])
def test_invalid_real_source_topology_cannot_be_made_into_a_panel(failure):
    xyz, faces, selected = _cylinder()
    if failure == "bad_cuff":
        faces = faces[:-1]
    elif failure == "missing_panel":
        selected = selected[:-1]
    elif failure == "bad_face":
        faces[0, 0] = len(xyz) + 1
    else:
        selected[1] = selected[0]
    with pytest.raises(ValueError):
        slit_real_panel(xyz, faces, selected, expected_cuff_edges=64)


def test_conformal_solver_refuses_unbounded_iteration_budget():
    disk = _cut()
    with pytest.raises(ValueError):
        flatten_cut_panel(disk, iteration_cap=10)


def test_svg_must_reject_nonfinite_failed_net_coords():
    disk = _cut()
    score, uv = flatten_cut_panel(disk, iteration_cap=1000)
    uv[0, 0] = np.nan
    with pytest.raises(ValueError):
        render_full_panel_research_svg(disk, uv, score)



def test_large_int32_blender_ply_edge_keys_are_64bit_before_multiplication():
    # Source PLY faces are <i4, while global edge IDs exceed int32 range.
    triangles = np.array(
        [[59997, 59998, 59999], [0, 1, 2]], dtype=np.int32
    )
    unique, _, _, keys, _ = _edges(triangles, vertex_count=60000)
    assert unique.dtype == np.int64
    assert keys.dtype == np.int64
    assert np.all(np.diff(keys) > 0)
    assert int(keys[-1]) > (2**31 - 1)


def test_cylinder_panels_from_int32_original_faces_preserve_topology():
    xyz, faces, selected = _cylinder()
    disk = slit_real_panel(
        xyz, faces.astype(np.int32), selected, expected_cuff_edges=64
    )
    assert disk["cut_disk_euler"] == 1
    assert disk["source_cuff_edges"] == 64
    assert disk["source_outer_seam_edges"] == 64
