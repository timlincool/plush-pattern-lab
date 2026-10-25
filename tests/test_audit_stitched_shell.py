"""Topological closure checks must reject almost-closed/doubled-up cloth."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

p=Path(__file__).resolve().parents[1]/"scripts"/"audit_stitched_shell.py"
spec=importlib.util.spec_from_file_location("weld",p)
weld=importlib.util.module_from_spec(spec)
spec.loader.exec_module(weld)


def cube():
    v=np.array([
        [-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],
        [-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1],
    ],dtype=float)
    f=np.array([
        [0,3,2,1],[4,5,6,7],[0,1,5,4],
        [1,2,6,5],[2,3,7,6],[3,0,4,7]
    ],dtype=int)
    return v,f


def test_closed_oriented_shell_has_euler_two_and_positive_volume():
    v,f=cube()
    d=weld.inspect_welded_shell(v,f,[])
    assert d["research_topological_sphere_screen_pass"]
    assert d["euler_characteristic"]==2
    assert d["connected_components"]==1
    assert d["boundary_edges"]==0
    assert d["inconsistent_edge_winding"]==0
    assert d["signed_volume_l"]==pytest.approx(8000)


def test_unpaired_seam_is_a_topological_hole_even_at_zero_gap():
    v,f=cube()
    v=np.r_[v,v[[4,5]]]
    f=f.copy()
    f[1]=[8,9,6,7]  # top face has duplicated coordinates, not matching vertex IDs
    d=weld.inspect_welded_shell(v,f,[])
    assert not d["research_topological_sphere_screen_pass"]
    assert d["boundary_edges"]>0
    assert d["euler_characteristic"]!=2 or d["boundary_edges"]>0
    fixed=weld.inspect_welded_shell(v,f,[[8,4],[9,5]])
    assert fixed["research_topological_sphere_screen_pass"]
    assert fixed["max_pair_gap_mm"]==pytest.approx(0)


def test_reversed_face_winding_fails_even_without_boundaries():
    v,f=cube()
    f=f.copy()
    f[1]=f[1][::-1]
    d=weld.inspect_welded_shell(v,f,[])
    assert d["boundary_edges"]==0
    assert d["inconsistent_edge_winding"]>0
    assert not d["research_topological_sphere_screen_pass"]


def test_wrong_merging_creates_degenerate_faces():
    v,f=cube()
    d=weld.inspect_welded_shell(v,f,[[0,1]])
    assert d["faces_collapsed_by_weld"]>0
    assert not d["research_topological_sphere_screen_pass"]


def test_unconnected_vertex_component_fails():
    v,f=cube()
    v=np.r_[v,[[10,10,10]]]
    d=weld.inspect_welded_shell(v,f,[])
    assert not d["research_topological_sphere_screen_pass"]
    assert d["unused_vertex_classes"]==1


def test_reject_invalid_arrays_and_sewing_pairs():
    v,f=cube()
    with pytest.raises(ValueError):
        weld.inspect_welded_shell(v,np.array([[1,2,99,4]]),[])
    with pytest.raises(ValueError):
        weld.inspect_welded_shell(v,f,[[3,3]])
    with pytest.raises(ValueError):
        weld.inspect_welded_shell(v,f,[[0,-1]])
    vv=v.copy();vv[0,0]=np.nan
    with pytest.raises(ValueError):
        weld.inspect_welded_shell(vv,f,[])
