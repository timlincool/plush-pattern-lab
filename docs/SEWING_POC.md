# 从二维净裁片启动真实 Blender 缝合弹簧试验

采用独立参数化八瓣椭球，不使用私有模型。目的：验证“二维静止裁片长度、拼缝对应关系、预定位和 Blender Cloth 缝合弹簧”是否构成真正可求解的研究闭环。

程序 `scripts/sewing_poc_blender.py` 从 `plush_gore_pattern.py` 生成的 JSON 创建每片独立的平面静止网格（形态键），在三维圆周预定位，并用跨片**独立边（loose edges）**建立缝线对应，Blender Cloth 设置 `use_sewing_springs=True`。该机制由 Blender 4.3 Python API 提供。使用统一质量、伸缩刚度和无重力条件，只检查缝线间距是否下降，保存真实求解快照及数值报告。

真实执行情况请查看 [Actions 的 Sewing PoC 工作流](../.github/workflows/sewing-poc.yml)，不能把理论脚本等同于运行成功。

阶段 1 **不**引入压力、棉花或自碰撞。这是有意控制变量：若缝线未闭合，则内部填充压力根本不具有正确的封闭体积基础。后续应先完成缝合后拓扑重建/自碰撞审计，再根据真实样布校准，才进入填棉测试。

依赖依据：
- Blender 4.3 ClothSettings `use_sewing_springs`、`rest_shape_key`：https://docs.blender.org/api/4.3/bpy.types.ClothSettings.html
- *ToyAssembler* (2022) 通过缝线关系图和曲面预定位，模拟二维裁片形成三维玩偶：https://doi.org/10.1016/j.cad.2022.103356
- *Plushie* (2007)：https://doi.org/10.1145/1276377.1276433
