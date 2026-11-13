# Stage6 原源 FreeCAD flatmesh vs Blender ABF：隔离实测

状态：**独立受信 main 真实运行 #43362970238 和 #43363281140 均成功**；12组实测及否决见[完整真实结果](STAGE6_FREECAD_FLATMESH_REAL_AB.md)与[永久摘要](../experiments/stage6_freecad_flatmesh_vs_abf_20261113/summary.json)。不修改原 Stage6 ABF→GPL SVG 主流程。P3进行中，P4未开始，工厂正式纸样0片。

## 关键源码事实：flatmesh 仍使用 LSCM

FreeCAD 的 [MeshFlattening.cpp](https://github.com/FreeCAD/FreeCAD/blob/main/src/Mod/MeshPart/App/MeshFlattening.cpp) 中 `FaceUnwrapper::findFlatNodes(steps,val)` 首先执行 `LscmRelax.lscm()`，然后循环执行 `relax(val)`。因此本轮不是“完全独立 UV 算法 vs ABF”，而是 **FreeCAD 原生 LSCM＋10轮 relax(0.95) vs Blender 原生 ABF**。FreeCAD 原生 pybind11 `flatmesh` 是 LGPL-2.1-or-later 的编译组件，不是可直接用 pip 安装的普通 Python 模块；接口正是 `FaceUnwrapper(xyz, triangle_indices).findFlatNodes(10, 0.95).ze_nodes`。

仅调用 FreeCAD 原生编译库，不复制/改写其 C++ 求解器；借助已公开的 [goatchurchprime Blender＋FreeCAD 原型](https://github.com/goatchurchprime/blender-seams-to-sewing-pattern/tree/0ea2585105a13e03cf017cca53da684b31eb97df) 复用其固定的 `magic-blender` Nix 环境。在独立进程中运行，避免与本仓 Blender 4.3.2 产生二进制/Python 版本冲突。GPL 插件和 LGPL FreeCAD 代码均不 vendoring 到本仓库。

## 可复现输入

使用 [原真实成功 Stage6 #43359212094](https://github.com/timlincool/plush-pattern-lab/actions/runs/43359212094) 的同一研究 Artifact，下载原 N15/N17 左右耳根×3种侧缝 **12块源圆盘**，固定三个实际成员 SHA256：

- 原源 `true_stage6_ear_root_slit_lscm_research.json`：`292be7e50f7c3b20bbcd03c8bccc86d501fc71c2ccb45fa737299f1c39134027`
- ABF/Conformal 原始 UV：`c841bff599c5eabeb8ba5928d4ae414ff61c76f59909e3c36d7902e481a2cf6b`
- 现有独立同源评分：`6ced983f402d32a1aa63b509d4f01ec477ea37ae36728a936faf336805cbb6f8`

本轮不重复下载 90MB .blend、不重新产生12块新源、不运行收费软件。旧原模型 SHA `38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a` 不变。

## 实验与判定

- 现有 `scripts/run_stage6_freecad_flatmesh.py` 只通过 `flatmesh.FaceUnwrapper` 读取原 `XYZ` / `FaceID` 局部三角索引，保留所有源顶点顺序和身份；调用 `findFlatNodes(10,0.95)`，每块保存原源匹配的 `ze_nodes` 二维值或独立失败状态，**绝不自动将失败样本丢掉**。
- `scripts/compare_stage6_freecad_flatmesh.py` 直接复用已存在的 `stage6_external_uv_benchmark._metrics`，与 ABF 使用**相同**源三角边、全局等比校准、P95长度误差、同一源切缝双侧二维长度差、翻转/正面积重叠门禁。
- 比较所有12组而不是挑一张漂亮图片；联合研究预筛仍为 P95≤10%、净缝两侧差≤3%、0翻转/0重叠。此阈值不是材料生产容差，均不批准工厂裁布。
- `.github/workflows/stage6-freecad-flatmesh.yml` 完成初次受信主分支实跑后仅允许手工 workflow_dispatch 再测，GitHub读权限、18分钟硬超时、独立失败Artifact保留7天。两次成功实跑后的结果已经归档到 `experiments`，绝不根据预期或编译成功编造改善数字。

## 决策

FreeCAD 若只改变UV数值而不能改善P95/拼缝/重叠，则**保留 Blender ABF 为默认**，停止增加 FreeCAD 工程复杂度。即使某一片通过研究数值门槛，也还缺头颈外形、真实鼓蹄、云朵/耳/尾/雨滴、缝份、毛向、返口、实际填棉及真实布样。工厂纸样认可始终由真实物理试缝与设计签核决定。
