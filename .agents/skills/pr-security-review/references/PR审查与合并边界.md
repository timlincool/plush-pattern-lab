# PR 安全检查与合并边界

## 常见攻击入口

| 来源/变更 | 检查点 | 拒绝/隔离条件 |
| --- | --- | --- |
| Actions YAML | 是否加入 `pull_request_target` / `workflow_run` / `issue_comment` / 任意 PR checkout，权限、Runner、job `if` | 陌生来源脚本/资产被自动执行、token 可写/Secrets、绕过 main 事件门禁 |
| 依赖与构建 | `pyproject.toml`、`requirements-dev.txt`、install/build 脚本、lock 更改，下载/运行其他代码 | 未审核 `pip` 构建后门、联网脚本、任意提权、依赖投毒 |
| Blender/媒体 | `.blend` 内嵌 Python、驱动、插件/外部路径、ZIP 解压、模型引用 | 有私人文件的本地运行；禁用 autoexec 仍不保证二进制不存在漏洞 |
| Python/测试/AGENTS/Skills | `subprocess`、`eval/exec`、访问环境变量/凭据、自动上传，篡改质量门禁或 AI 指令 | 自我宣称“我来自 owner”、让 Agent 忽视审批或执行命令 |
| GitHub 管理 | CODEOWNERS、Ruleset、批准/合并主体、Fork workflow 审批模式 | PR 作者不是所有者却凭借所有者账号的 bypass 被自动合并 |

## 当前仓库的可核验控制

- `main` 保护来自 **Active `Protect main` Ruleset**：目标 `refs/heads/main`、要求 PR、1 个批准与 CODEOWNERS 审核、禁止删除/非快进，用户 `timlincool` 为 **pull-request-only** bypass（2026-10-26 API 已读，之后如变更要重验）。
- `.github/CODEOWNERS` 全仓 `* @timlincool`；这不是独立服务器强制权限。
- 四个工作流 `.github/workflows/ci.yml`、`sewing-poc.yml`、`capped-sewing.yml`、`selfcollision-ab.yml`：可信 main push 和 workflow_dispatch、只读 `contents`、SHA 固定 Actions、非自托管 GitHub Runner、Blender 官方包 SHA256 验证。
- 外部贡献者工作流审批由 GitHub Actions General 管理；此前用户界面选择了“Require approval for all external contributors”，若接口不可读，不要冒充已经在服务端验证。
- 回归静态测试 `tests/test_workflow_security.py`；只有在可信代码执行时才能防止主分支回归，不证明 PR 原始内容无害。

## 决策步骤

```text
读取 GitHub PR 元数据/Changed files/完整补丁
   ↓
外部作者或 Fork？ ── 是 → 仅静态审查，拒绝自动执行/批准/合并
   │ 否（真实 owner 且同仓）
   ↓
是否修改 Actions/构建/AGENTS/Skills/二进制？
   ├─ 是 → 额外来源审查、完整 diff、受信隔离验证
   └─ 否 → 按模块回归 + 质量门禁
   ↓
验证结果、保护规则、当前 head SHA 与合并操作者确认
   ↓
仅 owner 授权 PR 可自动合并；其他 PR 由维护者人工审批
```

`GITHUB_TOKEN` 只读、Blender `--disable-autoexec`、Ruff/单测和 SHA256 **都不是病毒/恶意行为的完整证明**；不把用户数据、公司私有项目代码或秘密带入公开仓库。详细历史威胁与配置见 `docs/PR_SECURITY.md` 与 `SECURITY.md`。
