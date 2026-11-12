# Stage6 整体装配母版：复用现有18片／9页A4的 Panel—Interface 缝线图

**P3软件研究纸样，不是原Stage6雕塑工业纸样；没有实体试缝。P4未开始，工厂批准数0。**

## 目的

现有 [下半身13片](STAGE6_LOWER_MOTHER_TOILE.md) 和 [上身5片](STAGE6_UPPER_MOTHER_TOILE.md) 已经通过各自独立来源和数字净缝检查，但是一直缺一个统一的裁片清单、逐条拼缝关系和缝制顺序。本轮把**已有9张A4原尺寸研究纸样**组织为一个18片装配包，不重新展开三角面，也不调用任何付费API。

结构仅借鉴开源 [GarmentCode](https://github.com/maria-korosteleva/GarmentCode) 的 Panel（裁片）和 Interface（配边）分层思想。代码全部独立编写，不复制其源码。初始研究UV仍可使用上轮已经验证的免费Blender ABF，Source SHA和Netline QA继续保留。

| 现有A4纸 | 包含的研究裁片 | 实际来源与风险 |
| --- | --- | --- |
| 1 | 一块YOKE-01下腹 | 原4×512点蹄口，外缘是新设计 |
| 2 | LEG-FL/FR/RL/RR四布筒 | 原源环512段周长，40mm高度是新假设 |
| 3 | SOLE-FL/FR/RL/RR四临时平面蹄底 | 不是原真实鼓起蹄底的展开 |
| 4 | BAND-1至BAND-4四条外围带 | 按新增YOKE外围64段各16段 |
| 5至8 | UPPER-1至UPPER-4四片上身试验布片 | 原Source截面只作包络参考，头肩造型未通过 |
| 9 | TOP-CAP-TRIAL一片试验头盖 | 真实耳、云、眼部接口均未做 |

共 **1+4+4+4+4+1 = 18片**，9张A4保持原来受信工作流字节内容，不冒充新生成的3D->2D纸样。

## 32组明确的纸上净缝配对

- YOKE四源蹄口连接LEG筒顶：4组、每组512段；
- LEG筒底连接临时平面SOLE：4组、每组512段；
- 四LEG布筒自缝直边：4组；
- YOKE外围连接四BAND底：4组、每组16段；
- 四BAND纵向侧边：4组；
- 四BAND顶缘连接四UPPER底缘：4组、每组16段；
- 四UPPER彼此的纵缝：4组、每组五站位区间；
- 四UPPER顶缘连接TOP-CAP对应四段：4组、每组16段。

新程序对每组独立重新计算每段二维净缝线长度，任意段不一致超过0.0001mm就拒绝组装。同一部件接口禁止同时被两条不同的缝使用；18片必须在同一个可达研究拼缝图。该阈值仅是浮点数值一致性检查，**不代表布料生产公差、缝向或真正实体闭合已经验证**。

BAND-3与YOKE约42.49mm的研究返口标记继续保留；实际布料翻面、填充、缝制顺序仍待实体试样。

## 真正可交付的机器可读产物

使用 scripts/build_stage6_18piece_sewing_pack.py 从同一次可信Stage6执行的lower、upper目录生成：

- print/sheet-01.svg 至 sheet-09.svg，逐张A4 210×297mm、带10mm校准；
- panel_interface_research_graph.json，18个裁片ID、32对接口、原Source SHA；
- sewing_sequence_RESEARCH_ONLY.md，10步试布操作与失效条件；
- assembly_map_RESEARCH_ONLY.svg，结构装配关系图（非布料剪裁图）；
- manifest.json，所有旧source、lower/upper manifest和新文件的SHA256。

CLI拒绝不同轮次lower/upper原source SHA、任意旧纸张被替换、被缩放的A4或覆盖旧资产。受信main Stage6 workflow在真实旧lower/upper生成后运行，新研究包统一归档。

## 不得误判为整只玩偶已完成

**数字18片连通，不等于还原原设计外形。** 已有验证显示原Stage6颈部Z130至155截面中心位移约71.4mm；旧UPPER的拟合3D轮廓与研究2D经线最大差约89.1mm，头肩还需重新设计。原3D四只圆鼓蹄底未完成真正布片。内外耳、7云层、尾巴、双眼、10水滴+10带子都没被接上。绒布伸长、毛向、有效6mm缝份、试缝、站立、返口、填棉、四视图及厂商签核均未验证。

**下一步必须转向原设计正侧背顶与真实Stage6三维模型的结构匹配，替换不保真的UPPER头肩母版，而不是再发明通用UV算法。** 保持旧四蹄4×512和下腹全部真实负例。

状态：P3 in_progress；P4 not_started；正式工厂纸样0；实体试缝0。
