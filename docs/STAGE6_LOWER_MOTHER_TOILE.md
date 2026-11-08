# Stage 6 下半身制造母版研究：四个真实蹄口锚定的13片试缝套件

**研究等级：可信 Stage6 main 已从固定原模型实测四个源环与13片/4张A4研究试样，独立逐段数字配缝通过；材料/整角色外观/工厂仍未验证。** 不是整角色纸样、已批准DXF、工厂技术包、实体金样或儿童玩具合规证明。

## 为什么不再反复调高曲率主壳的UV

[完整可信 Stage6 C/D避脸实验](STAGE6_B2_FACE_AVOIDANCE_AB.md)显示原主壳四区和新增切缝虽源3D拓扑可切，却无法同时给出近似等长、无重叠、低应变的全片二维静止形状。若要求把雕塑原表面不加简化地直接拼成织物，会继续产生形式上漂亮、工艺上不能缝的结果。

本项先单独解决**结构必需的四蹄与下腹承接**，用较低复杂度的新母版替代雕塑的复杂下半部连接方式。做法不是把旧B三片重命名成合格纸样，而是从原蹄口位置、形状和长度设定可试布的接口，然后用新增组件明确谁与谁配缝。

## 必须区别的原始源与新增设计

实际输入为公开 [Stage6可编辑Blend](https://github.com/timlincool/plush-pattern-lab/releases/tag/cloud-alpaca-stage6-visuals-20261028)，原源SHA-256 `38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a`；由该模型受信Runner重算的25% PLY SHA-256 `5b52e3fd09c83b19c5b9d95d6d8d859a147ff4deef90f1518f868d2e82e3a2dd`。主壳的四个开放边界都在 **Z≈20mm**，每个512条原始面边且平面有效。中心与源周长实测：

| ID | 源坐标 X/Y/Z（mm） | 原512边3D净缝线长度 |
| --- | --- | ---: |
| FL 左前 | −29 / −34 / 20 | **101.6403 mm** |
| FR 右前 | +29 / −34 / 20 | **93.3091 mm** |
| RL 左后 | −29 / +81 / 20 | **119.1003 mm** |
| RR 右后 | +29 / +81 / 20 | **119.1003 mm** |

前蹄左右的原净缝不同，**禁止一键复制4个完全相同的圆孔**。原source Vertex IDs、512边顺序、每个原Source环的XY几何与各段长度均需保留，由独立QC逐段验算；布筒的定位记号沿源ID的第0/128/256/384个顶点记录，而不是把物理缝线简单四等分后猜记号。

**新母版并非原Stage6连续主壳表面：** 
- 构造一块研究性**下腹YOKE-01**，临时假设平面Z=60mm，4个独立内孔净缝线轮廓使用Z20的原蹄口XY投影；YOKE外轮廓为四原蹄口凸包外扩**18mm**后的64源序研究弧段。这是便于试缝的**新结构**，不是现有源上Z60处真实连续净缝。
- 四条 `LEG-FL/FR/RL/RR` 布筒高度暂设 **40mm**，研究连接Z60的YOKE与Z20的原蹄口；每条布筒顶部和底部的展开净缝以**原512个源边逐段累计**，避免通过缩放或改边长掩盖误差。
- 四块 `SOLE-FL/FR/RL/RR` 平面试样端片：净缝使用同一原512边XY投影。**实际Stage6的Rounded hoof base为20mm厚的三维鼓起蹄底，绝未完成其真正的2D裁片展开；平面SOLE不是替代已验证成品蹄底。**
- 四条 `BAND-1..4` 平直围带各高40mm，把YOKE外周64段原研究线分成四段，底边数值缝线逐段一致、纵向侧边等长。四条围带的**上沿仍完全未配到真实头身**，不能因此说整个玩偶主壳已完工。
- BAND-3/YOKE外周缝线约35–65%处预留研究性返口标记；**上围口仍是开放的**，实际翻面、填棉与最终返口位置尚未通过实体测试。

## 四页可量测 A4 试布样纸（P3局部）

| 页面 | 实际部件 | 裁切/净缝与对位 |
| --- | --- | --- |
| `sheet-01.svg` | 四孔下腹YOKE一片 | 黑色裁线：外围净缝外扩6mm、四蹄内孔裁切线**向孔心内缩6mm**；蓝线四个真实来源蹄口净缝、外围研究净缝 |
| `sheet-02.svg` | 四条独立布筒各一片 | 各有不同蹄口长度的顶/底缝线，四组源Vertex ID定位点、左右40mm侧缝 |
| `sheet-03.svg` | 四个**平面临时SOLE** | 原512边投影净缝，外扩6mm临时缝份，不能替代原三维蹄底打版 |
| `sheet-04.svg` | 四条外围连接带各一片 | 每带16段对应YOKE外围母线、侧缝40mm，预留上口和BAND-3候选返口 |

所有纸张必须使用 `width="210mm" height="297mm" viewBox="0 0 210 297"`，严格A4 **100% Actual Size** 打印，先用尺测10×10mm校准框，不可“适应页面”。蓝虚线净缝、黑线裁切、橙点按真实来源ID对位、紫线试验返口。**6mm缝份只是没有厂商材料确认的研究假设。**

新纯计算位于 `patterns/stage6_lower_mother_toile.py`；独立QA在 `validation/stage6_lower_mother_toile_qc.py`；A4 SVG绘图在 `patterns/stage6_lower_mother_toile_svg.py`。可信运行命令：

```bash
python scripts/build_stage6_lower_mother_toile.py \
  --proxy /tmp/stage6-proxy-candidates/core_shell_proxy_ratio_0.25.ply \
  --source-sha256 38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a \
  --out-dir /tmp/stage6_lower_mother_toile_research
```

输出 `manifest.json`、`lower_toile_source_geometry.json`、`lower_toile_seam_audit.json`、`sewing_guide.md` 与四张来源一致A4 SVG；所有文件SHA-256记录在manifest中，不覆盖旧研究或公有原Blend。受信 `main` 工作流拥有 `contents:read` 且加载固定SHA，只有实跑成功才能把证据提升为可信数据。

## 2026-11-08 可信 Stage6 主分支运行与原始样纸实测

- [Blender 实际 Stage6 #42460875416](https://github.com/timlincool/plush-pattern-lab/actions/runs/42460875416) 完成，从固定SHA公开Blend→25%代理PLY→原四蹄环→13件研究YOKE/LEG/平面SOLE/BAND→四张 A4 XML SVG 及 source JSON、独立 seam QC、试缝指南、manifest，并由同一受信工作流复核纸张大小、2048真实边和未配上半身状态。后续 [Python #42461595194](https://github.com/timlincool/plush-pattern-lab/actions/runs/42461595194) **474项测试、Ruff静态与包构建通过**。
- 实测蹄口圆周：左前 **101.640317056mm**、右前 **93.309140290mm**、左后 **119.100288087mm**、右后 **119.100289524mm**。独立Q​C逐条512边长差最大约 `7.11×10⁻¹⁵mm`（**同一原始点集的浮点计算精度，非布料尺寸精度**）；4组BAND外围64个边逐段差最大约 `1.42×10⁻¹⁴mm`，新YOKE外围净缝 **566.505532mm**。
- YOKE四孔裁切合法、四个原蹄口与新外围边净缝间最小距离 **17.638mm**；暂定缝份6mm，下腹试片裁切面积 **24,423.43mm²**；研究性BAND-3留返口 **42.487mm**，但四个上围边**完全开放**，不能声称已实际通过翻面/填棉。
- 在原Stage6主壳真代理Z≈60mm上下3mm样本（2,019源顶点），其1～99%分位XY包络为 X≈−53.14至+51.38mm、Y≈−60.04至+113.62mm；新YOKE外围为 X≈−62.51至+61.26mm、Y≈−68.73至+122.05mm。新结构XY包络四侧与真源**相差约8.43～9.88mm**。这是**包围盒差异**，不是准确原轮廓误差或高精度表面拟合结果，证明本轮不能假装已复原真实Stage6。
- 对 [GitHub临时真实Artifact ID 13609516815](https://github.com/timlincool/plush-pattern-lab/actions/runs/42460875416) 中 `lower_mother_toile_research/` 的7个子文件与manifest逐文件计算SHA-256 **全部通过**；四张原始SVG已实际独立渲染作视觉检查，A4 `210×297mm`/校准方框存在。具体固定的 ZIP、JSON、SVG 原始SHA和真源签名保存在[永久研究摘要](../experiments/stage6_lower_mother_toile_20261108/summary.json)，而非只依赖临时Actions Artifact。

**局部软件与源净缝已经过第一阶段验证，但下腹母版的真实造型、两处四线交汇工艺、布料、上身对接与翻面未验证；目前不发布制造级1:1 DXF或正式工业纸样。**

**独立重复验证：**可信后修复 [Stage6 #42461595241](https://github.com/timlincool/plush-pattern-lab/actions/runs/42461595241) 实际完成。与先前 #42460875416 两个独立Job上传的源13片试布文件**逐成员字节完全相同**：4个SVG、`lower_toile_source_geometry.json`、`lower_toile_seam_audit.json`、`sewing_guide.md`、`manifest.json` 的SHA-256逐项一致。两个完整Artifact ZIP哈希不同是因内含其他阶段实验资产，而非这8个母版文件变化；原始ZIP哈希和成员详见[永久证据](../experiments/stage6_lower_mother_toile_20261108/summary.json)。

## 明确尚未解决的真正制造结构

**本轮交付的是局部四蹄承接试样，不是整只羊驼可缝制的母版。** 尤其仍缺：

1. 从YOKE外围四条上口**实际连接到头身/胸颈母版**，并保证接缝线段顺序和左右净长一致。原连续主壳在Z60处不是平面YOKE，新造型外观变化必须量化。
2. 真实Stage6的四个三维鼓起蹄底需要独立低复杂度可展开方案，不能长期以平面SOLE代替；长短绒、材料经纬弹性与站立稳定性需要试布与填棉反馈。
3. 原始外观D参考正侧背顶四视角、头/颈、七云团、耳根、尾根、五官刺绣及10雨滴布片承接尚未批准。
4. 旧四区出现的两处四线交汇要通过新YOKE与实际配片结构**证明消除**，不能仅凭现在改了结构图就宣布解决；最终返口与缝制顺序需要实体验证。

通过本轮源蹄口、母版尺寸和配缝单测仅能说明**某个局部试样能按研究净缝线配对并在纸上打印**；不包含真实织物形状、工厂可制造性认证、P4整角色工业纸样、P5完整技术包或Golden Sample。唯一权威状态见[生产进度JSON](PRODUCTION_PROGRESS.json)。
