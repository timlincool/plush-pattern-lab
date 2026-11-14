# B24 R1 真正 Blender Cloth 研究实验

此目录对应 Stage6 24 片 B 连接圈方案的 R1 裁片修订。R1 的设计与预定位不等于缝合成功。

固定输入来自受信 `main` Blender 运行 [#43558523018](https://github.com/timlincool/plush-pattern-lab/actions/runs/43558523018)，来源文件各有 SHA-256 验证。只有项目本体可信 main 上的工作流 `.github/workflows/stage6-b24-r1-physical.yml` 会执行。拒绝 `pull_request` 未审核代码。

流程：24 片/46 组数字接口旧版资料 → 依据真实 Stage6 截面重建 R1 上部 11 片二维静止裁片及 3D 初始定位 → 原下半身 13 片与 974 条配对弹簧不变 → Blender 4.3.2 原生 Cloth/Sewing Springs 40 帧真实求解 → evaluated depsgraph 顶点、面、缝线差、独立 GLB、Blend 及 SHA 证据。

**不可混淆：** 代码和预定位不是 R1 物理结果。仿真若成功，也不代表外形达标、边界物理焊接、避免自穿插、面料变形可缝，或者工厂纸样获准。运行保持无填棉/压力、无自碰撞、零重力以便与旧版作同条件 A/B。三块真实 Stage6 顶部源曲面和耳、云、尾等附件尚未缝入 R1。
