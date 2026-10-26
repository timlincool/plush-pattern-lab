# 12片双帽片布壳穿插根因定位与反例实验（2026-10-26）

**研究结论：非缝线相关的三角面交叉集中在侧片顶/底端与帽片相接的前后两排；没有一个被试全局参数消除穿插，不能宣布可以量产。**

证据：[可信所有者分支 Blender 4.3.2 真实实验](https://github.com/timlincool/plush-pattern-lab/actions/runs/40278382515)、[冻结合成证据](../experiments/capped_contact_20261026/results.json)。状态为 `SYNTHETIC_RESEARCH_CONTACT_SCREEN_REJECTED`；该实验不是实测面料/目标真实角色。

## 做了什么

`src/plush_pattern_lab/validation/contact_localization.py` 将保存后的 `.blend` 网格每个三角形的 `polygon_index` 严格绑定回 **P01..P12、UPPER/LOWER 帽片**，并标注 `upper_join/lower_join/body`。`src/plush_pattern_lab/blender/audit_self_intersections_blender.py` 保留原 `BVHTree.overlap` 检测和缝线相关/非相关计数，追加按裁片/区域分组及有限的代表性三角形中心（mm）。

**三角形中心不是相交点，分组不是碰撞原因证明。** 缝线相关见证也不是可自动豁免的安全接缝；`assess_contact_integrity.py` 的否决语义原样保留。来源：[Blender 4.3 MeshLoopTriangle.polygon_index](https://docs.blender.org/api/4.3/bpy.types.MeshLoopTriangle.html)、[BVHTree.overlap](https://docs.blender.org/api/4.0/mathutils.bvhtree.html) 与 [Blender 实现](https://github.com/blender/blender/blob/main/source/blender/python/mathutils/mathutils_bvhtree.cc)。

### 默认 8°/3mm 径向、48 帧、12 侧片 + 2 帽片

| Cloth 自碰撞 | 非缝线相关 | 缝线相关 | 非缝线位置 |
| --- | ---: | ---: | --- |
| 关闭 | 4 | 900 | **4组都在 lower_join × lower_join** |
| 开启（假设1mm接触距离） | 7 | 851 | **upper_join 4、lower_join 3** |

关闭时的四对分别为 P05–P06、P06–P07、P07–P08、P10–P11；对应代表性三角形中心 `Z≈−69mm`。自碰撞开启后上下交汇处都有交叉。大部分缝线相关见证位于侧片主体与主体之间（关闭813、开启804），不得把这些见证简单判成“无需处理”。

## 实际完成的单因素 A/B（全部基于合成数据）

**A. 帽片截断角度**；保持 3mm 径向偏移、零重力、关闭自碰撞：

| 角度 | 非缝线相关 | 缝线相关 | 目标RMS |
| --- | ---: | ---: | ---: |
| 6° | 10 | 964 | 0.453mm |
| **8° 当前默认** | **4** | **900** | **0.216mm** |
| 12° | 4 | 1052 | 1.945mm |

**B. 同 8°，仅改变径向初始偏移**：

| 偏移 | 非缝线相关 | 缝线相关 | 目标RMS |
| --- | ---: | ---: | ---: |
| 1mm | 8 | 507 | 0.035mm |
| **3mm 默认** | **4** | 900 | 0.216mm |
| 5mm | 6 | 1189 | 0.785mm |

**C. 同 8°，改径向/椭球法向位移**：

| 初始定位 | 非缝线相关 | 缝线相关 | 目标RMS | 几何研究 |
| --- | ---: | ---: | ---: | --- |
| 径向1mm | 8 | 507 | 0.035mm | 通过 |
| 径向3mm（默认） | 4 | 900 | 0.216mm | 通过 |
| 法向1mm | 24 | 1176 | 0.972mm | 通过 |
| 法向3mm | 24 | 1369 | 2.772mm | **拒绝** |

**没有一个参数组通过独立接触门禁。** 降低偏移会降低大量缝线相关交叉，但可能增大帽片端部的非缝线交叉；较大的法向偏移全面恶化，不能据此把默认算法切换到法向，也不能把“目标RMS最小”当成真实最优。

## 下一轮应做的结构性工作

1. 将帽片交汇处的 Pxx 首末两排三角形在 Blender 中按 `triangle_indices` 着色/高亮，核对哪种端部三角化、边界重叠或缝合映射造成穿插。
2. 只改局部顶/底交汇的三角形与缝线连接方式，保持其它侧片和材料假设；以独立 A/B 验证全部非缝线相关和缝线相关相交、形状/应变、理论闭壳是否改善。
3. 保留 `docs/PHYSICAL_PROTOTYPE.md` 的 1:1 合成试布套件，采集实物缝合/填充数据；未通过接触门禁前不能将实验结果标为通过物理生产验收。

所有采样结果按源码提交、Action 运行、样本分母与实验变量标记；旧结果不能继承为新提交的验收。


## 2026-10-26 补充：局部帽片过渡仍然失败

为区分“局部拼片结构问题”与全局参数失配，单独实验了末端 2 排/4 排初始偏移逐步收敛到帽片，其他 12+2 布壳、8° 截断、3 mm 径向、48 帧和零重力都不变。

| 帽片过渡排数 | 非缝线相交 | 缝线相关相交 | 合成目标RMS | 几何筛选 |
| --- | ---: | ---: | ---: | --- |
| 0（已验证默认） | **4** | **900** | **0.216mm** | 通过 |
| 2 | 6 | 1092 | 1.117mm | 通过 |
| 4 | 10 | 1072 | 1.330mm | **拒绝（主伸长P95约33.4%）** |

**三者接触门禁都拒绝**。这个“帽片局部位移收敛”假设没有证据可取代默认；实验源提交和 48 帧实际运行见 [Actions #40283704780](https://github.com/timlincool/plush-pattern-lab/actions/runs/40283704780) 与 [冻结结果](../experiments/cap_transition_20261026/results.json)。生产源码不保留失败候选的额外 CLI 开关，只保留审计证据。未来需要研究的是帽片与侧片实际共享边界、缝纫拓扑与局部三角化，而不只改初始位置。
