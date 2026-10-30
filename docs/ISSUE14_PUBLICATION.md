# Issue #14｜单一公开开发仓：Stage 6 已迁入

**2026-10-30 状态：原型研发必要的四张 PNG 与可编辑 Stage 6 模型均在 `timlincool/plush-pattern-lab`，不再需要两仓来回开发。** 旧私有仓仅保留历史恢复资料和冷备。

## 本公开仓资产

| 已迁入内容 | 公开位置 |
| --- | --- |
| 原始设计、选中 D 外观、单蹄接缝与毛根对照四张 PNG | [参考图片](../design/reference-v25/images/README.md)，在 Git 中接受 SHA-256/PNG CRC/元数据测试 |
| 七份 v25 合同与 JSON、纸样/Blender/测试源码 | [参考目录](../design/reference-v25/README.md)、`src/`、`tests/` |
| **Stage 6 四蹄可编辑模型** | [公开 Release](https://github.com/timlincool/plush-pattern-lab/releases/tag/cloud-alpaca-stage6-visuals-20261028)，唯一附件 `cloud-alpaca-stage6.blend` |

公开模型：**89,853,017 字节**，SHA-256：

```text
38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a
```

[直接下载模型](https://github.com/timlincool/plush-pattern-lab/releases/download/cloud-alpaca-stage6-visuals-20261028/cloud-alpaca-stage6.blend)。GitHub Release API 确认 `draft=false`、一个 `uploaded` 附件、文件大小与 SHA-256 匹配。**维护者验收报告**：从公开地址匿名下载且固定大小/SHA-256 核验通过；Blender 4.3.2 在隔离环境、禁用自动执行下重开，469 个对象、四蹄 4/4 配准、最大误差 0 mm。Blender 结果来自维护者报告，非本仓 Python CI 再执行。

### 不依赖私有仓的下载与验签

```bash
python scripts/verify_issue14_public_release.py
python scripts/verify_issue14_public_release.py --download-dir local-assets/verified-stage6
```

工具检查公开 Release 的真实资产清单，再流式验证唯一模型 SHA-256 和字节数；第二条保存到新目录，拒绝覆盖。完成后在隔离环境依 [真实模型四蹄检查](REAL_MODEL_INTERFACES.md) 运行 Blender 4.3.2 `--disable-autoexec`。无须 PAT/Secret、跨仓工作流或 Git 分片。

## 剩下的不是研发必需输入

旧私有仓 `archive-20261023` 有 19 份 ZIP（含六阶段原件），`issue14-zip-staging-20261028` 有六份脱敏候选 ZIP；`source/` 含各阶段重建源码、H/E/D 外观脚本和旧补丁，其他 Releases 含早期 `.blend`、Artifact 与诊断证据。**这些均未整体迁入公开仓**。旧脱敏六阶段曾完整恢复通过一次，进一步隐私清理版本的 H/C3 签名仍有跨 Runner 非确定性。它们是从零复建及追溯资料，不影响从已公开 Stage 6 上继续研发。

旧高权限自动合并/PR 工作流、凭据、私人日志与未经授权第三方素材**不迁移**。旧仓仍为 private、未 Archived；在备份唯一原件与历史恢复能力未妥善处理前不得删除，避免将历史恢复工作变成新的公开仓开发前置条件。

## 验收边界

Stage 6 能匿名取得、完整重开、四蹄配准成立，**不代表外形已还原到二维设计，更不代表能打印、缝制、填棉或通过玩具安全要求**。新的几何、布壳和纸样研发只在公开仓进行。详情见[唯一开发基线](原型开发基线.md)。

授权：实际公开四 PNG 与 Stage 6 原创视觉模型 CC BY 4.0；已有七份 CC0 设计资料不变；代码 MIT。见 [ASSET_LICENSE.md](../ASSET_LICENSE.md)。
