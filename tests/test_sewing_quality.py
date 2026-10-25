"""Negative controls: seam closure must not masquerade as a correct sewn shape."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

MODULE=Path(__file__).resolve().parents[1]/"scripts"/"sewing_quality.py"
spec=importlib.util.spec_from_file_location("quality", MODULE)
quality=importlib.util.module_from_spec(spec)
spec.loader.exec_module(quality)


def joined_square():
    # Two quads, duplicated joining-edge vertices: a toy sewn surface
    a=np.array([
        [-.01,0,0], [0,0,0], [0,.01,0], [-.01,.01,0],
        [0,0,0], [.01,0,0], [.01,.01,0], [0,.01,0],
    ],dtype=float)
    rest=a[:,:2].copy()
    quads=np.array([[0,1,2,3],[4,5,6,7]],dtype=int)
    pair=np.array([[1,4],[2,7]],dtype=int)
    return a,rest,quads,pair


def test_perfect_seams_and_shape_have_zero_stretch():
    xyz,rest,faces,pairs=joined_square()
    d=quality.evaluate(xyz,rest,faces,pairs,xyz,xyz)
    assert d["status"]=="NUMERICAL_DIAGNOSTICS_NOT_MANUFACTURING_APPROVAL"
    assert d["seam"]["mean_gap_mm"]==pytest.approx(0,abs=1e-8)
    assert d["target_shape"]["rigid_aligned_correspondence_rms_mm"]==pytest.approx(0,abs=1e-8)
    assert d["strain"]["max_abs_principal_strain"]==pytest.approx(0,abs=1e-12)
    assert d["strain"]["area_3d_over_flat_rest"]==pytest.approx(1)
    assert d["strain"]["orientation_reversed_vs_initial"]==0


def test_false_pass_zero_gap_but_wrong_shape_and_strain():
    xyz,rest,faces,pairs=joined_square()
    distorted=xyz*1.25
    d=quality.evaluate(distorted,rest,faces,pairs,xyz,xyz)
    assert d["seam"]["max_gap_mm"]<1e-10
    assert d["target_shape"]["rigid_aligned_correspondence_rms_mm"]>1
    assert d["target_shape"]["symmetric_vertex_chamfer_mean_mm"]>1
    assert d["strain"]["p95_abs_principal_strain"]>0.2
    assert d["strain"]["area_3d_over_flat_rest"]==pytest.approx(1.5625)


def test_rigid_translation_is_not_shape_error_but_world_position_error():
    xyz,rest,faces,pairs=joined_square()
    shifted=xyz+np.array([.025,-.037,.009])
    d=quality.evaluate(shifted,rest,faces,pairs,xyz,xyz)
    assert d["seam"]["max_gap_mm"]<1e-10
    assert d["target_shape"]["rigid_aligned_correspondence_rms_mm"]<1e-8
    assert d["target_shape"]["unaligned_correspondence_rms_mm"]>40


def test_triangle_flip_warning_is_not_self_collision_claim():
    xyz,rest,faces,pairs=joined_square()
    flipped=xyz.copy()
    # Flip the second panel's winding by reflecting its y coordinates
    flipped[4:8,1]=.01-flipped[4:8,1]
    d=quality.evaluate(flipped,rest,faces,pairs,xyz,xyz)
    assert d["strain"]["orientation_reversed_vs_initial"]>=2
    assert any("self-intersection" in s or "intersections" in s for s in d["limitations"])


def test_refuse_unstable_or_undefined_inputs():
    xyz,rest,faces,pairs=joined_square()
    bad=xyz.copy()
    bad[0]=np.nan
    with pytest.raises(ValueError):
        quality.evaluate(bad,rest,faces,pairs,xyz,xyz)
    bad_rest=rest.copy()
    bad_rest[0]=bad_rest[1]
    with pytest.raises(ValueError):
        quality.evaluate(xyz,bad_rest,faces,pairs,xyz,xyz)
    with pytest.raises(ValueError):
        quality.evaluate(xyz,rest,faces,[[0,0]],xyz,xyz)
    with pytest.raises(ValueError):
        quality.evaluate(xyz,rest,faces,[[999,1]],xyz,xyz)
