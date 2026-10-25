import importlib.util
import json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("mat",ROOT/"scripts/material_calibration.py")
mat=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mat)
def sample():
    return json.loads((ROOT/"examples/synthetic_swatches.json").read_text())

def test_anisotropic_synthetic_curve_is_not_real_material():
    r=mat.calculate(sample())
    assert r["data_origin"]=="synthetic_demo"
    assert r["material_measured"] is False
    assert r["warp_weft_stiffness_ratio"]>2
    assert 0<r["axes"]["warp"]["hysteresis_ratio"]<1

def test_refuse_missing_provenance_and_wrong_unit():
    s=sample();s["data_origin"]="unverified"
    with pytest.raises(ValueError):mat.calculate(s)
    s=sample();s["material"]["mass_gsm"]=220000
    with pytest.raises(ValueError):mat.calculate(s)

def test_refuse_mismatched_loading_unloading_endpoints():
    s=sample();s["tests"]["weft"]["unloading"][0][0]=114
    with pytest.raises(ValueError):mat.calculate(s)

def test_cli_non_overwrite(tmp_path):
    import subprocess
    import sys
    input=tmp_path/"swatch.json";input.write_text(json.dumps(sample()))
    out=tmp_path/"report.json"
    cmd=[sys.executable,str(ROOT/"scripts/material_calibration.py"),
         "--input",str(input),"--output",str(out)]
    assert subprocess.run(cmd,capture_output=True).returncode==0
    assert subprocess.run(cmd,capture_output=True).returncode!=0
