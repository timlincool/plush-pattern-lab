# 毛绒面料实测：从“任意刚度”走向有来源的物性参数

专业设计人员在 Marvelous Designer / CLO 中可以试验缝合后压力支撑，但不能把气压直接等同于真实聚酯纤维棉。可参照 [毛绒设计师的实际测试方法](https://www.marvelousdesigner.com/learn/userspotlight/post/a5fc6095271d40faaaac58937898b431)：裁10×10cm布样，测不同方向的伸长，再缝合、填充并对照成品尺寸，逐步校准模拟参数。

## 输入数据合同

`examples/synthetic_swatches.json` 为**明确标注的合成演示数据**，绝非真正采购面料测量：

- 面料批次、规格、面密度（g/m²）、厚度/毛长（mm）
- 经向/纬向分别记录试布宽度、初始标距（mm）
- 加载与卸载 `[length_mm, force_N]`，多点、单调采样
- 试验温湿度、速率及刺绣位置硬化区域（需要未来提供真实样本）

运行：

```bash
python scripts/material_calibration.py --input examples/synthetic_swatches.json --output output/swatch_report.json
```

输出：经/纬方向归一化拉伸斜率（N/m 每单位工程应变）、加载/卸载做功（J）、滞回比、各自有效应变范围与经纬刚度比。**这些不是直接可用于 Blender 的真实物理参数**；剪切、弯曲、绒毛层压缩/纤维棉填充仍需要独立试验。

本合成示例预期经纬比约 **2.26**，经向 0.02–0.10 应变段归一化斜率约 **1187.5 N/m**，纬向约 **525 N/m**。这些数字只用于测试程序是否按单位计算，绝不用于玩偶制造建议。

真实材料采样的下一步是建立 *同一试布–同一缝线–同一填充质量–同一形变* 的 A/B 对照。没有标定样布，不应宣称物理仿真预测准确。
