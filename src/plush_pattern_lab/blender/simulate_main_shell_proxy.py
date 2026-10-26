"""在真实 H-compact 主躯干网格上执行 Blender Cloth 物理试验。

三种试验：无填充支撑 / 内部弹簧代理 / 均匀压力代理。使用同一低分辨率
闭合表面、同一重力和固定足端；比较形变与体积。材料为明确假设的
合成绒布参数，不是测得的采购面料，不得称为真实纤维棉填充模拟。
输出独立低模 .blend、OBJ(若受支持)、JSON、PNG，绝不覆盖 H 模型。
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

MAIN = "PRIMARY continuous sculpt | new anatomy"
CASES = {
    "unfilled": {"pressure_kpa":0.0,"internal_springs":False},
    "gas_proxy": {"pressure_kpa":0.07,"internal_springs":False},
    "spring_proxy": {"pressure_kpa":0.0,"internal_springs":True},
}
NOMINAL_AREAL_DENSITY_GSM = 220.0
GRAVITY_M_S2 = -9.81
FOOT_ANCHOR_Z_M = 0.041
CLOTH_FRAME_RATE = 24


def digest(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):
            h.update(block)
    return h.hexdigest()


def cli():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--output-dir",type=Path,required=True)
    p.add_argument("--case",choices=tuple(CASES),required=True)
    p.add_argument("--frames",type=int,default=20)
    p.add_argument("--target-faces",type=int,default=3000)
    a=p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    if not a.input.is_file() or a.input.suffix.lower()!=".blend":
        raise RuntimeError("缺少源模型")
    if a.output_dir.exists():
        raise RuntimeError("拒绝复写任何已存在的试验输出目录")
    if not 12<=a.frames<=72 or not 1200<=a.target_faces<=10000:
        raise RuntimeError("模拟帧数或低模大小超出试验门禁")
    a.input=a.input.resolve()
    a.output_dir=a.output_dir.resolve()
    if a.output_dir==a.input.parent:
        raise RuntimeError("必须使用新的独立输出目录")
    return a


def choose_primary_and_decimate(a):
    bpy.ops.wm.open_mainfile(filepath=str(a.input),load_ui=False)
    if len(bpy.context.scene.objects)!=470:
        raise RuntimeError("不是 H-compact 470 对象模型")
    src=bpy.context.scene.objects.get(MAIN)
    if src is None or src.type!="MESH" or len(src.data.vertices)<180000:
        raise RuntimeError("用户主躯干来源丢失")
    source_matrix=src.matrix_world.copy()
    mesh=src.data.copy()
    sim=bpy.data.objects.new("PHYSICS_PROXY_MAIN_NOT_PATTERN",mesh)
    bpy.context.scene.collection.objects.link(sim)
    sim.matrix_world=source_matrix
    # 物理场景仅保留一个代理网格，避免装饰绒毛数百万控制点参与碰撞。
    for other in list(bpy.context.scene.objects):
        if other!=sim:
            bpy.data.objects.remove(other,do_unlink=True)
    scene=bpy.context.scene
    scene.frame_set(1)
    bpy.ops.object.select_all(action="DESELECT")
    sim.select_set(True)
    bpy.context.view_layer.objects.active=sim
    initial_faces=len(mesh.polygons)
    mod=sim.modifiers.new("EXPERIMENT_DECIMATION_NOT_FABRIC_PATTERN","DECIMATE")
    # Blender collapse ratio相对于三角化面数
    mod.ratio=min(1.0,a.target_faces/max(1,initial_faces*2))
    bpy.ops.object.modifier_apply(modifier=mod.name)
    if not 500 <=len(sim.data.vertices)<=a.target_faces+800:
        raise RuntimeError("代理网格退化或 decimate 结果不符合上限")
    bm=bmesh.new()
    bm.from_mesh(sim.data)
    try:
        boundaries=sum(e.is_boundary for e in bm.edges)
        nonmanifold=sum(not e.is_manifold for e in bm.edges)
        vol=float(bm.calc_volume(signed=True)*sim.matrix_world.determinant())
        # 已审计主布壳理论体积约1.9425 L，简化不能严重偏离。
        if boundaries or nonmanifold or vol<=0 or abs(vol/0.0019425107237-1)>0.12:
            raise RuntimeError(f"闭合源退化，boundary={boundaries} nonmanifold={nonmanifold} V={vol}")
        area=0.0
        for face in bm.faces:
            verts=[sim.matrix_world @ v.co for v in face.verts]
            if len(verts)<3:
                continue
            # 通用多边形分扇计算世界面积
            for i in range(1,len(verts)-1):
                area+=((verts[i]-verts[0]).cross(verts[i+1]-verts[0])).length*0.5
    finally:
        bm.free()
    return sim, {
        "original_mesh_vertices":191370,
        "original_mesh_faces":191368,
        "proxy_vertices":len(sim.data.vertices),
        "proxy_faces":len(sim.data.polygons),
        "watertight":True,
        "signed_proxy_volume_m3":vol,
        "source_closed_volume_m3":0.001942510723711418,
        "proxy_surface_area_m2":area,
        "relative_proxy_volume_error":abs(vol/0.0019425107237-1),
        "source_matrix":[[float(v) for v in row] for row in source_matrix],
    }


def world_coords(obj, mesh):
    vec=np.empty(len(mesh.vertices)*3,dtype=np.float32)
    mesh.vertices.foreach_get("co",vec)
    xyz=vec.reshape(-1,3).astype(np.float64)
    m=np.asarray(obj.matrix_world,dtype=np.float64)
    return xyz@m[:3,:3].T + m[:3,3]


def signed_volume(mesh,xyz):
    # Mesh内都是多边形，使用 Blender 自身最终三角化顺序。
    mesh.calc_loop_triangles()
    triangles=np.array([list(t.vertices) for t in mesh.loop_triangles],dtype=np.int32)
    p,q,r=(xyz[triangles[:,i]] for i in range(3))
    return float(np.einsum("ij,ij->",p,np.cross(q,r))/6.0)


def add_cloth(sim,case,proxy):
    profile=CASES[case]
    points=world_coords(sim,sim.data)
    fixed=np.nonzero(points[:,2]<=FOOT_ANCHOR_Z_M)[0].tolist()
    if not 12<=len(fixed)<=len(points)*0.45:
        raise RuntimeError(f"支持点数异常 {len(fixed)}/{len(points)}")
    vg=sim.vertex_groups.new(name="PINNED_HOOF_INTERFACE_PROXY")
    vg.add(fixed,1.0,"REPLACE")
    modifier=sim.modifiers.new("ACTUAL_BLENDER_CLOTH_SOLVER","CLOTH")
    cloth=modifier.settings
    cloth.quality=5
    cloth.vertex_group_mass=vg.name
    cloth.pin_stiffness=30.0
    cloth.mass=(NOMINAL_AREAL_DENSITY_GSM/1000.0*proxy["proxy_surface_area_m2"])/len(points)
    # 数值参数为首轮灵敏度试验初始值。必须以后续实测织物力学数据标定。
    cloth.tension_stiffness=35.0
    cloth.compression_stiffness=35.0
    cloth.shear_stiffness=15.0
    cloth.bending_stiffness=0.8
    cloth.tension_damping=5.0
    cloth.compression_damping=5.0
    cloth.shear_damping=5.0
    cloth.bending_damping=0.5
    cloth.use_pressure=bool(profile["pressure_kpa"]>0)
    if cloth.use_pressure:
        cloth.pressure_factor=1.0
        cloth.uniform_pressure_force=profile["pressure_kpa"]
    cloth.use_internal_springs=profile["internal_springs"]
    if cloth.use_internal_springs:
        cloth.internal_tension_stiffness=12.0
        cloth.internal_compression_stiffness=12.0
        cloth.internal_spring_normal_check=True
    collisions=modifier.collision_settings
    collisions.use_collision=True
    collisions.use_self_collision=True
    collisions.collision_quality=3
    collisions.distance_min=0.0015
    collisions.self_distance_min=0.0015
    modifier.point_cache.frame_start=1
    return modifier, {
        "case":case,**profile,
        "pinned_vertices":len(fixed),"total_vertices":len(points),
        "areal_density_gsm_assumed":NOMINAL_AREAL_DENSITY_GSM,
        "effective_total_shell_mass_kg":cloth.mass*len(points),
        "vertex_mass_kg":cloth.mass,
        "tension_stiffness_arbitrary":cloth.tension_stiffness,
        "bending_stiffness_arbitrary":cloth.bending_stiffness,
        "internal_springs_as_material_surrogate":bool(cloth.use_internal_springs),
        "fabric_parameters_measured":False,
        "stuffing_constitutive_model":None,
        "gravity_m_s2":GRAVITY_M_S2,
    }


def capture(obj,depsgraph,initial,frame):
    evaluated=obj.evaluated_get(depsgraph)
    m=evaluated.to_mesh()
    try:
        xyz=world_coords(evaluated,m)
        if len(xyz)!=len(initial) or not np.all(np.isfinite(xyz)):
            raise RuntimeError(f"frame{frame}: 网格拓扑/非有限数值异常")
        vol=signed_volume(m,xyz)
        delta=xyz-initial
        dims=xyz.max(axis=0)-xyz.min(axis=0)
        measurement={
            "frame":frame,
            "centroid_mm":(xyz.mean(axis=0)*1000).round(5).tolist(),
            "bounds_min_mm":(xyz.min(axis=0)*1000).round(5).tolist(),
            "bounds_max_mm":(xyz.max(axis=0)*1000).round(5).tolist(),
            "extent_mm":(dims*1000).round(5).tolist(),
            "signed_volume_l":round(vol*1000,8),
            "relative_volume_vs_initial":vol/(signed_volume(obj.data,initial)),
            "rms_displacement_mm":round(float(np.sqrt(np.mean(np.sum(delta**2,axis=1)))*1000),6),
            "max_displacement_mm":round(float(np.linalg.norm(delta,axis=1).max()*1000),6)
        }
        return measurement,xyz
    finally:
        evaluated.to_mesh_clear()


def save_snapshot(scene,verts,mesh_faces,case):
    snapshot=bpy.data.meshes.new("DEFORMED_STATIC_SNAPSHOT_"+case)
    snapshot.from_pydata(verts.tolist(),[],mesh_faces)
    snapshot.update()
    obj=bpy.data.objects.new("SNAPSHOT_"+case+"_NOT_SEWING_PATTERN",snapshot)
    scene.collection.objects.link(obj)
    mat=bpy.data.materials.new(name="SIMULATED_SHELL_DIAGNOSTIC")
    mat.diffuse_color=(0.85,0.82,0.71,1.0)
    mat.use_nodes=True
    bsdf=mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value=(0.82,0.83,0.78,1.0)
        bsdf.inputs["Roughness"].default_value=0.94
    obj.data.materials.append(mat)
    return obj


def preview(scene,snapshot,path):
    # 渲染的是已求解快照，不是静态原始渲染模型。
    camdata=bpy.data.cameras.new("Simulator Orthographic")
    cam=bpy.data.objects.new("Simulator Orthographic",camdata)
    scene.collection.objects.link(cam)
    cam.location=(.38,-.51,.29)
    point=Vector((0,0.015,.139))
    cam.rotation_euler=(point-cam.location).to_track_quat("-Z","Y").to_euler()
    cam.data.type="ORTHO"
    cam.data.ortho_scale=.40
    scene.camera=cam
    # 后台 Linux 没有 OpenGL/EGL；Workbench 可能触发 libEGL.so 缺失甚至 abort。
    # Cycles CPU 不依赖 GUI/EGL，已用于项目历史稳定渲染链。
    scene.render.engine="CYCLES"
    scene.cycles.device="CPU"
    scene.cycles.samples=10
    scene.cycles.use_denoising=True
    scene.render.threads_mode="FIXED"
    scene.render.threads=2
    light=bpy.data.lights.new("Physics preview softbox","AREA")
    light.energy=110.0
    light.shape="DISK"
    light.size=0.35
    lamp=bpy.data.objects.new("Physics preview softbox",light)
    scene.collection.objects.link(lamp)
    lamp.location=(0.20,-0.28,0.53)
    lamp.rotation_euler=(Vector((0,0.015,.139))-lamp.location).to_track_quat("-Z","Y").to_euler()
    if scene.world is None:
        scene.world=bpy.data.worlds.new("Physics preview world")
    scene.world.use_nodes=True
    bg=scene.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value=(0.86,0.88,0.90,1.0)
        bg.inputs["Strength"].default_value=0.65
    scene.render.resolution_x=550
    scene.render.resolution_y=550
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.filepath=str(path)
    scene.render.film_transparent=False
    bpy.ops.render.render(write_still=True)
    if not path.is_file() or path.stat().st_size<5000:
        raise RuntimeError("物理快照渲染文件未生成")


def main():
    a=cli()
    source_sha=digest(a.input)
    start=time.monotonic()
    sim,proxy=choose_primary_and_decimate(a)
    scene=bpy.context.scene
    scene.render.fps=CLOTH_FRAME_RATE
    scene.frame_start=1
    scene.frame_end=a.frames
    scene.gravity=(0,0,GRAVITY_M_S2)
    modifier,settings=add_cloth(sim,a.case,proxy)
    modifier.point_cache.frame_end=a.frames
    rest=world_coords(sim,sim.data)
    mesh_faces=[list(p.vertices) for p in sim.data.polygons]
    base_volume=signed_volume(sim.data,rest)
    if abs(base_volume/proxy["signed_proxy_volume_m3"]-1)>0.0005:
        raise RuntimeError("世界坐标/网格体积核验不匹配")
    a.output_dir.mkdir(parents=True,exist_ok=False)
    data=[]
    solution=None
    previous=None
    step_speeds_mm=[]
    depsgraph=bpy.context.evaluated_depsgraph_get()
    for frame in range(1,a.frames+1):
        scene.frame_set(frame)
        measurement,solution=capture(sim,depsgraph,rest,frame)
        if previous is not None:
            step_mm=float(np.sqrt(np.mean(np.sum((solution-previous)**2,axis=1)))*1000)
            step_speeds_mm.append(step_mm)
            measurement["frame_to_frame_rms_mm"]=round(step_mm,6)
        previous=solution.copy()
        if frame<=12 or frame%4==0 or frame==a.frames:
            data.append(measurement)
        if frame%8==0:
            print("CLOTH_FRAME",a.case,frame,
                  measurement["rms_displacement_mm"],
                  measurement.get("frame_to_frame_rms_mm"),flush=True)
    latest=data[-1]
    if latest["max_displacement_mm"] < 0.0005:
        raise RuntimeError("求解器没有产生可检测位移：不得伪称物理模拟")
    if latest["max_displacement_mm"]>200 or latest["signed_volume_l"]<=0:
        raise RuntimeError("壳体剧烈失稳/法向反转：本次仿真失败，不能当作填充证据")
    if latest["relative_volume_vs_initial"]<0.05 or latest["relative_volume_vs_initial"]>3.0:
        raise RuntimeError("壳体体积失稳：需要调整代理参数")
    snapshot=save_snapshot(scene,solution,mesh_faces,a.case)
    sim.hide_render=True
    # 输出含已求解的静态快照，原动态 Cloth 节点作为可编辑试验设置保留。
    scene.frame_set(a.frames)
    blend=a.output_dir/("simulated_"+a.case+".blend")
    render=a.output_dir/("simulated_"+a.case+".png")
    bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
    # 不让图形预览失败吞掉实际求解的数据；下方 report 必须先完整写入。
    report={
        "status":"ACTUAL_BLENDER_CLOTH_SOLVER_RUN_UNCALIBRATED",
        "case":a.case,"source_file_sha256":source_sha,
        "model_origin":"H-compact primary mesh (source 470 objects, not original paper patterns)",
        "blender_version":bpy.app.version_string,
        "simulation_proxy":proxy,
        "assumed_material_and_fill_surrogate":settings,
        "frame_count":a.frames,"frame_rate":CLOTH_FRAME_RATE,
        "quasi_static_converged_at_last_5_frames":bool(
            len(step_speeds_mm)>=5 and max(step_speeds_mm[-5:])<0.03),
        "recent_frame_to_frame_rms_mm":[round(v,6) for v in step_speeds_mm[-5:]],
        "frames":data,"last":latest,
        "output_blend_sha256":digest(blend),
        "static_snapshot_object":snapshot.name,
        "elapsed_seconds":round(time.monotonic()-start,2),
        "limits":["静态已雕刻主躯干起步，不是从纸样缝合求解",
                  "无织物样布的拉伸/剪切/弯曲参数实测",
                  "气压是气体压力；内部弹簧是简化支撑代理，均不等于聚酯棉",
                  "不含颈部/四蹄/灰云实体缝线和其他零件接触",
                  "最终纸样、填棉质量和站立尚不能据此验收"],
    }
    (a.output_dir/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
    print("ACTUAL_CLOTH_SOLVER_COMPLETED",a.case,json.dumps(latest,ensure_ascii=False),flush=True)
    # 结果先保存，然后以 CPU Cycles 渲染静态求解快照。
    preview(scene,snapshot,render)


if __name__=="__main__":
    main()
