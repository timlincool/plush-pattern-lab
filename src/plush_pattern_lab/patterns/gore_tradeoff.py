#!/usr/bin/env python3
"""Enumerate panel-count Pareto tradeoff: geometric distortion vs stitch/cut demand.

This is NOT a fabric feasibility decision until actual textile data are available.
"""
import argparse
import json
from pathlib import Path
from plush_pattern_lab.patterns.plush_gore_pattern import generate

def sweep(radius_mm=55., half_height_mm=70., segments=64,
          allowance_mm=6., candidates=(6,8,10,12,14,16),
          study_threshold=.10):
    if not .02<=study_threshold<=.30:
        raise ValueError("Study threshold outside 2..30%")
    if len(set(candidates))!=len(candidates) or len(candidates)<2:
        raise ValueError("Need nonduplicate candidate panel counts")
    options=[]
    for count in sorted(candidates):
        result=generate(radius_mm,half_height_mm,count,segments,allowance_mm)
        metrics=result["metrics"]
        options.append({
            "panels":count,
            "worst_principal_strain":metrics["worst_absolute_principal_strain"],
            "p95_principal_strain":metrics["p95_absolute_principal_strain"],
            "geometry_area_ratio":metrics["area_2d_over_3d"],
            "total_net_pattern_area_mm2":result["panel"]["net_area_mm2"]*count,
            "total_cut_outline_area_mm2":result["panel"]["cut_area_mm2"]*count,
            "total_sewing_length_mm":metrics["actual_seam_length_mm"]*count,
            "sewing_relation_count":len(result["sewing_pairs"]),
            "geometric_study_threshold_met":metrics["worst_absolute_principal_strain"]<=study_threshold,
        })
    feasible=[o for o in options if o["geometric_study_threshold_met"]]
    minimal=min(feasible,key=lambda x:x["panels"]) if feasible else None
    return {
        "status":"GEOMETRIC_PARETO_STUDY_NOT_MATERIAL_CALIBRATED",
        "study_threshold":study_threshold,
        "options":options,
        "fewest_panels_meeting_study_threshold":minimal["panels"] if minimal else None,
        "material_measured":False,
        "note":"Geometric principal strain is not a certified material allowable strain. "
               "Actual fabric, notches, seam tension and filling still unvalidated.",
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--radius-mm",type=float,default=55)
    p.add_argument("--half-height-mm",type=float,default=70)
    p.add_argument("--allowance-mm",type=float,default=6)
    p.add_argument("--study-threshold",type=float,default=.10)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError("Refuse to overwrite an existing result")
    result=sweep(a.radius_mm,a.half_height_mm,
                 allowance_mm=a.allowance_mm,study_threshold=a.study_threshold)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"selected":result["fewest_panels_meeting_study_threshold"],
                      "options":[{k:v for k,v in o.items() if k in
                                  ("panels","worst_principal_strain",
                                   "total_cut_outline_area_mm2","total_sewing_length_mm")}
                                  for o in result["options"]]},ensure_ascii=False))
if __name__=="__main__":
    main()
