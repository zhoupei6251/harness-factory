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

### 2.1 对比度（实测值，2026-09-29）

按 WCAG 2.x 相对亮度公式对 §2 的 token 原值直接算（复算脚本
`.harness-news-runtime/tmp/contrast_policy.py`，输出与结果记录在
`.harness-news-runtime/verifications/2026-09-29-news-policy-layouts-verification-lite.md`）。
判读线：正文 4.5:1，大字 3:1（画布 1080 宽下 1cqw=10.8px，≥24px ≈ ≥2.3cqw 即算大字）。

| 组合 | 比值 | 判定 |
|---|---|---|
| ink / paper | 15.20 | ✓ 正文主力 |
| cobalt / paper | 9.84 | ✓ 标题、序号、强调字 |
| gray / paper | 4.65 | ✓ 大字档 —— 只给眉标/节点号这类配角 |
| cobalt / paper-dark | 8.51 | ✓ 条目标题 |
| ink / paper-dark | 13.13 | ✓ 条文说明 |
| paper / cobalt（暗面）| 9.84 | ✓ closer 地面、story `data-tone="dark"` |
| rule / cobalt | 6.23 | ✓ 来源行（3.4cqw 属大字）|
| cobalt-dark 字 / gold 片 | 4.85 | ✓ 强调片的正确写法是**金底深字** |
| gold / paper | 2.54 | ✗ 只作形状（印章环、发丝尺线）|
| gold / paper-dark | 2.20 | ✗ 只作形状 |
| gold / cobalt | 3.87 | 过大字线(3.0)、不过正文线(4.5) —— 但按下面的强制规则**只作形状**，金字改金片 |
| crimson / paper | 4.75 | 数学上够大字，但仍按下面的强制规则**只作形状** |
| paper / paper-dark | 1.16 | ✗ 两级米白之间不做文字分层，只用来换地面 |

> **强制规则**：gold 和 crimson 永远只作形状（印章、日期戳、横线），不作文字。
> 公文蓝 cobalt 可以染标题、序号、关键强调字。
> 补一条实测出来的细则：**要强调"日期/关键词"就贴片（金底 + cobalt-dark 字 4.85），
> 不要染金字（3.87 只过大字线、正文档也不过，且 gold 按上条规则一律不作文字）** —— `hook` 的 `.pk-ac`、`closer` 的 `.pf-ac` 都是这么写的。

---

## 3. 字阶（与已发射的 5 个 composition 一致）

| 位 | 字体 | 字号 | 字重 | 其他 |
|---|---|---|---|---|
| 眉标 | `"JetBrains Mono", monospace` | 2.6cqw | 700 | 钴蓝片 + 纸白字；暗面整片反相 |
| 公文标题（hook）| `"HF Serif CJK", serif` | 9cqw | 700 | cobalt，line-height 1.18；`split_headline` 切两行 + 强调片 |
| 小节标题（catalog / rail）| `"HF Serif CJK"` | 8.4cqw | 700 | cobalt，**脚本侧 ≤10 字**（三行会压到尺线/脊线，见 §6）|
| 领句（story）| `"HF Serif CJK"` | 8.6cqw | 700 | `fitCqw` 3 行封顶，作者没写标题就不选 story |
| 辅助行（hook 的 `support`）| `"HF CJK", sans-serif` | 3.6cqw | 400 | ink —— 取材处 = 屏句（见下方订正）|
| 条目 | `"HF Serif CJK"` | 4.4cqw | 700 | 序号 cobalt 片 |
| 条文说明 | `"HF CJK", sans-serif` | 3.4cqw | 400 | ink，`ROW_BODY_MAX_CHARS=42` 两行封顶 |
| 时间线节点 | `"JetBrains Mono"` | 3.6cqw | 800 | cobalt，`RAIL_VALUE_MAX_CHARS=8`（日期走短形）|
| 屏句（story）| `"HF CJK"` | 4.4cqw | 400 | 86cqw 盒两行封顶，light 走 gray / dark 走 rule |

- 公文型必须有衬线（公文 = 庄重）；正文说明可以无衬线（小字 = 可读）
- 拉丁显示族写裸族名。中文族由每个版式自带 `@font-face` + `local()` 六连。
- **订正（2026-09-29 落地时）**：原计划"施行日期 12cqw 900 + gold 印章底"没有落地。
  原因是发射器没有"只取日期"的取材处 —— hook 的这一位由 `_onscreen_phrase`（整条屏句）
  填充，12cqw 在 16 字屏句下必然溢出，而日期也不是独立变量。现在写成 3.6cqw 辅助行，
  **日期要上屏就让脚本在屏句里写全**（`屏: 2026年10月1日施行`），版式不自己编日期。

---

## 4. 版面法则

1. **内容只占顶部 80%**：底部 20cqh 留给字幕。
2. **首镜必出现公文标题 + 施行日期**：发布机关 + 施行日期 + "新规"红/金印章 = 一眼认出"这是政策"。
   落地方式：标题走 `title`（`split_headline` 两行 + 金片强调），**施行日期写在屏句里**
   （`屏: 2026年10月1日施行` → hook 的 `support` 位）；版式不许自己生成日期（§3 订正）。
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

## 6. 地面清单与已落地版式

发射器只认**文件名词干**（候选清单写死在 `path_b_build.choose_layout`：
`hook / story / stat / quote / catalog / rail / closer`）。本 pack 原计划的
`summary / points / timeline` 三个名字不在词汇表里，因此**按语义写成 canonical 文件名**，
composition id 统一 `np-*` 前缀保留公文身份：

| 计划名 | 实际文件 | composition id | 地面 | 文字色 | cobalt / gold 的出场方式 |
|---|---|---|---|---|---|
| `hook` | `hook.html` | `np-hook` | paper | ink / cobalt | 顶部 cobalt 粗尺 + gold 细尺（双书挡）+ gold 印章环；标题强调走金片 |
| `summary` | `story.html` | `np-story` | paper ⇄ cobalt（`tone` 逐镜翻转）| ink / cobalt / paper | 序号水印 + cobalt 眉标片（暗面反相）+ gold 尺线 |
| `points` | `catalog.html` | `np-catalog` | paper-dark | ink / cobalt | cobalt 序号片 + 纸白字；gold 只作尺线 |
| `timeline` | `rail.html` | `np-rail` | paper | ink / cobalt / gray | cobalt 主脊 + 节点日期 cobalt；gold 不出场 |
| `closer` | `closer.html` | `np-closer` | **cobalt（暗面）** | paper / rule | paper 双书挡（与 hook 同位反相）+ gold 末印环 + 金片 CTA |
| — | 未 author | — | — | — | `quote`（法则 4 政策类不上引文）、`stat`（数字型归 `news-stat` pack）|

**地面登记**（`path_b_build.GROUND_TONE_BY_HEX`，未登记的地面装包直接停机）：

| hex | 归 | 用在 |
|---|---|---|
| `#F5EFE3` paper | light | hook / story(light) / rail |
| `#E8DFCB` paper-dark | light | catalog |
| `#1F3A68` cobalt | dark | story(dark) / closer |

- **双地面翻转**：story 的明暗由发射器给（`_tone` 相对上一镜翻转），版式只认 `tone` 变量；
  公文系统不用黑底作暗面 —— 翻面走 cobalt，这样"暗面"仍然是同一份文件的一部分。
- **写屏算术（脚本侧必须知道的三条）**：
  1. 小节标题（catalog / rail）≤10 字 —— 三行 8.4cqw×1.2 = 30cqh 会压到 38cqh 的尺线（catalog）
     或 34cqh 的脊线起点（rail）。这一位是"小节标签"，整句走 story。
  2. rail 的 `value`（日期）≤8 字（`RAIL_VALUE_MAX_CHARS`）——`"2026年10月1日"` 11 字会让
     整个 rail 在自动模式不可选，写 `2026.10` / `10月1日`。
  3. 屏句 5–16 字（`ONSCREEN_MIN/MAX_CHARS`），且屏句是 hook `support`、story `onscreen`、
     closer `cta/ctaAccent` **唯一**的取材处 —— 日期、行动指令要上屏就必须写在屏句里，
     closer 的强调段只能落在作者点的 `｜` 上。
- 法则 4「政策类只看事实」在 closer 的体现：`channel` 走 `--source`/`source` 键（归属只能来自数据）。

---

## 7. composition 清单（已落地）

```
news-policy/
├── frame.md
├── host.html
└── compositions/
    ├── hook.html     np-hook     红头文件: 双书挡 + gold 印章环 + 标题金片
    ├── story.html    np-story    领句 + 烫金尺 + 屏句, paper ⇄ cobalt 翻转
    ├── catalog.html  np-catalog  三条要点: paper-dark 卡衬 + cobalt 序号片 + 逐行落
    ├── rail.html     np-rail     政策时间线: cobalt 主脊 + 事件/日期成对三节点
    └── closer.html   np-closer   尾镜书挡(与 hook 同位反相) + 金片 CTA + 来源行
```

`placeholder.html` 已删除（占位壳既不进版式选择也不进可渲染计数，留着只会误导）。
本 pack 现在**可渲染**：`path_b_build.ready_packs()` = `['news-coral', 'news-policy']`。
每个文件的契约（`data-composition-variables`）就是上表的变量集，新增版式前先确认
`choose_layout` 认这个名字（§6 第一段的词汇表限制）。

---

## 8. 与 news-coral 的关键差别

| 维度 | news-coral | news-policy |
|---|---|---|
| 主色 | 珊瑚红 #E85D5D | 公文蓝 #1F3A68 |
| 字体 | 无衬线巨号 | 衬线公文 |
| 节奏 | 0.6 漂移 | 0.7 漂移（稍慢）|
| 视觉气质 | 火带 + 故事感 | 公文蓝 + 烫金印章 |
| 适用稿件 | 故事 / 反转 | 政策 / 法规 / 通知 |
