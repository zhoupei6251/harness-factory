# 杂志·暖纸 —— frame.md

> ⚠️ 本文件由 `hf_compile.py`（schema `hf-compile/1`）从同目录的 `spec.toml` 编译生成，
> **勿手改**：改数值请改 spec，然后重编译。手抄一份色值表就是 D10/D20 复发。

- 包 id：`news-editorial-warm` · 族：`editorial`（网格语法 `asymmetric-columns`）
- 画布：1080×1920（竖屏 9:16）· 单位一律 `cqw/cqh`
- 渲染口径：三道闸 + `hyperframes check --strict`

## 1. 色板与对比度

下面两张表的**表头形状**是给 `audit_pack_contrast.py` 认的（`| token | 值 |` 色板表、
`| 组合 | 比值 | 判定 |` 对比度表）：改列名 = 把第三个闸对本包变成空转。

### 1.1 色板 token（含 HSL 明度与阶梯归属）

| token | 值 | HSL 明度 | 阶梯档 | 参与阶梯 |
|---|---|---|---|---|
| accent | `#B45309` | 37.06 | — | 否（强调色走 saturation-budget） |
| ink | `#1f1b16` | 10.39 | 10.0 | 是 |
| panel | `#e8dfcb` | 85.29 | 85.0 | 是 |
| paper | `#f5efe3` | 92.55 | 93.0 | 是 |
| rule | `#ddd3bf` | 80.78 | 81.0 | 是 |
| display | `#1f1b16` | 10.39 | — | —（文字色，不是地面/面板） |
| body | `#1f1b16` | 10.39 | — | —（文字色，不是地面/面板） |
| secondary | `#6b5f4f` | 36.47 | — | —（文字色，不是地面/面板） |
| panel-body | `#1f1b16` | 10.39 | — | —（文字色，不是地面/面板） |
| on-ink | `#f5efe3` | 92.55 | — | —（文字色，不是地面/面板） |
| on-ink-soft | `#ddd3bf` | 80.78 | — | —（文字色，不是地面/面板） |
| on-ink-accent | `#B45309` | 37.06 | — | —（文字色，不是地面/面板） |
| kicker | `#B45309` | 37.06 | — | —（文字色，不是地面/面板） |
| on-accent | `#ffffff` | 100.00 | — | —（文字色，不是地面/面板） |

阶梯 `93.0 → 85.0 → 81.0 → 10.0`，容差 ±2.0（口径 `hf_style_spec.value_ladder_violations`）。

### 1.2 文字 / 底色对（判据 3，逐对实测）

| 组合 | 比值 | 判定 | 两端色值 | spec 档位 |
|---|---|---|---|---|
| display / paper | 14.95 | 大字（≥3.0）过 | `#1f1b16` on `#f5efe3` | large |
| body / paper | 14.95 | 正文（≥4.5）过 | `#1f1b16` on `#f5efe3` | body |
| secondary / paper | 5.43 | 正文（≥4.5）过 | `#6b5f4f` on `#f5efe3` | body |
| panel-body / panel | 12.92 | 正文（≥4.5）过 | `#1f1b16` on `#e8dfcb` | body |
| on-ink / ink | 14.95 | 正文（≥4.5）过 | `#f5efe3` on `#1f1b16` | body |
| on-ink-soft / ink | 11.53 | 正文（≥4.5）过 | `#ddd3bf` on `#1f1b16` | body |
| on-ink-accent / ink | 3.41 | 大字（≥3.0）过 | `#B45309` on `#1f1b16` | large |
| kicker / paper | 4.39 | 大字（≥3.0）过 | `#B45309` on `#f5efe3` | large |
| on-accent / accent | 5.02 | 正文（≥4.5）过 | `#ffffff` on `#B45309` | body |

## 2. 字体

| 位 | 族 | 字重 | 供给方式 |
|---|---|---|---|
| 标题 display | `HF Serif CJK` | 900 | 本文件自带 `@font-face` + `local()`（CJK 只能走本机） |
| 正文 body | `HF CJK` | 400 | 同上 |
| 拉丁位 | `Playfair Display` | — | 引擎自动供给（裸族名，加 `local()` 反而失效） |

拉丁位锁死在引擎捆绑的 18 个族里（`hf_style_spec.LATIN_CANONICAL_FAMILIES`）；集合外的名字会打 `font_family_without_font_face`（error 级）。

## 3. 网格与安全区

- 语法 `asymmetric-columns`，12 栏
- 横向安全区左右各 `6.0` / `6.0`（cqw），内容一律落在其间
- 底部字幕禁入区 `20.0` cqh —— 由 `spec.subtitle` 的几何反算（不是手写的 20），见 `hf_style_spec.caption_reserve_cqh`

## 4. 动效签名

- 签名 `clip-rise-char` · 缓动 `power3.out`（allowed 第 0 个即招牌缓动），禁 `back.out`, `elastic`, `bounce`
- 招牌入场 `1.4s`，单动作下限 `0.5s`（法则 13：原语按 `max(下限, 招牌/2)` 构造，写不进去也就跳不过去）
- 动量预算常数 `INTRO_END = 1.5`、`MIN_DRIFT = 0.6`，每镜至少一条挂在 `driftDur` 上的持续位移（`drift = keep`）
- 一律 `fromTo`（`.from()` 在 seek 回退时失步）；自带 background 的面禁 `opacity` 补间（法则 8）；无运行时随机（法则 10，抖动编译期烘焙）

## 5. 版式清单

### `hook.html` — 合成 id `ew-hook`

- 地面：`paper` = `#f5efe3`
- 变量：`kicker`, `headTop`, `headBottomLead`, `headAccent`, `support`, `slotSeconds`
- 原语：`hairline`, `block-chip`, `char-rise`, `keyword-tint`, `rule-pull`, `cue-fade` + `drift-y`

### `stat.html` — 合成 id `ew-stat`

- 地面：`paper` = `#f5efe3`
- 变量：`kicker`, `value`, `unit`, `label`, `compareValue`, `compareUnit`, `compareLabel`, `slotSeconds`
- 原语：`hairline`, `block-chip`, `giant-numeral`, `cue-fade`, `clip-wipe-up` + `drift-y`

### `rail.html` — 合成 id `ew-rail`

- 地面：`paper` = `#f5efe3`
- 变量：`kicker`, `title`, `ordinal`, `item1Label`, `item1Value`, `item2Label`, `item2Value`, `item3Label`, `item3Value`, `slotSeconds`
- 原语：`hairline`, `block-chip`, `char-rise`, `giant-numeral`, `clip-wipe-up`, `cue-fade` + `drift-y`

### `quote.html` — 合成 id `ew-quote`

- 地面：`paper` = `#f5efe3`
- 变量：`kicker`, `quoteBody`, `attribution`, `slotSeconds`
- 原语：`hairline`, `block-chip`, `clip-wipe-up`, `cue-fade`, `rule-pull` + `drift-y`

### `catalog.html` — 合成 id `ew-catalog`

- 地面：`paper` = `#f5efe3`
- 变量：`kicker`, `title`, `step1Index`, `step1Label`, `step1Body`, `step2Index`, `step2Label`, `step2Body`, `step3Index`, `step3Label`, `step3Body`, `slotSeconds`
- 原语：`hairline`, `block-chip`, `char-rise`, `giant-numeral`, `cue-fade` + `drift-y`

### `story.html` — 合成 id `ew-story`

- 地面：`paper` = `#f5efe3`（`tone` 变量可翻墨面）
- 变量：`kicker`, `ordinal`, `tone`, `title`, `onscreen`, `slotSeconds`
- 原语：`hairline`, `block-chip`, `char-rise`, `giant-numeral`, `rule-pull`, `cue-fade` + `drift-y`

### `closer.html` — 合成 id `ew-closer`

- 地面：`ink` = `#1f1b16`
- 变量：`kicker`, `cta`, `ctaAccent`, `channel`, `slotSeconds`
- 原语：`hairline`, `block-chip`, `char-rise`, `keyword-tint`, `rule-pull`, `cue-fade` + `drift-y`

## 6. 禁忌（编译期断言，法则 13）

- `no-overshoot`：杂志族的力量来自收着，过冲（back/elastic/bounce）一秒钟就变成促销海报
- `entrance-not-faster-than-0p5s`：小于 0.5s 的入场在读完之前就结束了，读者只会觉得画面闪了一下
- `no-border-radius`：圆角是 UI 语言，纸面上只有直角与裁边；一旦圆角，暖纸就变成 App 截图

---

编译：`python skills/douyin-pro/scripts/hf_compile.py news-editorial-warm`
真源：`templates/hyperframes_path_c/news-editorial-warm/spec.toml`（schema `hf-style/1`）
