# news-blast — 设计系统与硬约束

本文件是 **`news-blast` 节目包的 token 源**。画布基准 1080×1920。排版 `cqw/cqh`，禁 `px`。

---

## 1. 用途与触发场景

体育赛事、比分播报、实时比赛、进球集锦、NBA / 世界杯 / 奥运 / 比分段子。视觉气质一句话：

> **球场绿 + 球衣白 + 比分红 + 极快节奏 = 像体育频道 live ticker。**

- 主线：每条都有"谁 vs 谁 + 当前比分 + 时间"
- 与 `news-coral` 的差别：coral 讲故事，blast 报数字
- 触发词：比赛、比分、进球、加时、绝杀、绝平、首发、阵容、得分、助攻、篮板、决赛、半决赛

不适合：人物故事（`news-coral`）、政策原文（`news-policy`）、深度报道（`news-ink`）。

---

## 2. 色板

| token | 值 | 用途 |
|---|---|---|
| `pitch` | `#2D6A4F` | 球场草绿（主底 70%）|
| `pitch-dark` | `#1B4332` | 深绿（次级卡底）|
| `pitch-line` | `#52B788` | 球场线（**只作细线**）|
| `white` | `#F8F9FA` | 球衣白（主文字）|
| `gray` | `#B0B0B0` | 次级文字 |
| `score` | `#C0392B` | 比分红（**只作形状**：红牌、比分下划条。旧稿"主队数字必染字"被复算否证，见 §2.1）|
| `opp-score` | `#FFFFFF` | 客队数字（白字）|
| `gold` | `#B8923E` | 加时 / 黄牌标识（**只作形状**）|
| `crimson` | `#9A0C24` | 红牌 / 判罚标识（**只作形状**）|

### 2.1 对比度

下表由 `python skills/douyin-pro/scripts/audit_pack_contrast.py news-blast` 按 §2 色板原值复算，改色板必须重跑它。
判读线：正文 4.5 / 大字 3.0（画布 1080 宽下 1cqw=10.8px，≥24px ≈ ≥2.22cqw 算大字）。

| 组合 | 比值 | 判定 |
|---|---|---|
| white / pitch | 6.06 | ✓ 任意字号 —— 比分数字的唯一合法文字色 |
| white / pitch-dark | 10.51 | ✓ 任意字号 |
| score / pitch | 1.18 | ✗ 红字压绿草等于没有字 —— score 一律只作形状 |
| gold / pitch | 2.20 | ✗ 连大字线 3.0 也不过 —— gold 只作黄牌/边饰形状 |

> 旧稿这张表写的是 `score / pitch 5.0`、`gold / pitch 6.2`，两个数都错了 4 倍以上，
> 于是 §3 字阶把 22cqw（≈237px）的主队比分染成 score 红 —— 那是**红字压绿底**的 1.18:1，
> 成片会直接产出看不清的巨号比分。复算把这条错误设计拦在了文档阶段。

> **强制规则**：
> - score（红）**不作任何文字**：主客队比分都走 white，红只作红牌与比分下划条（`score / white = 5.16` 可作白字下的色条）
> - 球场线 `pitch-line` 只作背景草坪细线
> - 黄牌 / 红牌永远只作形状（方块 + 字符），不作大字

---

## 3. 字阶

| 位 | 字体 | 字号 | 字重 | 其他 |
|---|---|---|---|---|
| 眉标 | `"JetBrains Mono", monospace` | 2.6cqw | 700 | "LIVE / 比分 / 战报" |
| 队伍名 | `"HF CJK", sans-serif` | 4.4cqw | 700 | white |
| 比分 | `"League Gothic", sans-serif` | 22cqw | 900 | 主客队都走 white（红字压绿 1.18 不可染）；主队下方 score 下划条作区分 |
| ":" 分隔符 | `"League Gothic"` | 22cqw | 400 | white，居中 |
| 时间码 | `"JetBrains Mono", monospace` | 3.4cqw | 700 | "78'" "加时" |
| 屏句 | `"HF CJK"` | 4.4cqw | 400 | 88cqw 盒两行封顶 |

- 体育型必须有无衬线大数字（League Gothic 是绝佳选择）
- 拉丁显示族写裸族名（League Gothic 引擎自动供给）。中文族由每个版式自带 `@font-face` + `local()` 六连。

---

## 4. 版面法则

1. **内容只占顶部 80%**：底部 20cqh 留给字幕。
2. **首镜必出现双方队名 + 当前比分**：开篇一眼知道"谁 vs 谁 + 多少比多少"。
3. **每镜必带比赛时间码**：分钟 / 加时 / 点球，缺一即拒收。
4. **比分横切 10cqw**：比分卡必须占满画面水平中段（不能小气）。
5. **节奏极快**：`MIN_DRIFT = 0.3`，比分刷得快。
6. **不要引文 / 不要叙事**：体育型不上引文（除非"赛后采访"作为独立镜）。
7. **被 GSAP 引用的元素必须有 `id`**（继承 news-coral 法则 9）。
8. **带 background 的片块只做 scaleX 擦入**（继承 news-coral 法则 8）。

---

## 5. 动量预算

```
INTRO_END = 0.4     // 体育型入场极快
MIN_DRIFT = 0.3     // 体育型漂移极短（比分刷得紧）
driftStart = max(0, min(INTRO_END, slot - MIN_DRIFT))
driftDur   = max(MIN_DRIFT, slot - driftStart)
```

---

## 6. 地面清单与计划版式

| layout | 地面 | 文字色 | score / white 的出场方式 |
|---|---|---|---|
| `hook`（开篇 "VS"）| pitch | white / score（形状）| 双方队名 + 中央 ":" + 时间码 |
| `score`（比分更新）| pitch | white | 比分巨号（双方白字，score 只做下划条/牌形）|
| `play`（关键回合）| pitch-dark | white | 进球 / 判罚描述 |
| `closer`（末镜 "全场结束"）| pitch | white | 终场比分 + 致谢 |

**单地面 pack**：90% pitch；play 卡切 pitch-dark 做二级层；hook / closer 比分必大。

---

## 7. 计划 composition 文件

```
news-blast/
├── frame.md
├── host.html
└── compositions/
    ├── hook.html   nc-blast-hook   开篇 "VS" + 比分
    ├── score.html  nc-blast-score  比分更新
    ├── play.html   nc-blast-play   关键回合
    └── closer.html nc-blast-closer "全场结束"末镜
```

---

## 8. 与 news-coral 的关键差别

| 维度 | news-coral | news-blast |
|---|---|---|
| 主色 | 珊瑚 #E85D5D | 球场绿 #2D6A4F + 比分红 |
| 字体 | 衬线 + 无衬线 | League Gothic 巨号 + JetBrains Mono |
| 节奏 | 0.6 漂移 | 0.3 漂移（极快）|
| 视觉气质 | 火带 + 故事感 | 球场 + live 比分 |
| 适用稿件 | 故事 / 反转 | 体育 / 比分 / 实时赛事 |
