# Stage6 耳根高位突出：原源边短省道 A/B（真实3D→Blender ABF）

状态：**源网格本地拓扑校验通过；受信 Blender ABF 真实数值待执行。P3进行中、P4未开始、正式工厂纸样0片。**

## 为什么不是继续优化全长X/Y切缝

[全长 X/Y 真实分片](STAGE6_REAL_PROTRUSION_BISECT_ABF.md)在左右各46～48mm，X 双侧2D逐段绝对缝长差仍13.01%/6.90%；[41原产品 Mesh五视角检查](STAGE6_PROTRUSION_XY_41MESH_VISIBILITY.md)发现X外侧视角许多点在原主壳第一表面附近，不能宣称原云/耳能够隐藏。

本轮**只选两个原已测路线的短半段**，不在ABF评分后筛选最优起点。用已有真实原Source三角网格和原边路径，以Z230原环的一点为开口，走到原高位突出源面最高顶点。保留顶部终点的原源顶点共享，仅重复切口上其它的Source顶点身份，使原单连通面形成一条边界**仍然连通**的开缝圆盘（不是无端分成两独立件，也不是新UV解算器）。

| A/B预声明候选 | 左原3D缝长 | 右原3D缝长 | 相对于原全长 |
| --- | ---: | ---: | --- |
| Y_REAR_RIM_TO_TIP 后侧底缘→顶点 | 22.8422mm | 23.4448mm | 旧Y约47.48/46.39mm |
| X_INNER_RIM_TO_TIP 内侧底缘→顶点 | 25.3810mm | 26.2836mm | 旧X约47.70/48.41mm |

以上4项仅来自原可信 Stage6 源网格的本地严格拓扑预检，**不代表二维形状改善或被耳/云隐藏**。

## 复用成熟代码与来源保护

- 输入固定：[原三真实高位3D帽](STAGE6_REAL_CROWN_3D_CAPS_ABF.md)同一 Source JSON + [全长 X/Y 真源边](STAGE6_REAL_PROTRUSION_BISECT_ABF.md)同一JSON，不重切原3D PLY、不重跑Dijkstra。
- 调用现有 real_panel_slit 的 _edges / _cut_fan_connections / _duplicate_face_fan / _validate_cut_disk，实现短切口源顶点扇区复制：只有路径首端到顶点前一位拆成双侧，顶部终点保留单一共享身份。每个源FaceID、XYZ、原113/112条Z230接口与Euler1的曲面拓扑核验必须不变。
- Blender适配器**仅调用原已验证的** unwrap_stage6_true_crown_caps_blender._unwrap 的原生 ANGLE_BASED（固定Blender4.3.2），不改底层UV求解器，无额外付费服务。
- 独立 _scale_free_gauge、_face_overlap_and_winding、_two_true_planar_seam_sides 逐源验证P95、零翻面/零正面积重叠、原切口两侧毫米长度。另补**逐段绝对2D缝长差之和/原3D缝长**，避免双侧总长偶然抵消。
- **原数值门槛不放宽**：全边P95≤10%、两侧二维逐段累计绝对缝差≤3%、每侧二维净缝相对3D源缝偏移≤3%、0翻面、0二维正面积重叠。这是研究预筛而非已测材料的工业公差；4片全纳入，失败也保存。

## 实测链路

修改原受信 main 的 Stage6 工作流后、依次产生并保存7天研究Artifact中的：

- source_rear_inner_short_slits.json：4个真源开缝圆盘与重复Source ID，**仅真实三维拓扑研究**。
- short_rear_inner_native_ABF.json：4组真 Blender4.3.2原生ABF UV。
- short_rear_inner_ABF_seam_QA.json：每项质量失败原因与联合门槛；生成即保存，不因为P95很差而丢弃候选。

没有真实ABF执行成功前不宣称任何指标改进；需要随后从原真实Stage6 Artifact提取4项报告并永久归档，不混用不同Run来源。

## 制造边界

开缝的端点为原高位几何尖部，是否需要三角省量/斜缝/加强衬、是否能够实际车缝/翻面，需真实设计四视图、绒面弹性、耳云装配与低成本废布试片验证。仅靠原Mesh的五视角BVH与数字2D配缝**都不足以批准**。下部原七边界壳尚未得到匹配的2D纸样，原四蹄4×512口不变。正式厂商可裁片仍是0。
