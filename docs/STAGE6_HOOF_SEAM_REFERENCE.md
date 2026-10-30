# Stage 6 四蹄：3D 弧长对位与 2D 缝线投影参考（P0）

此阶段第一次直接从[公开 Stage 6 模型](https://github.com/timlincool/plush-pattern-lab/releases/tag/cloud-alpaca-stage6-visuals-20261028)提取四只蹄与主体的真实开放缝环。它是 **3D → 2D 缝线注册实验**，不是生产纸样。

## 可验证的数学不变量

- 源 `.blend` **89,853,017 字节**、SHA-256 `38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a`；载入前验签，Blender 4.3.2 使用 `--disable-autoexec`。不使用私有仓库。
- 主体四个洞口、四只蹄各有 **512 点有向闭合边界**。沿用现有 `verify_mating_loops` 的最大空间误差 ≤0.0001 mm、同样严格的周长差以及 **反向绕序**，不重采样、不放宽阈值。
- 每一组输出 `body_to_hoof_ring_ordinals`（原拓扑环序号，不是原 Blender 网格 vertex ID），并按相同三维点给出 Q0～Q3 对位标记。
- `arc_length_stations_3d_mm` 按**真实 3D 边长累加**，最终 SVG 中的直线标尺采用该真实弧长坐标。因此它能精确标示缝线长度和对位位置（以导出时数值精度为限）。Q0 的锚点是世界坐标中最高 Z、其次最小 X/Y 的一个**已有顶点**；这不是解剖学的脚掌正面，也不是确定毛向。
- `projected_reference_ring_2d_mm` 是**最小二乘拟合平面投影**。输出三维环与投影环的周长差、最坏局部边长缩短率、离面 RMS/最大值；投影损失不得伪装成布料伸长或被静默抹平。

## 受信环境运行

~~~bash
python scripts/verify_issue14_public_release.py --download-dir local-assets/verified-stage6
blender --disable-autoexec --python-exit-code 1 -b -t 1 \
  --python scripts/export_stage6_hoof_seams.py -- \
  --input local-assets/verified-stage6/cloud-alpaca-stage6.blend \
  --source-sha256 38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a \
  --output local-output/stage6-hoof-seams.json \
  --svg local-output/stage6-hoof-seams.svg
~~~

输出 JSON 包含四蹄对应、拓扑顶点编号、每顶点的真三维弧长、四个 Q 标记和投影失真报告；SVG 使用 **mm 单位 1:1**，提供四幅二维投影参考与四条真实 3D 弧长标尺。**SVG 不提供裁切外轮廓，也没有缝份；不得当作可缝纸样打印裁布。** 输出目标必须事先不存在，避免覆盖历史证据。

主分支可信工作流 `.github/workflows/stage6-hoof-seam-reference.yml` 从公开 Release 匿名下载模型、核验 SHA 后在无凭据 Runner 上只读执行 Blender，保留 7 天 JSON/SVG 小证据，不上传 90MB `.blend`。不在 PR 中执行第三方代码或未经审核的模型。

## 下一关（尚未完成）

需提取主体与蹄部**相邻网格面**，按裁片分区和面片三角形做真实 2D 静止面展平，才可将 2D 缝线从“投影参考”升级为“净缝线”；然后根据面朝向和布纹决定缝份方向、增加裁切外轮廓、逐三角形伸长/翻面检测、实体试布回测。单独的环长相同、3D 接口误差为 0，**不足以**证明任何二维布片可无畸变缝合。

参考 [专业制造工作流](PROFESSIONAL_WORKFLOW.md) 中 Mori–Igarashi 2007 Plushie、ToyAssembler 与 fabrication-aware flattening 的已有证据，不引入新制造放行阈值。
