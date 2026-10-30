# Issue #14｜唯一公开仓库：Stage 6 单文件交付

**唯一持续开发仓：** [plush-pattern-lab](https://github.com/timlincool/plush-pattern-lab)。旧私有 cloud-alpaca-plush 只作一次性迁移来源与冷备份，不再开发，也不建立跨仓自动同步。

## 当前实际状态（2026-10-30）

- 原始设计图、选中 D 外观、单蹄接缝、毛根对照 **四张已脱敏 PNG 已进入本仓库** design/reference-v25/images/；由其 manifest.json 和 tests/test_public_reference_images.py 验签。无需再放入 Release。
- 七份第 25 轮参考资料以及纸样/模拟/校验代码均已在本仓库；历史合成布壳不能当成真实角色的实体纸样。
- 唯一尚缺的原型开发输入是 **Stage 6 四蹄可编辑 Blender 模型**。目标公开仓库目前没有 Release。
- 六份历史 ZIP、252 个成员的校验记录仍作灾备/溯源；不阻塞本仓库新研发。不在未保留唯一备份前删除旧私有仓库。

## Stage 6 Release 最小契约

| 项目 | 固定值 |
| --- | --- |
| 公开仓库 | timlincool/plush-pattern-lab |
| 标签 | cloud-alpaca-stage6-visuals-20261028 |
| **唯一 Release 附件** | cloud-alpaca-stage6.blend |
| 精确字节数 | 89,853,017 |
| SHA-256 | 38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a |
| 私有暂存来源 | timlincool/cloud-alpaca-plush 的 issue14-visual-staging-20261028 Release |
| 许可 | 已列名原创视觉/模型 CC BY 4.0；Python 源码 MIT；七份原有设计资料 CC0。见 ASSET_LICENSE.md |

该 Stage 6 候选源哈希已经在私有只读 Actions 中核对，但**尚未从目标公开 Release 匿名下载复核**。不上传未经审查的历史日志、私有路径、代码或第三方素材。

## 一次性搬运（维护者已登录 GitHub CLI 的 Windows PowerShell）

当前聊天 GitHub 连接不提供 Release 二进制上传接口。使用自己的 GitHub 登录态搬运即可，**不需要新建 PAT/Secret**，也不将 89MB 文件拆分进 Git 历史。

~~~powershell
gh auth status
gh release download issue14-visual-staging-20261028 --repo timlincool/cloud-alpaca-plush --pattern cloud-alpaca-stage6.blend --dir local-assets/stage6-handoff

$file = "local-assets/stage6-handoff/cloud-alpaca-stage6.blend"
$expected = "38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a"
if ((Get-Item $file).Length -ne 89853017 -or (Get-FileHash $file -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) { throw "Stage6 source failed SHA-256 or size check" }

gh release create cloud-alpaca-stage6-visuals-20261028 $file --repo timlincool/plush-pattern-lab --target main --title "Cloud Alpaca Stage 6 editable Blender model" --notes "Editable four-hoof research prototype. Original artistic asset © timlincool, CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ . Not a manufacturing pattern or toy safety certification."
~~~

**发布后的独立门禁：** 在没有 GitHub 登录态的环境，从本公开仓库运行：

~~~powershell
python scripts/verify_issue14_public_release.py
python scripts/verify_issue14_public_release.py --download-dir local-assets/verified-stage6
~~~

验签器先匿名读取 GitHub Release 的真实元数据，要求**恰好一个**指定模型附件且状态为 uploaded，再以已固定的大小和 SHA-256 流式校验整个二进制；可选择不落盘。不依赖私有仓、发布者自述的 SHA256SUMS 或任何 GitHub token。下载失败会删除未完成文件；本地目标目录必须事先不存在。

随后在隔离、无凭据环境使用 Blender 4.3.2 --disable-autoexec 重开验签文件并执行 scripts/audit_public_blend.py、scripts/audit_hoof_interfaces.py。通过后再更新原型基线的正式公开地址与 Issue #14 的资产状态。**哈希与几何吻合不等于二维纸样、填棉、实体打样或制造安全通过。**

历史六 ZIP 和相关安全审查保留在 [迁移审查](RELEASE_ASSET_MIGRATION.md) 与 [来源清单](PUBLIC_SOURCE_MIGRATION_20261026.md)；它们不是新开发的第二套主线。
