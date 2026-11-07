"""Front 3D depth is independent from historical 2D face feature proximity."""

import numpy as np
import pytest

from plush_pattern_lab.patterns.source_seam_view_svg import (
    render_source_seam_orthoview_svg,
)
from plush_pattern_lab.validation.seam_face_projection import (
    audit_front_paths,
    front_first_hit_y,
)


def _case():
    xy = np.asarray(
        [
            [-1, -10, 0],
            [1, -10, 0],
            [1, -10, 1],
            [-1, -10, 1],
            [-1, 10, 0],
            [1, 10, 0],
            [1, 10, 1],
            [-1, 10, 1],
        ],
        dtype=np.float64,
    )
    faces = np.asarray([[0, 1, 2], [0, 2, 3], [4, 5, 6], [4, 6, 7]])
    reference = {
        "revision": "surface14",
        "units": "mm",
        "eyes": [
            {
                "name": "near",
                "center_xz": [0, 0.5],
                "ellipse_radii_xz": [0.1, 0.1],
            }
        ],
        "y_nose_xz": [[-1, 0], [-1, 1]],
        "mouth_stem_xz": [[0, 1], [0, 0]],
        "mouth_left_xz": [[0, 0], [-0.5, 0.5]],
        "mouth_right_xz": [[0, 0], [0.5, 0.5]],
    }
    rows = [
        {"path_id": 0, "original_source_vertex_ids": [0, 3], "source_3d_length_mm": 1},
        {"path_id": 1, "original_source_vertex_ids": [4, 7], "source_3d_length_mm": 1},
        {"path_id": 2, "original_source_vertex_ids": [1, 2], "source_3d_length_mm": 1},
    ]
    return xy, faces, rows, reference


def test_actual_ray_direction_separates_front_surface_from_back_projection():
    xyz, faces, _, _ = _case()
    polygons = xyz[faces]
    assert front_first_hit_y(polygons, xyz[0]) == pytest.approx(-10)
    assert front_first_hit_y(polygons, xyz[4]) == pytest.approx(-10)
    assert front_first_hit_y(polygons, np.array([4, 0, 4])) is None


def test_historic_nose_projection_alert_requires_front_surface_depth():
    xyz, faces, rows, face = _case()
    report = audit_front_paths(xyz, faces, rows, face)
    front, back, other = report["routes"]
    assert front["source_front_near_side_vertex_count"] == 2
    assert front["historical_front_face_feature_alert_vertex_count"] == 2
    assert back["source_front_near_side_vertex_count"] == 0
    assert back["source_body_occluded_vertex_count"] == 2
    assert back["historical_front_face_feature_alert_vertex_count"] == 0
    assert not report["factory_approved_cut_patterns"]
    assert report["cloud_fur_eye_mesh_occlusion_not_tested"]
    assert other["source_3d_seam_length_mm"] == pytest.approx(1)


def test_five_view_overlay_is_source_proxy_not_final_design_registration():
    xyz, faces, rows, reference = _case()
    report = audit_front_paths(xyz, faces, rows, reference)
    svg = render_source_seam_orthoview_svg(xyz, report, reference)
    assert "NOT A CUTTING PATTERN" in svg
    assert "FRONT" in svg and "BACK" in svg and "TOP" in svg
    assert "Clouds, fleece, eye meshes" in svg
    assert "historic nose/mouth" in svg


@pytest.mark.parametrize("fault", ["bad_vertex", "wrong_length", "invalid_reference"])
def test_tampered_source_or_unbounded_reference_is_rejected(fault):
    xyz, faces, rows, reference = _case()
    if fault == "bad_vertex":
        rows[0]["original_source_vertex_ids"] = [0, 100]
    elif fault == "wrong_length":
        rows[0]["source_3d_length_mm"] = 100
    else:
        reference["revision"] = "unknown"
    with pytest.raises(ValueError):
        audit_front_paths(xyz, faces, rows, reference)
