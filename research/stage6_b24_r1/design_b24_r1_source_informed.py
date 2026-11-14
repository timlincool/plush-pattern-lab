"""Constrained Stage6 B24 research revision R1, *not* a sewn Blender result.

Reads trustworthy same-run 24-piece stage6 JSON and genuine original source
horizontal-section area measurements. Preserves 13 lower source-anchored pieces,
B100 lower band interface, 24 piece IDs and 46 digitally paired seams.
Replaces too-wide torso/head 2D gores and oversize head cap subject to a hard
shoulder-bridge allowance gate. No original source mesh UV unrolling claimed.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from shapely.geometry import Polygon

SEAM_ALLOWANCE_MM = 6.0
MIN_SHOULDER_BRIDGE_MM = 13.0  # 12.7 mm hard tolerance + 0.3 mm working slack
RESEARCH_VARIANT = "B_integrated_neck_port"
BODY_STATIONS = (100, 115, 125, 135)
HEAD_STATIONS = (145, 155, 180, 205, 230)
QUARTER = 16


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def lengths(points, *, close=False):
    pts = np.asarray(points, float)
    if close:
        pts = np.vstack((pts, pts[:1]))
    return np.linalg.norm(np.diff(pts, axis=0), axis=1)


def rescale_ring(ring, scale):
    old = np.asarray(ring, dtype=np.float64)
    if scale == 1.0:
        return old.copy()
    return (old - old.mean(axis=0)) * scale + old.mean(axis=0)


def true_targets(section_data, trial):
    sections = {int(r["source_plane_z_mm"]): r for r in section_data["actual_source_section_compact_summary"]}
    rows = []
    for kind, levels in (("body", BODY_STATIONS), ("head", HEAD_STATIONS)):
        rings = trial[f"{kind}_synthetic_rings_xy_mm"]
        for level, ring in zip(levels, rings):
            areas = sections[level]["source_contour_component_areas_mm2"]
            if level == 230:
                # Source is THREE loops. A central cap cannot cover both ears.
                a_ref = max(areas)
                source_loops = 3
            else:
                a_ref = sum(areas)
                source_loops = len(areas)
            actual = Polygon(ring).area
            rows.append({"kind":kind, "level_mm":level, "current_area_mm2":actual,
                         "source_area_mm2":a_ref,
                         "source_original_closed_loop_count":source_loops,
                         "best_equal-area_uniform_scale":float(np.sqrt(a_ref/actual))})
    return rows


def optimize_scales(trial, targets):
    t = np.asarray([r["best_equal-area_uniform_scale"] for r in targets])
    original_outer = np.asarray(trial["shoulder_cap"]["outer_stitch_xy_mm"],float)
    original_inner = np.asarray(trial["shoulder_cap"]["upper_head_opening_stitch_xy_mm"][0],float)
    def vec(x):
        return np.r_[1.0, x]
    def shoulder_gap(x):
        s = vec(x)
        a = Polygon(rescale_ring(original_outer,s[3]))
        b = Polygon(rescale_ring(original_inner,s[4]))
        if not a.contains(b):
            return -float(a.exterior.distance(b))
        return float(a.exterior.distance(b))
    def objective(x):
        s=vec(x)
        error=np.sum((s-t)**2)
        # weak smoothness discourages changes to adjacent sections being completely unrelated
        smooth=np.sum(np.diff(s[:4],n=2)**2)*0.012 + np.sum(np.diff(s[4:],n=2)**2)*0.012
        return float(error+smooth)
    constraints=[{"type":"ineq","fun":lambda x: shoulder_gap(x)-MIN_SHOULDER_BRIDGE_MM}]
    opt=minimize(objective, x0=np.ones(8), method="SLSQP",
                 bounds=[(0.60,1.06)]*2+[(0.75,1.0)]+[(0.75,1.40)]+[(0.55,1.10)]*4,
                 constraints=constraints,
                 options={"ftol":1e-11,"maxiter":250})
    s=vec(opt.x)
    if (not opt.success or not np.isfinite(s).all() or
        shoulder_gap(opt.x)<MIN_SHOULDER_BRIDGE_MM-1e-6 or s[0]!=1.0):
        raise ValueError("no credible 6mm seam allowance compliant optimized B24 R1")
    return s, shoulder_gap(opt.x), {"SLSQP_success":bool(opt.success),"iterations":int(opt.nit),"objective":float(opt.fun)}


def meridian_steps(rings, heights):
    xyz=np.stack([np.column_stack((ring,np.full(64,z))) for ring,z in zip(rings,heights)])
    length=np.linalg.norm(np.diff(xyz[:,[0,16,32,48]],axis=0),axis=2)
    per=np.asarray([[lengths(ring[(np.arange(17)+16*i)%64]).sum() for i in range(4)] for ring in rings])
    steps=np.maximum(length.max(axis=1),(np.abs(np.diff(per,axis=0))/2).max(axis=1))+0.2
    return steps


def gore(ident, rings, heights, steps, quarter=QUARTER):
    idx=int(ident.rsplit('-',1)[-1])-1
    stations=[]
    for ring in rings:
        arc=ring[(np.arange(quarter+1)+idx*quarter)%64]
        stations.append(np.r_[0,np.cumsum(lengths(arc))])
    widths=np.asarray([x[-1] for x in stations])
    side_y=np.sqrt(steps**2-(np.diff(widths)/2)**2)
    if not np.all(np.isfinite(side_y)) or np.any(side_y<=0):
        raise ValueError("R1 2D gore sides collapsed")
    y=np.r_[0,np.cumsum(side_y)]
    left=np.column_stack((-widths/2,y))
    right=np.column_stack((widths/2,y))
    bottom=np.column_stack((stations[0]-widths[0]/2,np.zeros(quarter+1)))
    top=np.column_stack((stations[-1]-widths[-1]/2,np.full(quarter+1,y[-1])))
    perimeter=np.vstack((bottom,right[1:],top[-2::-1],left[-2:0:-1]))
    poly=Polygon(perimeter)
    cut=poly.buffer(SEAM_ALLOWANCE_MM,quad_segs=8)
    if not poly.is_valid or poly.area<80 or not cut.is_valid or not cut.covers(poly):
        raise ValueError("R1 2D gore invalid or self-crossed")
    return {
        "lower_stitch_xy_mm":bottom.tolist(),
        "upper_stitch_xy_mm":top.tolist(),
        "left_stitch_xy_mm":left.tolist(),
        "right_stitch_xy_mm":right.tolist(),
        "stitch_polygon_xy_mm":np.asarray(poly.exterior.coords).tolist(),
        "cut_polygon_xy_mm":np.asarray(cut.exterior.coords).tolist(),
    }


def cap(ring, label, port=None):
    outer=Polygon(ring)
    if not outer.is_valid or outer.area<=100:
        raise ValueError("R1 3D profile collapses cap surface")
    cut=outer.buffer(SEAM_ALLOWANCE_MM,quad_segs=8)
    holes=[]
    if port is not None:
        inner=Polygon(port)
        if not outer.contains(inner) or outer.exterior.distance(inner)<MIN_SHOULDER_BRIDGE_MM-1e-6:
            raise ValueError("R1 shoulder port violates 6mm seam allowance")
        inner_cut=inner.buffer(-SEAM_ALLOWANCE_MM,quad_segs=8)
        if inner_cut.is_empty or inner_cut.geom_type != "Polygon":
            raise ValueError("R1 inner neck hole disappeared")
        cut=cut.difference(inner_cut)
        holes=[port.tolist()]
    if cut.geom_type!='Polygon' or len(cut.interiors)!=len(holes) or not cut.is_valid:
        raise ValueError("R1 cap sewing shape invalid")
    return {"id":label,"outer_stitch_xy_mm":np.asarray(ring).tolist(),
            "cut_outer_xy_mm":np.asarray(cut.exterior.coords).tolist(),
            "cut_inner_holes_xy_mm":[np.asarray(h.coords).tolist() for h in cut.interiors],
            "upper_head_opening_stitch_xy_mm":holes,
            "original_mesh_source_cut_surface":False}


def edge_segments(key, trial, row):
    part, designation=key.split('.',1)
    if part.startswith('TORSO-') or part.startswith('HEADNECK-'):
        group=trial['torso_gore_pieces'] if part.startswith('TORSO-') else trial['headneck_gore_pieces']
        p=group[int(part.split('-')[-1])-1]
        field={'bottom':'lower_stitch_xy_mm','top':'upper_stitch_xy_mm',
               'left':'left_stitch_xy_mm','right':'right_stitch_xy_mm'}[designation]
        return lengths(p[field])
    if part in {'SHOULDER-CAP-TRIAL','HEAD-TOP-CAP-TRIAL'}:
        capdata=trial['shoulder_cap'] if part.startswith('SHOULDER') else trial['head_top_cap']
        pts=capdata['outer_stitch_xy_mm']
        if designation=='inner-port':
            pts=trial['shoulder_cap']['upper_head_opening_stitch_xy_mm'][0]
            return lengths(pts,close=True)
        offset=(int(designation.split('-')[-1])-1)*16
        return lengths(pts,close=True)[offset:offset+16]
    if part=='COLLAR-TRIAL':
        if designation.startswith('side-'):
            return np.asarray([trial['neck_collar_if_integrated']['height_mm']],float)
        segments=np.diff(trial['neck_collar_if_integrated']['lower_and_upper_stitch_station_x_mm'])
        if designation=='bottom':
            return segments
        idx=(int(designation.split('-')[-1])-1)*16
        return segments[idx:idx+16]
    return None


def generate(upper_file, lower_file, original_graph_file, sections_file, output):
    original_upper=json.loads(Path(upper_file).read_text(encoding='utf8'))
    lower=json.loads(Path(lower_file).read_text(encoding='utf8'))
    graph=json.loads(Path(original_graph_file).read_text(encoding='utf8'))
    sections=json.loads(Path(sections_file).read_text(encoding='utf8'))
    if (original_upper.get('schema')!='stage6-separated-torso-headneck-mother-trial-ab-v1'
        or lower.get('schema')!='stage6-source-hoof-anchored-lower-mother-toile-v1'
        or graph.get('variant')!=RESEARCH_VARIANT
        or graph.get('numerically_paired_interface_count')!=46
        or graph.get('factory_cut_patterns_approved')!=0):
        raise ValueError('input not the verified B24 research structure')
    upper=copy.deepcopy(original_upper)
    trial=next(x for x in upper['options'] if x['name']==RESEARCH_VARIANT)
    original_trial=next(x for x in original_upper['options'] if x['name']==RESEARCH_VARIANT)
    targets=true_targets(sections,trial)
    scales,gap,opt=optimize_scales(trial,targets)
    body=np.asarray(trial['body_synthetic_rings_xy_mm'],float)
    head=np.asarray(trial['head_synthetic_rings_xy_mm'],float)
    corrected_body=np.asarray([rescale_ring(r,s) for r,s in zip(body,scales[:4])])
    corrected_head=np.asarray([rescale_ring(r,s) for r,s in zip(head,scales[4:])])
    assert np.array_equal(body[0],corrected_body[0])
    body_steps=meridian_steps(corrected_body,BODY_STATIONS)
    head_steps=meridian_steps(corrected_head,HEAD_STATIONS)
    for j,p in enumerate(trial['torso_gore_pieces']):
        p.update(gore(p['id'],corrected_body,BODY_STATIONS,body_steps))
    for j,p in enumerate(trial['headneck_gore_pieces']):
        p.update(gore(p['id'],corrected_head,HEAD_STATIONS,head_steps))
    trial['body_synthetic_rings_xy_mm']=corrected_body.tolist()
    trial['head_synthetic_rings_xy_mm']=corrected_head.tolist()
    trial['body_meridian_step_mm']=body_steps.tolist()
    trial['head_meridian_step_mm']=head_steps.tolist()
    trial['shoulder_cap']=cap(corrected_body[-1],'SHOULDER-CAP-TRIAL',corrected_head[0])
    trial['head_top_cap']=cap(corrected_head[-1],'HEAD-TOP-CAP-TRIAL')
    guide=lengths(corrected_head[0],close=True)
    station=np.r_[0,np.cumsum(guide)]
    trial['neck_collar_if_integrated']['lower_and_upper_stitch_station_x_mm']=station.tolist()
    length=station[-1]
    trial['neck_collar_if_integrated']['cut_rectangle_xy_mm']=[[-6,-6],[length+6,-6],[length+6,16],[-6,16]]
    trial['neck_source_inspired_guide']={"ring_xy_mm":corrected_head[0].tolist(),
            "indexed_64_segment_mm":guide.tolist(),"perimeter_mm":float(length)}
    trial['source_neck_port_modification']['minimum_body_cap_boundary_to_port_mm']=gap
    trial['source_neck_port_modification']['new_port_center_xy_mm']=corrected_head[0].mean(axis=0).tolist()
    trial['source_neck_port_modification']['neck_port_matches_actual_source_root_geometry']=False
    # Keep the old B-to-TORSO seam identity exactly: not simply equal perimeter,
    # but all 64 original B100 ring 2D indexed segment lengths are immutable.
    if not np.array_equal(corrected_body[0],body[0]):
        raise ValueError('lower 13 original source-linked pieces were changed')
    updated_graph=copy.deepcopy(graph)
    touched=0
    for e in updated_graph['sewing_interfaces']:
        aa=edge_segments(e['first'],trial,e)
        bb=edge_segments(e['second'],trial,e)
        if aa is None and bb is None:
            continue
        if aa is None or bb is None:
            # The lower band source must still be exactly the original B100 edge.
            other=aa if aa is not None else bb
            if abs(float(other.sum())-float(e['first_2d_netline_mm']))>1e-4:
                raise ValueError('R1 lower-band netline changed')
            continue
        if aa.shape!=bb.shape or np.max(abs(aa-bb))>1e-4:
            raise ValueError('R1 seam mismatch '+e['id'])
        e['first_2d_netline_mm']=float(aa.sum())
        e['second_2d_netline_mm']=float(bb.sum())
        e['max_segment_disagreement_mm']=float(np.max(abs(aa-bb)))
        touched+=1
    if len(updated_graph['sewing_interfaces'])!=46 or touched<22:
        raise ValueError('R1 failed 46-interface continuity')
    # Confirm zero material-approval elevation.
    if trial['industrial_cut_patterns_approved']!=0:
        raise ValueError('R1 cannot be declared production-ready')
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    files={'B24_R1_upper_source_envelope_ab_RESEARCH_ONLY.json':upper,
           'B24_R1_panel_interface_46_RESEARCH_ONLY.json':updated_graph}
    for f,j in files.items():
        (output/f).write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    report={
        'schema':'stage6-b24-r1-constrained-2d-research-v1',
        'source_original_blend_sha256':graph['source_public_stage6_blend_sha256'],
        'inputs_sha256':{'upper':sha256(upper_file),'lower':sha256(lower_file),
                         'graph':sha256(original_graph_file),'source_sections':sha256(sections_file)},
        'solver':opt,
        'ring_stations':[dict(row,applied_R1_scale=float(s),
                     R1_area_mm2=float(row['current_area_mm2']*s*s)) for row,s in zip(targets,scales)],
        'B100_original_source_linked_lower_band_preserved':True,
        'original_4_hoof_holes_512_source_edges_unchanged':True,
        'B24_parts_kept':24,
        'B24_numerical_pairs_kept':46,
        'R1_interfaces_with_both_sides_updated_and_verified':touched,
        'min_shoulder_bridge_mm':float(gap),
        'min_shoulder_bridge_required_mm':MIN_SHOULDER_BRIDGE_MM,
        'head_top_is_one_new_smaller_synthetic_central_cap_not_original_source_3D':True,
        'true_source_230mm_closed_loops':3,
        'two_original_side_high_protrusions_still_NOT_physically_sewn':True,
        'real_Blender_Cloth_R1_NOT_run':True,
        'factory_paper_patterns_approved':0,
    }
    (output/'B24_R1_seam_and_source_shape_QA.json').write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('upper','lower','graph','sections','output'):
        p.add_argument('--'+arg,required=True,type=Path)
    a=p.parse_args()
    print(json.dumps(generate(a.upper,a.lower,a.graph,a.sections,a.output),ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
