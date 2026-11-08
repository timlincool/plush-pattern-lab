# Stage 6：完整 41 个产品 Mesh 的五视角缝位遮挡审查

**项目阶段：P3 真实可缝结构研究。此证据不是工业纸样、材料试验、渲染可见性认证或量产批准。**

## 为什么新增全场景遮挡层

[上一轮经真实源确认的高位缝风险](STAGE6_B_FACE_SEAM_VIEW_QA.md)证明 B 方案新增路径2的 132 个原始源顶点中，126 个接近主壳正面、8 个接近历史鼻／嘴绣线，末端源点 40436 与历史鼻线 X/Z 距约 0.575 mm。但之前只用主壳25%代理检查自己是否挡住自己，没有考虑头云、额云、胸云、两侧云、独立眼部/耳/尾等 Mesh。

本轮使用**已验证原始 Stage6 Blender 4.3.2** 和 [42 Mesh 制造登记表](../design/manufacturing/STAGE6_COMPONENT_REGISTRY_DRAFT.json)，要求原场景每个 Mesh 名称、polygon 数量完全匹配。42 Mesh = **41 个产品视觉 Mesh + 1 个摄影棚地面**。地面不得算成遮挡，也不作为 BOM；产品 Mesh 逐项构建真实世界坐标三角形的 BVHTree，包括所有7云团、4蹄、4耳、4眼部标记、尾覆盖、10水滴、10短布片和连续主壳。

## 几何计算与五视角

相机约定使用同仓源 `X=0` 对称、`Y<0` 为正面、`Z>0` 向上，单位毫米。视角 `front/back/left/right/top` 分别沿 `+Y/-Y/+X/-X/-Z` 发正交射线。

每个原始 B 路径 source Vertex ID 的位置保持原3D，不修改 `.blend` 或25% PLY。对每个方向，沿该顶点投影像素在全部41产品Mesh中寻找**最近零厚度三角面交点**，记录：首交物体名称/类别、主壳是否自己在前、另一独立产品Mesh是否在前、source代理顶点与原高精度世界面相差多少毫米，以及未知或近重合区域。

研究性可见深度缓冲是**0.7 mm**，与上一轮固定主壳筛查保持同口径；它不是服装缝份、面料拉伸、摄影像素或工厂的接缝可见容差。

逐个样本用严格区分的状态而不是一个布尔值：

- `near_original_body_first_surface`：当前源点与**原始高精度主壳第一命中面**近重合；并不说明毛绒或装饰层完成后仍可见。
- `occluded_by_another_product_mesh`：其他产品原始Mesh比该缝顶点更靠近观察方向。只代表**几何遮挡**，不证明实际覆层绒毛能覆盖缝份。
- `self_occluded_by_original_body`：原始主壳自身更靠近观察方向；缝的另一视角仍可能暴露。
- `coincident_with_another_product_mesh_unresolved`：其他网格与源点近重合，不知道是贴片工艺、穿插还是物理遮挡。
- `proxy_source_ahead_of_full_mesh_surface_unresolved`、`no_authored_mesh_first_hit`：25%代理与全场景三角网格存在差异或投影不匹配；必须标成未知，不能凭“无遮挡”推断可见或不可见。

## 必须明示的未覆盖项

1. **423条左右毛发／造型曲线**等非 Mesh 类型、实际材质与绒向、长度以及渲染后的透明/遮挡均未用 BVH 审查。
2. 建立BVH的是全部41个源Mesh **未经渲染修改器求值的原始世界三角面**；原始修饰器、曲线、毛束和材质可能改变真正的可见表面。对隐藏或未链接到活动场景的产品对象另行列名；不能当成实际相机渲染。
3. 原始 Stage6 视觉模型与早期 `surface14` 五官 X/Z 注册线 **并非已完成几何匹配的正式设计版本**。历史8个面部警报只是需要设计确认的潜在冲突。
4. 原B三片只有拓扑/3D源缝真实配对，后续 LS​CM、ARAP、Tutte 均仍大幅失真，不能因遮挡诊断的结果而把任一片升级为真正静止布料纸样。

## 可信执行与研究证据

`src/plush_pattern_lab/blender/audit_stage6_full_mesh_visibility.py` 在验证源Blend SHA、原四蹄3D接口及登记表42Mesh精确一致后，读取**同一次可信主分支任务**上一阶段固定source Vertex IDs与面部警报，并对全部41个原始产品Mesh运行五组BVH射线。输出详细JSON。

`scripts/render_stage6_full_mesh_seam_views.py` 在重新核验同一固定25% PLY及当前JSON SHA/旧历史五官注册原件后，输出可追溯五视角 SVG/元数据。它仅是世界坐标研究**投影**，不可当最终设计四视图对齐/制造切割SVG。

可信 workflow 仍为**仅维护者 main push/manual、Token contents:read、Blender --disable-autoexec、固定公共资产 SHA**；不运行未知外部PR内容，不公布未授权恢复包。原始 JSON/SVG 与审查报告保存为临时 Artifact；永久摘要须在真实运行后将来源、对象、首次命中、警报与哈希归档。

## 下一个真正生产相关动作

用全场景五视角统计定位 B 高位缝2与眼鼻嘴、云团/耳尾实际原Mesh的遮挡或重叠：如果完整原Mesh也无法隐藏鼻口附近的点，优先沿真实3D源边避让脸部，寻找被云团覆盖且工厂可缝的缝位。任何改线必须从原源Face/Vertex ID重新进行 Euler=1分片、配缝、2D边长/重叠/翻向/面积及实际材料伸长评估；不得只看0重叠或近似左右缝长。两处四线交汇、返口、料样与制造商接口仍未解决。

完整项目门禁以 [唯一生产进度 JSON](PRODUCTION_PROGRESS.json) 为准。**P3在研，P4至P7没有获批。**
