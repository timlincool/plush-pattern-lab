# 已缝合布壳的非相邻面相交检查（2026-10-25）

**结果：开启 Blender 自碰撞并不等于成品无三角面穿插。** 此模块在保存后的真实合成试验 `.blend` 上重新检查，与 Blender Cloth 缝合求解和分析性拓扑检查相互独立。

## 工程依据与方法

- Blender 4.3.2，`mathutils.bvhtree.BVHTree.FromPolygons` 建立三角面 BVH，对同一 BVH 调用 `overlap`。
- Blender C 源码中 BVH callback 使用 `isect_tri_tri_v3` 交叉测试；代码移除自相交同一面、重复索引对与共享原顶点的邻接面片对。共享顶点的明显翻折可能被排除，这不是完备几何定理。
- 使用原始 Cloth 模型 `is_loose` 缝线边关系，把交叉见证分为**缝线相关**和**其他非邻接**；两者都不会直接当作可生产接缝。
- 审计脚本 `scripts/audit_self_intersections_blender.py`、反例 `scripts/verify_bvh_intersection_canary.py`，研究晋升否决 `scripts/assess_contact_integrity.py`。验签绑定同轮模拟 JSON 的 SHA，拒绝无来源报告。
- 阴性/阳性对照包括：两组三角面真实穿插、隔空分离、共享边邻接排除、缝线身份分类。简单开启 `use_self_collision` 无法替代这套独立检查。

## 真实实跑的观察

同一12侧片+上下盖、48帧、零重力合成研究模型，3,120个三角面：

| 有限面相交检查 | Cloth自碰撞关闭 | Cloth自碰撞开启 |
|---|---:|---:|
| 缝线相关面片相交对 | 900 | 851 |
| 非缝线相关相交对 | 4 | 7 |
| 原来的研究几何筛选 | 通过 | 通过 |
| 现在的交叉门禁 | **拒绝** | **拒绝** |

基准实跑：[40173028799](https://github.com/timlincool/plush-pattern-lab/actions/runs/40173028799)。这是保存重开的 Blender 真实几何，不能当作零厚度模型的全面认证，也不是实物材料内碰撞数量。

**重要：** 研究工作流成功运行只代表程序与数据采集成功；即使缝合间距/拓扑/主伸长都达标，独立穿插检查阳性仍禁止晋升为“无碰撞/可生产”。

## 仍需实验

- 对真实非相邻相交对分析对应裁片及接缝邻近程度，定位原因；不要把所有 900 多个缝线相关见证都解释为真实穿透或直接判安全。
- 用0.5/1/2mm等**假设厚度**做完整有限距离接触测量和灵敏度检查；从真实样布厚度测量校准。
- 后续研究需要面料伸缩、剪切、弯曲、摩擦、纤维棉压缩与滞回及真样物理对照。这些没有完成。

> 参考 Blender Python API `mathutils.bvhtree` 与 Blender 源文件 `mathutils_bvhtree.cc`。有限 BVH 三角片交叉见证不包含连续碰撞、所有共面/极小间隙、材料厚度或实际儿童玩具安全证明。

- https://docs.blender.org/api/4.4/mathutils.bvhtree.html
- https://github.com/blender/blender/blob/main/source/blender/python/mathutils/mathutils_bvhtree.cc
