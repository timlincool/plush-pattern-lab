# 代码质量硬门禁（2026-10-25）

## 第一性原则

复杂度门禁需要可自动复现、可证伪的硬指标，而不是靠行数或 AI 审查意见替代程序验证。所有门禁只在维护者信任的执行环境运行。

| 规则 | 上限与触发后果 | 实现 |
| --- | --- | --- |
| 圈复杂度 | 每个 Python 函数 McCabe **≤20**，超限直接失败 | Ruff C901，禁用 `noqa` 绕过 |
| 文件大小 | `scripts/` 和 `tests/` 每个 Python 文件 **≤2000 物理行** | 零依赖 `scripts/check_quality_limits.py` |
| 静态检查 | E4/E9/F 及 S102/S307/S602，违规失败 | Ruff 0.17.2 |
| 正确性 | 全量 pytest 与 compileall 必须成功 | GitHub 托管的 Python 3.11 |
| 工作流安全 | 只读令牌、固定 Action SHA、受信事件、官方 Blender SHA256 校验 | `tests/test_workflow_security.py` |

未强行要求使用任何设计模式。设计模式不是质量指标；应当根据重复、可测试性和变化轴来决定抽象。避免为了过门禁盲目拆函数，原有几何数值与仿真结果必须保持。

本轮将既有四个超限的复杂函数拆分数据准备与主流程，不改变求解参数或纸样研究阈值。

## 本地可信开发检查

从仓库根目录：

```bash
python -m pip install -r requirements-dev.txt
python scripts/check_quality_limits.py
ruff check scripts tests --ignore-noqa
python -m compileall -q scripts tests
python -m pytest -q
```

`--ignore-noqa` 确保在行内写 `# noqa: C901` 也不能豁免复杂度。CI 安装采用 `--only-binary=:all:` 禁止构建源码包；不保证第三方 wheel 无漏洞。

## PR 安全边界

公开 Fork PR **不自动运行**上述命令。审查者先检查 Files changed，尤其 `.github/workflows`、`requirements-dev.txt`、`ruff.toml`、`scripts/`、`tests/`、`.blend` 与外部下载脚本。确认可信后才可在无机密信息的隔离环境验证。

注意：当前 CI 只在已进入 `main` 的可信代码上执行，因此该质量检查虽会使 CI 失败，**并未形成 GitHub 级别的预合并状态门禁**。只有配置 Ruleset、人工确认安全，并为预合并建立经审核的可信验证路径后，才能声称存在完整的合并保护。详情见 [PR_SECURITY.md](PR_SECURITY.md)。

如果质量规则未来需要进一步收紧，须先运行整个仓库基线并修复历史超限项；不得因为一次质量门禁报错就大幅调高复杂度阈值。
