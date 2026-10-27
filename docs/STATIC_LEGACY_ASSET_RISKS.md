# 真实源归档的代码/数组静态检查（2026-10-26）

已核对过六个真实私有历史恢复 ZIP 的 **252 个成员 SHA-256**；本次再次对其内含源代码和 NPZ 做**不执行源码、不加载 pickle、不运行 Blender**的离线静态检测。

| 项目 | 实际检查 |
| --- | ---: |
| Python 脚本 | **56** |
| NPZ 归档 | **20** |
| 有效 .npy 数组头 | **134** |
| 需要反序列化对象类型的数组 | **0** |
| 数组头解析失败 | **0** |
| Python `exec()` 执行入口 | **7** |

其中 `02-selected-appearance-D.zip` 的五个执行入口用于按来源配置动态调用 Blender 补丁，`04` 与 `06` 各有一处出现在历史溯源重建脚本中。**这只是定位危险能力，不是判定这些代码有病毒**；即使有 SHA 守卫，执行前也需要先检查具体动态读取的目标路径、代码来源与环境边界。

[冻结摘要](../design/archive-v25/static-risk-20261026.json) 不包含个人路径、运行时令牌或脚本正文。此阶段不能因为 134 个数组都是数值数组、或者原始 Blender 场景预检 PASS_SCOPE_LIMITED，就认为可不经进一步审查直接公开执行。

## 可重复的本地校验

在已通过 `prepare_legacy_release.py` 的相同本地源 ZIP 文件上：

```bash
python scripts/prepare_legacy_release.py --download
python scripts/inspect_legacy_archives.py
```

`inspect_legacy_archives.py` 必须逐包先验证 **发布版 ZIP 哈希及成员哈希**，之后才以 AST 读取 Python 文件和只读 NumPy 格式头解析 NPZ；不调用 `np.load()`，不运行包内任何代码，不覆写现有检查报告。结果在本地 `local-output/legacy-static-review.json`，属于 **REVIEW_REQUIRED**，不是最终发布许可。

实际 Blender 4.3.2 六阶段恢复、各部件授权与保存重开检查仍待完成；当前公开项目的物理模拟依然只是合成椭球。
