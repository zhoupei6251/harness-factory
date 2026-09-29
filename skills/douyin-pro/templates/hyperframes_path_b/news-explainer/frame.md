# news-explainer — 设计系统与硬约束

本文件是 **`news-explainer` 节目包的 token 源**。画布基准 1080×1920。排版 `cqw/cqh`，禁 `px`。

---

## 1. 用途与触发场景

科普图解、知识概念、机制讲解、why-how、概念拆解、原理介绍。视觉气质一句话：

> **教科书米色 + 钢笔蓝 + 暗红 = 像老师写在黑板上的图解。**

- 主线：每条都把"复杂概念"切成"可看懂的图"
- 与 `news-coral` 的差别：coral 讲"发生了什么"，explainer 讲"为什么会这样"
- 触发词：为什么、原理、其实、揭秘、你知道吗、科普、图解、解读、什么是

不适合：人物故事（`news-coral`）、突发新闻（`news-onsite`）、政策原文（`news-policy`）。

---

## 2. 色板

| token | 值 | 用途 |
|---|---|---|
| `paper` | `#F5EFE3` | 教科书米色主底 |
| `paper-dark` | `#E8DFCB` | 二级卡底（图说卡）|
| `ink` | `#1A1A1A` | 主文字 |
| `pen` | `#2C5F8D` | 钢笔蓝（重点、连线、SVG 主体色）|
| `pen-soft` | `#3D7AAB` | 钢笔蓝浅（图说副色）|
| `rule` | `#C9C0AA` | 米白报纸细线 |
| `crimson` | `#C0392B` | 暗红（关键标注、箭头，**只作形状**）|
| `gold` | `#B8923E` | 关键概念高亮（**只作形状**）|

### 2.1 对比度

| 组合 | 比值 | 判定 |
|---|---|---|
| ink / paper | 12.6 | ✓ |
| pen / paper | 8.6 | ✓ |
| crimson / paper | 5.1 | ✓ 大字号 |
| gold / paper | 4.4 | ✓ 大字号 |

> **强制规则**：crimson / gold 永远只作箭头、序号、关键节点形状，不作正文文字。

---

## 3. 字阶

| 位 | 字体 | 字号 | 字重 | 其他 |
|---|---|---|---|---|
| 眉标 | `"JetBrains Mono", monospace` | 2.6cqw | 700 | "科普 / 原理 / 图解" |
| 主标题 | `"HF Serif CJK", serif` | 8.4cqw | 700 | line-height 1.18 |
| 概念名 | `"HF Serif CJK"` | 7cqw | 700 | pen 色（**核心蓝色字**）|
| 步骤编号 | `"JetBrains Mono", monospace` | 5cqw | 900 | crimson 色（但只用于编号块底）|
| 正文 | `"HF Serif CJK"` | 3.6cqw | 400 | ink |
| 图说 | `"HF Serif CJK", italic` | 3cqw | 400 | gray |
| 屏句 | `"HF Serif CJK"` | 4.4cqw | 400 | 88cqw 盒两行封顶 |

- 教科书型必须有衬线（衬线 = 严肃科普）
- 拉丁显示族写裸族名。中文族由每个版式自带 `@font-face` + `local()` 六连。

---

## 4. 版面法则

1. **内容只占顶部 80%**：底部 20cqh 留给字幕。
2. **每镜必须有图**：SVG 图解 / 步骤 / 时间线 / 对比图，无图即降级到 `news-coral`。
4. **图说按位置放债**：图下方 3cqw 斜体 gray（"图：细胞分裂示意图"）。
5. **概念名用钢笔蓝**：唯一允许染字的特殊色（`pen`），让概念在视觉上"突出"。
6. **箭头/连线用暗红**：crimson 永远只作引导元素（箭头、序号、连线）。
7. **被 GSAP 引用的元素必须有 `id`**（继承 news-coral 法则 9）。
8. **带 background 的片块只做 scaleX 擦入**（继承 news-coral 法则 8）。

---

## 5. 动量预算

```
INTRO_END = 1.5     // 教科书入场中等（讲清东西）
MIN_DRIFT = 0.6     // 教科书漂移中等（讲解要慢一点）
driftStart = max(0, min(INTRO_END, slot - MIN_DRIFT))
driftDur   = max(MIN_DRIFT, slot - driftStart)
```

---

## 6. 地面清单与计划版式

| layout | 地面 | 文字色 | pen / crimson 的出场方式 |
|---|---|---|---|
| `hook`（开篇"为什么 / 什么是"）| paper | ink / pen | 顶部 pen 细线（书挡）|
| `diagram`（图解主画面）| paper | ink | SVG 主图（钢笔蓝）|
| `list`（步骤清单）| paper-dark | ink | 编号 crimson + 概念 pen |
| `closer`（末镜 "现在你知道了"）| paper | ink / pen | 顶部 pen 书挡 |

**单地面 pack**：全程 paper；步骤卡切 paper-dark 做二级层；图说斜体 gray。

---

## 7. 计划 composition 文件

```
news-explainer/
├── frame.md
├── host.html
└── compositions/
    ├── hook.html    nc-explainer-hook    开篇钩子
    ├── diagram.html nc-explainer-diagram SVG 图解主体
    ├── list.html    nc-explainer-list    步骤清单
    └── closer.html  nc-explainer-closer  末镜
```

---

## 8. 与 news-coral 的关键差别

| 维度 | news-coral | news-explainer |
|---|---|---|
| 主色 | 珊瑚 #E85D5D | 钢笔蓝 #2C5F8D |
| 字体 | 无衬线 | 全衬线（教科书）|
| 节奏 | 0.6 漂移 | 0.6 漂移（相当）|
| 视觉气质 | 火带 + 故事感 | 教科书 + 图示 |
| 适用稿件 | 故事 / 反转 | 科普 / 原理 / why-how |
