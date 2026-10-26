"""灰侧云真实网格的低模切割平面扫描，不修改冻结场景（Blender 4.3.2）。

输出全世界坐标几何 JSON + 切割后的边界拓扑统计，用于选择两片式裁片试点。
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import bmesh
import bpy
import numpy as np

PART = "Grey flank cloud -1"
TEMPLATE_SOURCE_SHA = "e3ae7befad526938fd85d1460c1febb284292fc50fb887dd13a188faffb70fc2"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--mesh-output", type=Path, required=True)
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    if not a.input.is_file() or a.output.exists() or a.mesh_output.exists():
        raise RuntimeError("缺源或目标路径已占用")
    bpy.ops.wm.open_mainfile(filepath=str(a.input.resolve()), load_ui=False)
    source = bpy.context.scene.objects.get(PART)
    if source is None or source.type != "MESH" or len(source.data.vertices) != 12214:
        raise RuntimeError("灰侧云冻结来源不符")
    mesh = source.data.copy()
    obj = bpy.data.objects.new("EXPERIMENT_SIDE_CLOUD_TRIANGLE_PROXY", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.matrix_world = source.matrix_world.copy()
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    target_triangles = 2600
    mod = obj.modifiers.new("EXPERIMENT_SIDECLOUD_DECIMATE", "DECIMATE")
    mod.ratio = min(1.0, target_triangles / (max(1, len(mesh.polygons)) * 2))
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.ops.object.mode_set(mode="OBJECT")
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)
    bm.verts.ensure_lookup_table()
    xvals = np.asarray([v.co.x for v in bm.verts])
    yvals = np.asarray([v.co.y for v in bm.verts])
    zvals = np.asarray([v.co.z for v in bm.verts])
    bb = {
        "min": [float(v * 1000) for v in (xvals.min(), yvals.min(), zvals.min())],
        "max": [float(v * 1000) for v in (xvals.max(), yvals.max(), zvals.max())],
    }
    vol = float(bm.calc_volume(signed=True) * 1e6)
    candidates = []
    for axis in ("X", "Z"):
        coord_idx = 0 if axis == "X" else 2
        vals = xvals if axis == "X" else zvals
        for frac in (0.3, 0.4, 0.5, 0.6, 0.7):
            t = float(np.min(vals) + frac * (np.max(vals) - np.min(vals)))
            work = bm.copy()
            try:
                geom = list(work.verts) + list(work.edges) + list(work.faces)
                normal = (1, 0, 0) if axis == "X" else (0, 0, 1)
                point = [0.0, 0.0, 0.0]
                point[coord_idx] = t
                bmesh.ops.bisect_plane(
                    work, geom=geom, dist=1e-7, plane_co=point, plane_no=normal
                )
                work.faces.ensure_lookup_table()
                side = {f: (f.calc_center_median()[coord_idx] >= t) for f in work.faces}
                seam_edges = [
                    e
                    for e in work.edges
                    if len(e.link_faces) == 2
                    and side[e.link_faces[0]] != side[e.link_faces[1]]
                ]
                deg = defaultdict(int)
                nei = defaultdict(list)
                for e in seam_edges:
                    v0, v1 = e.verts[:]
                    deg[v0] += 1
                    deg[v1] += 1
                    nei[v0].append(v1)
                    nei[v1].append(v0)
                visited = set()
                loops = []
                for v in deg:
                    if v in visited:
                        continue
                    q = [v]
                    visited.add(v)
                    points = 0
                    while q:
                        p0 = q.pop()
                        points += 1
                        for p1 in nei[p0]:
                            if p1 not in visited:
                                visited.add(p1)
                                q.append(p1)
                    loops.append(points)
                valid = (
                    len(seam_edges) >= 12
                    and len(loops) == 1
                    and all(v == 2 for v in deg.values())
                )
                sidecounts = [
                    sum(1 for v in side.values() if v == k) for k in (False, True)
                ]
                candidates.append(
                    {
                        "axis": axis,
                        "fraction": frac,
                        "coordinate_mm": round(t * 1000, 5),
                        "seam_edges": len(seam_edges),
                        "seam_components": len(loops),
                        "loop_vertex_counts": loops,
                        "all_seam_vertex_degree_2": all(v == 2 for v in deg.values()),
                        "valid_single_cut": valid,
                        "half_face_counts": sidecounts,
                    }
                )
            except Exception as e:
                candidates.append(
                    {"axis": axis, "fraction": frac, "exception": repr(e)}
                )
            finally:
                work.free()
    # 尝试准确提取几何用于后续数值审计与断面图。
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    index = {v: i for i, v in enumerate(bm.verts)}
    verts = [[round(float(c) * 1000, 6) for c in v.co] for v in bm.verts]
    faces = [[index[v] for v in f.verts] for f in bm.faces]
    meshdata = {
        "source": PART,
        "vertices_mm": verts,
        "faces": faces,
        "bbox_mm": bb,
        "source_geometry_is_decimated": True,
    }
    report = {
        "status": "REAL_H_GREY_FLANK_CLOUD_CUT_PROBE",
        "part": PART,
        "blender": bpy.app.version_string,
        "target_triangles": target_triangles,
        "proxy_vertices": len(bm.verts),
        "proxy_faces": len(bm.faces),
        "signed_proxy_volume_cm3": vol,
        "bbox_mm": bb,
        "cuts": candidates,
        "selection": "只有单圈封闭切缝、无交叉且双片有足够面数，才允许做二片纸样",
        "limits": "低模只供方法验证；切断不等于已添加缝份、纺织材料和附着主壳的缝线",
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.mesh_output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8"
    )
    a.mesh_output.write_text(
        json.dumps(meshdata, separators=(",", ":")), encoding="utf8"
    )
    bm.free()
    print(
        "GREY_CLOUD_PROBE",
        json.dumps(
            {
                "vertices": report["proxy_vertices"],
                "faces": report["proxy_faces"],
                "volume_cm3": vol,
                "valid_cuts": [x for x in candidates if x.get("valid_single_cut")],
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
