"""只读审计 H-compact 玩偶真实 Blender 网格的闭合性、体积、边界和连通分量。

不把视觉模型中的互相穿插当作缝线或实际布壳。只有闭合正向流形可以直接
作为均匀压力代理试验输入。模拟并非对真实织物/棉花的材料标定。
"""

import argparse
import json
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np

NAME_PREFIXES = (
    "PRIMARY continuous sculpt",
    "Grey flank cloud",
    "Grey head cloud halo",
    "Varied ivory forehead cloud",
    "Asymmetric flowing ivory bib",
    "Hanging grey tail overlay",
    "Slender upright ivory ear",
    "Pink inset ear",
    "Rounded hoof base",
    "Fabric rain drop",
)
MAX_READABLE_OBJECTS = 55


def audit(o):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    try:
        V, E, F = len(bm.verts), len(bm.edges), len(bm.faces)
        open_edges = sum(e.is_boundary for e in bm.edges)
        nonmanifold = sum(not e.is_manifold for e in bm.edges)
        wire = sum(e.is_wire for e in bm.edges)
        # 多个连通分量不应假装为整体连续的缝合材料。
        verts = list(bm.verts)
        seen = set()
        components = []
        for start in verts:
            if start in seen:
                continue
            stack = [start]
            seen.add(start)
            size = 0
            while stack:
                item = stack.pop()
                size += 1
                for e in item.link_edges:
                    other = e.other_vert(item)
                    if other not in seen:
                        seen.add(other)
                        stack.append(other)
            components.append(size)
        area = sum(f.calc_area() for f in bm.faces) * abs(
            o.matrix_world.to_3x3().determinant()
        ) ** (2 / 3)
        # 通用矩阵可能非均匀，不以缩放面积近似作工程设计输入。
        volume = None
        if not nonmanifold and not open_edges:
            volume = float(bm.calc_volume(signed=True) * o.matrix_world.determinant())
        bounds = np.array(
            [list(o.matrix_world @ v.co) for v in o.data.vertices], dtype=np.float64
        )
        return {
            "name": o.name,
            "type": o.type,
            "vertices": V,
            "edges": E,
            "faces": F,
            "boundary_edges": open_edges,
            "nonmanifold_edges": nonmanifold,
            "wire_edges": wire,
            "connected_components": len(components),
            "component_vertex_counts_top3": sorted(components, reverse=True)[:3],
            "euler_characteristic": V - E + F,
            "signed_volume_m3": volume,
            "approx_surface_area_m2": float(area),
            "bounds_mm": {
                "min": (bounds.min(axis=0) * 1000).round(3).tolist(),
                "max": (bounds.max(axis=0) * 1000).round(3).tolist(),
            },
            "suitable_for_closed_uniform_pressure_proxy": open_edges == 0
            and nonmanifold == 0
            and len(components) == 1
            and volume is not None
            and volume > 0,
            "limits": "保形几何审计，不证明布片接缝、填棉、布料可缝合或几何自相交。",
        }
    finally:
        bm.free()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    if not a.input.is_file() or a.output.exists() or a.input.suffix != ".blend":
        raise RuntimeError("需要现有冻结 Blender 检查点及新的报告路径")
    bpy.ops.wm.open_mainfile(filepath=str(a.input.resolve()), load_ui=False)
    candidates = [
        o
        for o in bpy.context.scene.objects
        if o.type == "MESH" and o.name.startswith(NAME_PREFIXES)
    ]
    if not 10 <= len(candidates) <= MAX_READABLE_OBJECTS:
        raise RuntimeError(f"目标零件数量变化：{len(candidates)}")
    results = [audit(o) for o in sorted(candidates, key=lambda x: x.name)]
    main_body = next(
        (x for x in results if x["name"].startswith("PRIMARY continuous sculpt")), None
    )
    if not main_body or main_body["vertices"] < 100000:
        raise RuntimeError("未匹配到用户原始主躯干")
    result = {
        "status": "READ_ONLY_REAL_H_COMPACT_SHELL_AUDIT",
        "blender": bpy.app.version_string,
        "scene_objects": len(bpy.context.scene.objects),
        "target_meshes": len(results),
        "meshes": results,
        "simulation_ready": bool(
            main_body["suitable_for_closed_uniform_pressure_proxy"]
        ),
        "limitations": [
            "非实际布料试样",
            "非缝片连接图",
            "不保证法线以外的自交",
            "不含纤维棉填料本构",
            "不得把云团实体当作已缝入主布壳",
        ],
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf8"
    )
    print(
        "H_SHELL_TOPOLOGY_AUDIT",
        json.dumps(
            {
                "candidate_count": len(results),
                "primary": main_body,
                "closed_count": sum(
                    x["suitable_for_closed_uniform_pressure_proxy"] for x in results
                ),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
