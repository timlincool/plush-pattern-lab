"""Synthetic four-holed shell: four face regions must preserve all cuff rings."""

import numpy as np
import pytest

from plush_pattern_lab.patterns.whole_shell_seam_map import render_four_zone_seam_map

from plush_pattern_lab.validation.whole_shell_partition import (
    draft_four_zone_shell,
)


def cube_with_four_one_cell_hoof_openings():
    """Closed 8x8x6 sided cube surface, minus four bottom one-cell cuffs."""
    coordinates = np.arange(-4, 5)
    index, vertices, faces = {}, [], []

    def vertex(point):
        point = tuple(int(x) for x in point)
        if point not in index:
            index[point] = len(vertices)
            vertices.append(point)
        return index[point]

    for axis in range(3):
        u, v = [dimension for dimension in range(3) if dimension != axis]
        for side in (-4, 4):
            for i in range(8):
                for j in range(8):
                    if axis == 2 and side == -4 and (i, j) in {
                        (1, 1), (1, 5), (5, 1), (5, 5)
                    }:
                        continue
                    corners = []
                    for ui, vj in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)):
                        point = [0, 0, 0]
                        point[axis] = side
                        point[u] = coordinates[ui]
                        point[v] = coordinates[vj]
                        corners.append(vertex(point))
                    a, b, c, d = corners
                    faces.extend(((a, b, c), (a, c, d)))
    return np.asarray(vertices, dtype=float), np.asarray(faces, dtype=int)


def test_four_region_true_3d_shell_has_exactly_one_open_cuff_per_region():
    vertices, triangles = cube_with_four_one_cell_hoof_openings()
    report = draft_four_zone_shell(vertices, triangles, split_y_mm=0, cuff_size=4)
    assert report["source_triangles"] == len(triangles)
    assert report["source_original_open_boundary_edges"] == 16
    assert len(report["regions"]) == 4
    assert report["all_regions_single_connected_annuli_with_one_complete_hoof"]
    assert all(
        region["face_components_by_shared_edge"] == 1 for region in report["regions"]
    )
    assert all(
        region["contains_one_complete_expected_hoof_opening"] for region in report["regions"]
    )
    assert all(region["boundary_loop_count"] == 2 for region in report["regions"])
    assert all(region["euler_characteristic"] == 0 for region in report["regions"])
    assert {part["region_pair"] for part in report["seam_interfaces"]} == {
        "0:1", "0:2", "1:3", "2:3"
    }
    assert all(
        part["both_sides_use_identical_proxy_edges"] for part in report["seam_interfaces"]
    )
    assert not report["manufacturing_approved"]
    assert not report["real_2d_fabric_rest_shapes_generated"]


def test_face_assignments_are_complete_disjoint_and_in_original_face_order():
    vertices, triangles = cube_with_four_one_cell_hoof_openings()
    report = draft_four_zone_shell(vertices, triangles, split_y_mm=0, cuff_size=4)
    runs = report["face_region_label_rle"]
    assert runs[0][0] == 0
    assert runs[-1][1] == len(triangles)
    assert all(runs[i][1] == runs[i + 1][0] for i in range(len(runs) - 1))
    reconstructed = [
        label for start, end, label in runs for _ in range(end - start)
    ]
    assert len(reconstructed) == len(triangles)
    assert set(reconstructed) == {0, 1, 2, 3}
    assert report["total_shared_3d_seam_edges"] == len(report["seam_edges"])


def test_splitting_through_a_hoof_opening_is_not_approved():
    vertices, triangles = cube_with_four_one_cell_hoof_openings()
    report = draft_four_zone_shell(vertices, triangles, split_y_mm=1.5, cuff_size=4)
    assert not report["all_regions_single_connected_annuli_with_one_complete_hoof"]
    assert report["manufacturing_panel_count_approved"] == 0


@pytest.mark.parametrize("case", ("nan", "bad_index", "duplicate_face", "degenerate"))
def test_damaged_shell_input_is_refused(case):
    vertices, triangles = cube_with_four_one_cell_hoof_openings()
    if case == "nan":
        vertices[0, 0] = float("nan")
    elif case == "bad_index":
        triangles[0, 0] = len(vertices)
    elif case == "duplicate_face":
        triangles[0] = triangles[1]
    else:
        triangles[0, 0] = triangles[0, 1]
    with pytest.raises(ValueError):
        draft_four_zone_shell(vertices, triangles, split_y_mm=0, cuff_size=4)


def test_top_projection_svg_is_labeled_as_nonfabric_schematic():
    import xml.etree.ElementTree as ET

    vertices, triangles = cube_with_four_one_cell_hoof_openings()
    draft = draft_four_zone_shell(vertices, triangles, split_y_mm=0, cuff_size=4)
    svg = render_four_zone_seam_map(vertices, draft)
    root = ET.fromstring(svg)
    assert root.attrib["width"].endswith("mm")
    assert "NOT FABRIC CUT LINES" in svg
    lines = root.findall(".//{http://www.w3.org/2000/svg}line")
    assert len(lines) == draft["total_shared_3d_seam_edges"]
