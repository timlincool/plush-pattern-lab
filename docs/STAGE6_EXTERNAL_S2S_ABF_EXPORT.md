# Stage6：复用开源 Sewing Pattern SVG 导出器的真实 ABF 纸样预览

**仅用于研究；原Stage6三维裁片、缝份、布料、装配与工厂纸样均未通过制造验收。P3进行中，P4未开始。**

## 选型：不再自研 SVG 纸样边界导出或 UV 解算器

使用官方 **Blender 4.3.2 ANGLE_BASED（ABF）** 算好的原三维耳根 N15 左侧 lateral 开缝圆盘，并将 **artyredd/blender-seams-to-sewing-pattern**（GPL-3.0+）的现成 `object.export_sewingpattern` 操作作为单独的第三方程序运行。**不把 GPL 插件源码复制进本项目，不重新编写轮廓渲染器。**

上游固定提交：
- 仓库：[artyredd/blender-seams-to-sewing-pattern](https://github.com/artyredd/blender-seams-to-sewing-pattern/tree/919d031628264bb466840827a81f657133931de7)
- Git commit：`919d031628264bb466840827a81f657133931de7`
- 导出器 Git blob：`9bf263002593d6e9b09c7868da703a213948148c`
- 上游许可：`GPL-license.txt` GPL-3.0+，著作权与导出器义务归上游；本仓库仅包含独立调用适配器 `scripts/export_stage6_s2s_abf_svg.py`，该 Blender 侧脚本也声明 GPL-3.0-or-later。原本纯 Python 审查模块没有引入任何插件运行时依赖。

**不调用上游 `object.seams_to_sewingpattern`**：它会转换、修改、缩放网格，内部依赖人标注的接缝；这会破坏我们已验证过的原Source三角形、FaceID与ABF定位关系。只调用现成 `object.export_sewingpattern`，并指定 `alignment_markers=OFF` 避免在不存在制造配缝验证的阶段凭空生成对位。

## 真实来源与物理单位

沿用已实跑的 Stage6 12圆盘共同源实验：源 Blend SHA256 `38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a`，原 N15 左 lateral 原三角面、原VertexID、源开缝不改。

Blender 纹理 UV **不是毫米**。从已有 `stage6_free_blender_uv_vs_lscm.json` 中读取同一真实圆盘 ABF 的“全部原源边最小二乘单一比例” `uniform_scale_from_native_uv_to_research_mm`，再为第三方导出器设置其期待的 `S2S_UVtoWORLDscale = mm / 1000`。SVG 实际视口、每条源边的二维位置、闭合度、边总数、SHA由**独立 Python 模块**逐项核对；禁止直接把插件生成的 SVG 当作已合格纸样。

质量门禁：
- 同一轮原Source JSON、原生 ABF UV JSON、已有独立指标 JSON 三方 SHA 和 N15 左 lateral patch SHA 必须一致；
- 不允许更换求解器、增添新UV顶点内部开缝、更改三角Face索引、退化源边、放大/缩小/截断SVG、不允许外链/脚本SVG节点；
- 对源三角边“只出现一次”的全部原边求出真2D边集合，输出SVG每个轮廓点重投影回对应原ABF UV顶点，逐边拓扑严格匹配，误差0.001mm以内；
- 输出仅有 **一条净缝轮廓，无6mm缝份、裁切线、对位缺口、毛向和装配指令**；任何研究P95未通过的情况保留原始否决，严禁认作可直接裁布；
- 不允许将第三方上游的浮点打印精度误报成布料物理缝合精度或材料许可。

## 运行与输出

仅由已审查 `main` Stage6 工作流执行，真实 Bl​​ender 与所有Source SHA先核验，之后临时独立检出上游 Git commit 并核实导出器Git blob，运行：

```bash
blender -b --disable-autoexec --python-exit-code 1 \
  --python scripts/export_stage6_s2s_abf_svg.py -- \
  --source <same-run-source.json> --native <ABF-native.json> \
  --audit <ABF-audit.json> --addon-dir <pinned-gpl-addon-dir> \
  --addon-commit 919d031628264bb466840827a81f657133931de7 \
  --out-dir <new-research-directory>
python scripts/audit_stage6_s2s_svg.py \
  --source <same-run-source.json> --native <ABF-native.json> \
  --audit <ABF-audit.json> \
  --svg <new-research-directory>/N15_left_lateral_ABF_RESEARCH_ONLY_no_allowance.svg \
  --output <new-research-directory>/audited_original_source_netline_RESEARCH_ONLY.json
```

输出到可信临时 Artifact：一份 `N15_left_lateral_ABF_RESEARCH_ONLY_no_allowance.svg` 和一份单独的逐边、单位、SHA验收 JSON。没有付费API，无第三方服务账号。**提交/写好脚本并不代表真实Blender或本轮CI通过，只有受信main真实运行成功才更新永久证据。**

## FreeCAD flatmesh 与 GarmentCode 的位置

[goatchurchprime 的 FreeCAD 分支](https://github.com/goatchurchprime/blender-seams-to-sewing-pattern/tree/0ea2585105a13e03cf017cca53da684b31eb97df) 确实使用 `flatmesh.FaceUnwrapper`，但 README 依赖 FreeCAD+Nix+Blender 4.5，与我们固定4.3.2不一致。**暂不捆进受信Stage6的必需依赖**。后续用单独无凭据的隔离环境跑相同 Source 时，再按原 P95/净缝/翻转/重叠统一评分；不会通过复制 GPL 代码“改名为自研”。

[GarmentCode](https://github.com/maria-korosteleva/GarmentCode) 的 Panel / Interface 可在真正需要统一数据互操作时以 MIT 合法复用。目前18/24片数字接口已存在，没有出现必须重造的模型缺口，不为了“接第三方”重构已通过的32/44/46组研究接口。

## 下一门槛

本轮只证明**上游开源导出器可在固定真实 Stage6 原源圆盘上从 ABF 输出对应二维毫米净缝**，仍非整只羊驼纸样。再从真实主体/颈头和蹄底选定适合工厂缝合的切分位置，做完整隐藏缝/四视图/实际面料试缝。外内耳、7云团、尾巴、眼鼻、10水滴带、缝份、返口/填棉和实样工厂签核都不能被 SVG 文件自动解决。
