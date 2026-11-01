# Stage 6 三角环带：固定弧长的切缝展平实验

**研究性质：** 二维低边长误差候选，不是可裁剪纸样、缝份或实际布料静止形状。

## 输入与第一性原理

真实 Stage 6 八组接缝均为连通三角环带（512 点内缝线、256 点外边界、768 个三角片）。[既有投影实测](../experiments/stage6_hoof_seams_20261030/triangle_band_projection.json)显示直接平面投影的 P95 逐边缩短为 25%～30%，不能直接裁切。

1. 从[公开 Stage 6 Release](https://github.com/timlincool/plush-pattern-lab/releases/tag/cloud-alpaca-stage6-visuals-20261028)匿名下载，并按固定 SHA-256 在 Blender 4.3.2、禁用自动执行环境核验；只从真实模型提取八个相邻三角环带。原始三维坐标仅存 Runner 临时目录，**不上传 Artifact、不进 Git**。
2. 保留 512 点内侧缝线的真实三维累积弧长 s 与原顶点身份，二维令 (x,y)=(s,0)。按周长 L 做周期配对，跨周期三角形采用**每面角点 UV 副本**，形成单条径向切缝。
3. 只优化外圈自由顶点，最小化所有唯一网格边的相对边长差平方和：E=Σ[(二维边长－三维边长)/三维边长]²。用 SciPy 稀疏最小二乘和明确位移边界；最多 60 次函数评估，不改变原始三维网格。
4. **独立检查** mean/P95/max 逐三角片边长相对误差、局部面片翻转/退化、二维三角面重叠、切缝数量、求解收敛与边界命中。P95 下降不能覆盖翻面或重叠失败；不会设置自动制造合格状态。
5. 输出 8 组评分 JSON 和 **1:1 mm SVG 研究可视化**；SVG 不是裁布外轮廓，不包含缝份、毛向或实体工艺审核。

## 运行

可信 main 的 `.github/workflows/stage6-hoof-seam-reference.yml` 在已有 Blender 模型验签、3D 缝环与三角面门禁通过后调用：

~~~bash
python scripts/unroll_stage6_triangle_band.py \
  --input local-output/verified-only-patches.json \
  --output local-output/stage6-slit-score.json \
  --svg local-output/stage6-slit-reference.svg
~~~

其中输入 JSON 由前一步可信 Blender 实时生成，且绑定固定模型 SHA-256，不是仓库预置数据。现有两种方案的几何条件不同，比较时必须逐项报告，**不能把边长失配当成实际布料主伸长**。

## 论文依据

- Mori & Igarashi, *Plushie: An Interactive Design System for Plush Toys*, ACM TOG (2007), https://doi.org/10.1145/1276377.1276433：纸样几何与缝制模拟必须构成反馈。
- *Bounded-Distortion Piecewise Mesh Parameterization*, ETH IGL, https://igl.ethz.ch/projects/parameterization/BDPMP/index.php：切缝分片与失真应联合考虑。本实现不宣称具有该论文的方法或严格失真上界。
