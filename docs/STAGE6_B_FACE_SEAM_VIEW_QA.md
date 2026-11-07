# Stage6 B三片新增高位缝与历史五官位置：真实正面射线审查（P3）

**证据等级：可信 main Stage6 #42411444680 已真实复核固定PLY上的前表面鼻口位置风险；仍非最终外观设计签核或工厂裁布批准。**

## 来源和不可替代的限制

- 公共 Stage6 Blend SHA-256 `38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a`；25%主壳 PLY SHA-256 `5b52e3fd09c83b19c5b9d95d6d8d859a147ff4deef90f1518f868d2e82e3a2dd`。
- B三片原径向缝 source Vertex ID、原3D长度与整个主壳 Face ID来自同一次受信 Stage6 Runner `leftfront_multidisk_summary.json`。
- `design/reference-v25/face_embroidery_registration_v14.json` 提供历史鼻、嘴、眼在世界X/Z平面的注册坐标；**其结构目标是iteration12，不是已冻结的 Stage6 厂商五官**。它仅能做初步位置冲突筛查。
- 视角约定：X=0左右中心，负Y正面，Z向上，mm；射线从负Y朝+Y取真实代理三角形的首个交点，计算缝线上每个源顶点与首交面的深度差。差≤0.7mm视为“位于主壳正面附近”，但不等于云朵/毛绒遮挡下最终可见。
- 历史五官警报规则：处于主壳正面，且X/Z投影落在历史眼椭圆内，或与历史鼻/嘴绣线段距离≤3mm。**这只是研究筛查窗口，非工厂缝份或面料公差**。

## 可信 Stage6 Blender 主分支真实复核（2026-11-08 UTC+8）

[可信 Stage6 主壳/四蹄/原B三条切缝复算 #42411444680](https://github.com/timlincool/plush-pattern-lab/actions/runs/42411444680) 已实际重建源SHA固定25%代理并在原三角面计算 front first-hit 与历史 v14 五官注册线距离。对应研究 ZIP 包含带源顶点ID/逐点3D深度/原历史绣线见证的 `leftfront_source_face_review.json` 和真正五视角 `leftfront_body_only_5views_face_review.svg`，原始文件 SHA、历史v14源SHA和 Action Artifact ID 均保存在 [永久摘要](../experiments/stage6_face_seam_review_20261108/summary.json)。合并后 [Python CI #42411704796](https://github.com/timlincool/plush-pattern-lab/actions/runs/42411704796) 已完成418项测试、Ruff与构建。

研究证据范围限 **body proxy + 历史v14五官X/Z**，不能代替真实42Mesh上所有可见面、绒毛和设计图注册的工厂视觉审查。

| 原真实径向缝 | 3D源长度 | 顶点数 | 主壳正面近侧采样 | 主壳背面遮挡采样 | 历史五官警报 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 原短缝 | 40.8921mm | 33 | 32 | 1 | 0 |
| 1 高位缝 | 224.9200mm | 143 | 0 | 143 | 0 |
| **2 高位缝** | **210.6458mm** | **132** | **126** | **6** | **8** |

关键真实见证：B高位路径2末点的源顶点ID `40436`，世界坐标约 `(-0.9331,-86.3353,190.2309)mm`，同一X/Z下源主壳正面首交深度与其Y基本一致；距离历史鼻Y形绣线约 **0.5754mm**。另外鼻与嘴口附近至少7个连续真实源点也落入3mm研究筛查窗口。

**研发判断：B的原路径2很可能穿越拟定的鼻口刺绣区，不应当作已经隐藏的缝线使用。** 即便其二维无重叠/边长误差日后改善，也必须先完成外观避让与工艺接合审查。

## 五视角SVG是什么、不是什么

`patterns/source_seam_view_svg.py` 从固定真实25% PLY投影**正、背、左、右、顶**五个正交视图，画出原B三条源Vertex ID径向缝。仅正面用实际主壳首表面深度将自遮挡线段画虚线，粉色眼椭圆/鼻嘴属于历史X/Z注册参考；红圈标出前表面且临近历史鼻嘴的实际网格顶点。

**不是**从完整42 Mesh和真实毛纤维渲染的工厂外观，更不是设计参考图与Stage6已自动对齐；正面以外的视图仅为几何投影，没有遮挡/深度判定。云团、尾根、耳根、眼睛装饰层可能进一步覆盖或改变可见性，必须再对实际装配和工厂面料进行确认。

## 下一步

1. 首先将高位路径2在原设计正面及完成42 Mesh覆层的Stage6 Blender四视图中进行几何避让／覆盖判定，优先保证眼鼻嘴位置和表情，不得仅凭源主壳被遮挡就说隐藏。
2. 若有真实外观冲突，修改原3D源边上的路径/分片结构并重新执行拓扑、每片2D边长/折叠/重叠与原拼缝双侧长度审查；任何结果均需源SHA证明。
3. 处理已记录的两处四线交汇、返口、经纬/毛向、缝份及工厂材料实测；P3继续，P4仍未开始。

来源：[唯一生产进度](PRODUCTION_PROGRESS.json) · [现有B三片多盘数据](../experiments/stage6_multi_radial_20261107/summary.json) · [Tutte 凸边界失真反例](STAGE6_TUTTE_CONVEX_CONTROL.md)。
