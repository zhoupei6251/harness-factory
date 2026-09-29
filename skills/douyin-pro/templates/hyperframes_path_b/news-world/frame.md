# news-world — 设计系统与硬约束

本文件是 **`news-world` 节目包的 token 源**。画布基准 1080×1920。排版 `cqw/cqh`，禁 `px`。

---

## 1. 用途与触发场景

国际新闻、地理战况、跨国事件、外交、战争、贸易、气候、地图新闻。视觉气质一句话：

> **深海军蓝 + 经纬白 + 红色标点 = 像战情室的 briefing。**

- 主线：每条都带地理位置（"X 国 Y 地区 Z 事件"）
- 与 `news-coral` 的差别：coral 讲一个人，world 讲一片地
- 触发词：国际、海外、边境、战争、冲突、外交、制裁、出口、汇率、气候 COP、条约、联合国

不适合：人物故事（`news-coral`）、政策原文（`news-policy`）、数据排行（`news-stat`）。

---

## 2. 色板

| token | 值 | 用途 |
|---|---|---|
| `navy` | `#0E1B36` | 深海军蓝主底（70%，像海图）|
| `navy-soft` | `#152544` | 二级卡底（地图衬）|
| `paper` | `#F0F4F8` | 经纬白（文字、地图底图）|
| `paper-dark` | `#D9E0E8` | 二级米白（图说）|
| `lat` | `#4A6E9E` | 经纬线（细线，**只作形状**）|
| `crimson` | `#C0392B` | 标点 / 冲突地区高亮（**只作形状**）|
| `gold` | `#B8923E` | 我方 / 友方标记（**只作形状**）|
| `cool-gray` | `#7A8A9E` | 中性灰（次级文字、说明）|

### 2.1 对比度

下表由 `python skills/douyin-pro/scripts/audit_pack_contrast.py news-world` 按 §2 色板原值复算，改色板必须重跑它。
判读线：正文 4.5 / 大字 3.0（画布 1080 宽下 1cqw=10.8px，≥24px ≈ ≥2.22cqw 算大字）。

| 组合 | 比值 | 判定 |
|---|---|---|
| paper / navy | 15.46 | ✓ 任意字号 |
| crimson / navy | 3.14 | ✓ 仅大字档（7cqw 数据数字合法；正文线 4.5 不过 → 小字一律 paper）|
| gold / navy | 5.88 | ✓ 数学过正文线，但按法则 gold 只作标记形状 |
| lat / navy | 3.27 | ✓ 仅大字档，按法则 lat 只作地图细线与点位 |

> **强制规则**：lat / crimson / gold 永远只作地图细线、点位标记，不作正文文字。

---

## 3. 字阶

| 位 | 字体 | 字号 | 字重 | 其他 |
|---|---|---|---|---|
| 眉标 | `"JetBrains Mono", monospace` | 2.6cqw | 700 | "国际 / 战况 / 边境" |
| 主标题 | `"HF CJK", sans-serif` | 8cqw | 800 | paper，line-height 1.18 |
| 国名 / 地名 | `"JetBrains Mono", monospace` | 4cqw | 700 | paper，全大写或地区符号 |
| 屏句 | `"HF CJK"` | 4.4cqw | 400 | 88cqw 盒两行封顶 |
| 数据 | `"JetBrains Mono", monospace` | 7cqw | 700 | crimson（染大字数字）|
| 图说 | `"HF CJK", italic` | 3cqw | 400 | cool-gray |
| 经纬标记 | `"JetBrains Mono", monospace` | 2.4cqw | 700 | lat 色 |

- 国际型必须有等宽体（等宽 = 战报 + 经纬度）。
- 拉丁显示族写裸族名。中文族由每个版式自带 `@font-face` + `local()` 六连。

---

## 4. 版面法则

1. **内容只占顶部 80%**：底部 20cqh 留给字幕。
2. **首镜必出现经纬白地图轮廓**：简化世界轮廓 / 地区轮廓作为开场。
3. **每镜必带地理位置**：国 / 地区 / 城市三级粒度任一。
4. **数据可染 crimson**：跨国数据（GDP / 死亡数 / 移民数）大字可染 crimson。
5. **我方 / 友方标 gold，冲突标 crimson**：地图上的双标点系统（如同色版不同形状）。
6. **经纬线 lat 作背景**：所有地图背景必带 lat 色细线作经纬网。
7. **被 GSAP 引用的元素必须有 `id`**（继承 news-coral 法则 9）。
8. **带 background 的片块只做 scaleX 擦入**（继承 news-coral 法则 8）。

---

## 5. 动量预算

```
INTRO_END = 1.5     // 地图新闻入场中等（要看地图）
MIN_DRIFT = 0.7     // 地图漂移中等（要点亮 → 移动 → 静止）
driftStart = max(0, min(INTRO_END, slot - MIN_DRIFT))
driftDur   = max(MIN_DRIFT, slot - driftStart)
```

---

## 6. 地面清单与计划版式

| layout | 地面 | 文字色 | lat / crimson / gold 的出场方式 |
|---|---|---|---|
| `hook`（开篇世界轮廓）| navy | paper | 经纬白地图轮廓 + lat 经纬线 |
| `map`（地图 + 标点）| navy | paper | 国/地区标点 crimson / gold |
| `region`（地区放大）| navy-soft | paper | 地图局部 + 数据 crimson |
| `stat`（数字要点）| navy | paper / crimson | 大数字 crimson |
| `closer`（末镜）| navy | paper | 顶部 lat 书挡 + 经纬线 |

**单地面 pack**：全程 navy；地图区切 navy-soft 做二级层。

---

## 7. 计划 composition 文件

```
news-world/
├── frame.md
├── host.html
└── compositions/
    ├── hook.html   nc-world-hook   世界轮廓 + 经纬白
    ├── map.html    nc-world-map    地图 + 标点
    ├── region.html nc-world-region 地区放大
    ├── stat.html   nc-world-stat   数字要点
    └── closer.html nc-world-closer 末镜
```

---

## 8. 与 news-coral 的关键差别

| 维度 | news-coral | news-world |
|---|---|---|
| 主色 | 珊瑚 #E85D5D | 深海军蓝 #0E1B36 |
| 字体 | 衬线 + 无衬线 | 全无衬线 + JetBrains Mono 等宽 |
| 节奏 | 0.6 漂移 | 0.7 漂移（稍慢，看地图）|
| 视觉气质 | 火带 + 故事感 | 海图 + 战情 briefing |
| 适用稿件 | 故事 / 反转 | 国际 / 战况 / 地理 |
