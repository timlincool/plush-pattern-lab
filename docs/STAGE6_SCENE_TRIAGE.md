# Stage 6 全角色对象／部件盘点（P2 的首个真实动作）

此项直接服务 [工厂生产总路线图 P2](FACTORY_ROADMAP.md)，从**整只云朵羊驼模型**获取可用于规划完整角色纸样的工程清单，而不是只研究四蹄附近的局部三角带。

## 输入与执行约束

- 来源：[同仓库 Stage6 公开 Release](https://github.com/timlincool/plush-pattern-lab/releases/tag/cloud-alpaca-stage6-visuals-20261028)，SHA-256 固定为 38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a。
- 只在可信 main 工作流执行：核验源文件哈希、Blender 4.3.2，运行参数必须有 --disable-autoexec。继续使用主体和四蹄的严格几何配对门禁。
- 对全部 bpy.data.objects 统计类型分布；每个 Mesh 记录顶点/边/面/材质槽数量和世界坐标毫米包围盒尺寸，按面数列出前24个较大的网格及其信息。
- 按 Mesh 名称给出候选部件标签：主壳/头、四腿/蹄、云团、耳朵、尾巴、水滴、脸部细节、视觉毛发。**标签可交叉，仅是名称推断，不是已经确认的可缝生产部件**。
- 仅上传轻量 JSON 审计结果，不上传源模型、原始三维顶点数组、私有路径或可执行脚本；所有对象的生产归属初始仍为 UNCLASSIFIED_NOT_A_SEWABLE_PATTERN。

## 受信任环境运行

~~~bash
blender --disable-autoexec --python-exit-code 1 -b -t 1 \
  --python scripts/probe_stage6_scene_inventory.py -- \
  --input /tmp/verified-public-stage6.blend \
  --source-sha256 38a0be58ed4cb6b3af66fc392f4820d544851715002ee8520543d7e9fba85f3a \
  --output /tmp/stage6-whole-scene-inventory.json
~~~

工作流为 .github/workflows/stage6-hoof-seam-reference.yml。没有实际 main 运行证据时，不得声称 Blender 审计完成。

## 怎样把盘点结果转成真实制造结构

1. 对照原设计图与历史选定 D 外观，人工核对每个可见部件；区分可缝主壳、独立布件、覆盖云绒、绣花、毛发代理和未解决的连接。
2. 冻结正／侧／背／顶视图及关键成品尺寸。当前三维坐标是视觉原型，不等于正式成品生产公差。
3. 先实现真实的头身＋腿蹄主壳**完整可缝分片**、缝线配对及返口/填棉结构，再补耳根、灰云、额云、尾巴及十枚雨滴承接。
4. 每次几何分片通过独立翻面/相交/缝线校验，再向完整 1:1 SVG/PDF/DXF 纸样、样布试验和工厂技术包推进。

**阶段限制**：此次仅是 P2 的场景事实收集；不能据此把 P3（可缝分片）、P4（完整纸样）或 P5～P7（工厂打样、实体签核）标成已完成。
