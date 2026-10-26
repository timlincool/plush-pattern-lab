#!/usr/bin/env python3
"""Research-only axisymmetric plush gore with matched meridian seam segments."""
import argparse
import json
import math
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon

def generate(radius_mm=55., half_height_mm=70., panels=8, segments=64, allowance_mm=6.):
    if not (5 <= radius_mm <= 250 and 10 <= half_height_mm <= 500
            and 6 <= panels <= 24 and 24 <= segments <= 256
            and 0 <= allowance_mm <= 12):
        raise ValueError("Invalid pattern bounds")
    th = np.linspace(0, np.pi, segments + 1)
    r, z = radius_mm * np.sin(th), half_height_mm * np.cos(th)
    ds = np.hypot(np.diff(r), np.diff(z))
    w = r * np.pi / panels
    dw = np.diff(w)
    if np.any(ds * ds < dw * dw - 1e-9):
        raise ValueError("Width exceeds seam edge length")
    y = np.r_[0., np.cumsum(np.sqrt(np.maximum(0, ds * ds - dw * dw)))]
    left, right = np.c_[-w, y], np.c_[w, y]
    outline = Polygon(np.r_[left, right[::-1]])
    cut = outline.buffer(allowance_mm, join_style=1, quad_segs=12)
    if not outline.is_valid or outline.area <= 0 or cut.geom_type != "Polygon":
        raise ValueError("Invalid pattern/allowance geometry")
    strains, signs = [], []
    area3 = area2 = 0.
    for i in range(segments):
        angles = [(-1 + k) * math.pi / panels for k in range(3)]
        p = np.array([[r[j]*np.cos(a), r[j]*np.sin(a), z[j]]
                      for j in (i, i+1) for a in angles])
        q = np.array([[(-1+k)*w[j], y[j]]
                      for j in (i,i+1) for k in range(3)])
        for k in (0,1):
            for tri in ((k,k+3,k+4), (k,k+4,k+1)):
                e1,e2=p[tri[1]]-p[tri[0]],p[tri[2]]-p[tri[0]]
                t1,t2=q[tri[1]]-q[tri[0]],q[tri[2]]-q[tri[0]]
                a3=np.linalg.norm(np.cross(e1,e2))/2
                if a3<1e-8:continue
                cross2=float(np.linalg.det(np.c_[t1,t2]))
                u=e1/np.linalg.norm(e1)
                v=e2-np.dot(e2,u)*u
                B=np.array([[np.linalg.norm(e1),np.dot(e2,u)],
                            [0,np.linalg.norm(v)]])
                jac=np.c_[t1,t2]@np.linalg.inv(B)
                strains.extend(np.linalg.svd(jac,compute_uv=False)-1)
                signs.append(cross2)
                area2+=abs(cross2)/2
                area3+=a3
    strains=np.asarray(strains)
    cumul=np.r_[0.,np.cumsum(ds)]
    notches=sorted(set(int(np.argmin(abs(cumul-cumul[-1]*t))) for t in (.25,.5,.75)))
    return {
        "status":"UNVALIDATED_GEOMETRIC_RESEARCH_PATTERN", "units":"mm",
        "model":"synthetic axisymmetric ellipsoid",
        "parameters":dict(radius_mm=radius_mm,half_height_mm=half_height_mm,
                          panels=panels,segments=segments,allowance_mm=allowance_mm),
        "panel":{"seam_left":left.tolist(),"seam_right":right.tolist(),
                 "cut_outline":np.asarray(cut.exterior.coords).tolist(),
                 "grain_direction":[0,1],"notch_indices":notches,
                 "net_area_mm2":outline.area,"cut_area_mm2":cut.area},
        "sewing_pairs":[{"a":f"P{i:02d}.right",
                         "b":f"P{(i+1)%panels:02d}.left",
                         "notch_indices":notches} for i in range(panels)],
        "metrics":{
            "actual_seam_length_mm":float(ds.sum()),
            "left_right_seam_mismatch_mm":float(abs(
                np.linalg.norm(np.diff(left,axis=0),axis=1).sum()-
                np.linalg.norm(np.diff(right,axis=0),axis=1).sum())),
            "max_2d_vs_3d_seam_segment_error_mm":float(np.max(abs(
                np.linalg.norm(np.diff(left,axis=0),axis=1)-ds))),
            "worst_absolute_principal_strain":float(np.max(abs(strains))),
            "p95_absolute_principal_strain":float(np.quantile(abs(strains),.95)),
            "area_2d_over_3d":float(area2/area3),
            "reversed_or_degenerate_triangles":int(np.count_nonzero(np.asarray(signs)>=0)),
            "material_measured":False,"2d_to_3d_sewing_simulated":False,
            "stuffing_physically_calibrated":False},
        "limitations":[
            "Analytic ellipsoid gore demo, not a reverse engineered alpaca.",
            "Seam matching does not prove sewability.",
            "No measured fabric, embroidery or stuffing data."]
    }

def svg(spec):
    pts=np.asarray(spec["panel"]["cut_outline"])
    x0,y0=pts.min(axis=0)
    x1,y1=pts.max(axis=0)
    W,H=x1-x0+28,y1-y0+38
    def path(data):
        return " ".join(f"{x-x0+14:.3f},{y-y0+20:.3f}" for x,y in data)
    left,right=path(spec["panel"]["seam_left"]),path(spec["panel"]["seam_right"])
    dots=[]
    for i in spec["panel"]["notch_indices"]:
        for k in ("seam_left","seam_right"):
            x,y=spec["panel"][k][i]
            dots.append(f'<circle cx="{x-x0+14:.3f}" cy="{y-y0+20:.3f}" r="1" fill="#c64"/>')
    n=spec["parameters"]["panels"]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W:.2f}mm" height="{H:.2f}mm" viewBox="0 0 {W:.2f} {H:.2f}">
<style>.cut{{fill:#f6f9fb;stroke:#354453;stroke-width:.4}}.stitch{{fill:none;stroke:#1977a2;stroke-width:.3;stroke-dasharray:2 1}}text{{font:4px sans-serif}}</style>
<text x="14" y="10">Research only - not a production pattern</text>
<polygon class="cut" points="{path(pts)}"/>
<polyline class="stitch" points="{left}"/>
<polyline class="stitch" points="{right}"/>
{''.join(dots)}
<text x="14" y="{H-7:.2f}">Repeat {n} panels. Long axis = grain direction.</text>
</svg>
"""

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--radius-mm",type=float,default=55)
    p.add_argument("--half-height-mm",type=float,default=70)
    p.add_argument("--panels",type=int,default=8)
    p.add_argument("--segments",type=int,default=64)
    p.add_argument("--allowance-mm",type=float,default=6)
    p.add_argument("--out-prefix",type=Path,required=True)
    a=p.parse_args()
    result=generate(a.radius_mm,a.half_height_mm,a.panels,a.segments,a.allowance_mm)
    j,s=a.out_prefix.with_suffix(".json"),a.out_prefix.with_suffix(".svg")
    if j.exists() or s.exists():
        raise FileExistsError("Refuse to overwrite outputs")
    j.parent.mkdir(parents=True,exist_ok=True)
    j.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    s.write_text(svg(result))
    print(json.dumps(result["metrics"],indent=2))
if __name__=="__main__":
    main()
