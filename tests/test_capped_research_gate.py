import importlib.util
from pathlib import Path

P=Path(__file__).resolve().parents[1]/"scripts"/"assess_research_candidate.py"
m=importlib.util.module_from_spec(importlib.util.spec_from_file_location("capgate",P))
m.__loader__.exec_module(m)


def capped_report(flips,p95):
    return {
        "status":"ACTUAL_CAPPED_CLOTH_SEWING_RESEARCH_ONLY",
        "panels":12,"prepositioning":"analytic target assisted, gores offset 3mm",
        "analytical_stitch_weld_topology":{
            "status":"ANALYTICAL_WELDED_PROXY_NOT_A_PHYSICAL_CLOTH_SHELL",
            "research_topological_sphere_screen_pass":True},
        "final_geometry_quality":{
            "status":"NUMERICAL_DIAGNOSTICS_NOT_MANUFACTURING_APPROVAL",
            "seam":{"mean_gap_mm":.001,"max_gap_mm":.003},
            "target_shape":{"rigid_aligned_correspondence_rms_mm":.4},
            "strain":{"p95_abs_principal_strain":p95,
                      "orientation_reversed_vs_initial":flips,
                      "near_zero_area_triangles":0}}}


def test_cap_study_gate_cannot_hide_flips():
    r=m.assess(capped_report(1,.08))
    assert not r["passed"]
    assert r["status"]=="RESEARCH_CANDIDATE_REJECTED"
    assert r["failed_checks"][0]["metric"]=="orientation_reversals_max"


def test_cap_study_gate_cannot_ignore_excess_strain():
    r=m.assess(capped_report(0,.1325))
    assert not r["passed"]
    assert r["failed_checks"][0]["metric"]=="principal_strain_p95_max"


def test_cap_study_gate_passes_only_research_geometry():
    r=m.assess(capped_report(0,.07))
    assert r["passed"]
    assert r["panel_count"]==12
    assert r["target_assisted_prepositioning"]
    assert r["noncertified_requirements"]


def test_study_gate_cannot_promote_closed_gap_with_open_welded_topology():
    case=capped_report(0,.07)
    case["analytical_stitch_weld_topology"]["research_topological_sphere_screen_pass"]=False
    result=m.assess(case)
    assert not result["passed"]
    assert [f["metric"] for f in result["failed_checks"]]==[
        "topological_sphere_proxy_required"]


def test_study_gate_must_not_accept_missing_weld_evidence():
    case=capped_report(0,.07)
    del case["analytical_stitch_weld_topology"]
    result=m.assess(case)
    assert not result["passed"]
