---
name: pattern-engineering
description: 开发或修改毛绒玩偶二维裁片、帽片、缝线映射、对位缺口、1:1 SVG、材料经纬试片计算时使用；要求单位、几何不变量、负例与兼容性验证。
---

# 纸样与材料研发

**触发：** 新增裁片类型，修改裁片数/半径/帽片拼缝、布纹/裁切、修改材料试片指标、SVG 或研究筛选输入。只是查询现有能力时优先使用 `feature-map`。

## 开发顺序

1. 看 `docs/PROFESSIONAL_WORKFLOW.md`、`docs/ARCHITECTURE.md` 和 [研发与反例](references/研发与反例.md)；明确“合成目标”“来源几何”“实测材料”分别是哪种证据。
2. 保持计算进入 `src/plush_pattern_lab/patterns/`，数值检查进入 `validation/`，不把 `bpy`、私有资产、文件系统副作用混入纯几何函数。
3. 首先定义输入单位、坐标、面片/缝线身份、裁缝净线与缝份之别，及结果 JSON/真实比例 SVG 的兼容契约。
4. 用原场景和故意错配场景验证长度、方向、拓扑、边界；增加负例而非只求“画得像”。
5. 运行 `python scripts/check_quality.py`、相关 pytest 与完整 pytest；如果新纸样影响虚拟缝合或材料参数，再转 `blender-evidence` 实跑同条件 A/B。
6. 交付中区分几何候选、布料力学假设、尚未完成的实物打样，不下制造可行性结论。

不要因新设计模式而改动已通过的数学式；只有重复且存在独立变化轴时才抽象。
