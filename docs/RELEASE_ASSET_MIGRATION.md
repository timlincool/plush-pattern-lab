# 旧版云朵羊驼：核心六个 ZIP 安全迁移步骤

只把旧私有仓库当作**历史资产源**。所有新代码、设计映射与研究仍在公开的 `plush-pattern-lab` 进行。

## 已核实的发布版 SHA 基线

`design/archive-v25/release-integrity-manifest.json` 保存 2026-10-23 私有 Release 的六份选中档案：**每个发布 ZIP 的大小、SHA-256、252个成员的 SHA-256，以及旧原始 ZIP 哈希与重新整理文档后发布哈希的区分。**

此前单凭 `source_archive_sha256` 验证 03～06 将错误拒绝合法档案，**必须使用 `published_sha256` 校验下载版**。成员级哈希可以验证该包实际上有哪些脚本、Blender 模型、NPZ 和报告。

## 在受信任设备 / Work 的已登录 GitHub 环境

以下操作不会修改任何 GitHub 仓库，也不会运行 ZIP 内代码：

```bash
# 首先在当前环境确认 gh CLI 已连接你自己的 GitHub 账户：
gh auth status

# 从现有私有归档仅下载6份选中包，到 .gitignore 保护的本地目录：
python scripts/prepare_legacy_release.py --download

# 第二次运行不会覆盖已有 ZIP，并会重新检查：
python scripts/prepare_legacy_release.py
```

默认下载至 `local-assets/legacy-release-v25`，审查 JSON 写至 `local-output/legacy-asset-audit.json`，两者均处于本项目 .gitignore 排除目录。也可传 `--archive-dir`、`--report` 指定新的本地位置。

**只要某个 ZIP 的 SHA/大小、成员清单、成员哈希、文件路径或危险软链接不一致，即判 BLOCKED。** 静态文本若发现疑似令牌则拒绝；发现私人路径则记录警告（不回显路径本身）。所有 `.blend`／NPZ 仍要求隔离环境内容审查。审计即使 6/6 通过，结果仍标注 **NOT_PUBLICATION_AUTHORIZED**。

## 人工核准后才可公开发布

1. 核对归档代码与素材没有未授权第三方来源和敏感信息，包括 `.blend` 内嵌脚本、引用路径与贴图；
2. 在不含个人凭据的 Blender 4.3.2 隔离环境，按旧六阶段源守卫逐阶段恢复，并重开检查；
3. 逐项将资产加入 `ASSET_LICENSE.md`，CC0 仅授权发布者有权处分的设计；不得给第三方素材套用 CC0；
4. 使用 GitHub Release 上传验证通过的 ZIP 和 SHA-256 清单，而非把约 59MB 的模型恢复 ZIP 推入长期 Git 历史；**不要使用 `--clobber` 覆盖已有 Release 资产**。GitHub CLI 的命令格式见其官方 [Release 文档](https://cli.github.com/manual/gh_release_create) 与 [上传说明](https://cli.github.com/manual/gh_release_upload)。
5. 从新的**公开 Release** 重新下载并检查，确认任何新参与者都可以恢复外观，再把旧私有仓库设为 Archived。此前不可删除。

## 安全边界

本工具**不解压执行**任何未知程序、不调用 Blender、不从旧项目触发 `workflow_run` 高权限自动合并，也不会自动把私人归档上传到公共 GitHub。报告为来源核验，不能当作“病毒零风险证明”或实体玩具生产认证。

GitHub API 当前连接无法直接复制私有 Release 二进制到公开 Release；若 ChatGPT Work 支持已登录浏览器环境，可运行上述受控迁移流程。避免在聊天中粘贴 token 或密码。
