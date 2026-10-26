"""Blender-native negative controls for the finite intersection witness screen."""
import argparse
import json
import sys
from pathlib import Path
from plush_pattern_lab.blender.audit_self_intersections_blender import audit_geometry


def run():
    parser=argparse.ArgumentParser()
    parser.add_argument("--report",type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    if args.report.exists():
        raise RuntimeError("Refusing to overwrite earlier evidence")
    ground=[(-1.0,-1.0,0.0),(1.0,-1.0,0.0),(0.0,1.0,0.0)]
    crossing=[(0.0,-0.5,-1.0),(0.0,-0.5,1.0),(0.0,0.8,0.5)]
    separated=[(0.0,-0.5,2.0),(0.0,-0.5,3.0),(0.0,0.8,2.5)]
    tri=[(0,1,2),(3,4,5)]
    hit=audit_geometry(ground+crossing,tri)
    miss=audit_geometry(ground+separated,tri)
    seam=audit_geometry(ground+crossing,tri,[(0,3)])
    adjacent=audit_geometry(
        [(-1.0,-1.0,0.0),(1.0,-1.0,0.0),(0.0,1.0,0.0),(0.0,-2.0,0.0)],
        [(0,1,2),(1,0,3)])
    if hit["nonadjacent_other_pair_count"]<1:
        raise RuntimeError("Canary missed deliberate interior nonadjacent crossing")
    if miss["nonadjacent_total_intersections"]!=0:
        raise RuntimeError("Canary reported intersection in separated triangles")
    if seam["nonadjacent_seam_related_pair_count"]<1:
        raise RuntimeError("Canary failed to classify sewn identity relation")
    if adjacent["nonadjacent_total_intersections"]!=0:
        raise RuntimeError("Canary counted neighboring triangles as penetration")
    result={
        "status":"BVH_TRIANGLE_NEGATIVE_CONTROLS_PASS",
        "positive_crossing":hit["nonadjacent_other_pair_count"],
        "separated":miss["nonadjacent_total_intersections"],
        "seam_related":seam["nonadjacent_seam_related_pair_count"],
        "adjacent":adjacent["nonadjacent_total_intersections"],
        "limits":"Finite zero-thickness triangles; intentionally not coplanar-degeneracy proof"
    }
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf8")
    print("BVH_TRIANGLE_CANARY_PASS",json.dumps(result),flush=True)


if __name__=="__main__":
    run()
