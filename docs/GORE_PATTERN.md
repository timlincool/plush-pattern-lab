# 可复现的八瓣椭球形毛绒玩偶裁片

这是**专业制版原理的独立合成基准**，不含私有羊驼模型和原设计图。

## 用法

```bash
python scripts/plush_gore_pattern.py --radius-mm 55 --half-height-mm 70 \
  --panels 8 --segments 64 --allowance-mm 6 --out-prefix output/ellipsoid
```

生成 `output/ellipsoid.json`（含8组环形缝线关系、方向、缺口、经向和误差）与 `output/ellipsoid.svg`（**研究用**净缝线/裁切线）。不会覆盖旧输出。

## 实际执行过的几何校验（55×70mm 半轴、8 瓣、64 分段）

- 环绕侧面的每组两条缝线：约 **197.0373mm**。
- 2D 每段缝线 vs 3D 椭球经线最大误差：约 **1.4×10⁻¹⁴mm**（构造保证，浮点取舍）。
- 三角片主伸长最大偏差：**12.85%**；95 分位 **12.45%**。这是几何畸变，**不是实测布料承受的应变**。
- 总二维表面面积约为所采样三维表面面积的 **99.12%**；这不能代替局部形变门禁。
- 增加 `--panels` 往往减小单片面积畸变，但增加缝线和人工成本，应作为工程取舍而非“片数越多越好”。

## 与专业工具的关系

`Plushie` (SIGGRAPH 2007) 要求三维建模始终与2D纸样模拟相互约束；`ToyAssembler` (Computer-Aided Design 2022) 以缝线对应关系图定位二维纸样再动态缝合。服装计算制版研究强调面料布纹方向、缝线对称、裁片划分和局部畸变，不仅匹配总体面积。

本实现完成**合成形体的裁片几何、缝线一一配对和数值变形审计**；尚未实现真实二维动态缝合、真实布料或填棉压缩标定。禁止据此生成工厂定版。

- https://doi.org/10.1145/1276377.1276433
- https://doi.org/10.1016/j.cad.2022.103356
- https://igl.ethz.ch/projects/computational-patternmaking/
