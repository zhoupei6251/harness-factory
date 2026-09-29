#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""news-collect · 零成本热点采集器（stdlib only，无 key、无付费、不占端口）。

用途：把"当天什么在热"从人工粘贴变成一条命令，产出选题线索清单，喂给
skills/news-workflow 的步骤 0。它**不是**事实核查——采集到的标题一律按
待验证线索处理，进 Step 4 前仍必须过 fact-check 硬门禁。

两个默认可用源（2026-09-29 本机实测，无需任何部署）：
  baidu  百度热搜实时榜  https://top.baidu.com/api/board?platform=wise&tab=realtime
  rss    feedx 中文媒体 RSS 镜像（澎湃新闻 / 联合早报 / BBC 中文）

RSS 镜像的新鲜度**逐源差异极大**（同日实测：bbc-zh 当天、zaobao 停在 8-22、
thepaper 停在 2025-12-16），所以每条带 age_days，输出里有 feed_stats；
只挑"最新最热"时加 --max-age-days 3。百度热搜是实时榜，无 pubDate 概念。

可选第三源：自建 DailyHotApi（--base-url）。公共实例 api-hot.imsyy.top 本机
DNS 解析失败，所以它不是默认路径，只在你自己起了服务时才用。

用法：
  python skills/news-collect/scripts/collect.py                      # 默认源全跑
  python skills/news-collect/scripts/collect.py --limit 15           # 每源截断
  python skills/news-collect/scripts/collect.py --sources baidu      # 只跑榜
  python skills/news-collect/scripts/collect.py --sources rss        # 只跑 RSS
  python skills/news-collect/scripts/collect.py --max-age-days 3     # 丢陈旧条目
  python skills/news-collect/scripts/collect.py --base-url http://127.0.0.1:6688 \\
      --dailyhot-types weibo,zhihu                                   # 自建 API
  python skills/news-collect/scripts/collect.py --print              # 顺带打表

产物：.harness-news-runtime/hotboard/<YYYY-MM-DD>.json（按 --out 覆盖）
退出码：0 至少一条线索（已写文件）；1 所有源都失败（错误逐条打印，**不覆盖**上一次榜单）。
"""

import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
)

# 百度热搜：一个接口给多张卡（实时榜 + 分类榜），全部拍平成同一结构。
BAIDU_BOARD_URL = "https://top.baidu.com/api/board?platform=wise&tab=realtime"

# feedx 是 RSS 镜像；这三条是 2026-09-29 实测 200 且正文非空的源。
# 404 的（weibo / xinhuanet / 36kr / ithome / sspai / duanwu）不要加回来——
# 加了每次采集都白吃一个 error 行。
RSS_FEEDS = {
    "thepaper": "https://feedx.net/rss/thepaper.xml",   # 澎湃新闻
    "zaobao": "https://feedx.net/rss/zaobao.xml",       # 联合早报
    "bbc-zh": "https://feedx.net/rss/bbc.xml",          # BBC 中文
}

DEFAULT_OUT_DIR = os.path.join(".harness-news-runtime", "hotboard")


def _fetch(url, timeout, extra_headers=None):
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def _clean(text):
    if not text:
        return ""
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text))).strip()


def _age_days(pubdate, now):
    """RSS pubDate（RFC 822）→ 距采集时刻的天数；解析不了返回 None。

    返回 None 表示"判断不了新旧"，调用方按**保留**处理——宁可留一条日期脏数据的
    线索，也不要因为解析失败就把可能正在热的东西静默删掉。
    """
    if not pubdate:
        return None
    try:
        when = parsedate_to_datetime(pubdate)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=dt.timezone.utc)
    return round((now - when).total_seconds() / 86400, 1)


def collect_baidu(timeout):
    """百度热搜 → [{rank,title,url,hot}]。结构变了就抛，由调用方记成该源错误。

    实测（2026-09-29, platform=wise&tab=realtime）层级是
    data.cards[].content[].content[] —— 中间那层是"分组"，不是条目行。
    只按 cards[].content[] 取会拿到 1 个分组、0 条标题，所以必须下钻一层。
    """
    payload = json.loads(_fetch(BAIDU_BOARD_URL, timeout))
    if not payload.get("success"):
        raise ValueError("baidu board 返回 success=false")
    items = []
    for card in payload["data"]["cards"]:
        for node in card.get("content") or []:
            # node 既可能是分组 {content: [...]}，也可能直接是一条 {word, url}
            rows = node.get("content") if isinstance(node.get("content"), list) else [node]
            for row in rows:
                title = _clean(row.get("word") or row.get("title") or "")
                if not title:
                    continue
                items.append(
                    {
                        "rank": row.get("index"),
                        "title": title,
                        "url": row.get("url") or row.get("rawUrl") or "",
                        "hot": row.get("hotScore") or row.get("hot") or "",
                        "is_top": bool(row.get("isTop")),
                    }
                )
    if not items:
        raise ValueError("baidu board 解析成功但零条目（接口改版？）")
    return items


def collect_rss(timeout, feeds=None, limit=30, max_age_days=None):
    """RSS 多源合并 → 同一结构，source 字段标出来自哪个 feed。

    `limit` 是**每个 feed** 的上限，不是合并后的上限。原先按合并截断有实测 bug：
    --limit 12 时 thepaper(20 条) + zaobao(16 条) 已占满 36 的额度，排在最后的
    bbc-zh 一条也进不了结果 —— 而被挤掉的恰好是当天唯一新鲜的源。

    新鲜度（2026-09-29 实测，feedx 镜像）：bbc-zh = 当天，zaobao 停在 8 月，
    thepaper 停在 2025-12。所以每条打 `age_days`，并把各源最旧条目年龄报进 `feed_stats`；
    默认不删（整源滞后时删光会被误判成"源挂了"），传 `--max-age-days N` 才过滤。
    pubDate 解析不了的条目一律保留 —— 判断不了新旧不等于过期。
    """
    now = dt.datetime.now().astimezone()
    out = []
    errors = []
    feed_stats = {}
    for name, url in (feeds or RSS_FEEDS).items():
        try:
            root = ET.fromstring(_fetch(url, timeout).encode("utf-8", "replace"))
        except Exception as exc:  # 单个 feed 挂掉不拖垮整次采集，但必须留痕
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
            continue
        rows = []
        for node in root.iter("item"):
            title = _clean(node.findtext("title"))
            link = (node.findtext("link") or "").strip()
            if not title:
                continue
            pub = (node.findtext("pubDate") or "").strip()
            rows.append(
                {
                    "rank": None,
                    "title": title,
                    "url": link,
                    "hot": "",
                    "published": pub,
                    "age_days": _age_days(pub, now),
                }
            )
        if not rows:
            errors.append(f"{name}: 抓取成功但零条目")
            continue
        rows = rows[:limit]
        ages = [r["age_days"] for r in rows if r["age_days"] is not None]
        if ages:
            feed_stats[name] = {"items": len(rows), "max_age_days": max(ages)}
        if max_age_days is not None:
            keep = [r for r in rows if r["age_days"] is None or r["age_days"] <= max_age_days]
            if name in feed_stats and len(keep) < len(rows):
                feed_stats[name]["dropped"] = len(rows) - len(keep)
            rows = keep
            if not rows:
                errors.append(f"{name}: {max_age_days} 天内无条目，已全部过滤（该源滞后）")
                continue
        for i, row in enumerate(rows, 1):
            row["rank"] = i
            row["source"] = name
        out.extend(rows)
    return out, errors, feed_stats


def collect_dailyhot(base_url, types, timeout, limit=30):
    """自建 DailyHotApi：GET {base}/{type}。公共实例不作默认（本机 DNS 解析不到）。"""
    out = []
    for t in types:
        url = f"{base_url.rstrip('/')}/{t}"
        payload = json.loads(_fetch(url, timeout))
        rows = (payload.get("data") or [])[:limit]
        for i, row in enumerate(rows, 1):
            title = _clean(row.get("title") or row.get("word") or "")
            if not title:
                continue
            out.append(
                {
                    "rank": i,
                    "title": title,
                    "url": row.get("url") or row.get("mobileUrl") or "",
                    "hot": row.get("hot") or "",
                    "source": t,
                }
            )
    return out


def dedup(items):
    seen, kept = set(), []
    for row in items:
        key = re.sub(r"[\W_]+", "", row["title"])
        if not key or key in seen:
            continue
        seen.add(key)
        kept.append(row)
    return kept


def main():
    ap = argparse.ArgumentParser(description="零成本热点采集（百度热搜 + feedx RSS）")
    ap.add_argument("--sources", default="baidu,rss",
                    help="逗号分隔：baidu / rss / dailyhot（默认 baidu,rss）")
    ap.add_argument("--limit", type=int, default=30, help="每源最多取多少条（默认 30）")
    ap.add_argument("--timeout", type=float, default=15.0, help="单请求超时秒（默认 15）")
    ap.add_argument("--base-url", default=None, help="自建 DailyHotApi 地址（需 --sources 含 dailyhot）")
    ap.add_argument("--dailyhot-types", default="weibo,zhihu,douyin",
                    help="DailyHotApi 榜单类型，逗号分隔")
    ap.add_argument("--feeds", default=None,
                    help='覆盖 RSS 源，格式 name=url,name=url（默认见 RSS_FEEDS）')
    ap.add_argument("--max-age-days", type=float, default=None,
                    help="丢弃 pubDate 早于 N 天的 RSS 条目（默认不丢，只在 feed_stats 里报陈旧度）")
    ap.add_argument("--out", default=None, help=f"输出 JSON 路径（默认 {DEFAULT_OUT_DIR}/<date>.json）")
    ap.add_argument("--print", dest="do_print", action="store_true", help="打印前 20 条")
    args = ap.parse_args()

    feeds = RSS_FEEDS
    if args.feeds:
        feeds = dict(p.split("=", 1) for p in args.feeds.split(","))

    sources, items, failures, feed_stats = [], [], [], {}
    wanted = [s.strip() for s in args.sources.split(",") if s.strip()]

    for name in wanted:
        try:
            if name == "baidu":
                rows = collect_baidu(args.timeout)[: args.limit]
                for r in rows:
                    r.setdefault("source", "baidu-realtime")
                sources.append({"name": "baidu-realtime", "kind": "board",
                                "url": BAIDU_BOARD_URL, "count": len(rows)})
            elif name == "rss":
                rows, errs, feed_stats = collect_rss(args.timeout, feeds,
                                                max_age_days=args.max_age_days,
                                                limit=args.limit)
                sources.append({"name": "rss", "kind": "rss",
                                "url": ",".join(feeds), "count": len(rows)})
                failures += [f"rss/{e}" for e in errs]
            elif name == "dailyhot":
                if not args.base_url:
                    raise ValueError("dailyhot 需要 --base-url（自建实例；公共实例本机解析不到）")
                types = [t.strip() for t in args.dailyhot_types.split(",") if t.strip()]
                rows = collect_dailyhot(args.base_url, types, args.timeout, limit=args.limit)
                sources.append({"name": "dailyhot", "kind": "api",
                                "url": args.base_url, "count": len(rows)})
            else:
                raise ValueError(f"未知源 {name!r}（可用：baidu / rss / dailyhot）")
            items.extend(rows)
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")

    items = dedup(items)
    now = dt.datetime.now().astimezone()
    doc = {
        "collected_at": now.isoformat(timespec="seconds"),
        "date": now.date().isoformat(),
        "cost": "zero",
        "note": "选题线索，不是已核实事实；进渲染前必须过 fact-check",
        "sources": sources,
        "failures": failures,
        "feed_stats": feed_stats,
        "count": len(items),
        "items": items,
    }

    out_path = args.out or os.path.join(DEFAULT_OUT_DIR, f"{doc['date']}.json")

    if not items:
        # 零条目 = 全部源失败。这时**不覆盖**上一次成功的榜单文件：
        # 采集是每天重跑的，把"网络抖了一下"写成一份空榜，比不写更糟——
        # 下游会以为今天真的没有热点。
        for f in failures:
            print(f"  ! {f}", file=sys.stderr)
        print(f"[news-collect] 所有源都失败，未写 {out_path}（保留上一次榜单）—— 按硬规则不静默，退出码 1",
              file=sys.stderr)
        return 1

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)

    print(f"[news-collect] 写入 {out_path} · 线索 {len(items)} 条 / 成功源 {len(sources)} 个")
    for s in sources:
        print(f"  ✓ {s['name']}: {s['count']} 条")
    for f in failures:
        print(f"  ! {f}", file=sys.stderr)
    for name, info in feed_stats.items():
        # feedx 镜像的陈旧度按源实测差异很大（见 SKILL.md §5），必须打出来：
        # 否则下游把 2025-12 的旧稿当"今天的热点"。
        dropped = info.get("dropped")
        tail = f"，本次过滤 {dropped} 条" if dropped else "，未过滤（要过滤用 --max-age-days）"
        print(f"  ~ {name}: 最旧条目 {info['max_age_days']} 天前{tail}", file=sys.stderr)

    if args.do_print:
        for row in items[:20]:
            # 置顶条目没有 index（实测 baidu isTop=1 时 rank=None），打表用 "-" 占位
            print(f"  [{row['source']}] {row['rank'] if row['rank'] is not None else '-'}. {row['title']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
