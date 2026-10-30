# Issue #14｜公开资产归一的发布门禁与可复现说明

维护者已确认：有权公开的云朵羊驼原创 PNG、Blender 模型及六阶段恢复素材采用 **CC BY 4.0**，代码遵循原仓 MIT；已经发布为 CC0 的七份参考 JSON/文字不变。

## 发布范围（必须以发行清单为准）

- 视觉目标：原始设计图、选中 D 阶段渲染及两张蹄部工程对照图，保留像素而清除私人元数据。
- 可编辑研究模型：恢复后的 Stage 6 四蹄模型。清理旧 Render Output 路径后另存版本，并以全对象和材质签名复核。
- 六阶段恢复输入：从私有历史签名 ZIP 构造脱敏发行版。原始 ZIP 与清洗后 ZIP 的 SHA 不能混用；每一个内部成员与嵌套 SHA256.json 必须重新验签。
- 随包提供 `release-integrity-manifest.json`、`SHA256SUMS`、CC BY 4.0 原创视觉资产许可证与历史来源映射；未使用的 13 个旧实验包不作为默认发布物。

## 发行门禁（全部满足才可公开）

1. **源数据准确性**：旧 Release 原始六 ZIP 和 252 成员 hash 全部与固定 GitHub 公共来源清单相符。
2. **内容安全与隐私**：排除令牌、私人路径、私人 GitHub Library ID、历史日志中的个人数据；四张 PNG 的文本/EXIF 必须清理，渲染旧绝对路径须在公开模型中规范化。
3. **代码与模型语义不放宽**：旧执行脚本和 NPZ 数值字节保留；仅必要的来源配置路径在可解释的变更契约内调整。重新打包后保存新 SHA 清单；完整六阶段严格守卫及保存/重开检验必须在隔离环境通过。
4. **独立验证**：新建公开 Release 后从未经 GitHub 登录的会话下载，核对文件 SHA、ZIP 成员、模型重开、参考渲染及已有项目质量/碰撞测试。
5. **完成归一**：公开 Release 确认全部可下载/复现，再将旧私有 `cloud-alpaca-plush` 设置 Archived；不得提前删除历史唯一来源。

## 仓库权限边界

ChatGPT 当前 GitHub 连接支持 PR、Issue、文本文件与只读历史二进制元数据，**不包含创建 Release/上传二进制附件的接口**。不能把私有 Actions 任务的默认 `GITHUB_TOKEN` 当作有权写入另一公开仓库的令牌。

若需要无人值守迁移，维护者可在**私有仓库** Actions Secrets 创建一个仅授权 `plush-pattern-lab` 的 fine-grained GitHub PAT，仓库权限仅设 **Contents: Read and write**，供受信、手动触发的单次发布工作流使用。**不要将 PAT 粘贴到 Issue、聊天、日志、仓库源码或 PR。** 也可使用自己已登录的 GitHub CLI 或 ChatGPT Work 云端浏览器实施跨仓附件搬运。

本页不是 Release。由于权限、源文件内容及新发行包均需独立验收，只有发布后经实际下载验证的文件才可标记为公开完成。Open Source 不等于已验证可制造的玩偶；材料、缝制、填充和儿童安全仍属独立未完成课题。

## 第一批：公开视觉模型与图片的匿名验收

截至 2026-10-28，发布器位于私有仓库受信主分支，目标是公开预发布 `cloud-alpaca-stage6-visuals-20261028`。这个标签**在实际发布前不存在**，不能将私有 Release 当作公开成功。

第一批只包含一个经过路径规范化和保存重开检验的 Stage 6 可编辑模型、四张去元数据 PNG、CC BY 4.0 说明、发行清单与 SHA256SUMS；**不包含六份历史恢复 ZIP**。那些 ZIP 的跨 CPU 严格重建仍在单独处理。

在公开 Release 正式创建后，使用全新、无需 GitHub 登录的环境，从公开仓库根目录运行：

~~~bash
python scripts/verify_issue14_public_release.py
~~~

工具不依赖外部 Python 库，不传递 GitHub Token，逐文件流式下载但默认不落盘；检查五个二进制固定大小和 SHA-256、发行清单与 CC BY 4.0 许可、文件名称和 SHA256SUMS。想保留模型和图片时执行：

~~~bash
python scripts/verify_issue14_public_release.py \
  --download-dir local-assets/issue14-verified-stage6
~~~

目标目录必须不存在，拒绝覆盖。出现缺失、重复、额外文件、身份或哈希错误时直接失败，不将公开模型当成未经检验的可执行资源。

进一步使用 Blender 4.3.2 验证网格时，应在隔离环境里使用 `--disable-autoexec`，并执行 `scripts/audit_hoof_interfaces.py`。独立 SHA 与四蹄接口验证不等于二维布片、实体打样或制造放行。

**完成条件分层：** 第一批视觉资产匿名验签通过，只能将“视觉资产公开”标记完成；六份源 ZIP 的可公开恢复、完整独立重建与旧私有仓库 Archived 仍保持未完成，Issue #14 不提前关闭。

## 2026-10-30 实际迁移进展（优先满足单仓库研发）

原始设计、选中 D 阶段外观与两张单蹄工程对照 **四张 PNG 已提交至本公开仓库 Git 的 `design/reference-v25/images/`**，详情见 [图片与哈希清单](../design/reference-v25/images/README.md)。已在本仓库用字节大小、来源/目标哈希和 PNG CRC/元数据测试验签；不必再为图片额外建立一个 Release。

剩余独立任务是把约 89.85 MB 的 `cloud-alpaca-stage6.blend` 放入**本公开仓库的 Release**，从公共地址独立下载验证其原始候选 SHA-256、Blender 禁用自动执行重开与几何守卫，然后让后续研发只取本公开仓库。六份历史 ZIP 仅用于溯源/灾备而非日常开发输入，保留安全门禁；旧私有仓不得在未保存唯一来源前删除。

以上是对本文 2026-10-28 第一批五资产方案的**更新**；历史审批与验证记录保留，但不再需要重复公开四张已经入库的 PNG。
