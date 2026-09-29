# news-thread — 设计系统与硬约束

本文件是 **`news-thread` 节目包的 token 源**。画布基准 1080×1920。排版 `cqw/cqh`，禁 `px`。

---

## 1. 用途与触发场景

节日、纪念日、专题、回顾、年度盘点、纪念伟人、节气、传统节日。视觉气质一句话：

> **国旗红 + 烫金 + 米白 + 仪式感 = 像打开一本纪念册。**

- 主线：每条都是"纪念 / 回望 / 致敬"
- 与 `news-coral` 的差别：coral 讲正在发生的故事，thread 讲历史性的时刻
- 触发词：纪念、回顾、致敬、缅怀、节日、节气、清明、国庆、伟人、专题、百年、周年

不适合：人物故事（`news-coral`）、数据排行（`news-stat`）、突发新闻（`news-onsite`）。

---

## 2. 色板

| token | 值 | 用途 |
|---|---|---|
| `paper` | `#F5EFE3` | 米白主底（60%，仪式感纸面）|
| `paper-dark` | `#E8DFCB` | 二级卡底 |
| `red` | `#C8102E` | 国旗红（标题、装饰横条、关键纪念日数字）|
| `red-dark` | `#9A0C24` | 次级红（细线、装饰）|
| `gold` | `#B8923E` | 烫金（印章 + 烫金线 + 周年数字，**主要装饰元素**）|
| `gold-soft` | `#D4B056` | 烫金浅（次级装饰）|
| `ink` | `#1A1A1A` | 正文 |
| `gray` | `#6B6B6B` | 次级文字 |
| `rule` | `#C9C0AA` | 报纸细线 |

### 2.1 对比度

| 组合 | 比值 | 判定 |
|---|---|---|
| ink / paper | 12.6 | ✓ |
| red / paper | 6.2 | ✓ |
| gold / paper | 4.4 | ✓ 大字号 |
| gold / red | 2.5 | ✗（但两者从不同时作字）|

> **强制规则**：
> - 红色 + 烫金**永远分开**（不在同一元素上同时使用）
> - 烫金 gold 永远只作装饰（章、线、周年数字），不作正文文字
> - 国旗红 red 可以染标题、关键纪念日数字

---

## 3. 字阶

| 位 | 字体 | 字号 | 字重 | 其他 |
|---|---|---|---|---|
| 眉标 | `"JetBrains Mono", monospace` | 2.6cqw | 700 | "纪念 / 专题 / 周年" |
| 主标题 | `"HF Serif CJK", serif` | 9cqw | 700 | line-height 1.18，red |
| 周年数字 | `"HF Serif CJK"` | 14cqw | 900 | red（"100 周年"）|
| 引文 | `"HF Serif CJK", italic` | 6cqw | 700 | line-height 1.5 |
| 屏句 | `"HF Serif CJK"` | 4.4cqw | 400 | 88cqw 盒两行封顶 |
| 正文 | `"HF Serif CJK"` | 3.6cqw | 400 | ink |

- 仪式感 = 衬线 + 烫金 + 米白 + 红
- 拉丁显示族写裸族名。中文族由每个版式自带 `@font-face` + `local()` 六连。

---

## 4. 版面法则

1. **内容只占顶部 80%**：底部 20cqh 留给字幕。
2. **首镜必出现烫金印章或红字纪念标识**：开篇一眼知道"这是纪念日"。
3. **周年 / 历史数字必染 red**：所有 100 周年 / 50 周年 / 历史时刻大字走 red。
4. **每条必带引文**：纪念型不引一句原文不像纪念，至少一段引文必出现。
5. **节奏慢**：`MIN_DRIFT = 0.9`（比 coral / ink 都慢），给观众"停下来默哀"的时间。
6. **被 GSAP 引用的元素必须有 `id`**（继承 news-coral 法则 9）。
7. **带 background 的片块只做 scaleX 擦入**（继承 news-coral 法则 8）。

---

## 5. 动量预算

```
INTRO_END = 2.0     // 仪式型入场偏慢
MIN_DRIFT = 0.9     // 仪式型漂移最慢（默哀 / 致敬感）
driftStart = max(0, min(INTRO_END, slot - MIN_DRIFT))
driftDur   = max(MIN_DRIFT, slot - driftStart)
```

---

## 6. 地面清单与计划版式

| layout | 地面 | 文字色 | red / gold 的出场方式 |
|---|---|---|---|
| `hook`（开篇"今天是 X 周年"）| paper | red / ink | 顶部 red 书挡 + 烫金印章 |
| `segment`（分节回顾）| paper | ink / gray | 烫金细线分隔 + 标题 red |
| `quote`（历史引文）| paper-dark | ink | 烫金破折号 + 衬线引文 |
| `closer`（末镜"永远铭记"）| paper | red / ink | 顶部 red 书挡 + 烫金末印 |

**单地面 pack**：全程 paper；引文卡切 paper-dark；hook / closer 用 red + gold 双书挡。

---

## 7. 计划 composition 文件

```
news-thread/
├── frame.md
├── host.html
└── compositions/
    ├── hook.html   nc-thread-hook     "X 周年"开篇
    ├── segment.html nc-thread-segment  分节回顾
    ├── quote.html  nc-thread-quote    历史引文
    └── closer.html nc-thread-closer   "永远铭记"末镜
```

---

## 8. 与 news-coral 的关键差别

| 维度 | news-coral | news-thread |
|---|---|---|
| 主色 | 珊瑚 #E85D5D | 国旗红 #C8102E + 烫金 #B8923E |
| 字体 | 无衬线巨号 | 全衬线（仪式感）|
| 节奏 | 0.6 漂移 | 0.9 漂移（最慢）|
| 视觉气质 | 火带 + 故事感 | 烫金 + 米白 + 仪式感 |
| 适用稿件 | 故事 / 反转 | 纪念 / 节日 / 专题 |
