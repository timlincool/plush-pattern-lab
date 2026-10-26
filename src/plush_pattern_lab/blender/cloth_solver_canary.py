"""Blender Cloth smoke test: a 8x8 plane must fall under gravity."""
import json
import sys
from pathlib import Path
import bpy
import numpy as np
args=sys.argv[sys.argv.index("--")+1:]
path=Path(args[0])
mode=args[1] if len(args)>1 else "plain"
if mode not in ("plain","rest"):raise ValueError("Invalid canary mode")
if path.exists():raise FileExistsError(path)
bpy.ops.wm.read_factory_settings(use_empty=True)
verts=[(i*.02,j*.02,.2) for j in range(8) for i in range(8)]
faces=[]
for j in range(7):
    for i in range(7):
        v=j*8+i
        faces.append((v,v+1,v+9,v+8))
mesh=bpy.data.meshes.new("canary_plane")
mesh.from_pydata(verts,[],faces)
mesh.update()
obj=bpy.data.objects.new("gravity_cloth_canary",mesh)
bpy.context.scene.collection.objects.link(obj)
rest=None
if mode=="rest":
    obj.shape_key_add(name="Basis",from_mix=False)
    rest=obj.shape_key_add(name="Rest",from_mix=False)
mod=obj.modifiers.new("cloth","CLOTH")
if rest is not None:
    mod.settings.rest_shape_key=rest
mod.settings.mass=.01
mod.settings.quality=4
scene=bpy.context.scene
scene.gravity=(0,0,-9.81)
scene.frame_start=1
scene.frame_end=24
mod.point_cache.frame_start=1
mod.point_cache.frame_end=24
view=bpy.context.evaluated_depsgraph_get()
measures=[]
for frame in range(1,25):
    scene.frame_set(frame)
    ev=obj.evaluated_get(view)
    m=ev.to_mesh()
    z=np.array([v.co.z for v in m.vertices])
    ev.to_mesh_clear()
    if frame in (1,2,12,24):
        measures.append({"frame":frame,"mean_z":float(z.mean()),"range":float(np.ptp(z))})
path.parent.mkdir(parents=True,exist_ok=True)
path.write_text(json.dumps(measures,indent=2))
print("CANARY",mode,measures,flush=True)
if measures[-1]["mean_z"] >= measures[0]["mean_z"]-.001:
    raise RuntimeError("Cloth gravity integration absent")
