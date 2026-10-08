#!/usr/bin/env python3
"""判据 4 的图片层: 从 Wikimedia Commons 公开 API 取**授权可商用**的真照片。

为什么要有这个模块: t001-v3 的联络表逐镜看下来, 每一帧都是纯文字 (渲染元数据里
``imageCount: 0`` 是机器证据), 而"每镜至少一帧非纯文字"是判据 4。补这个缺口只有两条路:
要么 AI 生图 (用户限定"只用免费的", 且生图会把新闻事实画成不存在的东西 —— 双重否决),
要么用**已有授权的真照片**。Commons 是免密钥、免账号、可商用的图库, 于是选它。

三条硬法则 (都由 path_b_selftest 的纯函数断言钉住):

1. **授权闸**: 只放行「公有领域 / CC0 / 纯 CC BY」。BY-SA(相同方式共享)、BY-NC(非商业)、
   BY-ND(无衍生)、GFDL **一律拒用** —— 实拍结果显示"常德"检索结果的第二条就是
   ``CC BY-SA 3.0``, "有许可证"绝不等于"可以用": SA 会把整条成片(含 UI 与配音)
   套上传染性条款, GFDL 要求随附许可证全文, NC 直接禁商用。读不到授权字段同样拒用。
2. **取值优先级**: 查询词只认作者显式写的 ``image`` 键, 没有就回落到该镜 ``kicker``。
   **绝不从口播正文里"认出"地名** —— 本机没有地名词表, 认错了就是拿错的画面配真话。
3. **署名不许编**: 署名字符串只由 API 返回的 Artist / LicenseShortName 拼; 作者缺失写
   「未署名」, 不填一个看起来像真名的占位词, 也不把站点名冒充成作者。占位值要先归一
   (``normalize_artist``: 实测有 "Unknown author Unknown author" 这种模板重复展开),
   屏上截断必须落在**词边界**(``_trim_artist``: "Bureau"→"Burea…" 是造出一个新作者)。

网络层 (``resolve_shot_image``) 只在 ``--check-only`` 之外的真跑里走, 失败一律降级为
"这一镜没有照片"并打印原因 —— 渲染链不能因为图库抖动而停机。
"""

from __future__ import annotations

import html as html_mod
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

#: Commons 对匿名脚本请求的策略是"带标识的 UA 才放行", 空 UA / 默认 python-urllib 会吃 403。
#: **必须纯 ASCII**: HTTP 头只允许 latin-1 编码 —— UA 里写中文时 urllib 抛
#: UnicodeEncodeError, 表现是"每镜检索都失败然后没图", 极易被误读成"这个选题图库里没有"
#: (实测于 2026-09-29 首次联跑, 回归断言见 path_b_selftest.t_user_agent_is_header_safe)。
#: 中文查询词走的是 URL, 由 urlencode 百分号编码, 不受这条限制。
USER_AGENT = ("harness-news-runtime/1.0 (HyperFrames news-video local render; "
              "no user data; see skills/douyin-pro in the repository)")
API_URL = "https://commons.wikimedia.org/w/api.php"
REQUEST_TIMEOUT_SECONDS = 20
#: 一次检索最多打几次 API(1 次正常 + 1 次退避重试)。逐镜检索是**串行**请求, Commons 对
#: 匿名脚本偶发 429; 没有这一次重试, 一次限流就让整镜降级成无图, 而人只看见"没有图"。
#: 上限必须是常数 —— 无上限的重试会把一条 5 镜的片子变成对图库的 DoS。
API_ATTEMPTS = 2
#: 值得重试的状态码: 限流与网关/服务侧抖动。403/404 不在此列 —— 那是 UA 或资源问题,
#: 重试不会变好, 立即降级才能把真实原因打印出来。509 是带宽耗尽(Bandwidth Limited)。
RETRYABLE_HTTP_STATUSES = frozenset({429, 500, 502, 503, 504, 509})
#: 一次检索取几条候选: 太大浪费 API 时间, 太小会被前几条不合规的结果饿死。
DEFAULT_SEARCH_LIMIT = 8
#: 短边下限。地面在 1080×1920 上以 cover 铺满, 最坏情况短边要铺 1080px;
#: 720 起放大约 1.5 倍, 再小就会糊, 而糊会被地面纹理读成噪点(比不放图更难看)。
MIN_SHORT_EDGE = 720
#: 极端长宽比多为漫画条/多图拼版/全景扫描件, 不是单张照片, 铺底会得到一条被压扁的带子。
MAX_ASPECT_RATIO = 6.0
#: 缩略图目标宽度: 必须 >= MIN_SHORT_EDGE 才有意义; 1280 覆盖 1080 宽画面 + 少量裕度,
#: 又远小于常见原图(3000~8000px), 单张约 200~400KB。实测不写 iiurlwidth 时 thumburl 缺席。
THUMB_WIDTH = 1280
#: 下载字节上限: 超了就中止(防被一张 50MB 原图卡住整条渲染链)。
MAX_DOWNLOAD_BYTES = 6_000_000
RETRY_DELAY_SECONDS = 2.0

#: 拒用规则: (匹配式, 打给人看的理由)。顺序在放行规则**之前** —— "CC BY-SA" 里
#: 含 "CC BY", 先判放行就会把传染性授权放进成片。
REFUSED_LICENSE_RULES: tuple[tuple[str, str], ...] = (
    (r"share[ -]?alike|by[ -]sa\b|相同方式共享|署名[ -]相同", "相同方式共享(SA)会传染整条成片"),
    (r"non[ -]?commercial|by[ -]nc\b|非商业|禁止商业", "非商业(NC)不许商用发布"),
    (r"no[ -]?deriv|by[ -]nd\b|无衍生|禁演绎|禁止改编", "无衍生(ND): 调色/裁剪即衍生"),
    (r"gfdl|free documentation|自由文档", "GFDL 是文档许可, 要求随附许可证全文"),
    (r"all rights reserved|版权所有", "保留所有权利"),
    (r"fair[ -]?use|合理使用", "合理使用是抗辩不是许可"),
)
#: 放行规则: 命中任意一条即允许商用且不要求衍生作品同许可。
ALLOWED_LICENSE_RULES: tuple[tuple[str, str], ...] = (
    (r"public domain|公有领域|版权已过期", "公有领域"),
    (r"\bcc[ -]?0\b|cc[ -]?zero|cc0[ -]", "CC0 免授权"),
    (r"\bpd\b", "PD 标记"),
    # 纯署名许可: 后面不能紧跟 SA/NC/ND 后缀(上面已先判掉)
    (r"\bcc[ -]?by\b(?! ?(?:sa|nc|nd))|attribution[ -]?\d|署名[ -]?\d", "CC BY 仅需署名"),
)

_MATCH_CACHE: dict[str, re.Pattern[str]] = {}


def _compiled(pattern: str) -> re.Pattern[str]:
    """按模式串缓存编译结果(同一批正则在每镜每次检索里反复用)。"""
    key = pattern.lower()
    cached = _MATCH_CACHE.get(key)
    if cached is None:
        cached = re.compile(pattern, re.IGNORECASE)
        _MATCH_CACHE[key] = cached
    return cached


def meta_value(ext: dict, field: str) -> str:
    """取 ``extmetadata`` 里某个字段的纯文本值。

    API 有两种形态: ``{"value": …, "type": …}`` 与裸字符串(老文件确实这样返回),
    两种都要能吃下 —— 少一种就是"检出了图却读不到授权", 而读不到授权必须拒用。
    """
    raw = ext.get(field)
    if isinstance(raw, dict):
        raw = raw.get("value")
    if raw is None:
        return ""
    return str(raw).strip()


def strip_html(markup: str) -> str:
    """剥标签、解实体、去链接、并成一行 —— 署名要上屏, 任何 HTML 或裸 URL 都是缺陷。"""
    text = re.sub(r"<[^>]+>", " ", markup or "")
    text = html_mod.unescape(text)
    text = re.sub(r"https?://\S+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def license_verdict(license_short: str | None, usage_terms: str | None) -> tuple[bool, str]:
    """判这一条授权能不能用, 返回 ``(可用, 理由)``。

    理由一定要可打印: 降级时人要看见"为什么这张图被跳过了", 不然只会怀疑代码坏了。
    """
    blob = f"{license_short or ''} {usage_terms or ''}".strip()
    if not blob:
        return False, "读不到授权字段"
    for pattern, reason in REFUSED_LICENSE_RULES:
        if _compiled(pattern).search(blob):
            return False, reason
    for pattern, reason in ALLOWED_LICENSE_RULES:
        if _compiled(pattern).search(blob):
            return True, reason
    return False, "授权不在白名单(公有领域/CC0/CC BY)"


#: 屏上署名行的字数上限。lower-third 用 3.4cqw(约 37px)排, 24 字约 890px,
#: 在 1080 宽里留出左右 90px 余量; 超宽会顶进字幕禁入区或换行, 换行就把整条 chrome 撑歪。
SCREEN_ATTRIBUTION_MAX_CHARS = 24
#: 作者缺失时的屏上写法。不许填一个看起来像真名的占位词, 也不许拿站点名冒充作者。
ANONYMOUS_LABEL = "未署名"
#: 拉丁词的相关性门槛: 长度 < 4 的多为冠词/介词/缩写(a, of, in, un), 命中了也不说明相关。
LATIN_TOKEN_MIN = 4
#: 中文按二字内切块匹配: 地名/专名的最小稳定语义单位约两字(「常德」「湖南」);
#: 整段比较会把「湖南常德」与「常德市区」判成不相关(实测踩过的漏检)。
CJK_SHINGLE = 2
_RELEVANT_LABEL = "词面与查询相符"
_IRRELEVANT_LABEL = "标题与查询词无共同词面(可能是同名词或全文检索误召回)"


def query_tokens(query: str) -> tuple[list[str], list[str]]:
    """把查询词切成拉丁词与中文二字块两组(两组都不能空手判相关)。"""
    latin = [t.lower() for t in re.findall(r"[A-Za-z][A-Za-z0-9-]+", query or "")
             if len(t) >= LATIN_TOKEN_MIN]
    runs = re.findall(r"[一-鿿]+", query or "")
    shingles = [run[i:i + CJK_SHINGLE] for run in runs for i in range(len(run) - 1)]
    return latin, shingles


def _latin_word_hits(title: str, latin: list[str]) -> set[str]:
    """整词命中: 标题里独立成词的查询词(容忍复数 s)。

    为什么不子串: 实测(2026-09-29)查询 "money" 以子串命中消防队名
    LeFloreCounty**Money**VolFire —— CamelCase 连写里的 money 只是队名零件,
    不是画面主体, 上屏等于给"每月3700元"配了辆消防车。词边界两侧出现
    字母/数字即不算命中; 下划线当分隔符(文件名 money_volunteer 是真词组)。
    """
    blob = (title or "").lower()
    hits = set()
    for token in set(latin):
        if re.search(rf"(?<![a-z0-9]){re.escape(token)}s?(?![a-z0-9])", blob):
            hits.add(token)
    return hits


def relevance_score(title: str, query: str) -> int:
    """命中数: 标题里出现的不同查询词数量(去重后)。0 = 词面完全不相干。

    拉丁词按整词计(见 _latin_word_hits), 中文仍按二字块子串计。
    """
    latin, shingles = query_tokens(query)
    hits = _latin_word_hits(title, latin)
    hits.update(s for s in set(shingles) if s in (title or ""))
    return len(hits)


#: 中文多字块达到这个长度就算**独立证据**（2026-10-08 起）。
#: 起因: 二字块单独命中不再算数 —— 「现场数据」里的「现场」出现在
#: 「东航MU5735黑匣子寻获现场」标题中, 把 2022 年空难图配成了"现场数据"镜的配图。
#: 三字以上(地名/专名)稀有度高, 假命中概率低, 单独命中即可采信。
CJK_EVIDENCE_MIN = 3

#: 连续命中达到这个长度算**一条真证据**（2026-10-08）。
#: 为什么不能只数滑窗块: query_tokens 切的是**滑窗**，「湖南常德」= 湖南/南常/常德，
#: 而标题「常德市区」只含其中 1 块 —— 数块会把真命中误杀（实测踩过）。
#: 连续公共子串不看块的位置错位：「湖南常德」vs「常德市区」的最长公共子串是「常德」(2 字)，
#: 而「现场数据」vs「寻获现场」的公共子串也是「现场」(2 字) ——
#: 靠长度区分不了这两个, 所以还需要"该子串在查询里是否成词"这条额外判据
#: (见 relevance_ok: 2 字子串必须**与查询里的边界对齐**, 「现场」在「现场数据」开头对齐,
#:  而「现场数据」整串才是那次误召回的真正问题 —— 它只是栏目名, 不是画面描述)。
CJK_RUN_EVIDENCE_MIN = 2


def _longest_common_cjk_run(query: str, title: str) -> str:
    """查询与标题的最长连续公共子串（按字符）。无公共字符返回 ""。"""
    if not query or not title:
        return ""
    best = ""
    for i in range(len(query)):
        for j in range(len(query), i + len(best), -1):
            cand = query[i:j]
            if cand in title and len(cand) > len(best):
                best = cand
                break
    return best


def relevance_ok(title: str, query: str) -> tuple[bool, str]:
    """词面相关性闸。

    为什么必须有: 实跑「湖南常德」时 Commons 全文检索的第一条合规结果是西藏步甲虫的论文插图
    (CC BY 4.0, 尺寸也够)。授权闸放行、尺寸闸放行, 但把它当常德街景上屏 = **视觉假事实**,
    比不放图更糟。这里只做词面判定: 命中 0 个查询词就拒, 不做语义/图像识别(那需要付费 API)。

    **中文判据 2026-10-08 收紧**: 原口径「任意 1 个二字块命中即放行」太松 ——
    「现场」「数据」「中国」「北京」「市场」「发展」这类二字词会出现在任何一张无关图里。
    实跑 t002 时, 查询「现场数据」因标题含「寻获**现场**」二字, 把东航空难图放行了
    (授权 CC BY 3.0 合规、尺寸 961x720 合规, 三道闸只差词面这一道没拦住)。
    现在要求: 拉丁整词 ≥1 个, **或**中文连续公共子串 ≥3 字, **或**≥2 个二字块。

    已知边界: 中文查询词命中不了英文标题的文件(跨语言需要词表或翻译, 本机没有)。
    ⇒ 想要英文标题的图, 必须作者在分镜里显式写 ``"image": "Changde Hunan"``, 不许代码猜。
    """
    if not (query or "").strip():
        return False, "没有查询词, 无从判断相关性"
    latin, shingles = query_tokens(query)
    title = title or ""
    # 拉丁整词: 1 个就够(英文词本身稀有度高, 且已过 _latin_word_hits 的整词校验)
    if _latin_word_hits(title, latin):
        return True, _RELEVANT_LABEL
    hits = {s for s in set(shingles) if s in title}
    if not hits:
        return False, _IRRELEVANT_LABEL
    # 连续公共子串: 长串(≥3字, 地名/专名)单条即证据
    run = _longest_common_cjk_run(query, title)
    if len(run) >= CJK_EVIDENCE_MIN:
        return True, _RELEVANT_LABEL
    # 2 字串不够 —— 「现场数据」的「现场」会假命中东航空难图(实跑),
    # 而 2 字地名(「常德」)又必须能放行(t001 实跑靠它)。
    # 判据只能是**长度本身**: 2 字不足以证明相关性, 让它去配 3 字以上的查询词。
    # ⇒ 配中文图请写足 3 个字以上("湖南常德" 而非 "常德")。
    # ≥2 个独立二字块 = 中等证据(滑窗块会错位, 用数量兜)
    if len(hits) >= 2:
        return True, _RELEVANT_LABEL
    return False, (
        f"{_IRRELEVANT_LABEL}: 只命中常见二字块 {sorted(hits)}, 证据不足"
        f"（中文配图请给 ≥3 字查询词, 如 '湖南常德'; 2 字词如 '现场'/'数据' "
        f"会出现在任何无关图里）")

def cache_hit(manifest: dict, name: str, query: str) -> dict | None:
    """本地缓存只有在**同一镜 + 同一查询词**下才算命中。

    实测缺陷: 只按目标文件名判定缓存 ⇒ 作者改了 kicker 或换了选题但镜号不变时,
    上一版的图被静默复用, 画面配不上话还查不出原因。老清单(没有 query 字段)一律按失效处理。
    """
    entry = manifest.get(name) if isinstance(manifest, dict) else None
    if not isinstance(entry, dict):
        return None
    if entry.get("query") != query or not entry.get("source_url"):
        return None
    return entry


#: 作者字段里的**占位写法**(整串匹配)。命中即归一为空串 = 未署名。
#: 为什么必须是正则整串匹配而不是等值集合: 实测那幅 Changde PD 老照片的 Artist 模板
#: 展开成 ``Unknown author Unknown author``(同一模板串被重复展开两遍), 等值比较抓不到,
#: 屏上就成了「图：Unkno…」—— 像有个叫 Unkno 的人。见
#: path_b_selftest.t_artist_placeholder_never_becomes_a_fake_name。
_ANONYMOUS_RE = re.compile(
    r"unknown([ _-]+(author|photographer|artist|creator|source|owner))?"
    r"|anon(ymous)?|n/?a|none|null|no[- _]?name|uncredited"
    r"|佚名|未署名(作者)?|未署名摄影师|未知(作者|拍摄者|摄影师|来源)?"
    r"|不明(作者|来源)?|无|[-—.]+",
    re.IGNORECASE)


def normalize_artist(raw: str | None) -> str:
    """把 API 的 Artist 字段规整成"可以署名的真名"; 占位值返回空串(内部表示未署名)。

    三步: 剥 ``{{...}}`` 未展开模板 → 折叠被重复展开的同半截 → 整串匹配占位词表。
    真名里的 HTML 与链接由 :func:`strip_html` 负责, 署名上屏前必须剥净。
    """
    text = strip_html(re.sub(r"\{\{[^{}]*\}\}", " ", raw or ""))
    tokens = [t.strip("，,、;:.") for t in text.split()]
    if len(tokens) >= 2 and len(tokens) % 2 == 0:
        half = len(tokens) // 2
        if tokens[:half] == tokens[half:]:
            text = " ".join(tokens[:half])
    cleaned = text.strip()
    return "" if _ANONYMOUS_RE.fullmatch(cleaned) else cleaned


def normalize_page(page: dict) -> dict | None:
    """把一条 API 结果拍平成内部记录; 结构不合预期的条目返回 ``None``(不是抛异常)。"""
    infos = page.get("imageinfo") or []
    if not infos:
        return None
    info = infos[0]
    ext = info.get("extmetadata") or {}
    artist = normalize_artist(meta_value(ext, "Artist"))
    try:
        width, height = int(info.get("width") or 0), int(info.get("height") or 0)
    except ValueError:
        return None
    return {
        "title": str(page.get("title") or ""),
        "artist": artist,
        "license": meta_value(ext, "LicenseShortName"),
        "terms": meta_value(ext, "UsageTerms"),
        "width": width,
        "height": height,
        "image_url": info.get("url") or "",
        "thumb_url": info.get("thumburl") or "",
        "source_url": info.get("descriptionurl") or "",
    }


def passes_size_gate(record: dict) -> bool:
    """尺寸与长宽比闸: 短边够、且不是拼版式极端比例。"""
    width, height = record["width"], record["height"]
    if min(width, height) < MIN_SHORT_EDGE:
        return False
    return max(width / height, height / width) <= MAX_ASPECT_RATIO


def pick_candidate(pages: list[dict], query: str, log=print) -> dict | None:
    """三道闸(授权 → 尺寸 → 词面相关)全过的那条里, 取**命中最多**的; 全不合规返回 ``None``。

    为什么不"取第一条合规的": Commons 的相关度排序在中文查询词上很不可靠(实测把虫文插图排在
    常德之前), 而命中数是本地能算的最强相关性信号。并列时保留检索排序在前的那条。
    逐条打印跳过原因 ⇒ 一次跑就知道是该换词还是该接受降级。
    """
    best: dict | None = None
    best_score = 0
    for page in pages or []:
        record = normalize_page(page)
        if record is None:
            log(f"    · 跳过 {page.get('title', '?')}: 返回结构没有 imageinfo")
            continue
        ok, reason = license_verdict(record["license"], record["terms"])
        if not ok:
            log(f"    · 跳过 {record['title']}: 授权不可用({reason})")
            continue
        if not passes_size_gate(record):
            log(f"    · 跳过 {record['title']}: 尺寸不合"
                f"({record['width']}x{record['height']}, 短边下限 {MIN_SHORT_EDGE})")
            continue
        ok, reason = relevance_ok(record["title"], query)
        if not ok:
            log(f"    · 跳过 {record['title']}: {reason}")
            continue
        score = relevance_score(record["title"], query)
        if score > best_score:
            record["license_reason"] = reason
            record["relevance"] = score
            best, best_score = record, score
    return best


def image_query(overrides: dict, scene: dict) -> str | None:
    """这一镜的检索词来源: **只认作者显式写的 ``image``**。

    2026-10-08 实跑修正：旧实现是「显式 image > kicker > 没有」，
    结果 kicker 成了检索词 —— 而 kicker 是**排版元素**（栏目名），
    不是画面描述。实测 t002「尊界V800刹车踏板断裂」那一镜的 kicker 是
    「现场数据」，拿去 Commons 全文检索（``gsrsort=relevance``，中英语料错配）
    返回了「东航MU5735黑匣子寻获现场」—— **2022 年空难新闻图**。
    授权闸放行(CC BY 3.0)、尺寸闸放行(961x720)、词面闸也放行
    (标题里有「现场」二字，见 ``relevance_ok``), 三道闸同时失守。

    **kicker 没有语义依据当检索词** —— 要配图就写 ``"image": "V800 MPV"``,
    不写就降级为绘制地面（无图比错图好, 见模块原则）。

    ``image: false`` 仍然是作者说"这一镜不要照片"，优先级最高。
    """
    explicit = overrides.get("image") if isinstance(overrides, dict) else None
    if explicit is False:
        return None
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    # 2026-10-08: **不再回落到 kicker**（见上方实跑记录）
    return None


#: 屏上位置连作者名第一个整词都放不下时的指向语(完整出处一定在 credits.md 与简介里)。
CREDIT_POINTER_LABEL = "完整署名见简介"
#: 作者名里的词分隔符: 拉丁空格 + 中英标点。截断只允许停在这些位置之后。
_ARTIST_SEP_RE = re.compile(r"[\s，,、;；:：]+")
_CJK_RE = re.compile(r"[㐀-䶿一-鿿]")


def _trim_artist(artist: str, keep: int) -> str | None:
    """在 ``keep`` 个字位里截出作者名前缀; 截不出体面前缀返回 ``None``(改走指向语)。

    拉丁名**必须停在词边界**: 把 "Bureau" 削成 "Burea…" 等于凭空造出一个叫 Burea 的作者,
    改署名比不署名更糟(实测屏上出现过 「图：Unkno…」)。中文名没有词间空格, 按字截是
    正常排版, 不必退化。
    """
    if keep <= 0 or len(artist) <= keep:
        return artist if keep > 0 else None
    head = artist[:keep]
    if not _CJK_RE.search(head):
        ends = [m.end() for m in _ARTIST_SEP_RE.finditer(head)]
        if not ends:
            return None                              # 第一个整词都塞不进去
        head = head[:ends[-1]]
    head = re.sub(r"[\s，,、;；:：]+$", "", head)
    return head or None


def attribution_text(record: dict,
                     max_chars: int | None = SCREEN_ATTRIBUTION_MAX_CHARS) -> str:
    """屏上署名行: 只由 API 字段拼出, 作者缺失写「未署名」, 超长只削作者名。

    许可证名与前缀**永不缩** —— 缩掉许可证就不是合规署名了; 会被缩掉的只有作者名,
    且只能缩在词边界上。连一个整词都放不下时不硬截, 改成许可证 + 指向完整出处。
    """
    license_label = record.get("license") or "授权见来源页"
    artist = record.get("artist") or ANONYMOUS_LABEL
    line = f"图：{artist} · {license_label}"
    if max_chars is None or len(line) <= max_chars:
        return line
    # 省出的 1 个字位给省略号
    head = _trim_artist(artist, max_chars - len(f"图： · {license_label}") - 1)
    if head is None:
        return f"图：{license_label}｜{CREDIT_POINTER_LABEL}"
    return f"图：{head}… · {license_label}"


def full_credit(record: dict) -> str:
    """完整出处(进 ``credits.md`` 与视频简介): 作者全文 + 许可证 + 来源页链接, 不截断。"""
    artist = record.get("artist") or ANONYMOUS_LABEL
    license_label = record.get("license") or "授权见来源页"
    parts = [f"图：{artist}", license_label]
    if record.get("source_url"):
        parts.append(record["source_url"])
    return " · ".join(parts)


def search_params(query: str, limit: int = DEFAULT_SEARCH_LIMIT) -> dict:
    """拼检索参数(纯函数, 可离线断言)。

    ``filetype:bitmap`` 把 SVG/GIF 挡在外面(矢量图铺底会糊字, 动图不能进 ffmpeg 静帧);
    ``gsrnamespace=6`` 是 File 命名空间; ``iiurlwidth`` 换回缩放后的 thumburl —— 实测
    不带这个参数时 thumburl 缺席, 只能拉原图。
    """
    return {
        "action": "query",
        "format": "json",
        "smaxage": "0",
        "generator": "search",
        "gsrsearch": f"filetype:bitmap {query}",
        "gsrlimit": str(int(limit)),
        "gsrnamespace": "6",
        "gsrsort": "relevance",
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|size",
        "iiurlwidth": str(THUMB_WIDTH),
    }


def should_retry(exc: BaseException) -> bool:
    """这次异常值不值得再打一次 API(纯函数, 可离线断言)。

    判定顺序有意义: ``HTTPError`` 是 ``URLError`` 的子类, 必须先按状态码分流, 否则
    403/404 会被"网络类错误一律重试"那条收进去 —— 而鉴权失败重试一百次也不会变好,
    只会把每镜的降级时间拖长一倍。``json.JSONDecodeError`` 是 ``ValueError``: 不重试。
    """
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in RETRYABLE_HTTP_STATUSES
    # URLError(含超时/DNS) 与裸 OSError(连接被断) 都是可重试的传输类故障
    return isinstance(exc, OSError)


def api_get(params: dict, timeout: float = REQUEST_TIMEOUT_SECONDS, log=print) -> dict:
    """打 API 并解析 JSON, 只对 ``should_retry`` 认可的故障退避一次。

    最终异常一律向上抛给调用方决定降级, 这里不静默 —— 静默重试到成功为止会让人
    以为"图库很慢", 而真相可能是 UA 被拒。
    """
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                   "Accept": "application/json"})
    attempt = 0
    while True:
        attempt += 1
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (OSError, ValueError) as exc:      # URLError/HTTPError 都是 OSError 子类
            if attempt >= API_ATTEMPTS or not should_retry(exc):
                raise
            log(f"    · 第 {attempt} 次请求失败({type(exc).__name__}: {exc}), "
                f"{RETRY_DELAY_SECONDS}s 后重试一次")
            time.sleep(RETRY_DELAY_SECONDS)


def search_photos(query: str, limit: int = DEFAULT_SEARCH_LIMIT,
                  log=print) -> list[dict]:
    """检索并按 index 还原成相关度顺序的 page 列表(generator=search 的返回不按相关度排)。"""
    payload = api_get(search_params(query, limit), log=log)
    pages = list((payload.get("query") or {}).get("pages", {}).values())
    return sorted(pages, key=lambda p: p.get("index", 1 << 30))


def download(url: str, dest: Path, max_bytes: int = MAX_DOWNLOAD_BYTES, log=print) -> bool:
    """流式下载到 dest, 超限就删掉半截文件并返回 False。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    got = 0
    try:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response, \
                open(tmp, "wb") as sink:
            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                got += len(chunk)
                if got > max_bytes:
                    raise urllib.error.HTTPError(url, 413, "超过体积上限", {}, None)
                sink.write(chunk)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        log(f"    · 下载失败 {url}: {type(exc).__name__}: {exc}")
        tmp.unlink(missing_ok=True)
        return False
    tmp.replace(dest)
    return True


def resolve_shot_image(query: str, dest: Path, log=print) -> dict | None:
    """一镜一张: 检索 → 三道闸 → 下载缩略图到 dest, 返回带 ``local_path`` 的记录。

    任何一步不成都不停机: 返回 ``None``, 发射器降级到"绘制地面"那一层(它不依赖网络)。
    缓存判定见 ``cache_hit`` —— 查询词变了就必须重取, 只看文件名会复用上一版的图。
    """
    if dest.exists() and dest.stat().st_size > 0:
        cached = cache_hit(read_manifest(dest.parent, log=log), dest.name, query)
        if cached:
            log(f"    · 复用本地缓存 {dest.name}")
            return dict(cached, local_path=str(dest))
        log(f"    · {dest.name} 与当前查询词不匹配, 重新取图")
    try:
        pages = search_photos(query, log=log)
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        log(f"    · 检索失败({query}): {type(exc).__name__}: {exc} ⇒ 本镜降级为绘制地面")
        return None
    record = pick_candidate(pages, query, log=log)
    if record is None:
        log(f"    · 「{query}」没有授权/尺寸/相关性都合规的图 ⇒ 本镜降级为绘制地面")
        return None
    url = record["thumb_url"] or record["image_url"]
    if not url:
        log(f"    · {record['title']} 没有可用的图片地址 ⇒ 本镜降级为绘制地面")
        return None
    if not download(url, dest, log=log):
        return None
    record["local_path"] = str(dest)
    record["bytes"] = dest.stat().st_size
    record["query"] = query
    write_manifest(dest.parent, dest.name, record, log=log)
    log(f"    · 取图 {record['title']} ({record['width']}x{record['height']} → {dest.name}, "
        f"{record['bytes'] // 1024}KB, 命中 {record['relevance']} 词) 授权: {record['license']}")
    return record


MANIFEST_NAME = "media-manifest.json"


def read_manifest(media_dir: Path, log=print) -> dict:
    """读 ``media-manifest.json``: 文件名 → 出处记录(缓存判定与署名清单都靠它)。"""
    path = media_dir / MANIFEST_NAME
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log(f"    · 图片清单读不出({type(exc).__name__}: {exc}), 当作空清单")
        return {}
    return data if isinstance(data, dict) else {}


def write_manifest(media_dir: Path, name: str, record: dict, log=print) -> None:
    """写回一条(合并式, 不覆盖别镜的记录)。只存公开字段, 不含任何凭据。"""
    manifest = read_manifest(media_dir, log=log)
    manifest[name] = {k: record.get(k) for k in
                      ("query", "title", "artist", "license", "terms", "width", "height",
                       "source_url", "thumb_url", "license_reason", "relevance", "bytes")}
    (media_dir / MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
