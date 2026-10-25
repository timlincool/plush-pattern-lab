"""Promotion gate for *research* cloth candidates; never a product safety certificate.

A successful Blender simulation run is not an accepted shape. This module
separates execution success from geometric acceptance; selected/released
patterns must explicitly pass all declared study bounds.
"""
import argparse
import json
import math
from pathlib import Path

STUDY_LIMITS = {
    "seam_mean_gap_mm_max": 0.10,
    "seam_max_gap_mm_max": 1.00,
    "aligned_target_rms_mm_max": 2.00,
    "principal_strain_p95_max": 0.10,
    "orientation_reversals_max": 0,
    "zero_area_triangles_max": 0,
}


def assess(report, limits=STUDY_LIMITS):
    supported={
        "ACTUAL_CLOTH_SEWING_SPRINGS_NUMERICAL_TRIAL",
        "ACTUAL_CAPPED_CLOTH_SEWING_RESEARCH_ONLY",
    }
    if report.get("status") not in supported:
        raise ValueError("Unknown trial report status")
    q=report.get("final_geometry_quality")
    if not isinstance(q,dict) or q.get("status")!="NUMERICAL_DIAGNOSTICS_NOT_MANUFACTURING_APPROVAL":
        raise ValueError("Missing independently defined shape/strain metrics")
    shape=q["target_shape"]
    strain=q["strain"]
    seam=q["seam"]
    observed={
        "seam_mean_gap_mm_max":seam["mean_gap_mm"],
        "seam_max_gap_mm_max":seam["max_gap_mm"],
        "aligned_target_rms_mm_max":shape["rigid_aligned_correspondence_rms_mm"],
        "principal_strain_p95_max":strain["p95_abs_principal_strain"],
        "orientation_reversals_max":strain["orientation_reversed_vs_initial"],
        "zero_area_triangles_max":strain["near_zero_area_triangles"],
    }
    failed=[]
    for name,bound in limits.items():
        value=observed[name]
        if not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
            raise ValueError("Nonfinite or invalid diagnostic: "+name)
        if value>bound:
            failed.append({"metric":name, "measured":float(value), "study_limit":float(bound)})
    return {
        "status":"RESEARCH_CANDIDATE_REJECTED" if failed else "RESEARCH_GEOMETRY_SCREEN_PASSED",
        "placement":report.get("preposition_mode",report.get("prepositioning")),
        "target_assisted_prepositioning":bool(
            report.get("reference_assisted_initialization",
                       report.get("status")=="ACTUAL_CAPPED_CLOTH_SEWING_RESEARCH_ONLY")),
        "panel_count":report.get("synthetic_panel_count",report.get("panels")),
        "passed":not failed,
        "limits":dict(limits),
        "observed":observed,
        "failed_checks":failed,
        "noncertified_requirements":[
            "No guarantee of a watertight top/bottom closure or collision-free assembled surface",
            "No measured textile grain, bending, embroidery, sewing strength or filling",
            "Synthetic correspondence/rigid alignment not a real plush likeness check",
            "These thresholds are engineering study defaults, NOT fabric limits",
        ]
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--require-pass",action="store_true",
                   help="Exit 2 on rejected candidate; for explicit selection/promotion only")
    a=p.parse_args()
    if not a.report.is_file() or a.output.exists() or a.report.resolve()==a.output.resolve():
        raise RuntimeError("Source missing or would overwrite a report")
    decision=assess(json.loads(a.report.read_text(encoding="utf8")))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(decision,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"status":decision["status"],"failed_checks":decision["failed_checks"]},
                     ensure_ascii=False))
    if a.require_pass and not decision["passed"]:
        raise SystemExit(2)


if __name__=="__main__":
    main()
