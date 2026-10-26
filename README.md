# Plush Pattern Lab · 毛绒玩偶数字打版实验室

**开源研究：从可编辑三维毛绒造型，走向有证据的二维裁片、缝线配对与物理模拟。**

> **研发原型，不是可直接生产的纸样或经过安全认证的玩具。** 目前验证以程序化几何、布壳代理模拟和有限的裁片实验为主。真实面料、填充纤维的压缩与回弹、缝合后重建和实物打样尚未通过完整验证。

## 为什么做

漂亮的 Blender 渲染≠能缝出来的毛绒玩偶。专业路径需要让 **二维裁片与三维成形相互验证**，记录缝线、对位点、毛向、布料经纬向伸缩、填充密度、样布试验和差异。

我们的研发链：

```text
目标比例/多视角参考
       ↓
可编辑三维部件和分割缝线
       ↓
有向二维纸样、缝份、缺口、面料纹理方向
       ↓
应变/面积/边长/法向翻转门禁
       ↓
从 2D 开始的虚拟缝合 + 填充支撑代理
       ↓
真实样布量测校准 → 实物打样 → 工艺与安全验收
```

## 当前阶段

| 部分 | 当前证据 | 不要误解为 |
|---|---|---|
| Blender 外观与布壳代码 | 可阅读/复用的原型脚本 | 与原创参考图完全一致 |
| 灰云截面与二维展开研究 | 可检测边界、面积与应变风险 | 生产纸样 |
| 72 帧 Cloth 代理实验 | 前期已在私人研发库真实执行 | 真实聚酯棉本构 |
| 缝份、物料和裁片定位 | 研发中的契约与模板 | 可直接批量生产 |
| 实物试样、儿童安全认证 | 未完成 | 合格量产玩具 |

## 快速开始

Python 3.11+：

```bash
python -m pip install --only-binary=:all: -r requirements-dev.txt
python -m pip install --no-deps --no-build-isolation -e .
python scripts/check_quality.py
python -m pytest -q
```

Blender 建议使用 **4.3.2**。对于未经信任的 .blend，请禁用自动执行：

```bash
blender --disable-autoexec -b input.blend --python scripts/audit_physical_shell.py -- \
  --input input.blend --output shell_audit.json
```

**大型 H-compact 模型和原始设计图暂不在首批源码提交中发布。** 原始素材授权与嵌入资源仍需单独审查；现有私人研发档案不会复制或转为公开。所有需要真实模型的命令必须由使用者提供自己有权使用的输入，不存在时不可声称已复现。

## 最新实验：缝线闭合不代表还原目标造型

- [真实 Blender 48 帧 8/12 片 A/B 与独立形状质量报告](docs/SEWING_QUALITY.md)。
- 同一目标辅助预定位下，8片对合成目标的 RMS 约 0.266mm、P95几何应变14.23%；12片约0.469mm、8.07%。
- 两种方案均有**极点翻面**，因此 **都未通过研究候选筛选，更不能直接用于生产**。下一阶段优先设计独立极点帽片和实体缝线。

## 顶部/底部独立帽片：研究几何已通过，物理生产仍未验证

[可复现的双帽片纸样与真实 Blender A/B 实验](docs/CAPPED_PATTERN.md) · [12片研究SVG](https://github.com/timlincool/plush-pattern-lab/actions/workflows/capped-sewing.yml)

| 合成椭球研究指标 | 8片+2帽片 | 12片+2帽片 |
|---|---:|---:|
| 48帧后平均缝口间隙 | 0.000253mm | 0.000221mm |
| 对已知目标刚体对齐RMS | 0.325mm | 0.216mm |
| 主伸长绝对偏差P95 | 13.25% | 7.64% |
| 检出的相对初始法向翻面 | 0 | 0 |
| **研究几何门禁** | **拒绝：应变超限** | **通过** |

实验使用明确合成目标辅助三维初始化和原生 Blender Sewing Springs；不包含真实面料/聚酯填棉、自碰撞、最终拓扑焊接或工厂安全验证。**研究筛选通过≠可制作/可量产。** 12片要求更多缝线，是否最优须待面料和实际缝制成本证据。

## 当前自碰撞实验的限制

在[12片＋双帽片的真实 Cloth A/B](docs/SELF_COLLISION_AB.md)中，开启1mm**假设**厚度的自碰撞后，对合成目标的刚体对齐RMS从0.216mm升至1.284mm；研究几何门禁仍通过。但未进行真实三角面自相交检查，也未测实际布料与纤维棉参数。**不能把Blender的自碰撞开关等同于完成物理可制造性验证。**

## 专业工作流与论文

- <https://doi.org/10.1145/1276377.1276433> — *Plushie* (2007)，2D 模板与模拟协同设计。
- <https://doi.org/10.1016/j.cad.2020.102911> — 组件模板式玩偶纸样设计。
- <https://doi.org/10.1016/j.cad.2022.103356> — *ToyAssembler*：2D 裁片定位和缝合模拟。
- <https://igl.ethz.ch/projects/computational-patternmaking/> — 面向制作的曲面分片、布纹方向、对称缝线和变形约束。
- <https://www.marvelousdesigner.com/learn/userspotlight/post/a5fc6095271d40faaaac58937898b431> — 玩偶打版从业者的 Marvelous Designer、填充压力代理与真实面料校准案例。

代码为 **MIT**；设计图、3D 资产和第三方材料须独立核对授权，参见 [资产许可](ASSET_LICENSE.md)。报告安全问题请阅读 [SECURITY.md](SECURITY.md)。

## 参与贡献

请提交可复现测试、输入来源、计算误差、失败反例及制造限制。外部 PR 不自动执行 Python、依赖安装或 Blender CI；维护者先审查，再在受信任的主分支验证。参考 [CONTRIBUTING.md](CONTRIBUTING.md)。


## 第三方 PR 安全策略

陌生人的 PR **不会自动执行**依赖安装、Python 测试或 Blender 模拟。仅信任维护者推送到 `main` 的代码；PR 必须先人工审核，运行陌生模型前禁用 Blender 自动执行。详见 [PR 安全与维护者设置](docs/PR_SECURITY.md)。


## 物理穿插风险（研究现状）

已对真实保存的合成布壳运行独立 **Blender BVH 非相邻三角面相交检查**。即使缝口和闭壳拓扑的研究门禁通过，开启 Cloth 自碰撞的版本仍检测到穿插，因此新的接触晋升门禁会明确**拒绝**它；详见 [接触审计与当前失败证据](docs/CONTACT_INTERSECTION_SCREEN.md)。不能将可运行的 `.blend` 当作经验证的生产纸样。

## 可维护性门禁

所有受信任主分支 CI 执行 [统一质量门禁](docs/QUALITY_GATES.md)：Ruff 格式、静态规则、**圈复杂度 ≤10、分支 ≤12、语句 ≤50、单文件 ≤2000 行**以及包内无循环依赖。主要实现已迁入可安装的 `src/plush_pattern_lab/`，`scripts/` 保留原命令行入口。这些限制会导致主分支 CI 失败，但由于不自动执行外部 PR，**不能将其误称为已强制阻止不可信 PR 合并**；预合并必须经人工检查及隔离验证。

## 项目代码结构

源代码按依赖方向分为 `patterns/`（纸样与材料）、`validation/`（纯数值验证）以及 `blender/`（Blender 适配/求解）。旧的 `python scripts/*.py` 和 Blender `--python scripts/*.py` 保留兼容；安装后也可用 `plush-capped-gore` 等命令。参见 [架构说明](docs/ARCHITECTURE.md) 与 [质量门禁](docs/QUALITY_GATES.md)。无需为了设计模式而增加抽象，重构不改变研发结果的制造边界。
