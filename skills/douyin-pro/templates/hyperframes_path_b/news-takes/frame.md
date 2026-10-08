# news-takes — 设计系统与硬约束

本文件是 **`news-takes` 节目包的 token 源**。画布基准 1080×1920。排版 `cqw/cqh`，禁 `px`。

---

## 1. 用途与触发场景

观点评论、专栏、解读、社论、深度思考、观察。视觉气质一句话：

> **单墨 + 浅米 + 单一中性灰 = 像一封写给读者的长信。**

- 主线：每条都是"我怎么看这件事"，靠论证而不是靠冲击
- 与 `news-coral` 的差别：coral 是"发生了什么"，takes 是"为什么这很重要"
- 触发词：观点、评论、专栏、解读、我觉得、我们应该、为什么这事、观察、思考、深度

不适合：人物故事（`news-coral`）、数据排行（`news-stat`）、突发新闻（`news-onsite`）、政策原文（`news-policy`）。

---

## 2. 色板

| token | 值 | 用途 |
|---|---|---|
| `paper` | `#F5EFE3` | 浅米主底（60%，写信纸感）|
| `ink` | `#1A1A1A` | 主文字 / 标题 |
| `ink-soft` | `#3A3A3A` | 次级文字 |
| `gray` | `#6B6B6B` | 唯一"强调色"（不是彩色灰）|
| `paper-dark` | `#E8DFCB` | 二级卡底（引文衬）|
| `rule` | `#C9C0AA` | 报纸细线 |
| `ink-ground` | `#0C0C10` | 墨黑底（近纯黑，观点域地面） |

> **本 pack 不用任何彩色强调**（没有红 / 蓝 / 黄 / 金）。
> 视觉的克制本身就是观点型应有的语气——少色 = 用繁简论证撑住。

### 2.1 对比度

下表由 `python skills/douyin-pro/scripts/audit_pack_contrast.py news-takes` 按 §2 色板原值复算，改色板必须重跑它。
判读线：正文 4.5 / 大字 3.0（画布 1080 宽下 1cqw=10.8px，≥24px ≈ ≥2.22cqw 算大字）。

| 组合 | 比值 | 判定 |
|---|---|---|
| ink / paper | 15.20 | ✓ 任意字号 |
| gray / paper | 4.65 | ✓ 任意字号（刚过正文线，只给次级文字）|
| ink / paper-dark | 13.13 | ✓ 任意字号 |

> **强制规则**：
> - 本 pack 永远只用 ink / gray / paper / paper-dark 4 个色
> - 不加彩色意味着引文卡 / 强调字 / 印章都只能靠排版（粗细 / 斜体 / 引号 / 缩进）

---

## 3. 字阶

| 位 | 字体 | 字号 | 字重 | 其他 |
|---|---|---|---|---|
| 眉标 | `"JetBrains Mono", monospace` | 2.6cqw | 700 | "观点 / 评论 / 专栏" |
| 主标题 | `"HF Serif CJK", serif` | 8cqw | 700 | line-height 1.2 |
| 引文 | `"HF Serif CJK", serif` | 6cqw | 700 italic | line-height 1.5（**唯一允许斜体**）|
| 屏句 | `"HF Serif CJK"` | 4.6cqw | 400 | 88cclclcl 盒两行封顶 |
| 正文 | `"HF Serif CJK"` | 3.6cqw | 400 | ink |
| 段落首字 | `"HF Serif CJK"` | 7cqw | 700 | drop cap（首字下沉，灰底米色）|
| 署名 | `"JetBrains Mono", monospace` | 2.6cqw | 700 | "——评论员 XXX"，gray |

- 观点型必须全衬线（衬线 = 严肃论证）
- 拉丁显示族写裸族名。中文族由每个版式自带 `@font-face` + `local()` 六连。

---

## 4. 版面法则

1. **内容只占顶部 80%**：底部 20cqh 留给字幕。
2. **首镜必出现署名 + "专栏 / 评论" 标识**：开篇知道"这是谁的观点"。
3. **每条必带引文链**：观点型引一句原文（"X 说……"）→ 自己解读（"这是问题所在……"）。
4. **段落首字下沉**：drop cap 是观点型的标志（**全 12 个 pack 中只在 takes 用**）。
5. **节奏偏慢**：`MIN_DRIFT = 0.8`，给观众"读"的时间。
6. **每镜必带署名横线**：右下角小字 "——评论员 XXX"，强调"这是观点不是新闻"。
7. **被 GSAP 引用的元素必须有 `id`**（继承 news-coral 法则 9）。
8. **带 background 的片块只做 scaleX 擦入**（继承 news-coral 法则 8）。

---

## 5. 动量预算

```
INTRO_END = 1.5     // 观点型入场偏慢
MIN_DRIFT = 0.8     // 观点型漂移中等偏慢（论证要让人"读进去"）
driftStart = max(0, min(INTRO_END, slot - MIN_DRIFT))
driftDur   = max(MIN_DRIFT, slot - driftStart)
```

---

## 6. 地面清单与计划版式

| layout | 地面 | 文字色 | 强调唯一元素 |
|---|---|---|---|
| `hook`（开篇"我说"）| paper | ink | 段落首字下沉 + 署名横线 |
| `quote`（引文 + 解读）| paper / paper-dark | ink | 衬线斜体引文 + 缩进 |
| `chain`（论证链）| paper | ink / gray | 编号 gray + 段落首字下沉 |
| `closer`（末镜"所以我说"）| pattern | ink | drop cap + 署名横线 |

**单地面 pack**：90% paper；引文卡切 paper-dark 做二级层；hook / closer 用 drop cap + 署名。

---

## 7. 计划 composition 文件

```
news-takes/
├── frame.md
├── host.html
└── compositions/
    ├── hook.html   nc-takes-hook   开篇"我说"+ drop cap
    ├── quote.html  nc-takes-quote  引文 + 解读
    ├── chain.html  nc-takes-chain  论证链
    └── closer.html nc-takes-closer 末镜"所以我说"+ 署名
```

---

## 8. 与 news-coral 的关键差别

| 维度 | news-coral | news-takes |
|---|---|---|
| 主色 | 珊瑚 #E85D5D | **无彩色**（仅 ink / gray / paper）|
| 字体 | 无衬线巨号 | 全衬线（论证感）|
| 节奏 | 0.6 漂移 | 0.8 漂移（慢一点）|
| 视觉气质 | 火带 + 故事感 | 单墨 + 米白 + 长信感 |
| 适用稿件 | 故事 / 反转 | 观点 / 评论 / 专栏 |
