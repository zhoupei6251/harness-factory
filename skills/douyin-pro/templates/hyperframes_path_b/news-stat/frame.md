# news-stat — 设计系统与硬约束

本文件是 **`news-stat` 节目包的 token 源**。色板/字阶/法则/动量预算以本文为准。
画布基准 1080×1920（竖屏 9:16）。1cqw = 10.8px，1cqh = 19.2px。排版用 `cqw/cqh`，禁 `px`。

---

## 1. 用途与触发场景

数据新闻、排行榜、数字冲击、成绩单、榜单、年报节选。视觉气质一句话：

> **米白纸面 + 巨号黑字 + 朱红高亮 = 让数字自己说话。**

- 主线：数字就是主角，每一镜至少一个数
- 与 `news-coral` 的差别：coral 的巨号用 League Gothic 无衬线"响"，stat 用衬线"重"
- 触发词：排行、TOP10、年报、数据、第一、最、增长、对比、%、同比

不适合：人物故事（用 `news-coral`）、深度揭露（用 `news-ink`）、政策原文（用 `news-policy`）。

---

## 2. 色板

| token | 值 | 用途 |
|---|---|---|
| `paper` | `#F5EFE3` | 米白主底（70%，所有数字卡都在纸上）|
| `paper-dark` | `#E8DFCB` | 米白卡衬（drilldown 二级层）|
| `ink` | `#1A1A1A` | 主数字、标题、正文 |
| `ink-soft` | `#3A3A3A` | 次级数字、说明文字 |
| `gray` | `#6B6B6B` | 米白底次级文字（眉标、标签）|
| `rule` | `#C9C0AA` | 米白报纸细线 |
| `crimson` | `#C0392B` | 数字高亮（"42万"的 42）、分隔色块 |
| `crimson-dark` | `#922B21` | 次级分隔形状（**只作形状**）|
| `gold` | `#B8923E` | 第一名 / 冠军 / TOP1 标记（**只作形状**）|

### 2.1 对比度（米白底常见组合）

下表由 `python skills/douyin-pro/scripts/audit_pack_contrast.py news-stat` 按 §2 色板原值复算，改色板必须重跑它。
判读线：正文 4.5 / 大字 3.0（画布 1080 宽下 1cqw=10.8px，≥24px ≈ ≥2.22cqw 算大字）。

| 组合 | 比值 | 判定 |
|---|---|---|
| ink / paper | 15.20 | ✓ 任意字号（主数字的色）|
| gray / paper | 4.65 | ✓ 任意字号（刚过正文线，配角仍只给次级文字）|
| crimson / paper | 4.75 | ✓ 数学过正文线，但按法则 crimson 只作形状 |
| ink / paper-dark | 13.13 | ✓ 任意字号 |

> **强制规则**：crimson 和 gold 永远是**形状**（色块、细线、序号底），不作文字。
> 主数字一律 ink（黑），crimson 只出现在"全场最关键的一个数字"上。

---

## 3. 字阶

| 位 | 字体 | 字号 | 字重 | 其他 |
|---|---|---|---|---|
| 眉标 eyebrow | `"JetBrains Mono", monospace` | 2.6cqw | 700 | letter-spacing .18em，paper 上 ink 字 |
| 主标题 display | `"HF Serif CJK", serif` | 8cqw | 700 | line-height 1.18 |
| 巨号数字 | `"HF Serif CJK"` | 28cqw | 700 | line-height 1.1（与 news-coral 校准值不同，衬线巨号行距略宽）|
| 次级数字 | `"HF Serif CJK"` | 9cqw | 700 | |
| 单位（万/亿/%）| `"HF Serif CJK"` | 8cqw | 400 | 紧贴数字右下 |
| 小标题 | `"HF CJK", sans-serif` | 5.2cqw | 700 | 比较项 / 副标用无衬线 |
| 正文 | `"HF Serif CJK"` | 3.4cqw | 400 | gray |
| 屏句 | `"HF CJK"` | 4.4cqw | 400 | 88cqw 盒两行封顶 |

- 拉丁显示族写裸族名。中文族由每个版式自带 `@font-face` + `local()` 六连。

---

## 4. 版面法则

1. **内容只占顶部 80%**：底部 20cqh 留给字幕，所有 `inset` 下边界一律 20cqh。
2. **每镜必须有数字**：无数字即 stat 落选（`MIN_STAT_FACTS = 2`，少于此拒收，事实不足就换包）。
3. **巨号走衬线 + 28cqw**：数字 1.1 行距（校准值），更小会和单位基线重叠。
4. **只有一个数字染 crimson**：当镜出现"最关键的一个数字"时使用，**其它数字一律 ink**——避免全场红字看花眼。
5. **comparing 必成对**：所有 `compareValue` 必须有 `compareLabel`，否则视为编造事实（参照 news-coral `MIN_STAT_FACTS`）。
6. **被 GSAP 引用的元素必须有 `id`**（继承 news-coral 法则 9）。
7. **带 background 的片块只做 scaleX 擦入**（继承 news-coral 法则 8）。

---

## 5. 动量预算

```
INTRO_END = 1.0     // 比 coral 更短（数字不等人）
MIN_DRIFT = 0.5     // 数字卡刷入快，漂移短
driftStart = max(0, min(INTRO_END, slot - MIN_DRIFT))
driftDur   = max(MIN_DRIFT, slot - driftStart)
```

---

## 6. 地面清单与计划版式

| layout | 地面 | 文字色 | crimson 的出场方式 |
|---|---|---|---|
| `hook`（首镜） | paper | ink / gray | 标题下整醒 crimson 横线（书挡）|
| `stat`（单巨号）| paper | ink / gray | 巨号染 ink / 一个 accent 染 crimson |
| `compare`（双数对比）| paper | ink / gray | 中间分隔线 crimson |
| `drilldown`（分层下钻）| paper-dark | ink / gray | 层级标号 crimson 数字 |
| `closer`（末镜） | paper | ink / gray | 顶部 crimson 横线 + 烫金印章形 |

**单地面 pack**：90% 时间在 paper 上，hook / closer 用 crimson 横线做书挡；drilldown 切 paper-dark 做二级层。

---

## 7. 计划 composition 文件

```
news-stat/
├── frame.md
├── host.html
└── compositions/
    ├── hook.html       nc-stat-hook     米白纸 + crimson 书挡
    ├── stat.html       nc-stat-stat     单巨号 + 单位
    ├── compare.html    nc-stat-compare  两巨号 + crimson 分隔
    ├── drilldown.html  nc-stat-drill    三层下钻 + crimson 层级
    └── closer.html     nc-stat-closer   米白纸 + crimson + 烫金印章
```

---

## 8. 与 news-coral 的关键差别

| 维度 | news-coral | news-stat |
|---|---|---|
| 主色 | 珊瑚红 #E85D5D | 朱红 #C0392B（只染 1 个数）|
| 字体 | 无衬线巨号（响）| 衬线巨号（重）|
| 节奏 | 0.6 漂移 | 0.5 漂移（更快）|
| 视觉气质 | 火带 + 冲击力 | 米白纸 + 数据感 |
| 适用稿件 | 故事 / 反转 | 数据 / 排行 / 数字冲击 |
