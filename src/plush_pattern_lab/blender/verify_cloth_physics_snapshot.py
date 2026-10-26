"""独立重开 Cloth 72 帧输出，验证模型快照真实与数值报告一致。

不能把静态快照误作原版生产纸样；仅验来源和保存后结果。
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np

CASES = {"unfilled", "gas_proxy", "spring_proxy"}
SOURCE_SHA = "e3ae7befad526938fd85d1460c1febb284292fc50fb887dd13a188faffb70fc2"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def positions(o):
    x = np.empty(len(o.data.vertices) * 3, np.float32)
    o.data.vertices.foreach_get("co", x)
    coords = x.reshape(-1, 3).astype(np.float64)
    m = np.asarray(o.matrix_world, dtype=np.float64)
    return coords @ m[:3, :3].T + m[:3, 3]


def volume(o, coords):
    m = o.data
    m.calc_loop_triangles()
    tris = np.array([list(f.vertices) for f in m.loop_triangles], dtype=np.int32)
    a, b, c = [coords[tris[:, i]] for i in range(3)]
    return float(np.einsum("ij,ij->", a, np.cross(b, c)) / 6.0)


def _verified_trial_inputs():
    p = argparse.ArgumentParser()
    for k in ("input", "report", "output"):
        p.add_argument("--" + k, type=Path, required=True)
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    if not a.input.is_file() or not a.report.is_file() or a.output.exists():
        raise RuntimeError("丢失独立结果，或拟覆盖已有复核文件")
    d = json.loads(a.report.read_text(encoding="utf8"))
    case = d.get("case")
    if case not in CASES or d.get("source_file_sha256") != SOURCE_SHA:
        raise RuntimeError("不允许其他来源的Cloth模型")
    if d.get("output_blend_sha256") != sha256(a.input):
        raise RuntimeError("布壳快照原文件SHA不符")
    if (
        d.get("frame_count") != 72
        or d.get("simulation_proxy", {}).get("proxy_faces") != 2400
    ):
        raise RuntimeError("当前只核验第72帧固定实验")
    return a, d, case


def _load_verified_scene(a, d, case):
    bpy.ops.wm.open_mainfile(filepath=str(a.input.resolve()), load_ui=False)
    sim = bpy.data.objects.get("PHYSICS_PROXY_MAIN_NOT_PATTERN")
    snap = bpy.data.objects.get("SNAPSHOT_" + case + "_NOT_SEWING_PATTERN")
    if not sim or not snap or sim.type != "MESH" or snap.type != "MESH":
        raise RuntimeError("保存场景未包含原动力学设置与最终静态网格")
    cloth = next((m for m in sim.modifiers if m.type == "CLOTH"), None)
    if not cloth or len(sim.data.polygons) != 2400 or len(snap.data.polygons) != 2400:
        raise RuntimeError("布料物理属性或几何面数变化")
    if len(sim.data.vertices) != 1202 or len(snap.data.vertices) != 1202:
        raise RuntimeError("布壳求解分辨率变化")
    if (
        abs(
            float(cloth.settings.mass)
            - d["assumed_material_and_fill_surrogate"]["vertex_mass_kg"]
        )
        > 1e-10
    ):
        raise RuntimeError("实际布料顶点质量与报告不一致")
    if (
        cloth.settings.use_internal_springs
        != d["assumed_material_and_fill_surrogate"]["internal_springs"]
    ):
        raise RuntimeError("填充弹簧设置不一致")
    if case == "gas_proxy" and (
        not cloth.settings.use_pressure
        or abs(cloth.settings.uniform_pressure_force - 0.07) > 1e-5
    ):
        raise RuntimeError("气压设置丢失")
    if case != "gas_proxy" and cloth.settings.use_pressure:
        raise RuntimeError("非气压实验意外开启了压力")
    return sim, snap


def _verify_snapshot_metrics(sim, snap, d):
    rest = positions(sim)
    final = positions(snap)
    if not np.isfinite(final).all():
        raise RuntimeError("已保存快照存在非法位置")
    delta = final - rest
    rms = float(np.sqrt(np.mean(np.sum(delta * delta, axis=1))) * 1000)
    maxi = float(np.linalg.norm(delta, axis=1).max() * 1000)
    vl = float(volume(snap, final) * 1000)
    reported = d["last"]
    if abs(rms - reported["rms_displacement_mm"]) > 0.005:
        raise RuntimeError(
            f"快照 RMS 与求解器报告不一致: {rms} vs {reported['rms_displacement_mm']}"
        )
    if abs(maxi - reported["max_displacement_mm"]) > 0.005:
        raise RuntimeError("快照 max displacement 与求解报告不一致")
    if abs(vl - reported["signed_volume_l"]) > 0.005:
        raise RuntimeError(
            f"快照体积与求解器报告不一致: {vl} vs {reported['signed_volume_l']}"
        )
    if not np.allclose(
        (final.max(axis=0) - final.min(axis=0)) * 1000,
        reported["extent_mm"],
        atol=0.005,
        rtol=0,
    ):
        raise RuntimeError("保存后轮廓包围盒漂移")
    return rms, vl


def main():
    a, d, case = _verified_trial_inputs()
    sim, snap = _load_verified_scene(a, d, case)
    rms, vl = _verify_snapshot_metrics(sim, snap, d)
    report = {
        "status": "PASS_INDEPENDENT_PHYSICS_SNAPSHOT_SAVE_REOPEN",
        "case": case,
        "input_sha256": sha256(a.input),
        "snapshot_mesh_vertices": len(snap.data.vertices),
        "source_mesh_vertices": len(sim.data.vertices),
        "rms_displacement_mm": round(rms, 6),
        "volume_l": round(vl, 8),
        "camera_belongs_to_static_preview": bpy.context.scene.camera is not None,
        "does_not_prove": "纤维棉物性、缝制可行、纸样、生产、材料安全",
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8"
    )
    print(
        "PHYSICS_SNAPSHOT_REOPEN_PASS",
        case,
        json.dumps(report, ensure_ascii=False),
        flush=True,
    )


if __name__ == "__main__":
    main()
