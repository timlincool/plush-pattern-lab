#!/usr/bin/env python3
"""Plot *research-only* net stitch lines and tentative cut outlines in real mm SVG.

One gore is repeated N times; upper/lower caps are distinct. Uses only
numeric geometry already verified by capped_gore_pattern.py. Never marks the
SVG production-ready or claims actual fabric grain/calibration.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def _points(values, name):
    array=np.asarray(values,dtype=float)
    if array.ndim!=2 or array.shape[1]!=2 or len(array)<3:
        raise ValueError(name+": expected numeric Nx2")
    if not np.isfinite(array).all() or np.max(abs(array))>10000:
        raise ValueError(name+": invalid coordinates")
    return array


def draw(spec):
    if spec.get("schema")!="synthetic-capped-plush-pattern-v1":
        raise ValueError("Only audited synthetic cap pattern schema supported")
    n=int(spec["parameters"]["panels"])
    allowance=float(spec["parameters"]["allowance_mm"])
    if not 6<=n<=24 or not 0<=allowance<=12:
        raise ValueError("Unexpected panel count or allowance")
    pieces=[
        {"name":f"GORES x{n}",
         "cut":_points(spec["gore"]["cut_outline_2d_mm"],"gore cut"),
         "stitch":np.vstack((_points(spec["gore"]["left_stitch_2d_mm"],"gore left"),
                              _points(spec["gore"]["right_stitch_2d_mm"],"gore right")[::-1])),
         "label":"Grain direction is a hypothesis"},
        {"name":"UPPER CAP x1",
         "cut":_points(spec["caps"]["upper"]["cut_outline_2d_mm"],"upper cut"),
         "stitch":_points(spec["caps"]["upper"]["stitch_ring_2d_mm"],"upper stitch"),
         "label":"Join top of each gore"},
        {"name":"LOWER CAP x1",
         "cut":_points(spec["caps"]["lower"]["cut_outline_2d_mm"],"lower cut"),
         "stitch":_points(spec["caps"]["lower"]["stitch_ring_2d_mm"],"lower stitch"),
         "label":"Join bottom of each gore"},
    ]
    dims=[]
    for piece in pieces:
        mn=piece["cut"].min(axis=0)
        mx=piece["cut"].max(axis=0)
        dims.append((mn,mx,mx-mn))
    # Actual millimetres, no viewport-only scaling: printable with 100% scale.
    margin=18.0
    gore_width,gore_height=dims[0][2]
    cap_width=max(dims[1][2][0],dims[2][2][0])
    cap_stack=dims[1][2][1]+dims[2][2][1]+24.0
    width=float(3*margin+gore_width+cap_width)
    height=float(max(gore_height+2*margin+16,cap_stack+2*margin+16))
    origins=[
        np.array((margin,margin+14)),
        np.array((2*margin+gore_width,margin+14)),
        np.array((2*margin+gore_width,margin+14+dims[1][2][1]+24)),
    ]

    def coords(p,idx):
        # Top-left align each cut bounding box; no geometry alteration.
        q=p-dims[idx][0]+origins[idx]
        return " ".join(f"{x:.3f},{y:.3f}" for x,y in q)

    parts=[
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.3f}mm" height="{height:.3f}mm" viewBox="0 0 {width:.3f} {height:.3f}">',
        '<style>.cut{stroke:#253649;stroke-width:0.38;fill:#f3f7f8}.stitch{stroke:#1579a5;stroke-width:0.30;fill:none;stroke-dasharray:2 1}text{font-family:Arial,sans-serif;fill:#203448}</style>',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="9" y="10" font-size="4">RESEARCH ONLY - NOT APPROVED</text>',
        '<text x="9" y="15" font-size="3.2">No approved sewing / fabric / fill</text>'
    ]
    for i,piece in enumerate(pieces):
        parts.append(f'<polygon class="cut" points="{coords(piece["cut"],i)}"/>')
        parts.append(f'<polygon class="stitch" points="{coords(piece["stitch"],i)}"/>')
        parts.append(f'<text x="{origins[i][0]:.2f}" y="{origins[i][1]-4:.2f}" font-size="4">{piece["name"]}</text>')
    # Draw only *reference* notches on stitch edges, not unverified cut notches.
    gores=spec["gore"]
    left=_points(gores["left_stitch_2d_mm"],"gore left")
    right=_points(gores["right_stitch_2d_mm"],"gore right")
    for arr in (left,right):
        idxs=(len(arr)//4,len(arr)//2,3*len(arr)//4)
        for idx in idxs:
            xx,yy=arr[idx]-dims[0][0]+origins[0]
            parts.append(f'<circle cx="{xx:.3f}" cy="{yy:.3f}" r="0.9" fill="#c54a38"/>')
    for k in (1,2):
        ring=pieces[k]["stitch"]
        for idx in range(0,len(ring),2):
            xx,yy=ring[idx]-dims[k][0]+origins[k]
            parts.append(f'<circle cx="{xx:.3f}" cy="{yy:.3f}" r="0.7" fill="#c54a38"/>')
    parts.extend([
        f'<text x="9" y="{height-9:.2f}" font-size="3.2">Scale 1:1 mm | dashed: sew | solid: cut (+{allowance:g} mm)</text>',
        f'<text x="9" y="{height-4:.2f}" font-size="3.2">Pattern is a geometric experiment, not a production tool.</text>',
        '</svg>',
    ])
    return "\n".join(parts)+"\n"


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if not a.input.is_file() or a.output.exists() or a.output.suffix.lower()!=".svg":
        raise RuntimeError("Input missing, output occupied or wrong extension")
    spec=json.loads(a.input.read_text(encoding="utf8"))
    output=draw(spec)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(output,encoding="utf8")
    print("RESEARCH_SVG_EXPORTED",a.output,flush=True)


if __name__=="__main__":
    main()
