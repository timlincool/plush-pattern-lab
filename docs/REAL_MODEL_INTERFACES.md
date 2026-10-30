# 真实模型主体—四蹄几何接口验证

本工具只判断：四只蹄部开放边界，是否与主体上的四个洞口一一对应、世界坐标逐点一致，且边界绕序相反。**几何配准不等于二维纸样、布料缝合、填棉或制造安全认证。**

## 在受信环境运行

要求 Blender 4.3.2、用户自己提供且 SHA-256 已核对的模型。请在无凭据、断网环境中运行，并禁用 Blender 自动执行。

~~~bash
blender --disable-autoexec --python-exit-code 1 -b -t 1 \
  --python scripts/audit_hoof_interfaces.py -- \
  --input /private/verified-stage6.blend \
  --source-sha256 "<已验证的64位SHA-256>" \
  --output /private/hoof-interface-report.json
~~~

输出仅包含环数、顶点数、三维周长、循环配准 RMS / 最大误差、绕序和判定结果。**不导出模型原始坐标、材质、贴图或私有资源。** 输入哈希不符、输出文件已存在或环结构错误时立即拒绝。

## 固定契约

- 主体对象为 PRIMARY continuous sculpt | new anatomy，四个蹄部对象为 Rounded hoof base 及其 .001/.002/.003 副本。
- 主体恰好四个独立闭合开放环、合计 2,048 条边；每个蹄部为一个 512 边闭合环。
- 从 Blender 网格面的有向半边还原拓扑，不按最近坐标猜测连边。
- 各蹄部与主体开放环按世界坐标中心唯一匹配，循环调整起点和正反方向，**禁止重采样**。
- 最大逐点误差、三维周长差均要求不超过 0.0001 mm，且方向相反；不可放宽到超过 0.01 mm。
- 浮点非法、退化、环数不符、一对多匹配、绕序同向或误差超限都不能视为合格接口。

## Stage 6 3D→2D 接缝注册参考

[四蹄弧长标尺与二维投影参考](STAGE6_HOOF_SEAM_REFERENCE.md) 已实现：对已配准的每组 512 点环记录精确三维边长累加、Q0～Q3 顶点对应、最小二乘平面投影与离面/弧长损失诊断，并生成研究 SVG。**没有从完整表面展平布片，也不生成缝份/裁切线。**

## 下一阶段

从几何接口导出双方的 **二维净缝线**、缝份、对位标记及毛向；对 2D→3D 主伸长和缝口误差单独验证，再通过实测合成面料样片、填充和实体打样回测。所有研究门禁与材料认证边界沿用 docs/PROFESSIONAL_WORKFLOW.md。

实现分层：validation/boundary_match.py 仅处理纯数值；blender/audit_hoof_interfaces.py 提取定向环；scripts/audit_hoof_interfaces.py 为命令入口。本工具不修改当前合成椭球纸样和碰撞判定阈值。
