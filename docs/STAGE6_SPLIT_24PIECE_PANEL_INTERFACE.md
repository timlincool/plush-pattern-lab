# Stage6 分离头身 24片 A/B：全装配 Panel–Interface 研究合同

**仅为软件试布研究。P3进行中，P4未开始；正式可裁工厂纸样和实体样品均为0。**

## 为什么在既有18片后继续做24片

原18片/9页A4已完成32组数字净缝；但原Stage6 Z130→155mm 头颈截面中心相差约71.386mm，原3D包络经线与新2D纵缝偏差约89.121mm。把这些裁片连接成完整数字图，并不能证明造型真实。

优先复用2026-11-10已实跑的 **A独立封闭头颈**、**B肩片内孔＋10mm COLLAR** 两套互斥母版：**每套13片旧下腹＋11片新上身=24片，旧4页＋新11页=15页A4**。不是18片＋24片累加。原四个Stage6蹄口4×512原Source边身份和旧下腹纸样不变；新头肩仍为量测包络指导下的人造几何，未从原主壳直接展平。

## 新增的真正可追踪关系

新模块 `patterns/stage6_split_volume_panel_interface.py` 从原下腹JSON与原A/B研究JSON重新建立：

- **20组既有下腹数字缝**：4组蹄口↔腿筒、4组腿筒↔临时平底、4组腿筒自身、4组下腹YOKE↔BAND、4组BAND自身；
- **20组新增头肩公共数字缝**：4组BAND↔TORSO、4组TORSO侧边、4组TORSO↔肩盖、4组HEADNECK侧边、4组HEADNECK↔头顶盖；
- **A额外5组**：4组HEADNECK下口↔独立封底盖，**1组肩盖表面↔头颈底盖的手工安装关系**。前44组是数值净缝可匹配，第45组不是可测的切边配缝，`first_2d_netline_mm=null`，不能伪装为机器车缝已经验证。删除这组手工关系后，头和身体是**两个分离数字组件**；
- **B额外6组**：肩盖内孔↔COLLAR下口1组（64段）、COLLAR上口按HEADNECK四片各16段分为4组、COLLAR自身纵缝1组；合计**46组数字配边**，纸上连通为一个组件。

这里的46/45属于“按实际Panel边命名”的分组数，不能与旧QC的A=25/B=23个研究关系直接相加：旧QC把B的四片头颈根缘汇总成一个64段关系，并包含既有研究接法分类。所有数字缝仍逐段重新核对有限、正长度、误差≤0.0001mm，禁止接口重复占用、未知裁片和图不连通；这**不是**布料缝长公差。

## 输出与运行

原 `scripts/build_stage6_split_volume_toile_ab.py` 在受信原Stage6固定源和同次下腹13片输入下，新追加两份：

- `split_volume_toile_AB_research/A_separate_stuffed_head/panel_interface_research_graph.json`
- `split_volume_toile_AB_research/B_integrated_neck_port/panel_interface_research_graph.json`

各自包含24片清单、所属11张新A4位置、全部接口、数字连接分量、手工未验证连接、原Source身份、阶段状态。原22张A/B纸张、其他QC、装配指南都保留；manifest继续为每一份新输出建立SHA-256。

`tests/test_stage6_split_volume_toile.py` 添加正例和篡改负例；受信main Stage6 workflow需要真正重算锁定的原Blender 4.3.2/PLY，检验旧四蹄、24片/15页、A两个数字组件、B一个数字组件以及全部成员SHA。**合并或Python单测成功不等于原Blender运行或实体试缝已经通过。**

## 两次可信main原Stage6运行 + Python质量门禁

- [真实原模型 #43349657766](https://github.com/timlincool/plush-pattern-lab/actions/runs/43349657766) 成功（合并PR #179初版）。A/B各24片对应图、Source、原下腹、文件SHA与组件数量均在受信工作流中检验。
- [最终main真实原模型 #43350338730](https://github.com/timlincool/plush-pattern-lab/actions/runs/43350338730) 成功（提交 `f3c54fd65412194d78a2ef29b2f609a50e383d64`），原Source 4×512不变，两套图/旧4页和新11页、手工与数值接口身份通过。
- [同一提交Python #43350338822](https://github.com/timlincool/plush-pattern-lab/actions/runs/43350338822)：**682/682测试、Ruff/复杂度和wheel打包均通过**。本轮另两次早期Python失败仅为I001导入空行及Ruff format的两处分行，已由PR #180/#181修复；另一次真实Stage6 #43350167038 因上游Blender下载HTTP 403失败，后来最终可信main运行成功。
- [永久实验摘要](../experiments/stage6_split_24piece_assembly_20261112/summary.json) 固定成功Run、原Source哈希、两个24片图接口计数、Artifact ID与工厂否决门禁；原始详细纸样与逐文件SHA仍以受信Run里的manifest为准。本轮没有实体缝合证据。

## 当前明确不能越过的门槛

A额外手缝位置、强度、填棉稳定性未测。B肩孔最小余量仅约13.41mm，双份6mm缝份加研究余量只剩约0.41mm，返口42.49mm的真实翻出能力未知。两版的头颈根相对原Z145源截面最大XY偏移25.55/29.14mm；后身源代理经线与2D研究净缝仍相差约54.36mm。原鼓蹄底、内外耳、七云、尾巴、五官和十水滴带均缺正式纸样。

**下一步实物工作**：优先用A废布打印/试缝并记录四方向头身比例和手缝强度；若B进入废布验证，先试颈圈狭窄桥宽与返口。之后依据真实样片和原四视图重新设计不保真的头肩，而不是降低数值阈值或重写UV。