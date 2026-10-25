#!/usr/bin/env python3
"""Validate measured directional fabric swatch curves (engineering research, not stuffing FEM)."""
import argparse, json
from pathlib import Path
import numpy as np

def phase(points,gauge,kind):
    p=np.asarray(points,dtype=float)
    if p.ndim!=2 or p.shape[1]!=2 or len(p)<4 or not np.isfinite(p).all():
        raise ValueError("Missing finite length_mm,force_N samples")
    length,force=p[:,0],p[:,1]
    if np.any(force < -1e-9) or np.any(length < gauge-1e-8):
        raise ValueError("Negative force or below-gauge length")
    if kind=="loading" and not np.all(np.diff(length)>0):
        raise ValueError("Loading lengths must strictly increase")
    if kind=="unloading" and not np.all(np.diff(length)<0):
        raise ValueError("Unloading lengths must strictly decrease")
    return np.c_[(length-gauge)/gauge,force]

def calculate(spec):
    if spec.get("schema")!="plush-material-swatches-v1":
        raise ValueError("Unsupported schema")
    origin=spec.get("data_origin")
    if origin not in ("synthetic_demo","measured"):
        raise ValueError("Explicit provenance required")
    material=spec.get("material",{})
    for key in ("material_id","batch","fabric_type","test_condition"):
        if not isinstance(material.get(key),str) or not material[key].strip():
            raise ValueError("Missing material provenance: "+key)
    for key in ("mass_gsm","thickness_mm","pile_height_mm"):
        v=material.get(key)
        if not isinstance(v,(int,float)) or not np.isfinite(v) or v<=0:
            raise ValueError("Invalid "+key)
    if material["mass_gsm"]>2500 or material["thickness_mm"]>25:
        raise ValueError("Check material units")
    result={}
    for axis in ("warp","weft"):
        t=spec.get("tests",{}).get(axis)
        if not isinstance(t,dict):raise ValueError("Both directions required")
        gauge,width=t.get("gauge_length_mm"),t.get("width_mm")
        if not isinstance(gauge,(int,float)) or not 20<=gauge<=500:
            raise ValueError("Gauge must be 20..500 mm")
        if not isinstance(width,(int,float)) or not 5<=width<=300:
            raise ValueError("Width must be 5..300 mm")
        up=phase(t.get("loading",[]),gauge,"loading")
        down=phase(t.get("unloading",[]),gauge,"unloading")
        if abs(up[0,0])>1e-10 or not .04<=up[-1,0]<=.8:
            raise ValueError("Missing zero or ≥4% loading endpoint")
        if abs(up[-1,0]-down[0,0])>1e-6 or abs(down[-1,0])>1e-6:
            raise ValueError("Loading and unloading endpoints differ")
        if up[0,1]>.05 or down[-1,1]>.05 or up[-1,1]<=0:
            raise ValueError("End-point forces nonphysical")
        lo,hi=.02,min(.10,up[-1,0])
        if hi<=lo:raise ValueError("Insufficient calibration strain range")
        force_low=np.interp(lo,up[:,0],up[:,1])
        force_high=np.interp(hi,up[:,0],up[:,1])
        stiffness=(force_high-force_low)/(hi-lo)/(width/1000.)
        if stiffness<=0:raise ValueError("Nonpositive stiffness")
        grid=np.linspace(0,up[-1,0],401)
        loading=np.interp(grid,up[:,0],up[:,1])
        unloading=np.interp(grid,down[::-1,0],down[::-1,1])
        work_load=float(np.trapezoid(loading,grid)*gauge/1000.)
        work_unload=float(np.trapezoid(unloading,grid)*gauge/1000.)
        hysteresis=(work_load-work_unload)/work_load
        if not -.01<=hysteresis<=1:
            raise ValueError("Invalid unload hysteresis")
        result[axis]={
            "gauge_mm":gauge,"width_mm":width,
            "max_engineering_strain":float(up[-1,0]),
            "secant_window":[lo,hi],
            "effective_tensile_stiffness_N_per_m":float(stiffness),
            "loading_work_J":work_load,"unloading_work_J":work_unload,
            "hysteresis_ratio":float(hysteresis)}
    return {
        "status":"SWATCH_CURVES_VALIDATED_NOT_STUFFING_CALIBRATED",
        "data_origin":origin,"material_id":material["material_id"],
        "batch":material["batch"],"material_measured":origin=="measured",
        "warp_weft_stiffness_ratio":float(
            result["warp"]["effective_tensile_stiffness_N_per_m"]/
            result["weft"]["effective_tensile_stiffness_N_per_m"]),
        "axes":result,"limits":[
            "Slope per sample width, not an elastic modulus or a Blender preset",
            "Cannot infer bending, shear, embroidery or polyester stuffing compression",
            "Measurement provenance supplied by user; not independently certified"]}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if a.output.exists() or not a.input.is_file():
        raise FileExistsError("Input missing or output already exists")
    result=calculate(json.loads(a.input.read_text()))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__":
    main()
