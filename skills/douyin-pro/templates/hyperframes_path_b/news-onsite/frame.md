# news-onsite — 设计系统与硬约束

本文件是 **`news-onsite` 节目包的 token 源**。画布基准 1080×1920。排版 `cqw/cqh`，禁 `px`。

---

## 1. 用途与触发场景

突发新闻、现场直击、灾难、紧急事故、抢险、突发事件、突发政策。视觉气质一句话：

> **黑底 + 黄色 PRESS + 实时时间码 = 让你以为这是现场直播。**

- 主线：每条都有"时间 + 地点 + 发生什么"
- 与 `news-coral` 的差别：coral 是"事后讲完的故事"，onsite 是"正在发生的现场"
- 触发词：突发、现场、直击、抢险、救援、灾害、洪水、塌方、事故、紧急、直播、记者、刚刚、目前

不适合：人物故事（`news-coral`）、数据新闻（`news-stat`）、政策原文（`news-policy`）。

---

## 2. 色板

| token | 值 | 用途 |
|---|---|---|
| `black` | `#0E0E0E` | 主底（现场感） |
| `black-soft` | `#1A1A1A` | 卡片底（时间码条、引文卡）|
| `white` | `#F5F0E8` | 主文字（暖白）|
| `gray` | `#9A9A9A` | 次级文字（说明行）|
| `press` | `#F2C94C` | PRESS 黄（**只作形状 + 警示大字号**）|
| `alert` | `#D7263D` | 极少数用法（伤亡数字、紧急标记，**只作形状**）|
| `time-on` | `#3FA34D` | 录制指示点（右上"REC"绿点，**只作形状**）|

### 2.1 对比度

下表由 `python skills/douyin-pro/scripts/audit_pack_contrast.py news-onsite` 按 §2 色板原值复算，改色板必须重跑它。
判读线：正文 4.5 / 大字 3.0（画布 1080 宽下 1cqw=10.8px，≥24px ≈ ≥2.22cqw 算大字）。

| 组合 | 比值 | 判定 |
|---|---|---|
| white / black | 17.02 | ✓ 任意字号 |
| press / black | 12.17 | ✓ 任意字号（但按法则 press 不作正文）|
| time-on / black | 6.03 | ✓ 任意字号（但按法则 time-on 只作 REC 点形状）|

> **强制规则**：
> - press 永远不作正文文字，只作"PRESS / 现场 / 直击"标识和时间戳
> - alert 仅用于伤亡数字（如果稿件有的话）+ 紧急符号
> - 顶栏永远有"REC 红/绿点 + 时间码"——这是 onsite 的标识

---

## 3. 字阶

| 位 | 字体 | 字号 | 字重 | 其他 |
|---|---|---|---|---|
| PRESS 标识 | `"JetBrains Mono", monospace` | 3cqw | 900 | letter-spacing .3em，press 色，顶部横条 |
| 时间码 | `"JetBrains Mono", monospace` | 3.6cqw | 800 | 顶部右上 "2024-10-15 14:23" |
| 主标题 | `"HF CJK", sans-serif` | 8.5cqw | 900 | line-height 1.18，white |
| 屏句 | `"HF CJK"` | 4.4cqw | 400 | 88cqw 盒两行封顶 |
| 现场引语 | `"HF CJK"` | 5cqw | 700 | black-soft 卡上 white 字 |
| 地点 | `"JetBrains Mono", monospace` | 3cqw | 700 | gray + 区位符号（如 "📍" 简化为 #2c0f1d 附近）|

- 现场型不上衬线（衬线 = 慢，现场 = 即时）。
- 拉丁显示族写裸族名。中文族由每个版式自带 `@font-face` + `local()` 六连。

---

## 4. 版面法则

1. **内容只占顶部 80%**：底部 20cqh 留给字幕。
2. **首镜必出现 PRESS 标识 + 时间码**：PRESS 黄横条 + 右上时间码 = 一眼认出"这是现场"。
3. **每镜必带地点 + 时间戳**：地理颗粒（省 / 市 / 区）+ 时刻。
4. **屏句短促**：现场屏句 ≤16 字（长句会被切条成两条，节奏乱）。
5. **禁止做"故事化"叙事**：现场只陈述事实（什么时间、什么地点、发生什么、目前状态），不上情感、不上反转。
6. **入场动画硬切**：0.3s fade in，不用 scaleX 擦入（擦入 = 慢，现场 = 快）。
7. **被 GSAP 引用的元素必须有 `id`**（继承 news-coral 法则 9）。

---

## 5. 动量预算

```
INTRO_END = 0.4     // 现场型入场极快
MIN_DRIFT = 0.2     // 现场型几乎不漂移（要"暂停"的现场感）
driftStart = max(0, min(INTRO_END, slot - MIN_DRIFT))
driftDur   = max(MIN_DRIFT, slot - driftStart)
```

> 入场曲线：`power4.out` 或 `none`，**禁用 `power3.out` 慢曲线**（现场要快）。

---

## 6. 地面清单与计划版式

| layout | 地面 | 文字色 | press / time-on 的出场方式 |
|---|---|---|---|
| `hook`（开篇 "突发 / 现场"）| black | white | PRESS 横条 + REC 绿点 + 时间码 |
| `clock`（"截至 X 时"）| black | white | 大时间码（中央）+ 现场引语卡 |
| `sit`（现场描述）| black-soft | white | 地点 + 时间戳 + 屏句 |
| `quote`（现场引语）| black-soft | white | 引文卡底 |
| `closer`（末镜 "持续追踪"）| black | white | REC 持续红/绿点 + 时间戳 |

**单地面 pack**：90% black；引文 / 时间戳卡切 black-soft 做二级层。

---

## 7. 计划 composition 文件

```
news-onsite/
├── frame.md
├── host.html
└── compositions/
    ├── hook.html   nc-onsite-hook   PRESS 横条 + REC + 时间码
    ├── clock.html  nc-onsite-clock  截至 X 时
    ├── sit.html    nc-onsite-sit    现场描述（地点 + 时间）
    ├── quote.html  nc-onsite-quote  现场引语卡
    └── closer.html nc-onsite-closer REC 持续点
```

---

## 8. 与 news-coral 的关键差别

| 维度 | news-coral | news-onsite |
|---|---|---|
| 主色 | 珊瑚 #E85D5D | PRESS 黄 #F2C94C |
| 字体 | 衬线 + 无衬线 | 全无衬线 + JetBrains Mono |
| 节奏 | 0.6 漂移 | 0.2 漂移（极静止）|
| 视觉气质 | 火带 + 故事感 | PRESS + 时间码 + 现场直播 |
| 适用稿件 | 故事 / 反转 | 突发 / 现场 / 抢险 |
