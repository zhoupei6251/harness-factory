# news-policy — 设计系统与硬约束

本文件是 **`news-policy` 节目包的 token 源**。画布基准 1080×1920。排版 `cqw/cqh`，禁 `px`。

---

## 1. 用途与触发场景

政策法规、官方文件、新规解读、税务社保、补贴申领、官方通知。视觉气质一句话：

> **公文蓝 + 米白 + 烫金印章 = 像政府文件但能刷完。**

- 主线：每条都是"什么 + 谁 + 何时 + 怎么办"
- 与 `news-coral` 的差别：coral 讲人，policy 讲条文
- 触发词：新规、政策、办法、通知、规定、施行、实施、修订、印发、调整、发布

不适合：人物故事（`news-coral`）、数据排行（`news-stat`）、突发新闻（`news-onsite`）。

---

## 2. 色板

| token | 值 | 用途 |
|---|---|---|
| `paper` | `#F5EFE3` | 米白主底（70%，像公文纸）|
| `paper-dark` | `#E8DFCB` | 米白卡衬（条目卡底）|
| `cobalt` | `#1F3A68` | 公文蓝（主标题、序号、关键强调）|
| `cobalt-dark` | `#142B4F` | 公文蓝深（细线、装饰形）|
| `ink` | `#1A1A1A` | 正文（黑色，比米白更深一点）|
| `gray` | `#6B6B6B` | 次级文字（眉标、来源）|
| `rule` | `#C9C0AA` | 报纸细线 |
| `gold` | `#B8923E` | 烫金（印章形 + 关键日期，**只作形状**）|
| `crimson` | `#C0392B` | 极少数用法（生效日期 / 强制字，**只作形状**）|

### 2.1 对比度

| 组合 | 比值 | 判定 |
|---|---|---|
| ink / paper | 12.6 | ✓ |
| cobalt / paper | 9.5 | ✓ |
| gray / paper | 4.7 | ✓ 大字号 |
| cobalt / paper-dark | 8.0 | ✓ |

> **强制规则**：gold 和 crimson 永远只作形状（印章、日期戳、横线），不作文字。
> 公文蓝 cobalt 可以染标题、序号、关键强调字。

---

## 3. 字阶

| 位 | 字体 | 字号 | 字重 | 其他 |
|---|---|---|---|---|
| 眉标 | `"JetBrains Mono", monospace` | 2.6cqw | 700 | "新规 / 政策 / 官方" 字样 |
| 公文标题 | `"HF Serif CJK", serif` | 8cqw | 700 | cobalt，line-height 1.18 |
| 施行日期 | `"HF Serif CJK"` | 12cqw | 900 | cobalt，年/月/日走 gold 印章底 |
| 条目 | `"HF Serif CJK"` | 4.4cqw | 700 | 序号 cobalt |
| 条文说明 | `"HF CJK", sans-serif` | 3.4cqw | 400 | ink |
| 时间线节点 | `"JetBrains Mono"` | 3.6cqw | 800 | cobalt |
| 屏句 | `"HF Serif CJK"` | 4.4cqw | 400 | 88cqw 盒两行封顶 |

- 公文型必须有衬线（公文 = 庄重）；正文说明可以无衬线（小字 = 可读）
- 拉丁显示族写裸族名。中文族由每个版式自带 `@font-face` + `local()` 六连。

---

## 4. 版面法则

1. **内容只占顶部 80%**：底部 20cqh 留给字幕。
2. **首镜必出现公文标题 + 施行日期**：发布机关 + 施行日期 + "新规"红/金印章 = 一眼认出"这是政策"。
3. **每条政策用 bullet 落点**：政策清单（编号 + 一句话 + 适用对象），每条 ≤8 秒。
4. **禁止"故事化叙事"**：不上引文、不上屏句的诗化表述（政策类只看事实）。
5. **时间线节点必成对**：所有 timeline 节点必须带日期 + 事件描述，缺一即拒收。
6. **被 GSAP 引用的元素必须有 `id`**（继承 news-coral 法则 9）。
7. **带 background 的片块只做 scaleX 擦入**（继承 news-coral 法则 8）。

---

## 5. 动量预算

```
INTRO_END = 1.5     // 公文型入场偏慢（庄重）
MIN_DRIFT = 0.7     // 公文型漂移中等（不能太快——失庄重；不能太慢——失节奏）
driftStart = max(0, min(INTRO_END, slot - MIN_DRIFT))
driftDur   = max(MIN_DRIFT, slot - driftStart)
```

---

## 6. 地面清单与计划版式

| layout | 地面 | 文字色 | cobalt / gold 的出场方式 |
|---|---|---|---|
| `hook`（公文发布）| paper | ink / cobalt | 顶部 cobalt 横线（书挡）+ gold 印章 |
| `summary`（核心摘要）| paper | ink | 序号 cobalt + 条目 ink |
| `points`（关键变化）| paper-dark | ink | 编号 cobalt 方块 + 变化说明 ink |
| `timeline`（施行节点）| paper | ink | 时间线 cobalt 主轴 + 节点圆点 |
| `closer`（末镜）| paper | ink / cobalt | 顶部 cobalt 书挡 + gold 末印 |

**单地面 pack**：90% 时间在 paper 上；条目卡切 paper-dark 做二级层；hook / closer 用 cobalt + gold 双书挡。

---

## 7. 计划 composition 文件

```
news-policy/
├── frame.md
├── host.html
└── compositions/
    ├── hook.html      nc-policy-hook     公文发布 + gold 印章
    ├── summary.html   nc-policy-summary  核心摘要
    ├── points.html    nc-policy-points   关键变化 bullet
    ├── timeline.html  nc-policy-timeline 施行节点时间线
    └── closer.html    nc-policy-closer   末镜 + gold 末印
```

---

## 8. 与 news-coral 的关键差别

| 维度 | news-coral | news-policy |
|---|---|---|
| 主色 | 珊瑚红 #E85D5D | 公文蓝 #1F3A68 |
| 字体 | 无衬线巨号 | 衬线公文 |
| 节奏 | 0.6 漂移 | 0.7 漂移（稍慢）|
| 视觉气质 | 火带 + 故事感 | 公文蓝 + 烫金印章 |
| 适用稿件 | 故事 / 反转 | 政策 / 法规 / 通知 |
