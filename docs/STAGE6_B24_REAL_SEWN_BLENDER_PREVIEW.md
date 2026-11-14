# Stage6 B24：真正二维裁片→Blender Cloth物理缝合→可核验3D成品研究图

**2026-11-14**：受信main [Stage6 #43558523018](https://github.com/timlincool/plush-pattern-lab/actions/runs/43558523018) 已成功跑通**真实的物理求解**，这不是ImageGen和不是原Stage6三维网格重绘。具体机器证据在 [实验摘要](../experiments/stage6_B24_actual_Cloth_20261114/summary.json)。

## 输入及使用的现有开源框架

- 2D裁片：此前已构建的 B_integrated_neck_port 共**24件仿真研究二维布片**、46组数字缝线接口（下半13件+头肩11件），不是直接从源Stage6 466,278个原三角面低失真展平，更不是工厂批准裁片。
- 四孔腹片：已有的Shapely/GEOS `constrained_delaunay_triangles` 约束多边形算法，从源下腹外边64点、四蹄孔各512原边每8点采样的64点构造，验证326三角面、原外边+四蹄共5条完整边界、320边不丢、不插新点，不能直接声称原512点全部参与了求解。
- 缝合：现有 Blender 4.3.2 的原生 Cloth/Sewing Springs，原二维Rest Shape单独存为形状键；源Stage6包络只作为初始几何定位与左侧视觉参照，**最终顶点从第40帧evaluated depsgraph Cloth读取，绝不抄原目标顶点**。
- 文件： `research/stage6_b24_source_yoke_cdt.py`、`research/stage6_b24_real_cloth_preview.py`，受信main `.github/workflows/stage6-hoof-seam-reference.yml`。此Runner无`libEGL.so.1`，会导致Blender Workbench后台渲染中止；故代码先保存完整真实物理顶点、面和弹簧源端为NPZ，再在CPU上使用开源Trimesh/Matplotlib制作图片/GLB。用户下载研究包自带原Rest Shape、输入SHA、真实输出和渲染源码。

## 同一真实Runner的完整结果

| 研究指标 | 成绩 | 能证明/不能证明 |
|---|---:|---|
| 独立二维代理试布件数 | 24 | 只证明24片有对应二维静止网格 |
| Sewing Springs | 974 条 | 原软件确实读取这些边界配对 |
| 物理求解 | 40帧，约1.83秒 | 有真实逐帧求解，不是摆好3D截图 |
| 初始平均缝合弹簧端点距离 | 0.558522mm | 数学物理界面初始间距 |
| 最终平均缝合弹簧端点距离 | **0.007380mm** | **缝合弹簧接近**，不等于原物理边焊接/布料闭壳/不穿插 |
| 最终最大缝合弹簧距离 | 0.116483mm | 仍有个别不为0的弹簧端点距离 |
| 实际第40帧网格 | 2431顶点、1798原面 | 有可独立观察的真实求解结果 |
| 真聚酯棉填充/压力 | **未开启** | 不证明鼓胀/成品比例 |
| 自碰撞/面料厚度 | **未开启** | 不证明真实布料没有穿插 |
| 工厂可裁批准 | **0片** | 物理模拟和产品打样需分开认证 |

右侧真正的求解网格可以通过同源`NPZ`导出GLB、对比正面/侧面/3/4视图。真实计算结果显示：**头部像扁筒、身子近盒形、四腿近圆管，整体和目标Stage6原主体相差很大**。这是重要的否决证据：数字缝长可以拉近到0.007mm，而视觉上仍完全不像预期羊驼。源Stage6 25%主壳对比只包含核心身形，耳朵/云层等独立装饰不在左侧原PLY视图中。

### 后续每次迭代必须这样验收

必须提供 `source 2D pieces + stitched edges + evaluated Blender 3D mesh + target vs actual front/side/3quarter + seam gap/shape/overlap/fullness metrics + all original Source IDs`。旧算法对三角面P95<10%不代表成品外观合格；有形状偏差就优先重新设计头身围片/云耳装配/省道或真实绒布物理，而不是不断调UV。初步B24物理试布就是**证明能模拟，同时证实当前形体错误**的研究里程碑。

真实填棉、重力、碰撞、毛绒/经纬伸长、返口能力、实体样布和工厂签核都尚未确认。工程状态持续 P3 in_progress、P4 not_started、正式工厂纸样0片。
