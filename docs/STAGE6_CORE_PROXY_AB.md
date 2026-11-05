# Stage 6 主壳：非破坏性低密度制造代理 A/B

当前是**三维几何研究代理**，不是已获批准的完整角色纸样、BOM 或量产文件。项目路线：[工厂路线图 P3](FACTORY_ROADMAP.md)，此前实测主壳 [V/E/F 拓扑证据](../experiments/stage6_core_shell_20261104/topology.json)。

## 实验目标和输入

公开 Stage6 主壳实测 234,161 顶点、700,441 边、466,278 三角面、1 个面连通区域和四个512点蹄部开放环，均无非流形或游离边。它是高密度视觉网格，不等于能直接裁剪的布片。

本轮固定公开源模型 SHA-256 **38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a**，仅比较两种相同条件下的减面目标比例：**0.50 与 0.25**。

1. 通过 Blender 4.3.2 和 --disable-autoexec 核对公开 .blend 的 SHA；先执行原四蹄严格配准。
2. 将高密度主体复制到**独立研究对象**，不得改原始数据或保存回源模型。保护四个512点洞口及相邻**两圈**拓扑顶点；只有剩余内部顶点加入 Blender Collapse Decimate 顶点组。
3. 对减面结果重新检查四条有向边界的每个顶点世界毫米坐标、原始顺序/绕向和唯一的旧顶点到新顶点身份映射。任何破坏即**拒绝代理导出**，保留实测报告。独立检查 V/E/F、面片连通、Euler、非流形/游离边。
4. 几何门禁通过时输出仅含主体的 **PLY（mm）**；绝不上传原始 90 MB .blend、毛发对象或历史脚本。研究 JSON 同时保留所有失败原因。
5. 固定等间隔采样源→代理以及代理→源的最近三角面距离，报告平均、P95、最大和 RMS（毫米）。它**不是连续 Hausdorff 上界**、面料主伸长或真实填棉外观验收。
6. 所有输出严格标明 NOT_FACTORY_PATTERN，不能仅因保留四蹄边界或减面成功就标成正式制造合格。

Blender Decimate 的 vertex group 控制并不天然保证缝线不变，必须重算上述门禁。参考：[Blender 4.3 Decimate 官方手册](https://docs.blender.org/manual/ca/4.3/modeling/modifiers/generate/decimate.html) 与 [Blender Python API](https://docs.blender.org/api/4.0/bpy.types.DecimateModifier.html)。

## 可信复现命令

~~~bash
blender --disable-autoexec --python-exit-code 1 -b -t 1 \
  --python scripts/build_stage6_core_proxy.py -- \
  --input /tmp/verified-public-stage6.blend \
  --source-sha256 38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a \
  --output /tmp/stage6-core-proxy-ab.json \
  --proxy-dir /tmp/stage6-core-proxy-ply
~~~

主仓受信任工作流入口：.github/workflows/stage6-hoof-seam-reference.yml。只有通过独立拓扑和接缝核验的候选才会输出 core_shell_proxy_ratio_0.50.ply 或 core_shell_proxy_ratio_0.25.ply；PLY 不含腿蹄、云团、耳尾、五官、材料和 2D 缝份。

## 对真正可缝纸样的下一步

根据保留四蹄身份的最佳保形代理，**先在真实主体＋四腿上规划完整制版分区、裁片互配净缝线和返口/填棉路径**；随后才是二维约束展平、缝份、布纹方向、虚拟缝合、样布及实体打样。缺独立 BVH 自交与实际材料试片时，不得把研究代理转化为生产纸样。


## 2026-11-05 真实 Blender 4.3.2 测量与 PLY

[受信任 Stage6 工作流 #41953627248](https://github.com/timlincool/plush-pattern-lab/actions/runs/41953627248) 已用同仓库固定 SHA 的 Stage6 原模型实跑两种比例。双方都保留 **4×512 个原有开放边界点**，每点世界坐标最大偏移 **0.0000 mm**，有源/代理逐点顶点 ID 映射。原主壳 234,161点/466,278面未被修改，按边连续组件仍为1、Euler=-2、无非流形/游离边，独立导出两个仅含主壳的研究 PLY。

| 同源 A/B | 原始 | 50%目标 | 25%目标 |
|---|---:|---:|---:|
| 顶点 | 234,161 | 117,591 | **59,306** |
| 三角面 | 466,278 | 233,138 | **116,568** |
| 原表面→代理采样 P95 (mm) | — | 0.003977 | **0.009736** |
| 原表面→代理采样最大 (mm) | — | 0.006782 | **0.018427** |
| 代理→原表面采样 P95 (mm) | — | 0.003906 | **0.009980** |
| 四组512点边界误差 (mm) | — | **0** | **0** |
| 单连通／0非流形／Euler=-2 | 原模型证实 | **成立** | **成立** |

[长期证据 JSON（含双方 PLY 哈希与原来源）](../experiments/stage6_core_proxy_20261105/summary.json) 对应源 SHA、Blender 版本、运行号、点/面数量、采样方式及 PLY 校验值。原始 Actions Artifact 暂存7天；过期后使用公开源 Release 和本仓库脚本可重新生成。

- ratio 0.50 的 PLY SHA-256：22020a5631ccd6b171f242d6c5c9f9713e9b0d600a20f8a0fcf3b7c08149bd4f。
- ratio 0.25 的 PLY SHA-256：5b52e3fd09c83b19c5b9d95d6d8d859a147ff4deef90f1518f868d2e82e3a2dd。

**初步选择 25% 方案作为下一步制造分片研究起点**：已保留所有原四蹄世界点位，同时减少 75% 三角面，实测采样 P95 约 0.0097mm。然而这只是顶点到最近面采样，并非全曲面 Hausdorff/轮廓证明；**还没做独立的代理面朝向一致性、BVH 自交、与所有装饰组件接触和四视图比对**，因此不是已验收生产纸样。下一阶段应从这约 59k 点模型规划完整头身/四腿曲面分片、净缝线和填棉返口，不再仅调局部顶点权重。
