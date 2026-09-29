---
name: news-collect
description: 零成本热点采集：百度热搜 board API + feedx 中文媒体 RSS，一条命令把"今天什么在热"落成选题线索 JSON，喂给 news-workflow 步骤 0。stdlib-only，无 key、无付费、不占端口；产出是线索，不是已核实事实。
version: 1.0.0
when_to_use: route=news 需要热点候选清单时（选题的前置输入）；用户自己带来了素材就不用它
status: active
tags:
- news
- hot-topic
- collect
- rss
- zero-cost
domain: news
category: news.research
---

# 零成本热点采集（news-collect）

把「采集热点」从人工粘贴变成一条命令，并且**一分钱不花**：只用标准库（`urllib` / `json` /
`xml.etree`），不需要 API key、不需要装服务、不启端口。

## 1. 用途与边界

| 是 | 不是 |
|---|---|
| 选题**线索**清单（标题 + 链接 + 热度 + 出处） | 事实来源 —— 每条线索进渲染前仍必须过 `fact-check`（硬门禁） |
| news-workflow **步骤 0 的输入** | 步骤 0 的裁决者 —— 选哪条仍然由人/工作流定 |
| 每天可重跑的采集器 | 爬虫框架 —— 不做翻页、不做正文抓取、不存历史库 |

`--print` 打出来的表给人扫一眼用；下游读的是 JSON 文件，字段见 §4。

## 2. 为什么不直接用 `hot-topic-content-maker` 的热榜

`hot-topic-content-maker` 的「读热榜」走 Beatra 付费额度（其 `references/trend-lookup.md`
文档标价：`social.douyin.hot_search.list` 6 credits，抖音/小红书按话题搜索 **60** credits；
实时价格以 `beatra.social.tools.get` 为准）。本路线的约束是**零云费/零付费创作**，
所以采集层自己写；选题裁决、脚本、渲染、发布仍走原链路不变。

需要抖音站内榜（百度/媒体 RSS 覆盖不到的那部分）时，用 §6 的自建 DailyHotApi，
依旧免费——只是要你自己起一个服务。

## 3. 快速开始

```bash
# 默认：百度热搜 + 三个 RSS 源全跑，写 .harness-news-runtime/hotboard/<date>.json
python skills/news-collect/scripts/collect.py

# 每源截断 + 顺带打表
python skills/news-collect/scripts/collect.py --limit 12 --print

# 只要"最新"：丢掉 pubDate 早于 3 天的 RSS 条目（见 §5 陈旧度实测）
python skills/news-collect/scripts/collect.py --max-age-days 3

# 只跑一个源
python skills/news-collect/scripts/collect.py --sources baidu
python skills/news-collect/scripts/collect.py --sources rss
```

全量参数看 `python skills/news-collect/scripts/collect.py --help`。

## 4. 产物结构（2026-09-29 实测输出，非示意）

```json
{
  "collected_at": "2026-09-29T12:25:45+08:00",
  "date": "2026-09-29",
  "cost": "zero",
  "note": "选题线索，不是已核实事实；进渲染前必须过 fact-check",
  "sources": [
    {"name": "baidu-realtime", "kind": "board", "url": "https://top.baidu.com/api/board?...", "count": 30},
    {"name": "rss", "kind": "rss", "url": "thepaper,zaobao,bbc-zh", "count": 60}
  ],
  "failures": [],
  "feed_stats": {
    "thepaper": {"items": 20, "max_age_days": 288.0},
    "zaobao": {"items": 20, "max_age_days": 39.4},
    "bbc-zh": {"items": 20, "max_age_days": 3.9}
  },
  "count": 80,
  "items": [
    {"rank": 1, "title": "Tiffany中国区负责人致歉", "url": "https://m.baidu.com/s?word=...", "hot": "", "is_top": false, "source": "baidu-realtime"},
    {"rank": 1, "title": "FBI遭黑客入侵起底 特工们的恐惧与愤怒", "url": "https://www.bbc.com/zhongwen/...", "hot": "", "published": "Tue, 29 Sep 2026 00:13:02 +0000", "age_days": 0.2, "source": "bbc-zh"}
  ]
}
```

读这个文件时注意四件实测出来的事：

- **`sources[].name` 和 `items[].source` 不是一套值域，不能 join**。`sources` 是端点组（`baidu-realtime` / `rss`），
  `items[].source` 是具体源（`baidu-realtime` / `thepaper` / `zaobao` / `bbc-zh`）。要按源统计用 `items[].source` 或 `feed_stats`。
- **`sources[].count` 求和(90) > `count`(80)**：前者是去重前，`count` 是标题去重（去标点后比较）之后。别把两者当成同一个数。
- **`hot` 恒为空字符串** —— 百度 `platform=wise` 榜的响应里根本没有 `hotScore`/`hot` 字段（实测 80/80 条为空）。
  别写排序逻辑去依赖它；热度信号只能用榜内 `rank`。RSS 本来也无热度。
- **置顶条目 `rank` 为 `null`**（实测 `is_top: true` 恰好 1 条，就是它 `rank` 为 null）。
  置顶 ≠ 第一名，别当脏数据过滤掉，也别把 null 参与排序。
- RSS 条目额外带 `published`（RFC 822 原文）与 `age_days`（距采集时刻天数，解析不了为 `null`）。
- 路径按日期命名，被 `.gitignore` 忽略（`.harness-news-runtime/` 整域不入库）。

## 5. 源清单（2026-09-29 本机实测，无 key）

**默认启用（实测 200 且正文非空）**

| 源 | 端点 | 说明 |
|---|---|---|
| `baidu` | `https://top.baidu.com/api/board?platform=wise&tab=realtime` | 返回 JSON。**层级是 `data.cards[].content[].content[]`** —— 中间层是分组，不是条目行；只取一层会得到 0 条。实时榜，无 pubDate 概念 |
| `rss` | `https://feedx.net/rss/{thepaper,zaobao,bbc}.xml` | 澎湃新闻 / 联合早报 / BBC 中文。`bbc-zh` 对应文件名 `bbc.xml` |

**RSS 镜像的新鲜度逐源差异极大**（2026-09-29 实测，`--limit 12` 那次的 `feed_stats`）：

| feed | 最旧条目距采集 | 判定 |
|---|---|---|
| `bbc-zh` | 1.7 天 | 真·当天，可直接当今日热点线索 |
| `zaobao` | 38.9 天 | 停在 8 月下旬 |
| `thepaper` | 287.9 天 | 停在 2025-12，**这个源的"最新"是 9 个多月前** |

所以：`--limit` 是**每个 feed 的上限**，不是合并后的上限（改成合并截断时实测到 bug —— 陈旧源会把唯一新鲜的 `bbc-zh` 挤成 0 条）；
每次运行都在 stderr 打 `~ <feed>: 最旧条目 N 天前`；要只要新的就加 `--max-age-days 3`（实测该次：thepaper/zaobao 各 20 条全过滤、
bbc-zh 过滤 6 条留 10 条，两个全灭的源各记一行 `failures`，但因 baidu+bbc-zh 仍有条目 → 退出码 0）。
**默认不过滤**是刻意的：整源滞后时全删会让它看起来像"源挂了"，而它其实是能追溯的历史素材。

**实测不可用，别加回默认**（加进去只会让每次采集白吃一个 `failures` 行）

| 端点 | 现象 |
|---|---|
| `api-hot.imsyy.top`（DailyHotApi 公共实例） | 本机 DNS 解析失败 → 降级为 `--base-url` 自建选项 |
| `tophub.today` | 503 |
| `rsshub.app` | 403 |
| `api.vvhan.com` | DNS 失败 |
| 微博 `ajax.../realtime` | 403（要 cookie/签名） |
| 知乎 `api/v3/conten.../hot` | 401 |
| `feedx.net/rss/{weibo,xinhuanet,ithome,36kr,sspai,duanwu}.xml` | 404 |

想换/加 RSS：`--feeds name=url,name=url`（不用改代码）。

## 6. 自建 DailyHotApi（可选，仍然免费）

公共实例解析不到，所以不是默认路径。要微博/知乎/B站榜单，就自己起一个：

```bash
# 交给你自己执行 —— agent 不启占端口的服务
git clone https://github.com/imsyy/DailyHotApi && cd DailyHotApi && npm i && npm run start
```

服务起来后：

```bash
python skills/news-collect/scripts/collect.py --sources baidu,rss,dailyhot \
  --base-url http://127.0.0.1:6688 --dailyhot-types weibo,zhihu,douyin
```

## 7. 失败策略（不静默）

| 情形 | 行为 | 退出码 |
|---|---|---|
| 部分源失败 | 正常写文件，失败逐条进 `failures` + stderr `!` 行 | 0 |
| 单源抓取成功但零条目 | 记成该源失败（接口改版的信号），不假装成功 | — |
| 某源条目被 `--max-age-days` 全过滤 | `failures` 记「该源滞后」，`feed_stats` 记 `dropped`；其他源仍有条目 → 照常写 | 0 |
| **所有源都失败（零线索）** | 打印每条错误，**不覆盖**上一次榜单（写成空榜会让下游以为今天真没热点） | 1 |

两条都是实测的（不接管道跑，`$?` 才是 python 的而不是 `tail` 的）：默认跑 `EXIT=0` 写 80 条；
构造全失败场景 `EXIT=1` 且旧榜单 `count` 保持 44 不变 —— 保留保证成立。

## 8. 接入工作流

`skills/news-workflow/SKILL.md` 步骤 0 先跑本采集器拿候选，再做选题裁决；
裁决结果写 `routes/news/MEMORY.md` 的 `topics[]`（`id + title + source + status: researching`），
`source` 建议写成 `百度热搜榜 #N（news-collect 采集于 YYYY-MM-DD）` 这种可回溯形式。

本 skill 不改变任何下游门禁：`fact-check` 仍是硬门禁，Path B 渲染仍无条件产出 AIGC 标识。

## 9. 已知限制

- **`hot` 对所有源都恒为空**（百度 `platform=wise` 响应里没有 `hotScore`，RSS 本来也没有）→ 没有真热度值，
  能用的排序信号只有榜内 `rank`（百度）与 feed 顺序（RSS）。要真热度数字得换源，别在字段上编逻辑。
- **百度条目的 `url` 是 `m.baidu.com/s?word=<标题>` 搜索页，不是原文页**（实测）→ 进 `fact-check` 时
  不能把它当出处链接，仍需按标题定位到具体媒体原文。
- 不做正文抓取，只有标题 + 链接；要正文再单独走网页工具，别塞进这个脚本。
- 不翻页、不做"今天 vs 昨天"的榜变化检测 —— 每天一份 `<date>.json` 是快照，没有 diff 语义。
- 采集时间取本机时区（`datetime.now().astimezone()`），跨天/跨时区不合并历史文件。
- 百度接口无版本承诺，改版的表现是「解析成功但零条目」→ 已抛 `ValueError` 并计入失败源。
- feedx 是第三方镜像：源活着不代表内容新（见 §5），别把"抓到 20 条"当"20 条今天的新闻"。
