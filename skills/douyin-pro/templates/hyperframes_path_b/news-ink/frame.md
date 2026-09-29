# news-ink — 设计系统与硬约束

本文件是 **`news-ink` 节目包的 token 源**。色板/字阶/法则/动量预算以本文为准；
改风格先改这里。`compositions/*.html` 与 `host.html` 出现的每个值必须能在本文找到出处。

画布基准: 1080 × 1920（竖屏 9:16）。1cqw = 10.8px，1cqh = 19.2px。
排版一律用 `cqw/cqh`，禁止 `px`（继承 `news-coral` 的同条法则）。

---

## 1. 用途与触发场景

调查报道、深度揭露、长篇解释、追踪类专题。视觉气质一句话：

> **全墨底 + 米白衬线 + 报纸细线 = 让人想读完的长文。**

- 主线：单色克制，节奏慢，靠结构而不是颜色撑住信息层级
- 与 `news-coral` 的差别：火带变细线、衬线替代黑体、米白替代珊瑚色
- 触发词：调查、卧底、起底、深度、揭露、追踪、复盘、年终、专题

不适合：突发新闻（用 `news-onsite`）、政策原文（用 `news-policy`）、数字排行（用 `news-stat`）。

---

## 2. 色板

| token | 值 | 用途 |
|---|---|---|
| `ink` | `#0E0E0E` | 墨底（主地面 70%）|
| `ink-soft` | `#1A1A1A` | 卡片底 / 二级地面（仅用于衬底，永远不是字）|
| `cream` | `#F5EFE3` | 米白（次地面 30%；调查文段、引文、表格）|
| `cream-dark` | `#E8DFCB` | 米白卡衬（quote 的衬底）|
| `rule` | `#2A2A2A` | 报纸分隔细线（墨底场景）|
| `rule-cream` | `#C9C0AA` | 报纸分隔细线（米白场景）|
| `text-light` | `#E8E2D2` | 墨底正文 / 大标题（默认文字色）|
| `text-mute` | `#9A9A9A` | 墨底次级文字（说明行、署名）|
| `text-ink` | `#1A1A1A` | 米白底正文（默认文字色）|
| `text-ink-mute` | `#6B6B6B` | 米白底次级文字（眉标、标签）|
| `accent` | `#C9A24A` | 烫金（仅用于细线分隔、序号水印、章节钩 **闭合）**——**不作文字** |

### 2.1 对比度（只测常出现的 4 个）

下表由 `python skills/douyin-pro/scripts/audit_pack_contrast.py news-ink` 按 §2 色板原值复算，改色板必须重跑它。
判读线：正文 4.5 / 大字 3.0（画布 1080 宽下 1cqw=10.8px，≥24px ≈ ≥2.22cqw 算大字）。

| 组合 | 比值 | 判定 |
|---|---|---|
| text-light / ink | 14.93 | ✓ 任意字号 |
| text-mute / ink | 6.86 | ✓ 任意字号 |
| text-ink / cream | 15.20 | ✓ 任意字号 |
| accent / ink | 8.04 | ✓ 数学过正文线，但按法则 accent 只作细线/形状，不作字 |

> **强制规则**：accent 永远是**形状**（细线、水印、序号块底），不是文字。
> 订正（2026-09-29 复算）：旧表写"烫金字在墨底只到 6.5，不如 news-coral 的珊瑚白字 9.96 稳"，
> 两个数都是错的 —— accent/ink 实测 **8.04**，而 coral 那个"9.96"其实是 `ink / white`（真值 17.40），
> coral 的白字在珊瑚片上是 **3.41**（只算大字档）。所以本包的克制**不是**因为金色读不出来，
> 而是设计选择：颜色少，字才有重量。

---

## 3. 字阶

| 位 | 字体 | 字号 | 字重 | 其他 |
|---|---|---|---|---|
| 眉标 eyebrow | `"JetBrains Mono", monospace` | 2.6cqw | 700 | letter-spacing .18em，米白底烫金字 / 墨底米白字 |
| 主标题 display | `"HF Serif CJK", serif` | 9.6cqw | 700 | line-height 1.18，墨底用 text-light、米白底用 text-ink |
| 小标题 | `"HF Serif CJK"` | 6.4cqw | 700 | |
| 巨号数字 | `"HF Serif CJK"` | 22cqw | 700 | 与 news-coral 的无衬线巨号有意区分：调查型数字应当"重"而不是"响" |
| 次级数字 | `"HF Serif CJK"` | 8cqw | 700 | |
| 壁纸序号 | `"JetBrains Mono"` | 38cqw | — | line-height .82，6% ink + data-layout-ignore |
| 正文 / 说明 | `"HF Serif CJK"` | 3.6cqw | 400 | 墨底用 text-mute、米白用 text-ink-mute |
| 屏句（整句）| `"HF Serif CJK"` | 4.6cqw | 400 | 88cqw 盒两行封顶（法则 4）|
| 引文 | `"HF Serif CJK"` | 6.0cqw | 700 italic | line-height 1.5；斜体表示"这是引述" |

- 拉丁显示族（`JetBrains Mono`）只写裸族名，让引擎自动下载。
- 中文族 `"HF Serif CJK"` 由每个版式自带 `@font-face` + `local()` 六连（Noto Serif SC / Source Han Serif SC / SimSun / Noto Serif CJK SC / Songti SC / 思源宋体）。

---

## 4. 版面法则

1. **内容只占顶部 80%**：底部 20cqh 留给烧录字幕，所有 `inset` 下边界一律 20cqh。
2. **墨↔米白逐镜翻转**：相邻两镜必须不同地面（避免"暗调长片"）。`story` 跟前一镜取反。
3. **细线即分隔**：版式之间的层级用 1px `rule` 细线、双线（3px double）或空白间距，不要用色块当分隔。
4. **屏句、领句、行动句都走衬线**：调查型不上无衬线，正文从头到尾都是衬线。
5. **被 GSAP 引用的元素必须有 `id`**（继承自 news-coral 法则 9）：选择器解析成空数组时 GSAP 只打 console 警告，`--strict` 因此不过。
6. **带 background 的片块只做 scaleX 擦入**（继承自 news-coral 法则 8）：opacity 补间在墨底导致片底与地面混色后字掉对比度。
7. **数据 / 引文 / 章节钩三类是新闻调查的脊椎**——必须有这三种 card 的专门版式，不能用通用条替代。

---

## 5. 动量预算

```
INTRO_END = 1.5     // 入场节拍上限（hero 在 t≤0.5s 可见）
MIN_DRIFT = 0.8     // 调查型漂移偏慢（coral 是 0.6，ink 0.8 — 让画面有"翻页"感）
driftStart = max(0, min(INTRO_END, slot - MIN_DRIFT))
driftDur   = max(MIN_DRIFT, slot - driftStart)
```

- 补间一律 `fromTo`（`from()` 在 seek 回退时失步）。
- 漂移作用在内容容器，绝不作用在 `.clip` 挂载元素上。
- 非末帧禁止退场；末帧只保留漂移不做淡出（判据 3 对每一镜成立）。

---

## 6. 地面清单与计划版式

| layout | 地面 | 文字色 | 烫金的出场方式 |
|---|---|---|---|
| `hook`（首镜） | ink | text-light / text-mute | 顶部 1px 烫金细线（书挡），序号水印在右下 |
| `lead-detail`（领句+屏句） | **light↔dark 翻转**（跟随前一镜取反）| 跟随地面 | 无 |
| `evidence`（证据 / 时间线） | ink | text-light | 左侧烫金竖线（脊）|
| `quote`（引文） | cream + 米白卡 | text-ink / text-ink-mute | 卡顶 1px 烫金细线 + 烫金破折号 |
| `closer`（末镜） | ink | text-light | 顶部 1px 烫金细线（与 hook 同几何）+ 烫金署名横线 |

**三段混调**（与 coral 镜像）：`hook/evidence/closer` 墨底书挡，"lead-detail/quote" 米白叙述，结尾再回墨。

---

## 7. 计划 composition 文件

```
news-ink/
├── frame.md          ← 本文件
├── host.html         ← 沿用 news-coral 的骨架结构（容器尺寸、挂载盒约定一致）
└── compositions/
    ├── hook.html       nc-ink-hook       烫金书挡 + 米白字 + 大数字
    ├── lead-detail.html nc-ink-lead       双地面叙事节拍（领句 + 屏句）
    ├── evidence.html   nc-ink-evidence   三行证据 / 时间线（烫金脊线）
    ├── quote.html      nc-ink-quote      米白卡引文（烫金破折号）
    └── closer.html     nc-ink-closer     烫金书挡 + 署名横线
```

---

## 8. 与 news-coral 的关键差别（看完本节就能区分两个 pack）

| 维度 | news-coral | news-ink |
|---|---|---|
| 主色调 | 珊瑚红 #E85D5D | 烫金 #C9A24A（只作形状）|
| 字体 | 无衬线 `HF CJK` | 衬线 `HF Serif CJK` |
| 节奏 | 0.6 漂移（快） | 0.8 漂移（慢）|
| 视觉气质 | 火带 + 巨号 + 冲击力 | 细线 + 衬线 + 克制 |
| 适用稿件 | 故事 / 反转 / 钩子 | 调查 / 深度 / 长文 |

> 同一发射器、同一自检规则、同一动量公式；只换色板、字阶、版式几何 → 12 个 pack 共享同一套基础设施。
