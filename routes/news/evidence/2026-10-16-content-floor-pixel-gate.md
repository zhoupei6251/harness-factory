# 内容下沿的像素闸（Task 5 后半）· 顺带量出静态支一笔没记账的空带

**日期** 2026-10-16 · 承接 `2026-10-16-vue-guard-registry.md`（登记表当时剩两个洞）

## 为什么只能按像素量

`layout_selfcheck` 规则 7 读 CSS 的 `bottom:`/`inset:`，成立前提是**偏移相对满幅 `#root`**。
组件不是：`.fd-place{bottom:6cqh}` 在 `.fd-stage{inset:0 0 36cqh 0}` 里，实际 42cqh ⇒
文本口径搬到组件上**假红**。而引擎的 `--caption-zone` 已用活体负例证明**不是侵入探测器**
（`2026-10-16-task5-precheck-findings.md` §2）。所以两边都不许抄，只能量。

## 口径（三条界全部现取，不抄数）

- **墨** = 与**本帧地面色**构成 ≥ 3:1 的像素。3:1 不是新阈值，是本仓库对比度审计与引擎
  `contrast_aa_failure` 用的同一条 AA 大字档线 —— "看得见的字"本就是它的语义。
- **地面色** = 本帧像素按 8 阶量化后的众数（版式是平涂地面 + 少量墨，按面积必赢）。
- **界** = 字幕区上沿 `100 − CAPTION_RESERVE_CQH = 80.0cqh`；填幅下界
  `80.0 − CONTENT_FLOOR_MARGIN_CQH − MAX_BOTTOM_DEAD_CQH = 71.5cqh`（后两个常数取自 `hf_compile`）。
- **只量无图镜**：照片本身就是画面内容，判它等于判"这张图铺满了"。
  "缺 `imagePath` 这一格"（field 的 none 单态）与"有格但值为空串"两种形态都算无图，
  由 `t_content_floor_skips_image_bearing_shots` 一头一条钉住。

工具：`routes/news/scripts/content_floor.py`（`--png` 单帧 / `--video` 逐无图镜中点帧）。

## 先校验尺子，再拿它量

| 帧 | 已知 | 本尺量出 |
|---|---|---|
| `field-frame-after.png` | 上一轮用 >120 亮度粗尺量得 77.3cqh | **77.34cqh** ✓ |
| `field-frame-before-contrast-fix.png` | 同画面，地点行更暗 | 77.40cqh ✓（不受影响，符合预期） |
| `caption-intrusion-negative.png` | 活体负例，地点行故意压进 14cqh | **85.57cqh ✗ 判红** ✓ |

两把独立的尺在同一帧上差 0.04cqh，负例被同一把尺判红 —— 尺子先自证。

## 31 包普查（拿现成的 10-16 上午那轮 `silent.mp4`，零渲染成本）

每包取"最底墨线最高"的那一镜（worst）：

```
54.7cqh  news-policy
58.0cqh  news-alert / news-alert-warning / news-blast / news-blast-score / news-bulletin /
         news-bulletin-strip / news-coral / news-coral-mono / news-dawn / news-dusk /
         news-explainer / news-explainer-blueprint / news-ink / news-ink-graphite /
         news-mosaic / news-noir / news-onsite / news-onsite-urgent / news-paper /
         news-podcast / news-polarity / news-policy-bold / news-stat / news-stat-grid /
         news-takes / news-takes-column / news-thread / news-thread-tribute /
         news-world / news-world-globe
包数 31 · 最差 54.7 · 中位 58.0 · 最好 58.0
达标(≥71.5) 0/31        越字幕区(>80) 0/31
```

⇒ **两件事，分开看**：
1. 字幕区半边 **31/31 干净** —— 把它开成硬闸今天零成本，且能防回归。已开（普查判据 6）。
2. 填幅半边 **0/31 达标**。今天所有 pack 的无图镜下半部空 **21.5–25.3cqh**，
   而 `field`（新组件）是量到 **77.34cqh** 的那一个 —— 唯一过的。
   这不是新退化：法则 17 从来没在 path_b 上量过（`hf_compile` 那条只管 path_c 配方几何）。
   30 包都恰好 58.0 是因为它们同一份 t001 稿、同一副骨架（v008 从 news-coral-night 复制），
   最差镜都是 closer。

⇒ 半边硬、半边报，写死在代码里而不是"以后再说"：
`row["intrude"] == 0` 进 `pass`；`floor_worst` / `thin_fill` 进 `_summary.md` 的列上当账。
把填幅开成硬闸 = 普查永久全红且没人修，那是把闸改成装饰。

## 接线时测试自己抓到的一个 bug

`text_only_windows` 第一版用 `'"imagePath"' in 属性值` 判有没有图 —— 但 `data-variable-values`
里的 JSON 是 **HTML 转义**的（`&quot;`），那个子串**永远不成立** ⇒ 带图镜一条都不会被跳过。
是 `t_content_floor_skips_image_bearing_shots` 的"前提断言"（改不到 imagePath 就抛）先失败
才暴露的。改成 `html.unescape` 后再 `json.loads`。

## 现在谁守 `CAPTION_RESERVE_INTRUDED`

登记表里那行从 `none` 改成 `moved`，站点 `census:intrude` —— 站点串本身就是接线断言
（普查源码里必须出现 `row.get("intrude", 0) == 0`，改了写法当场红）。
Vue 支的守卫洞数从 2 降到 **0**（另一个洞 `NO_TIMELINE_REGISTER` 由 vue-build 的正向断言补上：
删掉注册语句时，旧的"键不写死"那条仍是绿的，只有新那条红 —— 实测）。

`path_b_selftest.py` **245/245**；`reused 11 · moved 6 · 洞 0`。

## 判据 6 上全量（同日，Task 4/5 五连改之后的产线复验）

`HF_NODE22_DIR=… python routes/news/scripts/pack_render_census.py` → **31/31 通过**。
每包新增三列：`intrude = 0`（31 包全 0，硬判据今天零成本）、`floor_worst ≈ 58.02`、
`thin_fill = 4~5`、`floor_shots = 5`；原有的 1309/1309 帧与 0 WARN 一条不少。
⇒ 发射器与闸门这五轮改动（六类消费者假设、暂存清理、正向注册断言、像素闸、登记表）
没让任何一包退化。

## 再跑一轮：`field` 进普查稿件清单（同日）

`t001-scenes.json` 第 3 镜换成 `layout: "field"`（6 镜），于是判据 6 第一次量到新角色。
**31/31 通过**：`clips 6` · `vue 2`（hook + field）· 1468/1468 帧 · 0 WARN · `intrude` 全 0 ·
`floor_worst` 54.74–58.02 · `thin_fill` 4~5。
`thin_fill` 从 5 降到 4 的那 21 包，少的正是 `field` 那一镜 —— 它是这条片子里唯一过法则 17 的版式，
而且这次是**被普查量出来的**，不是我拿探针帧说的。

顺带修两处假话：汇总行里手抄的「（5 镜）」改成现算（镜数 / 点名版式数 / Vue-only 镜数 / 稿件路径，
D20 同一个病）；`vue` 列原来数 `data-vue-mount`，而 loader 脚本里的 `[data-vue-mount]` 选择器
也被数进去 —— **2 个 Vue clip 报成 3**。改成数 `data-vue-bundle`。

## 留给下一步的两件事

1. **`field` 进普查稿件清单**（Task 6）：现在这条闸量的是 t001 那条片子里的镜，
   `field` 不在里面 —— 它今天只被探针帧量过。不进去，新角色就还是"闸扫不到"。
2. **填幅这笔账要不要平**（未拍）：21.5–25.3cqh 的下半部空带是 227 份模板共有的设计事实，
   不是某包的偏差。要么按法则 17 把无图态的版式往下推（动骨架，31 包 × 7 版式），
   要么承认"无图态就该上半部构图 + 下半部留给字幕"并把法则 17 的口径改成按有图态判。
   两条都比开闸便宜地伤人，所以先落账不先动手。

## 追加（同日，写完 D25 之后）：第 2 件的前提被我读错了

准备按上面那句"把版式往下推"去移植 `closer` 时，读了源文件的几何注释 ——
**空带是设计者算过并按法则 1 主动留的**，不是漏改：

```
closer.html:  内容高度 = 23.2cqh; 区高 58cqh 居中 → 上下各余 17.4cqh,
              漂移 yPercent -3 只吃掉 1.7cqh → 距字幕禁入区始终有一整块余量
story.html:   居中后上下各余 12.2cqh … 距底部 20cqh 字幕禁入区始终有一整块余量(法则 1)
```

⇒ 真问题是**法则 1（别怼字幕区）与法则 17（要填满）在短文本版式上互相拉扯**。
path_b 当年按法则 1 选了居中；法则 17 是后来只为 path_c 配方写的，从没说它管单行 CTA 的收口镜。
`field` 77.40cqh 也不是"修好了空带"，而是**另一种结构自带更高填充**（巨号事实 + 下沿锚定文案块）。

本文件的 31 包数字**全部仍然有效**（量的是像素，不是判断）；作废的只是"0/31 ⇒ 31 份缺陷"这句解读。
裁决记在 `ARCHITECTURE.md` D25 / D25.1，三选一待拍：
(a) 法则 17 只管有图/多行版式，单行书挡镜豁免并写进 frame.md；
(b) 两者共存 ⇒ 内容必须**放大到填满**（改字号；移位只把空洞从下挪到上）；
(c) 承认居中是终态，填幅半边连"报"都撤。

## 探针实测：选项 (b)"放大填满"对 closer 不成立（同日，已回退）

只改 `news-coral/compositions/closer.html` 一个文件：CTA `10.5cqw → 13.5cqw`（+29%）、
`gap 3.2cqh → 6cqh`（+87%）、来源行 `3cqw → 4cqw`。重渲同一条普查片：

| | 下沿 | 判定 |
|---|---|---|
| 原样 | 58.02cqh | ✗ 空 21.5 |
| 探针 | **66.77cqh** | ✗ 仍空 12.7 |

⇒ 字号 +29% 只买到 **+8.75cqh**，离 71.5 还差 4.7；再往上第一件撞上的事是
**8 个字的 CTA 在 88cqw 里换行**（探针帧里"今天查一下 / 社保"已经是两行 + 反相块自成一行），
继续放大就会挤成三行顶到色带底下。也就是说 **法则 17 的 8cqh 线与"三元素书挡镜"在 9:16 上
几何不相容** —— 不是我们没做好，是这条线对这类版式不该按同一个数判。
探针帧存 `2026-10-16-task6-render/closer-probe-66.77cqh.png`（**模板已回退**，
回退后重渲 `floor_worst` 回到 58.02、`thin_fill` 回到 5，产物与基线一致）。

⇒ 对 (a)/(b)/(c) 的影响：**(b) 对 closer 这一类可以划掉了**；`story`/`rail`/`stat` 是多行版式，
(b) 对它们仍可能成立，但那是另一件有内容可撑的事，不是同一道题。

## 按角色拆开：我那句"0/31 达标"是**每包最坏那一镜**的口径，不是各版式都不行

拿现成的 31 条 `silent.mp4` 重量（不重渲），角色取自 `data-composition-src="compositions/<role>.html"`
与 `data-vue-bundle="<role>-<variant>"` —— 不解析 `composition_id`（两套命名法混着用，
`nc-night-hook__1` 与 `field-news-coral__3` 的角色一个在尾一个在头，按串切必错）。

| 角色 | n | 中位 | 最差 | 最好 | 达标(≥71.5) |
|---|---|---|---|---|---|
| rail | 31 | **80.0** | 66.3 | 80.0 | **21/31** |
| field | 31 | 77.4 | 77.4 | 77.4 | **31/31** |
| stat | 31 | 68.7 | 68.7 | 68.7 | 0/31（差 2.8） |
| hook(Vue) | 31 | 62.9 | 57.9 | 62.9 | 0/31 |
| story | 31 | 58.7 | 58.7 | 58.7 | 0/31 |
| closer | 31 | 58.0 | 54.7 | 58.0 | 0/31 |

三处要改口的地方：

1. **`rail` 是这套里填充最好的版式**（21/31 包下沿正好落在 80.0cqh），不是我此前引的 66.3 失败者 ——
   那个数来自 news-coral 单包，被当成了全体。
2. 问题范围从"227 份模板"缩到 **三个角色：`story` / `closer` / `hook`**（`stat` 只差 2.8cqh，
   属于另一档）。豁免线该不该画、画在哪，现在是可算的而不是感觉。
3. **`rail` 卡在 80.0 这条线上是脆的**：`intrude_only` 用的是严格 `> 80.0`，
   它今天算过；再长 1px 就变成"侵入字幕区"而普查会当场红。
   这不是 bug（贴线本来就该警告），但说明**字幕区硬闸与填幅软线之间没有余量带** ——
   要么给 rail 留 1–2cqh 缓冲，要么接受它随时翻成硬失败。
