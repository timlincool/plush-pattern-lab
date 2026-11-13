# Stage6 头顶 Z230 原始三闭环 vs 现有 A/B 24片旧顶盖：1:1 设计校正图

**状态：P3 真实三维源截面对照（设计核对工具），不是可裁布纸样、真实缝线、缝份或工厂技术包。P3 in_progress；P4 not_started，正式工厂裁片0。**

## 为什么做这一张 A4

此前 ABF vs FreeCAD 同源12组实验已完成：FreeCAD 改善边长 P95，但两侧缝长一致性不如 ABF，双方0/12同时通过质量预筛。问题是**真实三维造型如何分片**，而不是再造新 UV 求解器。

[原始 Stage6 真实截面](STAGE6_TRUE_SOURCE_CONTOUR_GATE.md)与[跨高度源面连续性](STAGE6_TRUE_SOURCE_SLAB_LINEAGE.md)证实 Z230mm 有中央+左右三个分离的真实原源三角面交线，Z230→245主头顶中央环终止，两侧环继续，Z245靠近内外耳原视觉Mesh；但这些**不自动是可缝布片**。旧24片A/B的头顶纸片只有一张基于点云百分位的单环包络，把三条原始截面包在一个较长外圈内，不能拿数字拼缝当成忠实外形。

## 同坐标、同高度、同尺度的真实对照

源 Stage6 Blender SHA-256：`38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a`。复用可信原 Blender [#43359212094](https://github.com/timlincool/plush-pattern-lab/actions/runs/43359212094) 产生的两份**同轮原始Artifact成员**：

| 原始文件 | 已核实 SHA256 |
| --- | --- |
| `true_stage6_source_section_detail.json` | `f99ddcb834b4e68bec2487b41730e805c14928953b768d41fc249efe44920717` |
| `split_volume_toile_AB_research/two_volume_source_envelope_ab.json` | `eebda049ac34ee201a3251b363a915fa05ad6417394bc565bb4cc7942b4545ae` |

`scripts/build_stage6_crown_230_overlay.py` 从上面**原数据**读取 Source 顶点边对以及精确3D平面内插坐标，逐环重算 `SHA256(源边ID + 原XY)`、Polygon闭合、无重叠与周长；A/B须同一原始顶盖及同 Z230。没有修改任何原Source顶点、源面、切缝或工厂研究门槛。

| Z230截面项目 | 原始三角面实测 |
| --- | ---: |
| 中央闭环 | **189交边、153.094mm周长** |
| 左侧闭环 | **113交边、45.517mm周长** |
| 右侧闭环 | **112交边、45.511mm周长** |
| 三条真实截面周长之和 | **244.122mm** |
| 旧A/B单片头盖外围 | **319.771mm** |
| 旧单片顶盖 / 原中央环 | **2.089倍** |
| 原中央 vs 旧顶盖同高XY边界Hausdorff距离 | **38.212mm** |

研究渲染仅作**刚性平移与Y轴翻转**（1原毫米 = 1纸上毫米），一张 `210×297mm` SVG 对照真实中央蓝、左绿、右紫、旧单片橙色虚线；附 100mm 标尺和 10×10mm 打印校验框。所有原环按真实XYZ原截面投影，**不是三维曲面的布片静止展开**，也没有任何缝份、净缝工艺、毛向、制版镜像、填棉或实际材料认证。

## 永久源证据与复现

由于 GitHub Action Artifact 默认只保留7天，本仓库将真实同一原 Stage6 源数据中 Z230 的 **414条原三角形交叉边 Vertex ID+真实插值XY** 与旧A/B头顶64点单环一并保存在[27KB精简Witness](../experiments/stage6_z230_true_crown_20261113/witness.json)，原始完整13层文件SHA和旧A/B完整试样SHA仍原样记录。每环独立存储原交边ID/XY哈希与完整长度，**不声称这是一张可以缝的布片**。程序固定校验Witness SHA-256 `b561770a6cfeaea33abedc11bfb3992b2fe80b4bf83d10a66459682938af6571`，拒绝原始来源、三环或旧A/B轮廓遭替换。

正常情况下不需要下载原始90MB Blend，也不依赖已过期的 Actions ZIP：

```bash
python scripts/build_stage6_crown_230_overlay.py \
  --svg crown_source_vs_old_AB_A4_REVIEW_ONLY.svg \
  --report crown_source_vs_old_AB_source_audit.json
```

如要审计最初同一受信 Runner 的完整文件，也支持 `--source-detail <original.json> --trial <trial.json>` 显式传入二者；仍严格校验两个原始成员SHA，而不是信任新文件名。每次输出拒绝覆盖已有文件。单元测试除故意篡改、缩放、少环、错源ID外，直接从本仓固定Witness重放全部414条真Source交边和真实319.77mm A/B旧盖片，**不依赖网络或重复运行Blender**。

## 接下来只解决一个实际设计决定

旧A/B上头盖**不应继续被当作忠实原Stage6顶盖**。下一设计审阅要确定中央头顶与两侧突出是否需要独立盖片、省道或另设真实源面分片；参考[已有真实41Mesh邻近证据](STAGE6_SECTION_41MESH_CORRESPONDENCE.md)和原选定设计正/侧/背/顶外观，先确认耳根/云层承接是否能藏缝。经工艺分片选择后，再让Blender ABF/FreeCAD的已实现求解器按同原Source净缝重算与比较，而不再调12组旧耳根算法。

**这一张纸只说明原模型哪里与旧母版不一致；不能直接打印剪布、也不能凭A4标尺证明实体缝合可行。**
