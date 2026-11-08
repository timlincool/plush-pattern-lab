"""Full-scene five-view drawing remains a research witness, not cut geometry."""

import numpy as np
import pytest

from plush_pattern_lab.patterns.full_scene_seam_visibility_svg import (
    render_product_mesh_five_view_svg,
)
from plush_pattern_lab.validation.full_scene_seam_visibility import VIEWS


def _synthetic_svg_case():
    points = np.array(
        [[-2, -2, 0], [2, -2, 0], [2, 2, 2], [-2, 2, 2]],
        dtype=np.float64,
    )
    one = {
        "original_source_xyz_mm": [-2, -2, 0],
        "classification": "near_original_body_first_surface",
        "historic_face_v14_alert": False,
    }
    two = {
        "original_source_xyz_mm": [2, -2, 2],
        "classification": "occluded_by_another_product_mesh",
        "historic_face_v14_alert": True,
    }
    views = [
        {
            "view": name,
            "paths": [
                {
                    "samples": [one, two],
                    "classifications": {"near_original_body_first_surface": 1},
                    "other_mesh_occluded_count": 1,
                    "unresolved_or_no_hit_count": 0,
                }
                for _ in range(3)
            ],
        }
        for name, _, _, _ in VIEWS
    ]
    report = {
        "schema": "stage6-original-full-41-product-mesh-source-seam-occlusion-v1",
        "product_meshes_raytested": 41,
        "view_results": views,
    }
    historic = {
        "revision": "surface14",
        "eyes": [{"center_xz": [0, 1], "ellipse_radii_xz": [0.5, 0.5]}],
        "y_nose_xz": [[0, 0], [0, 1]],
        "mouth_stem_xz": [[0, 1], [0, 2]],
        "mouth_left_xz": [[0, 1], [-1, 1]],
        "mouth_right_xz": [[0, 1], [1, 1]],
    }
    return points, report, historic


def test_full_scene_svg_has_independent_views_and_clear_research_limits():
    xyz, report, historic = _synthetic_svg_case()
    svg = render_product_mesh_five_view_svg(xyz, report, historic)
    assert svg.count("PRODUCT RAW MESH FIRST-HIT") == 5
    assert "FRONT" in svg and "BACK" in svg and "TOP" in svg
    assert "NO APPROVED FABRIC CUTTING PATTERNS" in svg
    assert "Other Mesh occlusion is NOT a verified hidden manufacturing stitch" in svg
    assert "historic eye/nose/mouth alert" in svg
    assert svg.count("<svg ") == 1


@pytest.mark.parametrize("failure", ["nan", "missing_view", "wrong_mesh", "historic"])
def test_source_linked_scene_view_svg_rejects_malformed_evidence(failure):
    xyz, report, historic = _synthetic_svg_case()
    if failure == "nan":
        xyz[0, 2] = float("nan")
    elif failure == "missing_view":
        report["view_results"] = report["view_results"][:-1]
    elif failure == "wrong_mesh":
        report["product_meshes_raytested"] = 40
    else:
        historic["revision"] = "unverified"
    with pytest.raises(ValueError):
        render_product_mesh_five_view_svg(xyz, report, historic)
