# news-bulletin — 设计系统与硬约束

本文件是 **`news-bulletin` 节目包的 token 源**。画布基准 1080×1920。排版 `cqw/cqh`，禁 `px`。

---

## 1. 用途与触发场景

新闻速报、今日要闻合辑、多事件播报、整点新闻。视觉气质一句话：

> **黑底白字 + 等宽编号 + 极简直条 = 像电视台整点新闻字幕条。**

- 主线：每条 ≤8 秒，多条事件并列，节奏像电报
- 与 `news-coral` 的差别：coral 一条故事 60s，bulletin 五条新闻 60s
- 触发词：今日要闻、整点新闻、新闻速报、合辑、盘点、汇总、24 小时、热点

不适合：单条人物故事（`news-coral`）、深度报道（`news-ink`）、政策原文（`news-policy`）。

---

## 2. 色板

| token | 值 | 用途 |
|---|---|---|
| `black` | `#0E0E0E` | 主底 |
| `black-soft` | `#1A1A1A` | 卡片底（每条新闻之间用这个衬底）|
| `white` | `#F5F0E8` | 主文字 / 标题（米白）|
| `gray` | `#9A9A9A` | 次级文字（来源、时间戳）|
| `rule` | `#3A3A3A` | 极细分割线（条目之间）|
| `accent` | `#F2C94C` | 序号片底色（**只作形状**）|

### 2.1 对比度

| 组合 | 比值 | 判定 |
|---|---|---|
| white / black | 16.8 | ✓ |
| gray / black | 10.4 | ✓ |
| accent / black | 11.5 | ✓（但只作序号方块底）|

> **强制规则**：accent 永远只作序号方块底，不作文字。

---

## 3. 字阶

| 位 | 字体 | 字号 | 字重 | 其他 |
|---|---|---|---|---|
| 编号 index | `"JetBrains Mono", monospace` | 5cqw | 800 | accent 方块底 + 黑字（数字反白）|
| 标题 | `"HF CJK", sans-serif` | 4.6cqw | 800 | line-height 1.3 |
| 摘要 | `"HF CJK"` | 3.4cqw | 400 | gray，单行省略 |
| 时间戳 | `"JetBrains Mono", monospace` | 2.6cqw | 400 | gray |
| 屏句 | `"HF CJK"` | 4.4cqw | 400 | 88cqw 盒两行封顶 |
| 来源 | `"HF CJK"` | 2.8cqw | 400 | gray，"央视 / 澎湃" |

- 全用无衬线 + 等宽（无衬线 = 速读；等宽 = 编号感）。
- 拉丁显示族写裸族名。中文族由每个版式自带 `@font-face` + `local()` 六连。

---

## 4. 版面法则

1. **内容只占顶部 80%**：底部 20cqh 留给字幕。
2. **每条新闻 ≤8 秒**：超过 8 秒强制切条（保证速报节奏）。
3. **5-7 条并列**：少于 4 条不像合辑，多于 8 条观众记不住。落选即降级到 `news-coral` 单条。
4. **每条新闻必须含三件套**：编号 + 一句话标题 + 来源；任一缺失即拒收。
5. **极简动画**：每条之间用 fade（不是 scaleX），强切感 = 切换感。
6. **不要装饰带 / 火带**：bulletin 不要装饰，每条都是平等的条目。
7. **被 GSAP 引用的元素必须有 `id`**（继承 news-coral 法则 9）。

---

## 5. 动量预算

```
INTRO_END = 0.6     // 速报型入场快
MIN_DRIFT = 0.2     // 几乎不漂移（条目短，不给人"停下来读"的时间）
driftStart = max(0, min(INTRO_END, slot - MIN_DRIFT))
driftDur   = max(MIN_DRIFT, slot - driftStart)
```

---

## 6. 地面清单与计划版式

| layout | 地面 | 文字色 | accent 的出场方式 |
|---|---|---|---|
| `hook`（开篇 "今日 N 件"）| black | white / gray | 无（开篇不强调）|
| `list`（每条新闻）| black-soft | white / gray | 序号方块底 |
| `closer`（收尾"明天见"）| black | white / gray | 无 |

**单地面 pack**：黑底全程；条目之间靠 black-soft 衬底区分（不是分隔线）。

---

## 7. 计划 composition 文件

```
news-bulletin/
├── frame.md
├── host.html
└── compositions/
    ├── hook.html   nc-bulletin-hook   "今日 N 件"开篇
    ├── list.html   nc-bulletin-list   单条新闻条目（编号 + 标题 + 来源）
    └── closer.html nc-bulletin-closer "明天见"收尾
```

---

## 8. 与 news-coral 的关键差别

| 维度 | news-coral | news-bulletin |
|---|---|---|
| 主色 | 珊瑚 #E85D5D | 单一白字（无强色）|
| 字体 | 无衬线巨号 | 无衬线 + JetBrains Mono 等宽 |
| 节奏 | 0.6 漂移（一条 60s）| 0.2 漂移（多条 ≤8s/条）|
| 视觉气质 | 火带 + 单故事 | 编号条目 + 极简直条 |
| 适用稿件 | 单故事 / 反转 | 多事件速报 / 整点新闻 |
