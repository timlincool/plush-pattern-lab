# 双帽片布料自碰撞 A/B：真实求解但尚无自交认证

2026-10-25 在公开标准 GitHub 4核/16GiB Runner 和 Blender 4.3.2 上完成独立实验。

[实际 Blender Actions 运行](https://github.com/timlincool/plush-pattern-lab/actions/runs/40170736427)。

## 对照条件

12 片椭球侧裁片 + 1 顶盖 + 1 底盖、相同二维静止长度、相同参考辅助三维预定位、相同缝线弹簧参数和48帧，零重力。仅变动布片自碰撞开关。

- 不碰撞：`use_self_collision=False`、`use_collision=False`。
- 自碰撞：`use_self_collision=True`、`use_collision=True`、`collision_quality=3`、`self_distance_min=0.001m`，摩擦数值 5。1mm 为**假定材料间隙**，不是样布实测厚度；且这并未设置独立的外部碰撞体。
- 输出 `.blend`、完整逐帧求解/签名与固定研究门禁；没有在真实羊驼模型上运行。

## 结果

| 指标 | 自碰撞关闭 | 自碰撞开启 |
|---|---:|---:|
| 平均缝口距离 | 0.000221mm | 0.009630mm |
| 最大缝口距离 | 0.001208mm | 0.188191mm |
| 目标辅助合成几何刚体对齐RMS | 0.215840mm | 1.284028mm |
| 静止2D→最终3D主伸长偏差P95 | 7.638% | 7.656% |
| 相对初始法向翻面警告 | 0 | 0 |
| 分析性理论焊接的闭壳条件 | 通过 | 通过 |
| 研究几何筛选（非量产认证） | 通过 | 通过 |

自碰撞选项使合成目标形状的对齐RMS增大约 **5.95倍**，最大缝口距放大至0.188mm。这些差异表明碰撞假设在此实验中具有实际影响。

**不能把 `use_self_collision=True` 当作无面片交叉证明**：当前研究质量门禁只检查配对缝线间距、离散顶点形状差异、局部主伸长、三角面法向、分析性闭合网格的开边/拓扑；它**没有做非邻接三角形-三角形空间相交检查**。近距离高速穿透、片间褶皱和真实布料厚度都可能导致失败。自碰撞模拟未证明棉花、缝制牢度、洗涤、安全或准确的实物外形。

## 下一步最小可证伪工作

1. 对同一次保存后的末帧模型，独立执行排除相邻三角形的真实面-面自交检查（不仅是点距）；
2. 在同一模型上试验0.5/1/2mm假设厚度并测误差及剩余自交数，避免把任意一个数值误称为采购材料；
3. 用已测面料压缩、厚度、回弹数据校准模型，再考虑填充代理。

### 参考

- [Blender Cloth Collisions 官方手册](https://docs.blender.org/manual/en/4.1/physics/cloth/settings/collisions.html)
- Bridson/Fedkiw/Anderson: [Robust Treatment of Collisions, Contact and Friction for Cloth Animation](https://doi.org/10.1145/566654.566623)
- Ji/Li/Qiu: [Three-dimensional Garment Simulation Based on a Mass-Spring System](https://doi.org/10.1177/0040517506057169)


## 2026-10-25 追加：独立三角片空间相交审计改变了候选裁决

原来表中的“研究几何筛选通过”只针对缝口长度、局部主伸长、法向与分析性闭壳拓扑，**不包括面片交叉**。现在已真正保存重开并运行 Blender BVH 逐对三角面相交测试，增加单独的接触晋升否决门禁：

| 新增独立接触证据 | 自碰撞关闭 | 自碰撞开启 |
|---|---:|---:|
| 非相邻、缝线相关相交对 | 900 | 851 |
| 非相邻、非缝线相关相交对 | 4 | 7 |
| 有限接触筛选 | **拒绝** | **拒绝** |

完整证据、反例、算法界限：[CONTACT_INTERSECTION_SCREEN.md](CONTACT_INTERSECTION_SCREEN.md)，[实际 Blender 测试（含10项安全/篡改负测）](https://github.com/timlincool/plush-pattern-lab/actions/runs/40173337532)。

**重要修订**：任何“接缝拓扑通过”都不能推导为无面片穿插；此前通过的候选在新增严格接触筛选下均被拒绝。工作流执行成功只说明采样、计算和报告成功。剩余问题是定位实际穿插在何处、排查帽片和缝口预定位，之后才适合讨论真实布料厚度、材料试样与填充。
