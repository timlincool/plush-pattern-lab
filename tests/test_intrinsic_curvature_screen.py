"""Independent curvature tests include flat, dome and saddle disk geometry."""

import numpy as np
import pytest

from plush_pattern_lab.validation.intrinsic_curvature_screen import (
    audit_intrinsic_curvature,
)


def _disk(center_z=0, corner_z=(0, 0, 0, 0)):
    points = np.asarray(
        [
            [-1, -1, corner_z[0]],
            [1, -1, corner_z[1]],
            [1, 1, corner_z[2]],
            [-1, 1, corner_z[3]],
            [0, 0, center_z],
        ],
        dtype=float,
    )
    faces = np.asarray([[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]], dtype=int)
    return {
        "points_xyz_mm": points,
        "faces": faces,
        "boundary_edges": [[0, 1], [1, 2], [2, 3], [0, 3]],
        "source_vertex_ids": np.asarray([10, 11, 12, 13, 99]),
    }


def test_flat_disk_has_zero_interior_defect():
    report = audit_intrinsic_curvature(_disk())
    assert report["interior_vertex_count"] == 1
    assert report["excluded_cut_and_outer_boundary_vertices"] == 4
    assert report["abs_defect_degrees_p95"] == pytest.approx(0, abs=1e-9)
    assert report["exact_isometry_possible_with_uncut_interior"]
    assert not report["fabric_properties_or_manufacturing_approved"]


def test_dome_has_positive_intrinsic_defect():
    report = audit_intrinsic_curvature(_disk(center_z=1))
    assert report["positive_defect_over_threshold"] == 1
    assert report["negative_defect_below_minus_threshold"] == 0
    assert report["top_abs_defect_hotspots"][0]["source_vertex_id"] == 99
    assert not report["exact_isometry_possible_with_uncut_interior"]


def test_saddle_has_negative_intrinsic_defect():
    report = audit_intrinsic_curvature(_disk(corner_z=(1, -1, 1, -1)))
    assert report["negative_defect_below_minus_threshold"] == 1
    assert report["positive_defect_over_threshold"] == 0


@pytest.mark.parametrize("corruption", ["face", "boundary", "nan", "limit", "source"])
def test_corrupt_mesh_or_reporting_boundaries_rejected(corruption):
    disk = _disk()
    if corruption == "face":
        disk["faces"][0] = [0, 0, 4]
    elif corruption == "boundary":
        disk["boundary_edges"] = [[0, 1], [1, 2]]
    elif corruption == "nan":
        disk["points_xyz_mm"][4, 2] = np.nan
    elif corruption == "source":
        disk["source_vertex_ids"] = np.ones(5, dtype=float)
    with pytest.raises(ValueError):
        audit_intrinsic_curvature(disk, max_hotspots=0 if corruption == "limit" else 12)
