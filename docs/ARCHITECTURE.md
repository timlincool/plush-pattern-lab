# Python 包与依赖架构

**首要目标：纯数学算法可复用、可测；Blender 作为外部运行时适配层；对旧 CLI 保持兼容。**

```text
plush-pattern-lab/
├── pyproject.toml
├── src/plush_pattern_lab/
│   ├── patterns/                  # 2D 裁片、帽片、SVG 与材料样条
│   ├── validation/                # 应变、缝口、拓扑、穿插报告判定
│   └── blender/                   # Blender 4.3.2 场景、仿真、审计
├── scripts/                       # 旧脚本兼容入口 + 质量工具
├── tests/                         # 正反例与架构验证
└── .github/workflows/             # 受信 main 的 CI / 仿真
```

依赖方向：

```text
scripts（入口）──────► patterns ─► NumPy/Shapely
          ├─────────► validation ─► NumPy
          └─────────► blender ────► patterns/validation + bpy
```

规则：`patterns` 和 `validation` 不导入 `bpy` 和 `scripts`；包内不得循环依赖。Python 能用函数表达的纯计算，不强制引入工厂/单例/策略模式；真实发生变化的物理求解参数与评估口径才抽离成明确函数边界。

现有命令仍支持：

```bash
python scripts/capped_gore_pattern.py --out /tmp/cap.json
python scripts/plush_gore_pattern.py --out-prefix /tmp/gore
blender --disable-autoexec -b --python scripts/sewing_capped_poc_blender.py -- --spec pattern.json --output trial.blend --report trial.json
```

安装后可用入口例如 `plush-capped-gore --out /tmp/cap.json`；Blender 必须使用 `--disable-autoexec` 执行不可信资产检测。

迁移不改原 JSON 对外证据契约、实验阈值、材料参数或目标初始化方式。必须用真实 Blender 仿真复验新代码，不能只靠纯 Python 单测。严格分层及质量门禁不是“已经能量产”的承诺。
