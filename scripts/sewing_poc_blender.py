"""Blender 4.3.2: 2D rest-gore cloth + loose-edge sewing springs; synthetic, NOT production."""
import argparse
import json
import sys
from pathlib import Path
import bpy
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sewing_quality import evaluate

def _prepare_geometry(a, par, right, n, N):
    vertices,rest,faces,loose,seams,reference=[],[],[],[],[],[]
    rad=par["radius_mm"]*.001
    half=par["half_height_mm"]*.001
    height=max(q[1] for q in right)
    for i in range(n):
        az=2*np.pi*i/n
        outward=np.array([np.cos(az),np.sin(az),0.])
        tangent=np.array([-np.sin(az),np.cos(az),0.])
        start=len(vertices)
        for j in range(N):
            yy=right[j][1]
            theta=np.pi*j/(N-1)
            f=yy/height
            radius=(.30+.70*np.sin(np.pi*f))*rad
            # Pole rows otherwise contain coincident vertices and zero-area quads.
            # Use a 0.035mm numerical cap; this is NOT an approved seam allowance.
            half_width=.035 if j in (0,N-1) else abs(right[j][0])
            for slot,x in enumerate((-half_width,0.,half_width)):
                angle=az+(slot-1)*np.pi/n
                goal=np.array((rad*np.sin(theta)*np.cos(angle),
                               rad*np.sin(theta)*np.sin(angle),
                               half*np.cos(theta)),dtype=float)
                if a.placement=="reference_offset":
                    # Known target assists *pre-positioning*; not independent
                    # reconstruction. Small panel radial displacement gives
                    # sewing springs a real gap to close.
                    pos=goal + .004*outward
                    if j in (0,N-1):
                        pos=pos + x*.001*tangent  # non-degenerate pole cap
                else:
                    pos=radius*outward+x*.001*tangent+np.array([0,0,half*(1-2*f)])
                vertices.append(tuple(pos))
                rest.append((x*.001+i*.20,yy*.001,0.))
                reference.append(tuple(goal))
        for j in range(N-1):
            v=start+3*j;w=v+3
            faces.append((v,w,w+1,v+1))
            faces.append((v+1,w+1,w+2,v+2))
    for i in range(n):
        for j in range(N):
            a1=i*N*3+j*3+2
            a2=((i+1)%n)*N*3+j*3
            loose.append((a1,a2))
            seams.append((a1,a2))
    points_array=np.asarray(vertices,dtype=float)
    a3=np.asarray([np.linalg.norm(np.cross(points_array[f[1]]-points_array[f[0]],
                                           points_array[f[3]]-points_array[f[0]]))/2
                   for f in faces])
    if np.count_nonzero(a3 < 1e-12):
        raise RuntimeError(f"Degenerate faces before cloth: {np.count_nonzero(a3 < 1e-12)}")
    print("SEW_GEOMETRY",len(vertices),len(faces),
          "minimum_quad_half_area_m2",float(a3.min()),flush=True)
    return vertices, rest, faces, loose, seams, reference


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("spec","output","report"):
        p.add_argument("--"+key,type=Path,required=True)
    p.add_argument("--frames",type=int,default=48)
    p.add_argument("--placement",choices=("legacy","reference_offset"),default="legacy")
    a=p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    if not a.spec.is_file() or a.output.exists() or a.report.exists():
        raise RuntimeError("Input absent / outputs exist")
    if not 20<=a.frames<=144:raise ValueError("Invalid frame count")
    data=json.loads(a.spec.read_text())
    if data.get("status")!="UNVALIDATED_GEOMETRIC_RESEARCH_PATTERN":
        raise RuntimeError("Not a synthetic research pattern")
    par=data["parameters"]
    n=int(par["panels"])
    left=data["panel"]["seam_left"]; right=data["panel"]["seam_right"]
    N=len(left)
    if n<6 or n>24 or not 25<=N<=257 or len(right)!=N:
        raise RuntimeError("Unexpected pattern topology")
    if len(data["sewing_pairs"])!=n:
        raise RuntimeError("Stitch pairing graph incomplete")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    vertices,rest,faces,loose,seams,reference = _prepare_geometry(a, par, right, n, N)
    mesh=bpy.data.meshes.new("SYNTHETIC_2D_GORE_MESH")
    mesh.from_pydata(vertices,loose,faces)
    mesh.update()
    obj=bpy.data.objects.new("SYNTHETIC_SEWING_EXPERIMENT_NOT_FINAL_TOY",mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active=obj
    obj.select_set(True)
    obj.shape_key_add(name="InitialPrepositioned3D",from_mix=False)
    flat=obj.shape_key_add(name="Flat2DRestPattern",from_mix=False)
    for k,point in enumerate(rest):flat.data[k].co=point
    modifier=obj.modifiers.new("ACTUAL_SEWING_SPRINGS","CLOTH")
    setting=modifier.settings
    setting.rest_shape_key=flat
    setting.use_sewing_springs=True
    setting.sewing_force_max=50.0
    setting.quality=5
    setting.mass=.02/len(vertices)
    setting.tension_stiffness=15.
    setting.compression_stiffness=15.
    setting.shear_stiffness=8.
    setting.bending_stiffness=.5
    setting.use_pressure=False
    modifier.collision_settings.use_collision=False
    modifier.collision_settings.use_self_collision=False
    scene=bpy.context.scene
    # Isolate sewing forces; the independent cloth_solver_canary.py tests gravity.
    scene.gravity=(0,0,0)
    scene.frame_start=1
    scene.frame_end=a.frames
    modifier.point_cache.frame_start=1
    modifier.point_cache.frame_end=a.frames
    deps=bpy.context.evaluated_depsgraph_get()
    def gap(points):
        values=np.array([np.linalg.norm(points[p]-points[q]) for p,q in seams])
        return {"mean_gap_mm":float(values.mean()*1000),
                "p95_gap_mm":float(np.quantile(values,.95)*1000),
                "max_gap_mm":float(values.max()*1000)}
    initial=gap(np.asarray(vertices))
    trace=[]; last=None
    for frame in range(1,a.frames+1):
        scene.frame_set(frame)
        obj_eval=obj.evaluated_get(deps)
        m=obj_eval.to_mesh()
        try:
            xyz=np.empty(len(m.vertices)*3,np.float32)
            m.vertices.foreach_get("co",xyz)
            xyz=xyz.reshape(-1,3).astype(float)
        finally:
            obj_eval.to_mesh_clear()
        if not np.isfinite(xyz).all():raise RuntimeError("Nonfinite mesh in sewing simulation")
        if frame in (1,2,4,8,16,32,a.frames):trace.append({"frame":frame,**gap(xyz)})
        last=xyz
        if frame%12==0:print("SEW_FRAME",frame,gap(xyz),flush=True)
    final=gap(last)
    rest_xy=np.asarray(rest,dtype=float)[:,:2]
    reference_xyz=np.asarray(reference,dtype=float)
    initial_quality=evaluate(np.asarray(vertices,dtype=float),rest_xy,faces,seams,
                             reference_xyz,np.asarray(vertices,dtype=float))
    final_quality=evaluate(last,rest_xy,faces,seams,reference_xyz,
                           np.asarray(vertices,dtype=float))
    if not np.isfinite(final_quality["strain"]["max_abs_principal_strain"]):
        raise RuntimeError("The cloth deformation gradient is nonfinite")
    out={
        "status":"ACTUAL_CLOTH_SEWING_SPRINGS_NUMERICAL_TRIAL",
        "blender":bpy.app.version_string,
        "frames":a.frames,
        "synthetic_panel_count":n,
        "preposition_mode":a.placement,
        "reference_assisted_initialization":a.placement=="reference_offset",
        "seam_spring_edges":len(seams),
        "mesh_vertices":len(vertices),
        "mesh_faces":len(faces),
        "rest_shape_key":"Flat2DRestPattern",
        "used_sewing_springs":bool(setting.use_sewing_springs),
        "pressure_enabled":bool(setting.use_pressure),
        "gravity_m_s2":0.0,
        "initial":initial,"final":final,"trace":trace,
        "initial_geometry_quality":initial_quality,
        "final_geometry_quality":final_quality,
        "gap_reduction_ratio":1-final["mean_gap_mm"]/initial["mean_gap_mm"],
        "limitations":[
            "Synthetic ellipsoid, not an alpaca model",
            "Reference-offset placement uses known synthetic target for initialization",
            "No final welded shell, tension/contact certification",
            "No measured material, stuffing or manufacturability validation",
            "Rigid-aligned error is measured to synthetic geometry, not the user's plush"]}
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
    snapshot=bpy.data.meshes.new("FINAL_FRAME_SNAPSHOT_MESH")
    snapshot.from_pydata(last.tolist(),[],faces)
    snap=bpy.data.objects.new("FINAL_SNAPSHOT_NOT_MANUFACTURING",snapshot)
    scene.collection.objects.link(snap)
    obj.hide_render=True
    a.output.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(a.output),compress=True)
    if final["mean_gap_mm"]>=initial["mean_gap_mm"]*.95:
        raise RuntimeError("Sewing solver did not achieve >=5% gap reduction")
    print("SEWING_SOLVER_PASS",json.dumps(out,ensure_ascii=False),flush=True)
if __name__=="__main__":
    main()
