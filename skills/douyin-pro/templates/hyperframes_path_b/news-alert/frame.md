# news-alert — 设计系统与硬约束

本文件是 **`news-alert` 节目包的 token 源**。画布基准 1080×1920。排版 `cqw/cqh`，禁 `px`。

---

## 1. 用途与触发场景

应急提醒、安全提示、避险通知、防诈预警、健康警示、出行管制。视觉气质一句话：

> **黑底警示红 + 黄色三角 + 醒目大字 = 让你停下滑动的手指。**

- 主线：每条都是行动指令，不是叙述
- 与 `news-coral` 的差别：coral 是"故事"，alert 是"喊你做事"
- 触发词：紧急、提醒、务必、切记、不要、马上、立即、危险、警告、预警、骗子、骗局、出行、管制、停售、停运

不适合：人物故事（`news-coral`）、数据新闻（`news-stat`）、政策原文（`news-policy`）。

---

## 2. 色板

| token | 值 | 用途 |
|---|---|---|
| `black` | `#0E0E0E` | 主底 80% |
| `black-soft` | `#1A1A1A` | 卡片底 |
| `white` | `#F8F4EA` | 主文字 / 大标题（不是纯白，暖一点避硬）|
| `gray` | `#9A9A9A` | 次级文字（说明行）|
| `alert` | `#D7263D` | 警示红（**只作形状 + 强调大字号文字**）|
| `alert-dark` | `#A11D2E` | 次级警示（仅作形状）|
| `warn` | `#F2C94C` | 警示黄（**只作三角/感叹号形状**）|
| `ok` | `#3FA34D` | 极少使用（仅"安全/通过"动作的勾选）|

### 2.1 对比度

下表由 `python skills/douyin-pro/scripts/audit_pack_contrast.py news-alert` 按 §2 色板原值复算，
改色板必须重跑它。判读线：正文 4.5 / 大字 3.0（画布 1080 宽下 1cqw=10.8px，≥24px ≈ ≥2.22cqw 算大字）。

| 组合 | 比值 | 判定 |
|---|---|---|
| white / black | 17.58 | ✓ 任意字号 |
| alert / black | 3.89 | ✓ 大字档（正文线 4.5 不过 —— 小字号一律白字）|
| warn / black | 12.17 | ✓ 任意字号（但按法则 warn 只作形状）|

> **强制规则**：
> - warn 永远只作形状（三角/感叹号/分隔线），**不作文字**
> - alert 大字号（≥28cqw）可以染字，小字号仍是白字 + alert 形状
> - 不许 alert + warn 同时出现（视觉打架）

---

## 3. 字阶

| 位 | 字体 | 字号 | 字重 | 其他 |
|---|---|---|---|---|
| 警示标 alert-marker | `"JetBrains Mono", monospace` | 3cqw | 900 | letter-spacing .2em，全大写 `ALERT / WARNING / 紧急` |
| 警示巨字 | `"HF CJK", sans-serif` | 18cqw | 900 | line-height 1.05，黑底可染 alert |
| 行动指令 | `"HF CJK"` | 9cqw | 800 | 黑底白字 |
| 步骤 | `"HF CJK"` | 5cqw | 700 | 步骤编号走 warn 大方块 |
| 说明 | `"HF CJK"` | 3.4cqw | 400 | gray |
| 屏句 | `"HF CJK"` | 4.4cqw | 400 | 88cqw 盒两行封顶 |

- 警示型不上衬线（衬线 = 慢，警示 = 急）。
- 拉丁显示族写裸族名。中文族由每个版式自带 `@font-face` + `local()` 六连。

---

## 4. 版面法则

1. **内容只占顶部 80%**：底部 20cqh 留给字幕。
2. **首镜必出现三角警示符**：warn 三角 + ALERT 大写标识 = 一眼认出"这是警报"。
3. **每镜最后一行必须是行动**：祈使句 + 第二人称（"立即查一下"、"不要点这个"）。
4. **不要复杂动画**：警示型画面越直白越好。所有入场一律硬切（0.2s），不用 scaleX 擦入（避免"柔和"误导）。
5. **带 background 的片块只做硬切 / scaleX**（继承 news-coral 法则 8，本包内 opacity 直接禁）。
6. **不要退场动画**：警示型收尾必须干脆，不能渐隐（让人误以为"还没结束"）。
7. **被 GSAP 引用的元素必须有 `id`**（继承 news-coral 法则 9）。

---

## 5. 动量预算

```
INTRO_END = 0.5     // 警示型入场极快（hero 在 t≤0.2s 可见）
MIN_DRIFT = 0.3     // 警示型几乎不漂移（稳 = 可信）
driftStart = max(0, min(INTRO_END, slot - MIN_DRIFT))
driftDur   = max(MIN_DRIFT, slot - driftStart)
```

> 入场曲线禁用 ease: "power3.out" / "elastic.out"（柔缓 = 不可信），改用 `power2.out` 或 `none`。

---

## 6. 地面清单与计划版式

| layout | 地面 | 文字色 | alert 的出场方式 |
|---|---|---|---|
| `hook`（首镜） | black | white / alert | 顶部 warn 三角书挡 + ALERT 标识 |
| `risk-callout`（单一风险）| black | white | 整屏 alert 巨字 + warn 三角 |
| `list-steps`（步骤清单）| black-soft | white | 步骤编号 warn 方块 + 行动指令白字 |
| `closer`（末镜） | black | white | 顶部 ALERT book挡 + 行动召唤 |

**单地面 pack**：90% 时间在 black 上；步骤卡用 black-soft 衬底，避免纯黑纯白太刺眼。

---

## 7. 计划 composition 文件

```
news-alert/
├── frame.md
├── host.html
└── compositions/
    ├── hook.html         nc-alert-hook       三角警示书挡
    ├── risk-callout.html nc-alert-risk       单风险 alert 巨字
    ├── list-steps.html   nc-alert-steps      行动步骤清单
    └── closer.html       nc-alert-closer     行动召唤末镜
```

---

## 8. 与 news-coral 的关键差别

| 维度 | news-coral | news-alert |
|---|---|---|
| 主色 | 珊瑚 #E85D5D | 警示红 #D7263D |
| 字体 | 衬线 + 无衬线混用 | 全无衬线（急 = 不柔）|
| 节奏 | 0.6 漂移 | 0.3 漂移（几乎静止）|
| 视觉气质 | 火带 + 故事感 | 警示三角 + 行动指令 |
| 适用稿件 | 故事 / 反转 | 应急 / 防诈 / 健康警示 |
