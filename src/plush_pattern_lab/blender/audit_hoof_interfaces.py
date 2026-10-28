"""Blender 4.3.2 只读审计真实 Stage6 主体与四蹄的开放几何接口。

不修改模型、不生成二维裁片、不把配准成功当作缝制或制造合格。
调用时必须提供已核对的源文件 SHA-256，并用 --disable-autoexec。
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np

from plush_pattern_lab.validation.boundary_match import (
    unique_centroid_mapping,
    verify_mating_loops,
)

BODY = "PRIMARY continuous sculpt | new anatomy"
HOOFS = (
    "Rounded hoof base",
    "Rounded hoof base.001",
    "Rounded hoof base.002",
    "Rounded hoof base.003",
)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _boundary_successors(mesh):
    following = {}
    for edge in mesh.edges:
        if not edge.is_boundary:
            continue
        if len(edge.link_loops) != 1:
            raise ValueError("开放边界必须恰好邻接一个面")
        loop = edge.link_loops[0]
        origin = loop.vert.index
        if origin in following:
            raise ValueError("开放边界在同一顶点产生多个出边")
        following[origin] = loop.link_loop_next.vert.index
    if set(following) != set(following.values()):
        raise ValueError("开放边界不是一组有向闭合环")
    return following


def _walk_rings(following):
    visited = set()
    rings = []
    for start in sorted(following):
        if start in visited:
            continue
        current = start
        ring = []
        while current not in visited:
            visited.add(current)
            ring.append(current)
            current = following[current]
        if current != start or len(ring) < 3:
            raise ValueError("开放边界形成了错误的链或退化环")
        rings.append(ring)
    return rings


def object_boundary_rings_mm(obj):
    """在世界坐标提取拓扑上有向的边界环，而不是按最近距离猜顺序。"""
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.verts.index_update()
        following = _boundary_successors(bm)
        rings = _walk_rings(following)
        geometry = []
        for ring in rings:
            coords = [tuple(obj.matrix_world @ bm.verts[i].co) for i in ring]
            geometry.append(np.asarray(coords, dtype=np.float64) * 1000)
        return geometry, len(following)
    finally:
        bm.free()


def _source_objects():
    scene = bpy.context.scene
    names = (BODY, *HOOFS)
    meshes = []
    for name in names:
        obj = scene.objects.get(name)
        if obj is None or obj.type != "MESH":
            raise ValueError(f"指定网格缺失或不是 MESH：{name}")
        meshes.append(obj)
    return meshes


def build_report(source_hash):
    meshes = _source_objects()
    body_rings, body_edges = object_boundary_rings_mm(meshes[0])
    if len(body_rings) != 4 or body_edges != 2048:
        raise ValueError("主体应有四个 512 点的蹄部开放接口")
    hoof_rings = []
    for obj in meshes[1:]:
        loops, edges = object_boundary_rings_mm(obj)
        if len(loops) != 1 or edges != 512:
            raise ValueError(f"蹄部接口不是单个 512 点闭合环：{obj.name}")
        hoof_rings.append(loops[0])
    locations = unique_centroid_mapping(body_rings, hoof_rings)
    matches = []
    for obj, hoof, (index, gap) in zip(meshes[1:], hoof_rings, locations):
        result = verify_mating_loops(body_rings[index], hoof)
        matches.append(
            {"hoof": obj.name, "body_ring_index": index, "centroid_gap_mm": gap, **result}
        )
    return {
        "status": "REAL_MODEL_STAGE6_HOOF_INTERFACE_AUDIT",
        "source_sha256": source_hash,
        "blender": bpy.app.version_string,
        "body_open_edges": body_edges,
        "body_boundary_loops": len(body_rings),
        "hoof_count": len(hoof_rings),
        "interfaces": matches,
        "all_geometry_interfaces_match": all(
            row["world_boundary_geometry_match"] for row in matches
        ),
        "limitations": [
            "仅验证原始几何边界坐标和方向，仍保留分离网格",
            "不是二维净缝线或裁剪纸样，未证明缝份、布纹及材料伸长",
            "未验证装配接触、填棉、牢度、实体打样和玩具安全",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    a = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    )
    if not a.input.is_file() or a.input.suffix != ".blend" or a.output.exists():
        raise ValueError("源模型不存在、后缀错误或报告已存在")
    digest = sha256_file(a.input)
    if digest != a.source_sha256:
        raise ValueError("源模型 SHA-256 不符，禁止加载")
    bpy.ops.wm.open_mainfile(filepath=str(a.input.resolve()), load_ui=False)
    report = build_report(digest)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8"
    )
    print(
        "REAL_MODEL_HOOF_INTERFACE",
        json.dumps(
            {
                "body_loops": report["body_boundary_loops"],
                "hoofs": report["hoof_count"],
                "all_match": report["all_geometry_interfaces_match"],
                "max_gaps_mm": [x["max_gap_mm"] for x in report["interfaces"]],
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    if not report["all_geometry_interfaces_match"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
