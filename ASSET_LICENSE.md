# 艺术资产许可与来源

**MIT 仅作为本项目自己拥有授权权利的软件代码与其文档的授权；不能自动视为所有视觉资产也使用 MIT。**

包括 `images/`、历史 Release 附件、`.blend` 模型、渲染、材质贴图、PDF/SVG/DXF 工艺图等，在没有逐项完成来源与版权许可核验前，暂不提供独立的商业再分发授权，且不能将未有权限的外部素材纳入发行版。

计划中的开放方式：
- **代码：** MIT（见根目录 LICENSE；发布前仍应确认代码的全部权利）。
- **原创且确有完整授权的设计图/模型/纸样：** 经权利确认后，可单独选择 CC BY 4.0（允许商用改编但要求署名）或更宽松授权；应在正式发行说明中按文件列出。
- **他人素材：** 遵守原始许可证或从公共发行包排除。
- **历史诊断/私人运行日志：** 默认不随公开版发行，不应因为存在于私人仓库就认为可以公开。

**开源代码不代表所设计的玩偶已满足物理安全、填料或产品法规要求。**

## 本次明确授权的七份参考资料

`design/reference-v25/PROVENANCE.json` 中列出的**七份历史外观合同与几何JSON**，用户明确允许他人使用、修改和再发布，在发布方拥有可处置权利范围内以 [CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/) 尽可能放弃版权/数据库权利（必要时适用后备许可）。允许商用，不要求署名。

**CC0 只限上面七份已列名资料**，不自动覆盖 PNG、完整 Blender 模型、第三方贴图或旧 ZIP。图片另依下方 CC BY 4.0 清单授权；AI输出可能不享有独占版权，CC0也不能处分他人权利。

## Issue #14：云朵羊驼原创视觉资产的公开授权（2026-10-28）

维护者确认拥有或已取得可公开再分发的原始云朵羊驼设计 PNG、Blender 模型和选定六阶段恢复素材的相应权利，并选择对**实际纳入公开发行清单的原创视觉资产**使用 **Creative Commons Attribution 4.0 International（CC BY 4.0）**。

- 许可全文：https://creativecommons.org/licenses/by/4.0/legalcode
- 授权方/署名：Cloud Alpaca / timlincool。
- 建议署名：「Cloud Alpaca visual design and model © timlincool, licensed under CC BY 4.0」；再分发须提供许可链接、标记改动，不得暗示作者为改动背书。
- 适用范围：**本仓库实际提交的四张原型 PNG，以及已在[Stage 6 公开 Release](https://github.com/timlincool/plush-pattern-lab/releases/tag/cloud-alpaca-stage6-visuals-20261028) 发布的原创 `cloud-alpaca-stage6.blend`（SHA-256 `38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a`）**。以后新增视觉或模型须逐项核准。**不自动把未列名的旧私有历史附件视为已公开资产**。
- Python 源码在拥有相应权利的范围内遵循仓库 MIT 代码许可证。恢复包若同时包含源代码与艺术资产，应在发行说明中列出两类许可；第三方依赖/素材始终使用其各自许可，未核准的部分必须排除。
- 先前明确 CC0 的七份 `design/reference-v25/` 参考文件保留 CC0，不追溯改成 CC BY 4.0。对公开发行版的额外清理与改写应保留清单中的源文件 SHA、发行版 SHA、清理类型和出处。
- 非生产声明：许可允许商业再利用，但不构成实体玩具、缝制纸样、材料、填充、儿童产品安全或量产验收保证。

**当前发布状态（2026-10-30）：** 已有四张经来源与元数据审查的 PNG 进入本公开仓库的 `design/reference-v25/images/`，其具体文件和哈希由 [manifest.json](design/reference-v25/images/manifest.json) 固定：`original-design.png`、`selected-D-appearance.png`、`single-hoof-seam-comparison.png`、`single-hoof-fleece-comparison.png`。这四张适用上述 CC BY 4.0，且与先前七份 CC0 资料分别授权。**Stage 6 可编辑 `.blend` 已在上述 Release 公开，但六阶段历史恢复 ZIP 仍未公开**；不得以本声明代替二进制发布、安全审查或物理制造验收。
