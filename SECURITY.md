# 安全政策

本项目处于研发阶段，不保证外观模型、布料仿真或纸样的物理安全性。本文件讨论**软件、数据和 CI 安全**；儿童玩具材料、安全认证属于另一个问题。

## 报告漏洞
如发现真实访问令牌、凭据、恶意代码路径、任意脚本执行风险或私人信息，**不要创建包含密钥/可利用细节的公开 Issue**。优先使用 GitHub 仓库的 **Security → Report a vulnerability**（如维护者启用 Private vulnerability reporting）。如果入口不可用，请通过维护者 GitHub 账户取得私下联系渠道，不要把敏感信息直接发布。

报告请提供影响范围、复现所需最小输入、相关文件名、适用 Blender/Python 版本；不要提供真实帐号密码或私人数据。

## 使用者安全边界
- 从已校验的 Release 获取输入资产，并核对 SHA-256；不要执行来源未知的 ZIP 内脚本。
- 所有外部 `.blend` 首次打开时禁用自动运行：`blender --disable-autoexec -b ...`。Blender 文件可以携带 Python、外部文件路径与自定义数据，`.blend` **不是天然安全的纯图片**。
- GitHub Actions 应使用最小 `permissions`，不对 Fork PR 提供 Secrets 或写入令牌；公开版重型渲染仅限可信维护者触发。
- 对外部补丁/模型文件做 SHA 和差异检查；不把外部 PR 的产物交给 `workflow_run` 高权限任务执行。
- 不上传私人会话、API 密钥、公司数据、原始商业项目或本机工作目录。
- 建议在干净容器、临时账户和隔离运行器里执行未验证代码；不要在存有私人文件的主机上运行不明模型中的自动执行脚本。

## 尚未做的安全认证
实物打样、填棉、缝线拉力、洗涤、站立与儿童玩具法规测试均未通过。任何研究模型/数值输出不能当作合格玩具生产或销售依据。

## 外部 PR 的默认处理方式（2026-10-25）

**不会自动执行 Fork PR 的 Python、依赖安装、Blender 文件或脚本**。项目 Actions 只运行已提交至维护者 `main` 的代码，或维护者在 `main` 明确手动触发的实验。仅扫描代码差异不代表代码无害；`GITHUB_TOKEN` 设置为只读，Checkout 不持久化凭据。

2026-10-26 GitHub API 已确认 `main` 受到 Active `Protect main` Ruleset 保护，个人 `timlincool` 仅有 PR 范围的豁免；外部 Actions 审批由用户在 GitHub UI 选择，当前连接无法读取管理员项的实时服务器值。仓库 YAML **不能替代真实设置**。详情见 [PR_SECURITY.md](docs/PR_SECURITY.md)。
