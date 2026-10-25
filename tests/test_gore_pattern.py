import importlib.util
from pathlib import Path
import pytest

SOURCE=Path(__file__).resolve().parents[1]/"scripts"/"plush_gore_pattern.py"
module=importlib.util.module_from_spec(importlib.util.spec_from_file_location("gore",SOURCE))
module.__loader__.exec_module(module)

def test_seam_correspondence_and_segment_lengths():
    out=module.generate(55,70,8,64,6)
    metric=out["metrics"]
    assert len(out["sewing_pairs"])==8
    assert metric["max_2d_vs_3d_seam_segment_error_mm"]<1e-7
    assert metric["left_right_seam_mismatch_mm"]<1e-7
    for i, pair in enumerate(out["sewing_pairs"]):
        assert pair["a"]==f"P{i:02d}.right"
        assert pair["b"]==f"P{(i+1)%8:02d}.left"
        assert pair["notch_indices"]==out["panel"]["notch_indices"]

def test_reports_geometric_strain_not_manufacturing_approval():
    d=module.generate()["metrics"]
    assert 0 < d["worst_absolute_principal_strain"] < .2
    assert .96 < d["area_2d_over_3d"] < 1.03
    assert d["reversed_or_degenerate_triangles"] == 0
    assert d["material_measured"] is False
    assert d["2d_to_3d_sewing_simulated"] is False

def test_output_non_destructive(tmp_path):
    import subprocess
    import sys
    out=tmp_path/"gore"
    cmd=[sys.executable,str(SOURCE),"--out-prefix",str(out)]
    assert subprocess.run(cmd,capture_output=True).returncode==0
    assert out.with_suffix(".json").exists() and out.with_suffix(".svg").exists()
    assert subprocess.run(cmd,capture_output=True).returncode!=0

def test_reject_invalid_panels_and_seam_allowance():
    with pytest.raises(ValueError): module.generate(panels=2)
    with pytest.raises(ValueError): module.generate(allowance_mm=30)
