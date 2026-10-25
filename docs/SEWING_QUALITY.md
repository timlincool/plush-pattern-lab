# 缝合闭合 ≠ 目标玩偶成形：Sewing Quality Gate v1

## 为什么需要独立质量审计

之前的 Blender 4.3.2 虚拟缝合确实把 8 片合成椭球体的 520 对缝线顶点间隙从约 5.06mm 压低至极小值。但这仅能证明 **sewing springs 拉动了接缝**，并不说明缝好后呈现目标轮廓，或仍可承受真实布料的拉伸。

本轮用独立的 `scripts/sewing_quality.py` 评价同一编号的 3D 顶点、静止二维裁片和合成参考三维形状，并由 `scripts/sewing_poc_blender.py` 在 Blender 求解后记录 **初始/最终两个报告**。

## 可执行数值定义

| 检查 | 计算办法 | 为什么不能取代实物 |
|---|---|---|
| 接缝间隙 | 每组缝合顶点距离的均值/P95/最大值，mm | 贴合不代表已焊接或强度合格 |
| 对目标形状误差 | 按明确编号的合成参考顶点做刚体最佳对齐（不缩放），计算 RMS/P95，mm | 仅有合成目标，真实相机/软毛姿态需重建登记 |
| 双向 Chamfer | 刚体对齐后，对两组**离散顶点**互找最近邻求平均，mm | 顶点密度敏感，不是连续曲面/有保证 Hausdorff 上界 |
| 局部主伸长 | 对每个 2D 静止三角形到 3D 求解三角形计算奇异值，取 `abs(σ−1)` 的 P95/最大值 | 这是几何主应变，不是面料安全伸长或无皱褶证明 |
| 面积比、疑似翻折 | 三维网格面积 / 静止二维面积；对比初始 3D 面法线与当前方向 | 法线翻面和零面积仅作预警，不是自相交/体积闭合证明 |

固定的 **负向测试**：故意将两块已完美合缝的试验面板一起放大 25%，其缝线间隙仍为 0，但目标形状误差和局部拉伸必须明显增加；测试不能因为“缝口闭合”给它假通过。此外验证刚体平移（世界坐标错误但对齐形状不变）、法线翻转、NaN、零面积二维片等反例。

## 物理建模边界

- 使用 Blender 4.3.2 `use_sewing_springs=True` 与 `rest_shape_key`；重力积分另由 Cloth Canary 负责任校验，**缝合 A/B 为零重力**，便于隔离缝合驱动力。 
- 结果保存 `.blend`、原始 2D 形状键、模拟后静态网格和完整 JSON。未设置自碰撞、真实样布正交异性、局部棉花填充，尚不构成稳定封闭布壳。
- 不是把模型的 3D 视觉外形当作静止布壳；所有拉伸量都以 `flat_rest` 净裁片长度为基准。
- 现在仅在**独立合成椭球**上建立监控，不会声称验证了私有云朵羊驼设计/物料/纸样。

## 后续优先级

下一阶段不先调高计算面数，而是让上述结果驱动优化：**闭合质量门禁 → 形状重建误差 → 局部主伸长/翻折 → 真实面料标定 → 自碰撞/填充**。没有真实面料和样布测试前，外观截图只能用于定性比较。

## 相关依据

- [Blender Cloth Shape / Sewing / Rest Shape Key 官方文档](https://docs.blender.org/manual/en/5.3/physics/cloth/settings/shape.html)——缝合弹簧只会把点拉近，Rest Shape Key 定义自然长度。
- [Inverse Garment and Pattern Modeling with a Differentiable Simulator (CGF 2024)](https://doi.org/10.1111/cgf.15249)——由模拟后形状偏差反向约束纸样；3D 评价采用 Chamfer 与法线角误差。
- [Computational Pattern Making from 3D Garment Models (SIGGRAPH 2022)](https://igl.ethz.ch/projects/computational-patternmaking/)——缝线对称、布纹方向、各向异性展开应变有界。
