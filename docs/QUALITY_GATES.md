# Python 质量硬门禁

参考私有项目 Metric Foundry 的严格质量理念；这些数值是本工程约定，不是玩具制造认证。

| 条目 | 阈值 / 规则 | 机制 |
| --- | --- | --- |
| 圈复杂度 | C901 ≤10 | Ruff 独立配置、拒绝 noqa |
| 函数分支数 | PLR0912 ≤12 | Ruff 独立配置、拒绝 noqa |
| 函数语句数 | PLR0915 ≤50 | Ruff 独立配置、拒绝 noqa |
| Python 单文件 | ≤2000 物理行 | `scripts/check_quality_limits.py`，覆盖 scripts/tests/src |
| 代码规范 | Ruff E4/E7/E9/F/I、S102/S307/S602、格式检查 | `scripts/check_quality.py` |
| 包依赖 | 不允许环；纯计算不依赖 Blender 或 CLI | Python AST + TopologicalSorter |

工具 Ruff 固定 **0.17.2**。内核只解析源码并执行安全的静态程序；不会主动导入项目的 `bpy` 或执行任何外部 PR 代码。

## 可信开发

```bash
python -m pip install --only-binary=:all: -r requirements-dev.txt
python -m pip install --no-deps --no-build-isolation -e .
python scripts/check_quality.py
python -m pytest -q
```

本地**可选** `python scripts/install_quality_hook.py`，不会覆盖既有钩子；`python scripts/check_quality.py --staged` 用 `git ls-files --stage -z` + `git cat-file blob` 解析整个暂存索引，拒绝符号链接、子模块、冲突路径；不使用已经更改但尚未暂存的工作区数据，不能被 `# noqa` 绕过函数硬阈值。已有反例测试覆盖这些限制。无真实克隆时不宣称预提交钩子已安装；GitHub 连接器提交也不会运行该钩子。

## 受信 GitHub CI 与 PR 安全

`ci.yml` 仍**仅**针对 `main` 的 push 和 workflow_dispatch 执行，使用 GitHub 托管临时 Runner、只读 GITHUB_TOKEN、SHA 固定的官方 Action，安装依赖限制为 wheels；运行统一质量检查、完整 pytest、打包 wheel。三个 Blender 任务仍只在 main 或维护者手动触发，现在也监听 `src/plush_pattern_lab/**` 修改。不能把 main 提交之后的绿灯称为对不可信 PR 的预合并状态检查；Fork PR 执行必须先审查和符合仓库设置。外部 `.blend` 始终可能包含恶意资源，禁止在有密钥的本机直接打开。

## 适用边界

单测绿灯不证明数值等价，也不是织物、填充料、缝线寿命或儿童玩具安全认证。重构必须对照 Blender 4.3.2 的实际求解产物与接触反例证据。质量约束不能通过提高阈值或新建任意豁免文件掩盖风险。
