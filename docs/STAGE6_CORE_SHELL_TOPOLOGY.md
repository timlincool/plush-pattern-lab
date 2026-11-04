# Stage 6 主壳 466,278 面的真实拓扑门禁

此项属于 [工厂路线图 P3](FACTORY_ROADMAP.md) 的**可缝主壳制版前审计**，不是对三维模型做减面，也不生成裁片或缝份。制造方案必须先确认主壳是否是**单块连通、边界有向匹配、无非流形边**的真实曲面，再讨论如何建立低面数可制版代理；不能简单按原 Mesh 面数做“百分比减面”并宣称生产可行。

## 原始输入与不变量

- 唯一输入：[本仓库 Stage6 公开 Release](https://github.com/timlincool/plush-pattern-lab/releases/tag/cloud-alpaca-stage6-visuals-20261028)，SHA-256 固定为 38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a。
- Blender 固定 4.3.2，必须使用 --disable-autoexec；只读加载源文件，先运行已存在的四蹄世界坐标与有向 3D 接缝严格配对。
- 对主壳 PRIMARY continuous sculpt | new anatomy 的所有**原始网格**统计：顶点/边/面数、三角/四边/其他面分布、每条边相邻面计数（0松散/1边界/2流形/>2非流形）、按共用边连通的面片区域数，以及真实有向边界环的 512×4 计数。
- 单壳拓扑的欧拉示性数 χ=V−E+F；仅在无非流形/松散边、四条512点有向边界、单个面连通分量等前提下，给出**条件性的**可定向亏格参考。真实面朝向仍需独立验证。
- 报告中的 candidate_for_non_destructive_proxy_experiment 只允许进入**下一阶段减面/分片实验**；无论 true/false，low_poly_proxy_created 与 cutting_patterns_approved 始终是 false。

## 可信运行

~~~bash
blender --disable-autoexec --python-exit-code 1 -b -t 1 \
  --python scripts/probe_stage6_core_shell.py -- \
  --input /tmp/verified-public-stage6.blend \
  --source-sha256 38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a \
  --output /tmp/stage6-core-shell-topology.json
~~~

此命令作为既有 main-only、仅只读 GITHUB_TOKEN 的 Stage6 工作流附加审计，不上传原始顶点坐标或修改 .blend。真实运行通过后，将数值和运行号归档到 experiments/，并同步更新 PRODUCTION_PROGRESS.json。

## 如何进入真正的低密度制版

若拓扑满足：以已有四蹄 512 点世界坐标与 vertex identity 作**不可降级的保护约束**，另设计几组可解释的头身/四腿分片与返口方案，然后比较代理 3D 外形偏差、曲率、缝线长度和三角面翻转/自交；**不是先降到某个面数再找借口接受**。

若拓扑不满足：先定位松散/非流形/独立面组件，明确哪些属于视觉毛发或真正需要修补的主壳；不删除、不覆盖真实 Stage6 主文件。

无论结果如何：始终以设计图与工厂可缝纸样、真实样布、完整装配关系和最终实物 Golden Sample 作为后续制造门禁。
