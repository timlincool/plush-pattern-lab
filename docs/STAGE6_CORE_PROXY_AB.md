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
