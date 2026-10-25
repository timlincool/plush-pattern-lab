# 专业制造工作流：让数字模型真正接近可缝制

**核心定义**：最终能缝成什么形状，取决于裁片的静止长度、真实布料弹性、缝线、填充与工艺，不由三维渲染效果决定。

## 专业人员常用工具与数据

| 环节 | 常见工具 | 必需数据 | 软件能判断的范围 |
|---|---|---|---|
| 设计与分片 | Blender、Marvelous Designer / CLO 3D、二维制版 CAD | 前/侧/后视、成品尺寸、体积分区、材料布局 | 几何参考/缝线初稿 |
| 纸样与裁切 | 二维矢量 CAD、纸样图纸、DXF/SVG | 每片净缝线、缝份、对位缺口、布纹与毛向、尺寸公差 | 长度配对、排料和局部可展性 |
| 布料试验 | 拉伸试验、弯曲/剪切试验、称重 | 经/纬向载荷-伸长曲线、面密度、松弛滞回、厚度 | 将“假设弹性”改为实测材料模型 |
| 绣花与表情 | Brother PE-DESIGN 等刺绣程序 | 眼嘴点位、绣线、针数、衬布、局部刚度 | 面部定位、绣花局部加固 |
| 试样与填充 | 物理打样/样布测量，CLO/MD压力 *仅作近似* | 填棉重量、局部密度、压缩/恢复曲线、成品多视角尺寸 | 压缩支撑可先做代理，不能代替棉纤维 |
| 质量验收 | 实物样品、检验规范 | 缝线牢度、附件拉力、洗后变形、适用市场玩具安全要求 | 必须实际验证 |

## 本项目下一阶段工程门禁

1. **输入可追溯**：多视角设计、实际尺寸、部件清单和经审查的素材权限。
2. **裁片有意义**：对位缝线长度互相对应，正反/毛向有记录，2D 顶点与 3D 来源互相映射。
3. **畸变受控**：报告逐三角片的局部伸长主值、翻面、投影面积和布纹方向。遇到大畸变要增加裁片/省道，而不是只给面料增大弹性。
4. **模拟自二维开始**：为每片赋予面料测量数据，按关系图定位裁片，逐步缝合，再添加填充代理。
5. **对样布校准**：以 10×10cm 双向试布与相同形状充棉样件匹配力-伸长、尺寸变化、恢复，不通过就不能升级成“可生产”。

## 依据与边界
- Mori & Igarashi 2007, *Plushie*: https://doi.org/10.1145/1276377.1276433
- Jin et al. 2020, component template methods: https://doi.org/10.1016/j.cad.2020.102911
- Jin et al. 2022, *ToyAssembler*: https://doi.org/10.1016/j.cad.2022.103356
- Pietroni et al. 2022, fabrication-aware anisotropic flattening: https://igl.ethz.ch/projects/computational-patternmaking/
- Plush designer's account of MD + Photoshop + PE-DESIGN + fabric swatch calibration: https://www.marvelousdesigner.com/learn/userspotlight/post/a5fc6095271d40faaaac58937898b431
- CLO documentation, pressure for inflated/padded pieces: https://support.clo3d.com/hc/en-us/articles/115012381348-Pressure

**压力不是棉花，服装模拟器也不是对实际生产合格的证明。**
