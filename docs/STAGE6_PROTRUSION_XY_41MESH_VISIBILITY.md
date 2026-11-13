# Stage6 左右高位突出 X/Y：真实41产品 Mesh五视角原切缝预审

**待真实运行，不是已确定隐藏工艺缝。P3进行中、P4未启动、厂商正式纸样0。**

## 测试动机

[原真三维X/Y分片ABF](STAGE6_REAL_PROTRUSION_BISECT_ABF.md)已证明，两侧单片P95约94%，改为两片后明显改善；但X左/右新增切缝两侧ABF净缝逐段累计绝对差仍为**13.01%/6.90%**，超过3%研究门槛。BVH可见性不能消除这个制造否决。

旧[Z230/245与41 Mesh关联](STAGE6_SECTION_41MESH_CORRESPONDENCE.md)发现低位接近灰头云与额云、高位接近原外耳与内耳。邻近两层原截面**不证明X/Y新切缝经过云/耳**，必须沿真实路径重审。

## 复用技术、不自研新解算器

- 固定原Stage6 Blend SHA-256为38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a；25%原代理PLY SHA-256为5b52e3fd09c83b19c5b9d95d6d8d859a147ff4deef90f1518f868d2e82e3a2dd。
- 复用Blender 4.3.2现有 _object_bvh_cache、_five_view_hits、_independent_neighbor_hits，按真实原场景41个产品Mesh建立BVH，摄影棚地面排除。没有换UV算法、重新补面或创造缝线。
- 每个实际候选要求X/Y两方向、左右各一条全部纳入，不依照效果挑选。用同次原三维caps和bisect JSON哈希关联；逐个cap本地原Vertex ID核实双片Source身份/XYZ、原源FaceID分配完整、3D路径总长。
- 每条原路径确定性抽取至多20个cap-local源Vertex，含首尾。记录正背左右顶五视角**原始产品网格首命中**及6mm搜索半径其他独立Mesh的三角面近邻（按3mm归类），**不是全路径每条边扫描**，顶点ID也不是原高密Blend全球ID。
- 任一缺视角、缺路线、来源篡改、改面或原缝对不上就失败。输出报告始终保留工厂批准0、P3 in_progress、P4 not_started。

## 实际执行与证据

现有可信main Stage6 工作流在已经成功的原X/Y真实三维切割+ABF双侧缝长审计之后，用Blender受信原Blend和41 Mesh只读计算，产生：

  z230_three_real_caps_research/side_XY_meridian_41mesh_fiveviews_RESEARCH_ONLY.json

输出含4条源路径的有限采样、每采样点原Source XYZ和5视角首命中结果。直到真实Runner完成之前不填造比例；原始JSON由7天研究Artifact保存，重要结果进入永久实验摘要。

## 工艺否决边界

可见视图中源缝被独立网格挡住，仅表示原二维视线经过了某个3D装饰Mesh，**不等于绒毛、缝份、线迹、填棉后真的隐藏**。即使数值上优选X，已有ABF边差和配缝门槛仍失败；下部七开口主壳尚无真正匹配的二维缝线。下一步是结合原设计四视图人工选隐藏省道位置、实布试片与下部母版，而不是继续自研参数化。
