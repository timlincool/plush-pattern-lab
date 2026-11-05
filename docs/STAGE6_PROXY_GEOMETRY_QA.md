# Stage 6：真实主壳代理的独立几何审计

本研究承接[厂商路线图 P3](FACTORY_ROADMAP.md)与[上一阶段 25%/50% 实际低模代理](../experiments/stage6_core_proxy_20261105/summary.json)。目标是在创建整只羊驼的分片、裁片和缝份**之前**发现坏法线、非相邻三角面自交及多视角明显失真。不修改原模型，不作裁布合格声明。

## 输入与源保护

固定输入是同仓库公开 Stage6 源 `cloud-alpaca-stage6.blend`，SHA-256 `38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a`。依旧必须使用 Blender 4.3.2、`--disable-autoexec`、主分支只读权限及四蹄原始 3D 配对门禁。

真实减面步骤先在独立复制网格上重建两版 PLY；独立 QA 步骤按先前实际测得的两个 PLY SHA 校验文件内容再读取：50% 的 SHA `22020a5631ccd6b171f242d6c5c9f9713e9b0d600a20f8a0fcf3b7c08149bd4f`，25% 的 SHA `5b52e3fd09c83b19c5b9d95d6d8d859a147ff4deef90f1518f868d2e82e3a2dd`。若来源变化或缺文件，拒绝审核而不是猜测。

## 逐项分析（不能互相替代）

- **面片绕向一致性**：检查每条恰好连接两个面的内部边，其两个有向面循环是否相反；即使全部一致，也**不能直接证明整壳法线向外**。
- **BVH 非相邻面自交**：用 Blender 原生 BVHTree 对每个网格自身取真实相交三角面候选。过滤共享任意顶点的邻接面，输出完整计数和最多12组面索引反例。**非零值必须作为阻塞信息保留**；即使零值也不能证明有限厚度、邻件接触或整个缝合时序安全。
- **正/背/左/右/顶的实际第一命中深度**：固定同一来源包围盒、每视角 96×96 正交光线，分别投向原主壳和每个代理，计算命中/漏命中的 silhouette IoU、差异像素及共同命中处 first-hit depth mean/P95/max（mm）。这比只比顶点包围盒更接近真实可见轮廓，但不是光照渲染/连续曲面 Hausdorff。
- **直观证据**：为每版代理输出五视角并排 PNG；白色=都无几何、深灰=都命中、红色=原始有而代理漏、蓝色=代理多出。按顺序 front/back/left/right/top。颜色是**射线掩码**而不是原始设计图的面料颜色。
- **来源与批准边界**：报告以真实 SHA 和固定历史 A/B 绑定；是否存在自交和法线不一致必须公开，不因降低面数、IoU 接近1或 CI 成功自动准入 P4。

## 可信运行与产物

~~~bash
blender --disable-autoexec --python-exit-code 1 -b -t 1 \
  --python scripts/audit_stage6_proxy_surface.py -- \
  --input /tmp/verified-public-stage6.blend \
  --source-sha256 38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a \
  --proxy-dir /tmp/verified-produced-proxy-ply \
  --output /tmp/proxy_independent_screen.json
~~~

来源 PLY 必须是相同受信任 Runner 在上一步生成且哈希符合历史测量，不读取不可信 PR 资产。工作流保存 `proxy_independent_screen.json` 和两份五视角 PNG，**不上传原始 .blend**；已验证的代理 PLY 另以 7 天临时 Artifact 保存。

## 下一步真实制版

独立审计结果进入 [唯一进度表](PRODUCTION_PROGRESS.json)。如果发现自交或明显外轮廓缺陷，先定位并改变局部分片/代理构造；不要通过调高阈值自称合格。几何诊断清晰后，先设计可由工厂实际缝制的头身主壳区域与四腿/蹄的接合线路、返口和填棉方案，再导出完整 1:1 净缝/裁切图。
