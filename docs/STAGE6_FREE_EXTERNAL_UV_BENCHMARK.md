# Stage6：免费成熟展开器的同源实测（P3）

**状态：功能分支已实现，最终数值需以受信 main Blender 4.3.2 / Python CI 的真实运行结果为准。仅技术选型，不是工厂纸样。**

## 为什么选这个实验

用户目标是免费生成能够交厂的整只约25cm羊驼纸样，而不是把2D展开求解器重新写一遍。优先用免费 Blender 4.3.2 内建的 Angle Based（ABF）与 Conformal 展开器，不借用闭源付费服务源码、不需要任何商业订阅。Blender官方FAQ确认可商业使用其输出：https://www.blender.org/support/faq/ ，UV API：https://docs.blender.org/api/4.3/bpy.ops.uv.html 。

Blender bpy适配脚本为独立GPL-2.0-or-later文件；纯指标审计脚本与研究JSON在Python外部运行，未复制任何第三方插件源码。

## 同输入、同指标，不能作弊

数据源：原 Stage6 Blend SHA256 为 38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a；12个研究圆盘必须来自同一受信 main 的N15/N17左右耳根片，各固定内、后、外侧开缝方向。每个算法输入的原3D XYZ、Source FaceID、三角形、顶点身份和切口完全一致，不允许重新划缝、减面、补点或凭结果选择好看的候选。

| 求解器 | 真实输入数 | 对照 |
| --- | ---: | --- |
| 自研稀疏LSCM | 12 | 原研究基准，P95边长误差约23–41%，二维双侧缝长差约3–39% |
| Blender 原生 ANGLE_BASED | 12 | 外部成熟ABF，研究性实验 |
| Blender 原生 CONFORMAL | 12 | 外部成熟Conformal，研究性实验 |

Blender纹理UV没有毫米单位。先以完全相同的全局单一等比例最小二乘边长相对误差公式归一化，再对三种结果用相同代码统计：

1. 原3D Source三角网格边到2D P95相对长度误差；
2. 同一原3D源边被切开后的两条真实2D缝线长度差；
3. 二维三角形反转、坍塌数量；
4. 所有二维三角形正面积重叠对数；
5. 原生求解器运行秒数、UV逐顶点连续性及全部源哈希。

原项目10% P95边差、3%二维配缝差、无翻转/重叠为**研究预筛**，不是工厂材料公差；不满足则不得晋升。即使满足，仍须真实材料、外/内耳和云层、缝份、返口/填充、四视图与实布试缝证明。

## 可执行输出

- 独立Blender脚本：scripts/benchmark_stage6_blender_uv.py
- 同一质量审计：src/plush_pattern_lab/validation/stage6_external_uv_benchmark.py
- JSON/SVG接口：scripts/audit_stage6_external_uv_comparison.py
- 可信 main Stage6 workflow 在原LSCM后运行，产生24组原生UV明细、12组三算法数值对照JSON和SVG研究图；默认源图和输出都在RUNNER_TEMP，受信workflow保留7日Artifact。

**决策：** 如果Blender免费成熟求解器显著同时减少边长应变与二维配缝长度差且没有自交，考虑替换自研求解器默认实现；如果一样失败，应该停止反复追求高密3D雕塑的数学展开，优先复用纸样模板与GarmentCode Panel/Interface等二维结构思路，将3D原雕塑作为外形验收目标。不要以免费纹理UV漂亮为由批准裁布。

**P3 in_progress，P4 not_started，正式厂商裁布纸样0。** 原Blend、四蹄4×512、13片下腹和旧否定实测不改变。
