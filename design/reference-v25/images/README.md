# 云朵羊驼对照图片（已公开，开发用）

本目录与原型合同、纸样源码位于**同一个** `plush-pattern-lab` 仓库。后续开发只引用这里的公开资源，不必去旧私有仓库找两张单蹄工程对照图。

## 已迁入

| 图片 | 阶段与含义 |
| --- | --- |
| [单蹄接缝对照](single-hoof-seam-comparison.png) | 2026-10-22 单蹄共享边界的历史工程对照，**不是最终四蹄渲染** |
| [单蹄毛根修整对照](single-hoof-fleece-comparison.png) | 同期局部毛根/接缝的历史工程对照，**不代表已经完成服装级或实体打样** |

这两份图从旧私有仓库独立读取，按原字节创建 Git 对象；旧、新仓 Git blob SHA-1 完全一致。结构审计确认 PNG 完整、无 `tEXt/iTXt/zTXt/eXIf` 元数据块。每份宽高、字节数、SHA-256 与 Git blob SHA-1 见 [manifest.json](manifest.json)。

## 仍需一次性迁入

- **原始设计图** `original-design.png`：必须使用已清除私密元数据的原版，不以重新生成/截图替代。
- **D 阶段选中外观** `selected-D-appearance.png`：需使用清理过渲染元数据的版本。
- **Stage 6 可编辑场景** `cloud-alpaca-stage6.blend`：建议置于本仓库 Release，配套 SHA-256；它是四蹄几何检查点，不能混同为 D 阶段图片。

原始设计和 D 阶段图片在旧仓私有暂存 Release 已有清理候选，Stage 6 也有保存重开过的候选；**当前本仓库还未取得以上三份二进制，不能声称已经完整自包含。** 完成一次性转移后，应删除本段过期状态并更新清单。

许可：本目录已迁入的两份原创视觉资产采用 [CC BY 4.0](../../../ASSET_LICENSE.md)；代码仍是 MIT。若图片中含另有权利的第三方素材，其许可不因本项目声明而改变。

[原型开发唯一入口](../../../docs/原型开发基线.md) · [Issue #14](https://github.com/timlincool/plush-pattern-lab/issues/14)
