# field 结构原型 · 与"示意图到底能不能用"的实测（2026-10-16）

> 触发：用户裁决「不同题材用合适的结构」→ 选定先做 `field`（画面主导镜）；
> 又选定「none 优先，图是增强」。本探针回答两个问题，**都是要拿真帧和真命中率回答的，不是讨论出来的**。
> 相关：`docs/plans/2026-10-15-news-vue-phase2-redesign-spec.md` §7
> 本目录留了可复看的东西：`none-frame.png` / `schematic-frame.png` 两帧，
> 与两份原型源 `field-none.html` / `field-schematic.html`（放进任意 HyperFrames 项目目录
> `npx hyperframes render -o out.mp4 -f 25 --quality=draft --no-browser-gpu` 即可重渲，Node ≥22）。

---

## 1. 问题一：`field` 没有影像时，画面还成立吗？

**成立。** 设计主张是「无图不留空洞，让**事实本身**当画面主体」：

- 顶部画面区用本镜最关键的事实做 ghosted 巨号（`1000万`，`rgba(245,240,232,0.12)`），
  与 story 的序号水印同一套语言 ⇒ 复用 §3-A 的「装饰层不吃通用文字阴影」规则，不新造机制；
- 斜纹地面 + 顶部径向光撑住 0–62cqh，不靠图；
- 底部文字带坐在 20cqh 字幕禁入区上方：珊瑚尺 `scaleX` 擦入 + 8.4cqw 领句 + 4.1cqw 屏句；
- 阴影只给 `.fd-head/.fd-sub/.fd-kicker` 三处文字，装饰层与地面不吃。

**两处待改（目视这张帧看出来的，不是想出来的）**：

1. 眉标写的是「现场无影像」——**道歉式文案**。观众本来不知道"该有图"，这一句反而把缺口指给他看。
   换成事件词/栏目词；地点信息已有独立一行（`浙江宁波 · 鄞州`）。
2. 36cqh–62cqh 之间有一条空带（ghost 数字在 12–36cqh，文字带在 62cqh 起）。
   ghost 下移或放大即可，不需要新元素。

## 2. 问题二：示意图能用吗？——**这张原型图说服得太像了**

`schematic` 态原型：图占顶部 62cqh、常驻「示意画面 · 非事件现场」标、CC BY 3.0 署名上屏、
降饱和 `saturate(.72)`、**不做 Ken Burns**（推镜会把示意图读成纪实）。合规要素一个不缺。

**但那张图是拉脱维亚 2008 年的一栋空置木楼，窗是砸破的。**
配的新闻是「宁波高端小区、室内精装被拆成毛坯、**楼外观完好**」。
标在、字够大、位置正 —— 而看着自己渲出来的这一帧，第一反应仍是"房子被砸成这样了"。

⇒ **画面在断言一件没发生的事，角标只是文字，对冲不了。**
这条是本探针最有价值的产出：它否证了我自己在 spec §7.1 写的「强制标注 + 降饱和就够了」。

## 3. 问题三：加一道类别闸能救吗？——量完是 **0/9**

按 §7.3 的三个维度（场景类 / 地域 / 状态）跑 10 条真实题材查询，先看三闸原命中率：

| 查询 | 三闸命中 | 类别闸判定 |
|---|---|---|
| flood rescue emergency | ✅ 2013 Colorado floods | ✗ 地域+场景+状态 |
| earthquake damaged building | ✅ Fukui Earthquake **1948** | ✗ 地域+状态 |
| press conference podium | ✅ President **Reagan** | ✗ 地域 |
| factory assembly line workers | ✅ **An armored car** near the assembly… | ⚠️ 漏判（词表把 armored car 当 device） |
| hospital ward bed | ✅ Women's Ward, **Mengo**（乌干达） | ✗ 地域 |
| police tape crime scene | ✅ **NYPD** Crime Scene Tape | ✗ 地域+场景+状态 |
| school classroom children | ✅ School children in **Tel Aviv** | ✗ 地域 |
| wind turbine field renewable | ✅ Wind turbine field - **US-54 - Kansas** | ⚠️ 漏判（境外地名表不全） |
| vacant apartment building | ✅ Vacant apartment building in **Leveri**（拉脱维亚） | ✗ 地域 |
| abandoned bare room interior | ❌ 三闸已拦 | — |

**9/10 → 2/9**，而那 2 条是我词表太糙漏过去的 ⇒ 按应有的主体比对，**真实存活率 0/9**。

结论：**问题不在闸，在库存** —— Commons 几乎没有中国新闻事件的可用影像。
给一个 0/9 的供给建三道闸门是本末倒置。

## 4. 对排序的影响（已回写 spec）

1. `field` 先按 **`none` 单态**落地（本探针已证成立），`real`/`schematic` 态**不在本轮做**；
2. **图供给**升为新闻域独立前置缺口（spec §7.5），三条路各有明确代价：
   报道正文授权图（采集链现在不做正文抓取 + 版权追溯）／AI 生图（撞零云费口径，且**生成画面配新闻=造事实**）／接受无图；
3. §7.3 的类别闸保留为**将来有图时的硬约束**，本轮不建；
4. `rank` / `versus` **不依赖图**，是「不同题材用合适结构」这条裁决里当下就能兑现的部分 → 建议下一个做 `rank`。

## 5. 未证与边界

- 类别闸的三维比对是**这次临时写的粗词表**（境外地名 20 个、场景词 6 类），不是实现；
  它足够回答"能不能用"，不足以当生产判据。真做时要按 `relevance_ok` 的规矩配反向负例。
- 两帧原型是**手工 HTML**，没接发射器：`field` 作为新角色，`layouts` 只从 `compositions/*.html` 扫
  （`path_b_build.py:1930`），槽位与 `composition_id` 也来自静态文件 ⇒ 接线需要先支持
  「Vue-only 版式」，这是 spec §5 里 P2-1 之外的一笔独立架构改动，本探针刻意没碰。
- 图占比、动量、对比度这三项**没机检**（原型阶段目视即可），进产线前必须补。
