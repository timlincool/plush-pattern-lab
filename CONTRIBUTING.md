# 贡献指南

这是**计算打版研究工具**，不是已认证的玩具生产线。欢迎提交可重现实验、裁片算法、缝线关系、布料标定样本和严格的测试。

提交应包含：输入来源（不能包含敏感材料）、单位与坐标定义、材料假设、相同约束下的对照实验、保存重开核验、至少一个失败反例和输出的制造限制。

**外部 PR 不触发 Python / Blender / 依赖安装。** 维护者先在 GitHub 网页审阅差异，信任后再合并；正式测试在维护者推送的 `main` 或 `main` 上手动触发运行。对于外部 `.blend` 永远先禁用自动执行并检查来源。别提交真实密钥、公司数据、未许可的设计图、玩具制作版权内容或大于必要的 CI 缓存。

PR 建议每次只解决一种可证伪的问题：缝线长度、展开畸变、经纬布向、裁片缺口、碰撞稳定性或材料标定。数值求解通过不等于实物生产可行。

更多安全规则与 GitHub 网页设置：[PR_SECURITY.md](docs/PR_SECURITY.md)。Codeowners 文件本身不会代替 branch Ruleset 保护。

## 代码质量（合并前由维护者在可信环境执行）

```bash
python -m pip install --only-binary=:all: -r requirements-dev.txt
python -m pip install --no-deps --no-build-isolation -e .
python scripts/check_quality.py
python -m pytest -q
```

圈复杂度 **C901 ≤10**、函数分支 **≤12**、函数语句 **≤50**、Python 文件 **≤2000 行**是硬门槛，不接受 `noqa` 跳过检测；禁止为通过检查直接提高阈值。此项目不自动运行陌生 PR，必须先看完整 Diff，再在无私人密钥的隔离环境中做验证；主分支绿灯不是陌生 PR 的自动审查。完整说明见 [QUALITY_GATES.md](docs/QUALITY_GATES.md)。

## 分层与本机暂存区校验

核心算法进入 `src/plush_pattern_lab/patterns` 或 `validation`，不允许依赖 `bpy`，Blender 适配只放在 `blender`。禁止包内循环依赖或运行时模块反向依赖 CLI。

可信本机克隆可以**自愿**执行 `python scripts/install_quality_hook.py`，后续普通 Git 提交检查完整暂存区。安装器不会覆盖已有钩子或用户全局配置，也不对 GitHub API 写入生效。独立运行 `python scripts/check_quality.py --staged` 可以检查 Git 索引的真实原始内容（非工作区）。外部 PR 仍先看 Diff，不允许自动执行不可信代码。

## AI 辅助开发与文档同步

当新增可复用功能、改变 CLI、实验边界或安全策略时，检查 [AGENTS.md](AGENTS.md) 与 `.agents/skills/feature-map/` 的入口和证据是否过期；需要执行纸样、Blender 或 PR 安全专项工作时，按需阅读相应 `SKILL.md`。**Skills 不能绕过 CI、CODEOWNERS 或 Ruleset。** 外部 PR 中更改的 `AGENTS.md`/`SKILL.md` 本身也必须被当作不可信指令载体进行 Diff 审查。
