"""Small pure-Python negative controls for the R5 side-head lobe experiment."""

from __future__ import annotations

import numpy as np
import pytest
from shapely.geometry import Polygon

from research.stage6_b24_r5.audit_r5_side_lobes import comparison
from research.stage6_b24_r5.build_r5_side_lobes import (
    _cap_clearances,
    _cap_with_two_real_openings,
    _fabric_unfold_gore,
    _load_inputs,
    _make_hole,
    _resample_source_loop,
)


def _ellipse_outer():
    theta = np.linspace(0, 2 * np.pi, 64, endpoint=False)
    return np.column_stack((34 * np.cos(theta), -47 + 22 * np.sin(theta)))


def test_r5_two_head_ports_keep_sewing_clearance():
    outer = _ellipse_outer()
    holes = [_make_hole(-10), _make_hole(10)]
    _, border, between = _cap_clearances(outer, holes)
    assert border > 12.7 and between > 12.7


def test_r5_rejects_overlap_between_two_ports():
    outer = _ellipse_outer()
    hole = _make_hole(-10)
    with pytest.raises(ValueError, match="allowances|topology"):
        _cap_clearances(outer, [hole, hole.copy()])


def test_r5_cdt_crown_keeps_original_center_and_two_real_holes():
    pos = np.zeros((2699, 3))
    outer = _ellipse_outer()
    holes = [_make_hole(-10), _make_hole(10)]
    pos[876:940, :2] = outer * .001
    pos[940, :2] = [0, -.047]
    pos[940, 2] = .236
    pos[2635:2667, :2] = holes[0] * .001
    pos[2667:2699, :2] = holes[1] * .001
    faces, border, gap = _cap_with_two_real_openings(
        {"initial_3d_prepositioned_vertices_m": pos}, holes, 2635
    )
    assert len(faces) == 132 and border > 12.7 and gap > 12.7
    assert any(940 in face for face in faces)
    assert set.union(*(set(face) for face in faces)) == (
        set(range(876, 941)) | set(range(2635, 2699))
    )


def test_r5_source_ring_resampling_is_ccw_and_keeps_32_stations():
    theta = np.linspace(0, 2 * np.pi, 73, endpoint=False)
    coords = np.column_stack((51 + 7 * np.cos(theta), -43 + 4 * np.sin(theta)))
    sampled = _resample_source_loop(Polygon(coords), 32)
    assert sampled.shape == (32, 2)
    assert Polygon(sampled).is_valid and Polygon(sampled).exterior.is_ccw


def test_r5_narrow_gore_both_sides_retain_true_3d_lengths():
    xyz = []
    t = np.linspace(0, np.pi / 2, 9)
    for z, x, w in ((230, 12, 2), (240, 30, 5), (230, 55, 8),
                    (235, 58, 7), (245, 61, 4)):
        xyz.append(np.column_stack((x + w * np.cos(t), -45 + w * np.sin(t),
                                     np.full(9, z))))
    arc = np.asarray(xyz)
    uv = _fabric_unfold_gore(arc)
    for index in (0, -1):
        a = np.linalg.norm(np.diff(arc[:, index, :], axis=0), axis=1)
        b = np.linalg.norm(np.diff(uv[:, index, :], axis=0), axis=1)
        assert np.max(abs(a - b)) < 1e-4


def test_r5_rejects_unverified_prior_geometry(tmp_path):
    r3 = tmp_path / "bad_r3.npz"
    source = tmp_path / "bad_source.ply"
    r3.write_bytes(b"not the pinned original R3")
    source.write_bytes(b"not the true Stage6 source")
    with pytest.raises(ValueError, match="unverified"):
        _load_inputs(r3, source)


def test_r5_netline_mutation_canary():
    uv = np.array([[0, 0], [1, 0], [2, 0], [2, 2], [3, 2], [4, 2]], float)
    assert comparison(uv, [0, 1, 2], [3, 4, 5]) == 0
    uv[5, 0] += 0.5
    assert comparison(uv, [0, 1, 2], [3, 4, 5]) > 1e-4
