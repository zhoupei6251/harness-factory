#!/usr/bin/env python3
"""path_b_build 的纯函数断言集（不需要 ffmpeg / 引擎 / 网络，可离线跑）。

仓库没有 Python 测试基建（根 pom.xml 只管 Java，skill 目录里也没有 pytest 配置），
所以这里自带 20 行 check() harness 与退出码：0 = 全绿，1 = 有失败并逐条打印。
它是 Harness 验证单里"证据"那一栏的命令:

    python skills/douyin-pro/scripts/path_b_selftest.py

覆盖的是判据 1/4/5/6 的可机检部分:
  判据 5(屏上整句 ≠ 口播句) 的全部结构保证 —— 屏句(onscreen)是整句型屏上位唯一来源;
  D1 的字幕几何两半(行宽 + 封顶两行 + 按时长切条);
  D2 的 stat 小标题法则; D5 的屏句长度/强调段/一条两屏句停机;
  判据 4(每镜至少一帧非纯文字) 的图片层法则 —— 授权闸 / 尺寸闸 / 取值优先级 / 署名合成
  (纯函数部分, 网络那一层由 --check-only 的真跑覆盖);
  判据 6 的字面可读层 —— 12 个 pack 的 frame.md 对比度表按色板原值复算(audit_pack_contrast)。
"""

import json
import os
import re
import sys
import tempfile
import urllib.error  # 只用来造 HTTPError/URLError 实例喂 should_retry(不打网络)
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import audit_pack_contrast as apc  # noqa: E402  (判据 6 的色板层: frame.md 对比度表复算)
import check_publishable as cpk  # noqa: E402  (发布闸门: 照台账核 ①②, ③ 的必带参数由它给)
import commons_media as cm  # noqa: E402  (判据 4 的图片层纯函数; 与 pb 同样必须先落地 sys.path)
import path_b_build as pb  # noqa: E402  (sys.path 必须先落地)

FAILURES: list[tuple[str, str]] = []


def check(name: str, fn) -> None:
    try:
        fn()
    except AssertionError as exc:
        FAILURES.append((name, str(exc) or "断言失败(无描述)"))
        print(f"  FAIL  {name}: {exc}")
    except Exception as exc:  # noqa: BLE001  测试里意外异常就是失败, 不许静默
        FAILURES.append((name, f"{type(exc).__name__}: {exc}"))
        print(f"  ERROR {name}: {type(exc).__name__}: {exc}")
    else:
        print(f"  ok    {name}")


def expect_error(fn, *args, **kw):
    """断言 fn 抛 EmitterError 并返回异常消息(供再检查文案里提到了什么)。"""
    try:
        fn(*args, **kw)
    except pb.EmitterError as exc:
        return str(exc)
    raise AssertionError(f"期望 EmitterError, 实际返回成功: {fn.__name__}{args}")


def base_ctx(**kw) -> dict:
    ctx = {"shot_no": 2, "shot_ordinal": "02", "slot_seconds": 8.0,
           "is_first": False, "is_last": False, "prev_ground_tone": None,
           "overrides": {}}
    ctx.update(kw)
    return ctx


PACK = pb.load_style_pack(pb.DEFAULT_STYLE)

#: 12 个模板各自的 pack 对象 (用于挨个过自检; 不存在则跳过 load, 标记为 partial)。
def _load_one_template(name):
    """单个模板的 pack; 未落地(host.html 缺 / 只有 placeholder 壳)则返回 None。

    `load_style_pack` 对"只有占位壳"的 pack 现在会抛 EmitterError (D7: 占位不是版式,
    宁可加载期停机), 所以这里必须同时接 OSError 类路径与 EmitterError —— 否则
    自检会在盘点 12 包时直接崩, 而不是老实报"这一包还没真版式"。
    """
    pack_dir = os.path.join(pb.TEMPLATE_ROOT, name)
    host_path = os.path.join(pack_dir, "host.html")
    if not (os.path.isdir(pack_dir) and os.path.isfile(host_path)):
        return None
    try:
        return pb.load_style_pack(name)
    except pb.EmitterError:
        return None

TEMPLATE_PACKS = {name: _load_one_template(name) for name in pb.ALL_TEMPLATES}
FRAME_ONLY_TEMPLATES = {name for name, pack in TEMPLATE_PACKS.items() if pack is None}
#: 已知"只有 frame.md, host/compositions 待落地" 的 pack 名 (frame-only 自检用)。


# ---------------- D1: 字幕几何（实测 ASS: 1080x1920 / 字号60 / 边64） ----------------
def t_caption_line_chars():
    # 可用宽 = 1080 - 2*int(1080*0.06) = 952; 952 // 60 = 15
    assert pb.caption_line_chars(1080, 1920) == 15


def t_short_cue_not_split():
    cues = pb.split_cue(0.0, 4.0, "社保账户从未清零", 15, 2)
    assert len(cues) == 1, cues
    assert cues[0][0] == 0.0 and abs(cues[0][1] - 4.0) < 1e-9, cues


def t_long_cue_split_contiguous():
    text = "他一直以为下岗之后要自己缴满社保才能领钱可是口袋里一分钱都没有只能先放着"
    cues = pb.split_cue(0.0, 6.0, text, 15, 2)
    assert len(cues) >= 2, cues
    assert cues[0][0] == 0.0, cues
    assert abs(cues[-1][1] - 6.0) < 1e-9, cues
    for a, b in zip(cues, cues[1:]):
        assert abs(a[1] - b[0]) < 1e-9, (a, b)
    for cue in cues:
        assert len(cue[2].split("\\N")) <= 2, cue
    assert "".join(c[2].replace("\\N", "") for c in cues) == text, cues


# ---------------- D2: stat 的小标题不许含自己的数字、不许粘句 ----------------
def t_stat_label_rejects_own_number():
    assert pb.stat_label("比42万更可惜的", "42万") is None


def t_stat_label_prefers_after_number():
    assert pb.stat_label("他每月有3700元养老金", "3700元") == "养老金"


def t_stat_label_single_side_not_glued():
    # 数字在句尾时只许取前半截, 且必须是可以独立读的一截
    assert pb.stat_label("账户累计42万, 他自己不知道", "42万") == "账户累计"


# ---------------- D5: 屏句（唯一合法的整句型屏上位） ----------------
def t_onscreen_length_limits():
    expect_error(pb.check_onscreen, "查一下", 1)                      # 4 字 < 下限
    expect_error(pb.check_onscreen, "一二三四五六七八九十一二三四五六七", 1)  # 17 字 > 上限
    whole, _ = pb.check_onscreen("没人告诉他", 1)                       # 5 字 = 下限
    assert whole == "没人告诉他"


def t_onscreen_accent_marker():
    whole, accent = pb.check_onscreen("今天查一下｜社保", 1)
    assert whole == "今天查一下社保" and accent == "社保", (whole, accent)


def t_onscreen_bad_marker_stops():
    msg = expect_error(pb.check_onscreen, "｜今天查一下社保账户余额", 1)
    assert "屏" in msg, msg                      # 停机文案必须说的是屏句


# ---------------- 输入解析: 屏行不进正文、一条两屏句要停机 ----------------
BEAT = """一个误会，困住半辈子
他一直以为，下岗后要自己缴满社保才能领钱；没钱，就干脆放弃。他没料到，30多年工龄系统一直记着。
屏: 没人告诉他，他一直没问
"""

# hook 版式的标题必须能给出一个**合法断点**(数字+单位 或 ｜), 所以测试里另备一个带数字的节拍。
HOOK_BEAT = """拾荒21年，账户里42万
他一直以为下岗之后要自己缴满社保才能领钱，可是口袋里一分钱都没有。
屏: 30多年工龄，系统一直记着
"""


def t_markdown_onscreen_line_parsed():
    scenes = pb.parse_input(BEAT)
    assert len(scenes) == 1, scenes
    scene = scenes[0]
    assert scene["onscreen"] == "没人告诉他，他一直没问", scene
    assert scene["onscreenAccent"] is None, scene
    assert "屏" not in scene["body"] and "没人告诉他" not in scene["body"], scene


def t_markdown_two_onscreen_lines_stop():
    expect_error(pb.parse_input, BEAT + "屏: 再来一条屏句就行了\n")


def t_json_onscreen_checked_too():
    payload = '[{"title": "拾荒21年", "body": "账户累计42万，他自己不知道。", ' \
              '"onscreen": "太短"}]'
    expect_error(pb.parse_input, payload)


# ---------------- 版式契约: story 只剩 领句 + 屏句 ----------------
STORY_IDS = {"kicker", "ordinal", "title", "onscreen", "tone", "slotSeconds"}


def t_story_contract_shape():
    ids = pb.contract_ids(PACK["layouts"]["story"])
    assert ids == STORY_IDS, f"story 契约变了: {sorted(ids)}"


def t_dead_derivers_removed():
    for gone in ("lead", "detail"):
        assert gone not in pb.DERIVERS, f"{gone} 已从 story 契约移除, 推导器是死代码"
    assert not hasattr(pb, "_story_clauses"), "story 不再靠分句数量竞选"
    assert not hasattr(pb, "scene_headline"), "标题不许从口播正文里偷第一句"
    assert not hasattr(pb, "looks_quoted"), "引文卡只认作者写的 quote, 不许自动认领整段"
    assert not hasattr(pb, "MIN_STORY_CLAUSES")


def t_story_needs_authored_title_and_onscreen():
    with_both = pb.parse_input(BEAT)[0]
    assert pb.missing_variables(PACK["layouts"]["story"], with_both, base_ctx()) == []
    no_onscreen = dict(with_both, onscreen=None, onscreenAccent=None)
    assert "onscreen" in pb.missing_variables(PACK["layouts"]["story"], no_onscreen, base_ctx())
    no_title = dict(with_both, title=None)
    assert "title" in pb.missing_variables(PACK["layouts"]["story"], no_title, base_ctx())


def t_story_screen_text_is_not_spoken():
    scene = pb.parse_input(BEAT)[0]
    values = pb.fill_variables(PACK["layouts"]["story"], scene, base_ctx())
    spoken = " ".join(scene["body"].split())
    assert values["onscreen"] == scene["onscreen"], values
    assert values["onscreen"] not in spoken, values        # 屏上不出现被念出来的整句
    for spoken_clause in pb.clauses(scene["body"]):
        assert spoken_clause not in values["onscreen"], (spoken_clause, values)
        assert values["onscreen"] not in spoken_clause, (spoken_clause, values)


def t_story_wins_before_catalog():
    # 有屏句的中段镜头: 作者是"要一句陈述", 不许被从句拼出来的三步清单抢走
    assert pb.choose_layout(PACK, pb.parse_input(BEAT)[0], base_ctx()) == "story"


def t_hook_support_comes_from_onscreen():
    scene = pb.parse_input(HOOK_BEAT)[0]
    values = pb.fill_variables(PACK["layouts"]["hook"], scene, base_ctx(is_first=True))
    assert values["support"] == scene["onscreen"], values
    # 珊瑚片只落在"数字+单位"上: 标题第二行 = "账户里" + 片"42万"
    assert values["headBottomLead"] == "账户里", values
    assert values["headAccent"] == "42万", values


def t_hook_refuses_illegible_accent():
    # 标题既没数字也没 ｜ ⇒ 没有合法断点 ⇒ 这一镜不进 hook。
    # 旧实现在这里兜底切 text[-4:], 把"困住半辈子"切成 墨字"困" + 珊瑚片"住半辈子"。
    scene = pb.parse_input(BEAT)[0]
    missing = pb.missing_variables(PACK["layouts"]["hook"], scene, base_ctx(is_first=True))
    assert "headAccent" in missing, missing


def t_marker_never_renders_on_screen():
    # ｜ 是断点不是内容: 落在第一行窗口里时必须被剥掉, 否则成片上多一个竖线字形
    parts = pb.split_headline("没人告诉他｜他一直没问")
    assert parts is not None, parts
    assert "｜" not in "".join(parts), parts
    assert parts[0] == "没人告诉他", parts
    assert parts[1] == "他一直没问", parts


def t_closer_cta_pair_uses_marker():
    closer = PACK["layouts"]["closer"]
    scene = {"title": "家里有长辈的，今天查一下",
             "body": "打开平台看三样，转给从不查账的老人。",
             "onscreen": "今天查一下社保", "onscreenAccent": "社保"}
    ctx = base_ctx(is_last=True, overrides={"channel": "新闻拆解"})
    assert pb.missing_variables(closer, scene, ctx) == []
    values = pb.fill_variables(closer, scene, ctx)
    assert values["cta"] == "今天查一下" and values["ctaAccent"] == "社保", values
    # 关键: 不许出现"切在词中间"的强调段(旧 pick_accent 的 text[-4:] 缺陷)
    assert values["cta"] + values["ctaAccent"] == scene["onscreen"], values


def t_closer_without_accent_stops():
    scene = {"title": "家里有长辈的", "body": "今天查一下。",
             "onscreen": "今天记得查一下", "onscreenAccent": None}
    msg = expect_error(pb.fill_variables, PACK["layouts"]["closer"], scene,
                       base_ctx(is_last=True, overrides={"channel": "新闻拆解"}))
    assert "ctaAccent" in msg, msg


# ---------------- 行式位: 说明必须短到不构成整句 ----------------
def t_row_body_capped_at_two_lines():
    # catalog 说明 3.4cqw(37.7px) 在 74cqw(800px) 盒里一行约 21 字 → 两行封顶 42 字。
    # 旧上限 64 字允许三行, 实测把三行清单顶进底部 20cqh 字幕禁入区。
    assert pb.ROW_BODY_MAX_CHARS == 42, pb.ROW_BODY_MAX_CHARS
    long_clause = "打开国家社会保险公共服务平台或者在支付宝微信里搜索社保查询并且查看每一年的缴费明细和账户余额变化情况"
    assert len(long_clause) > pb.ROW_BODY_MAX_CHARS, len(long_clause)   # 前提: 确实超过两行
    # phrase_label 的拒收约定是 ("", 整句) —— **头为空**才是"这句不适合行式版式"
    assert pb.phrase_label("先看这里，" + long_clause, pb.ROW_LABEL_MAX_CHARS,
                           pb.ROW_BODY_MAX_CHARS)[0] == "", "超长说明必须整条拒收"
    # 正控制: 同一法则下合规的说明必须切得出来, 否则上面那条断言是假阳性
    head, body = pb.phrase_label("先看这里，打开平台查三样", pb.ROW_LABEL_MAX_CHARS,
                                 pb.ROW_BODY_MAX_CHARS)
    assert head == "先看这里" and body == "打开平台查三样", (head, body)


def t_title_falls_back_only_for_label_slots():
    # `title` 两种身份: story 的领句(必须作者写) vs rail/catalog 的小节标签(版式词汇)。
    # 把两者混成一条规则, 要么 story 上屏一句发射器编的结论, 要么每镜都得手写小节标签。
    bare = {"title": None, "body": "他一直以为下岗后要自己缴满社保才能领钱。",
            "onscreen": None, "onscreenAccent": None}
    assert "title" in pb.missing_variables(PACK["layouts"]["story"], bare, base_ctx()), \
        "story 的领句不许回落到单文件预览词"
    catalog = dict(bare, items=[{"label": "打开平台", "value": "首页点社保查询"},
                                {"label": "查缴费", "value": "看近一年明细"},
                                {"label": "看余额", "value": "账户累计金额"}])
    # 必须走 choose_layout: 带序号的推导器是在那里按需注册的(直填 fill_variables 会假失败)
    assert pb.choose_layout(PACK, catalog, base_ctx()) == "catalog", "三条合规条目应进 catalog"
    values = pb.fill_variables(PACK["layouts"]["catalog"], catalog, base_ctx())
    assert values["title"] == pb.layout_default(PACK["layouts"]["catalog"], "title"), values


def t_title_without_slot_is_flagged():
    # 作者写了标题行 ⇒ parse_input 把它从 body 里摘出去(不当配音念)。若选中的版式
    # 没有 title 变量(stat/closer/quote 都没有), 这句话就既不上屏也不出声 = 静默丢稿。
    # 发射器必须点名提醒, 不能安静地把稿子吃掉。
    with_title = {"title": "他不是没交过社保", "body": "茹先生干了30多年国企工人。",
                  "onscreen": None, "onscreenAccent": None}
    assert pb.title_needs_slot(with_title, PACK["layouts"]["stat"]), \
        "stat 没有标题位, 写了标题必须提醒"
    assert not pb.title_needs_slot(with_title, PACK["layouts"]["story"]), \
        "story 有标题位, 不提醒"
    assert not pb.title_needs_slot(dict(with_title, title=None), PACK["layouts"]["stat"]), \
        "没写标题就不该提醒"
    # 实测踩过的误报: hook 的契约里没有叫 `title` 的变量, 但 headTop/headBottomLead/
    # headAccent 全部由 split_headline(title) 切出来 —— 标题照样上屏。判定只看
    # "有没有 title 这个 id" 就会对着一条好稿子喊丢稿。
    hook_scene = {"title": "拾荒21年，账户里42万", "body": "湖南常德，71岁老人捡了21年废品。",
                  "onscreen": "他自己完全不知道", "onscreenAccent": None}
    assert not pb.title_needs_slot(hook_scene, PACK["layouts"]["hook"]), \
        "hook 用标题切主视觉, 不算丢稿"


# ---------------- 挂载时间窗: 相邻配音窗不许在边界上相遇 ----------------
def audio_window(tag: str) -> tuple[float, float]:
    """按引擎自己的算法读回一条 ``<audio>`` 的时间窗(起点 + 浮点相加出的终点)。"""
    start = float(re.search(r'data-start="([^"]+)"', tag).group(1))
    dur = float(re.search(r'data-duration="([^"]+)"', tag).group(1))
    return start, start + dur


def t_audio_windows_never_meet_on_the_boundary():
    # 实测(t001-v3, 2026-09-29): 画面与配音写同一个 start/dur 时, 首尾**正好相接**的
    # 两条配音窗会被 lintDuplicateAudioTracks 判成重叠 —— 它的判据是 `b.start < a.end`,
    # 而 a.end 是它自己算的 11.88 + 11.808 = 23.688000000000002, 比 b.start 大 2e-15。
    # duplicate_audio_track 是 warning, --strict 把 warning 升级成失败 ⇒ 拒绝渲染。
    # 所以配音窗必须在自己的镜头结束前留一点余量, 让浮点噪声再也翻不过这个不等式。
    durations = [11.88, 11.808, 13.128]          # t001-v3 真跑出来的三个时长
    starts, acc = [], 0.0
    for dur in durations:
        starts.append(acc)
        acc += dur
    tags = [pb.emit_audio_mount(i, f"scene_{i}.mp3", "work", s, d)
            for i, (s, d) in enumerate(zip(starts, durations), 1)]
    windows = [audio_window(tag) for tag in tags]
    for (s1, e1), (s2, e2) in zip(windows, windows[1:]):
        assert not (s1 < e2 and s2 < e1), f"配音窗 {s1}-{e1} 与 {s2}-{e2} 在引擎眼里重叠"
    # 余量不许吃掉内容: 最短一窗仍要覆盖几乎整镜(成片声音另有 narration.mp3,
    # 这层挂载只服务"目录里有 mp3 就必须有 <audio>"的工程一致性, 但不能提前多少)。
    for (s, e), d in zip(windows, durations):
        assert 0.0 <= d - (e - s) <= 0.2, f"第 {s}s 的配音窗被削掉了 {d - (e - s)}s"
    # 下限自检: 契约允许的最短一镜(MIN_SLOT_SECONDS)减去余量后仍是正数,
    # 否则会写出 data-duration<=0 的挂载, 那比 warning 更难查。
    assert pb.audio_slot_duration(pb.MIN_SLOT_SECONDS) > 0.0


# ---------------- 图片层(判据 4): 授权闸 / 尺寸闸 / 署名, 全离线 ----------------
# Wikimedia Commons 免密钥公开 API 的返回形态 (2026-09-29 实跑 t001 选题抓下来的两条):
#   File:Bride's Chair, Changde …  → LicenseShortName=Public domain
#   File:Changde Street.jpg        → LicenseShortName=CC BY-SA 3.0   ← 这条必须被拒
# extmetadata 的 value 有两种形态: 纯字符串, 或 {"value": html, "type": "text"}。
PD_PAGE = {
    "title": "File:Bride's Chair, Changde, Hunan, China, ca.1910-1937 (1).jpg",
    "index": 1,
    "imageinfo": [{
        "url": "https://upload.wikimedia.org/wikipedia/commons/1/1a/Bride.jpg",
        "descriptionurl": "https://commons.wikimedia.org/wiki/File:Bride%27s_Chair.jpg",
        "thumburl": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Bride.jpg/1280px-Bride.jpg",
        "width": 3000, "height": 2200,
        "extmetadata": {
            "LicenseShortName": {"value": "Public domain", "type": "structured"},
            "UsageTerms": {"value": "Public domain", "type": "text"},
            "Artist": {"value": '<span class="fn"> Unknown</span>', "type": "html"},
        },
    }],
}
BY_SA_PAGE = {
    "title": "File:Changde Street.jpg",
    "index": 2,
    "imageinfo": [{
        "url": "https://upload.wikimedia.org/wikipedia/commons/8/8x/Street.jpg",
        "descriptionurl": "https://commons.wikimedia.org/wiki/File:Changde_Street.jpg",
        "thumburl": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8x/Street.jpg/1280px-Street.jpg",
        "width": 1600, "height": 1200,
        "extmetadata": {
            "LicenseShortName": "CC BY-SA 3.0",       # 字符串形态: 老文件确实这样返回
            "UsageTerms": "Creative Commons Attribution-Share Alike 3.0",
            "Artist": '<a href="//commons.example/u">某网</a>用户上传',
        },
    }],
}


def t_license_gate_refuses_share_alike_and_nc():
    # 判据是"能不能商用 + 会不会传染", 不是"有没有许可证"。
    # BY-SA 要求衍生作品也用 SA 授权发布 —— 整条片子(含 UI/配音)都会被套上传染性条款;
    # GFDL 是文档许可, 对视频同样要求随附全文; NC 直接禁商用; ND 禁衍生(改色/裁剪就是衍生)。
    ok, _ = cm.license_verdict("Public domain", "Public domain")
    assert ok, "公有领域必须放行"
    for short, terms in [("CC0", "CC0"), ("CC0 1.0 Universal", "Public Domain Mark"),
                         ("CC BY 3.0", "Creative Commons Attribution 3.0"),
                         ("CC BY 4.0", "Creative Commons Attribution 4.0")]:
        assert cm.license_verdict(short, terms)[0], (short, terms)
    for short, terms in [("CC BY-SA 3.0", "Creative Commons Attribution-Share Alike 3.0"),
                         ("CC BY-NC 2.0", "Creative Commons Attribution-NonCommercial"),
                         ("CC BY-ND 2.5", "Attribution-NoDerivs"),
                         ("GFDL", "GNU Free Documentation License"),
                         ("", ""), ("未知", None)]:
        ok, why = cm.license_verdict(short, terms)
        assert not ok, f"{short!r} 竟被放行"
        assert why, "拒收必须给出可打印的理由"


def t_license_gate_refuses_when_fields_are_missing():
    # 读不到授权字段 ≠ 可以随便用。宁可降级到绘制地面, 也不冒法定赔偿的险。
    assert not cm.license_verdict(None, None)[0]
    assert not cm.license_verdict("", "All rights reserved")[0]


def t_pick_candidate_applies_license_and_size_gates():
    # 第二参数是检索词(相关性闸要用): 这三条断言只关心授权与尺寸, 词一律用能命中的。
    assert cm.pick_candidate([PD_PAGE], "Changde Hunan")["license"] == "Public domain"
    assert cm.pick_candidate([BY_SA_PAGE], "Changde") is None, "BY-SA 不许进成片"
    assert cm.pick_candidate([PD_PAGE, BY_SA_PAGE], "Changde Hunan")["title"] == PD_PAGE["title"], \
        "两条都在时只能取合规那条"
    assert cm.pick_candidate([], "Changde Hunan") is None
    tiny = json.loads(json.dumps(PD_PAGE))
    tiny["imageinfo"][0]["width"], tiny["imageinfo"][0]["height"] = 640, 480
    assert cm.pick_candidate([tiny], "Changde Hunan") is None, "短边不足必须拒(否则在 1080 宽上会糊)"
    strip = json.loads(json.dumps(PD_PAGE))          # 漫画条/多图拼版: 极端长宽比不是照片
    strip["imageinfo"][0]["width"], strip["imageinfo"][0]["height"] = 800, 9000
    assert cm.pick_candidate([strip], "Changde Hunan") is None


def t_query_comes_only_from_authored_slots():
    # 发射器不许自己从正文里"认出"地名 —— 没有地名词表, 认出来的就是猜, 猜错了是假事实。
    assert cm.image_query({"image": "Changde Hunan"}, {"kicker": "湖南常德"}) == "Changde Hunan"
    assert cm.image_query({}, {"kicker": "湖南常德"}) == "湖南常德"
    assert cm.image_query({}, {"kicker": None}) is None
    assert cm.image_query({"image": False}, {"kicker": "湖南常德"}) is None, \
        "显式 image:false 是这一镜不要照片, 不许回落到 kicker"


def t_attribution_is_built_not_invented():
    rec = cm.pick_candidate([PD_PAGE], "Changde Hunan")
    text = cm.attribution_text(rec)
    assert "Public domain" in text, text
    assert "<" not in text and "span" not in text, f"署名里的 HTML 必须剥净: {text}"
    # 作者缺失时写成"未署名", 不许顶着一个看起来像真名的占位词
    assert "Unknown" not in text and "未知" not in text.replace("未署名", ""), text
    by_sa_as_by = dict(BY_SA_PAGE, imageinfo=[dict(
        BY_SA_PAGE["imageinfo"][0], extmetadata=dict(
            BY_SA_PAGE["imageinfo"][0]["extmetadata"],
            LicenseShortName="CC BY 3.0", UsageTerms="Creative Commons Attribution 3.0"))])
    by = cm.attribution_text(cm.pick_candidate([by_sa_as_by], "Changde"))
    assert "某网" in by and "CC BY 3.0" in by, by


def t_search_params_ask_for_scaled_thumbs():
    params = cm.search_params("湖南常德", limit=8)
    assert params["action"] == "query", params
    assert params["format"] == "json", params
    assert params["gsrnamespace"] == "6", f"只搜 File 命名空间: {params}"
    assert "filetype:bitmap" in params["gsrsearch"], f"位图限定(SVG/GIF 不进地面): {params}"
    assert int(params["gsrlimit"]) == 8, params
    # 两层 prop: prop 声明"要 imageinfo 这块数据", iiprop 才声明"这块里要哪些字段"。
    assert params["prop"] == "imageinfo", params
    assert "extmetadata" in params["iiprop"] and "url" in params["iiprop"], params
    # 实测不写 iiurlwidth 时 thumburl 缺席 ⇒ 只能拉原图(常见 20MB+)。缩略图 URL 是省流量的前提。
    assert int(params["iiurlwidth"]) >= cm.MIN_SHORT_EDGE, params
    assert cm.USER_AGENT.startswith("harness-news-runtime/"), \
        "Commons 要求带标识的 UA, 空 UA 会被 403"


def t_user_agent_is_header_safe():
    # 实测(2026-09-29 首次联跑): UA 里写中文 ⇒ urllib 抛 UnicodeEncodeError('latin-1'),
    # 每一镜都"检索失败"并静默降级成无图, 看上去像"这个选题 Commons 没有图"。
    # HTTP 头只允许 latin-1; 中文查询词进的是 URL(urllib.parse.urlencode 会百分号编码), 不受影响。
    assert cm.USER_AGENT.isascii(), f"UA 必须纯 ASCII: {cm.USER_AGENT!r}"
    assert cm.USER_AGENT.encode("latin-1"), "latin-1 编不出就是 400/异常"


# 实测证据(2026-09-29 首次联跑): 用「湖南常德」检索, Commons 全文检索返回的第一条合规图
# 是西藏布让的步甲虫论文插图 —— 授权是 CC BY 4.0(合法), 尺寸也够, 但**画面与新闻无关**。
# 把虫子上屏配"71岁拾荒老人"是视觉假事实, 比没图更糟 ⇒ 词面相关性必须先过一道闸。
BEETLE_PAGE = {
    "title": "File:Himalopenetretus burangensis (10.3897-zookeys.997.58125) Figures 2–7.jpg",
    "index": 1,
    "imageinfo": [{
        "url": "https://upload.wikimedia.org/wikipedia/commons/0/09/Beetle.jpg",
        "descriptionurl": "https://commons.wikimedia.org/wiki/File:Himalopenetretus_burangensis.jpg",
        "thumburl": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/Beetle.jpg/1280px-Beetle.jpg",
        "width": 1512, "height": 1382,
        "extmetadata": {
            "LicenseShortName": "CC BY 4.0",
            "UsageTerms": "Creative Commons Attribution 4.0",
            "Artist": {"value": "Yan W, Shi H, Liang H (2020) First discovery of the genus "
                                 "Himalopenetretus (Coleoptera, Carabidae, Patrobini) in China, "
                                 "with description of a new species. ZooKeys 997: 145-154.",
                       "type": "text"},
        },
    }],
}


def t_relevance_gate_refuses_legally_clean_but_wrong_picture():
    # 授权与尺寸都合规 ≠ 可以上屏。词面不搭就必须拒, 让它降级到绘制地面。
    ok, why = cm.relevance_ok(PD_PAGE["title"], "Changde Hunan")
    assert ok, why
    ok, why = cm.relevance_ok(BEETLE_PAGE["title"], "Changde Hunan")
    assert not ok, "步甲虫论文插图绝不能当作常德街景上屏"
    assert why, "拒用要给得出可打印的理由"
    # 中文标题对中文查询词: 二字内共享即命中(「湖南常德」与「常德市区」共享 常德/湖南)。
    assert cm.relevance_ok(CJK_PAGE["title"], "湖南常德")[0]
    # 跨语言命不中是**词面闸的边界**, 不是 bug: 没有地名词表/翻译时, 猜就是拿无关画面配真话。
    # ⇒ 中文 kicker 想拿到英文标题的图, 必须作者显式写 image: "Changde Hunan"。
    assert not cm.relevance_ok(PD_PAGE["title"], "湖南常德")[0]
    # 浅查询词(长度 < 4 的拉丁词、单字)不构成相关性证据
    assert not cm.relevance_ok(PD_PAGE["title"], "a of in")[0]
    assert not cm.relevance_ok(PD_PAGE["title"], "")[0], "空查询一律拒"
    # 闸只管词面, 不做语义判断: 拿虫子自己的词去搜, 就该放行(那是检索该负责的部分)
    assert cm.relevance_ok(BEETLE_PAGE["title"], "Himalopenetretus")[0]


def t_pick_candidate_requires_query_relevance():
    assert cm.pick_candidate([PD_PAGE], "Changde Hunan") is not None
    assert cm.pick_candidate([BEETLE_PAGE], "Changde Hunan") is None, \
        "合规但无关的图必须被挑掉"
    assert cm.pick_candidate([BEETLE_PAGE, PD_PAGE], "Changde Hunan")["title"] == PD_PAGE["title"], \
        "第一条无关时要继续往下找, 不是直接放弃"
    # 多条都相关时取**命中最多**的那条, 不是 API 顺序的第一条:
    # "Changde Hunan" 对只含 Hunan 的一条只算半命中, 对同时含两地名的 PD 条是全命中。
    assert cm.pick_candidate([HUNAN_ONLY_PAGE, PD_PAGE], "Changde Hunan")["title"] == PD_PAGE["title"], \
        "更相关的必须压过相关度顺序在前的次相关条目"


def t_cache_entry_is_keyed_on_query_not_filename():
    # 实测缺陷: 缓存只看目标文件名 ⇒ 作者改了 kicker/换了选题但镜号不变时, 旧图被静默复用。
    # 清单条目必须带 source_url(署名的法定一环), 缺了就当失效重取。
    entry = {"title": "File:A.jpg", "query": "Changde Hunan",
             "source_url": "https://commons.wikimedia.org/wiki/File:A.jpg"}
    manifest = {"shot_01.jpg": entry}
    assert cm.cache_hit(manifest, "shot_01.jpg", "Changde Hunan") == entry, "同镜同词必须命中"
    assert cm.cache_hit(manifest, "shot_01.jpg", "Zhuzhou Hunan") is None, "换词必须重取"
    assert cm.cache_hit(manifest, "shot_02.jpg", "Changde Hunan") is None, "换镜必须重取"
    assert cm.cache_hit({}, "shot_01.jpg", "Changde Hunan") is None, "空清单不可能命中"
    assert cm.cache_hit({"shot_01.jpg": {"title": "A", "query": "Changde Hunan"}},
                        "shot_01.jpg", "Changde Hunan") is None, "没有出处链接的条目按失效处理"


# 两条补正样本: 一条中文标题的真文件(实跑里确实检到过), 一条只命中半个地名的次相关条目。
CJK_PAGE = {
    "title": "File:常德市区 - panoramio.jpg",
    "index": 3,
    "imageinfo": [{
        "url": "https://upload.wikimedia.org/wikipedia/commons/3/3x/Changde.jpg",
        "descriptionurl": "https://commons.wikimedia.org/wiki/File:常德市区.jpg",
        "thumburl": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3x/Changde.jpg/1280px-Changde.jpg",
        "width": 2048, "height": 1365,
        "extmetadata": {
            "LicenseShortName": {"value": "CC BY 3.0", "type": "text"},
            "UsageTerms": {"value": "Creative Commons Attribution 3.0", "type": "text"},
            "Artist": {"value": "panoramio 用户上传", "type": "text"},
        },
    }],
}
HUNAN_ONLY_PAGE = json.loads(json.dumps(CJK_PAGE))
HUNAN_ONLY_PAGE["title"] = "File:Hunan University gate.jpg"


def t_attribution_is_truncated_without_losing_the_license():
    # ZooKeys 那类文件的 Artist 是整段引文, 上屏会占掉半个画面。
    rec = cm.pick_candidate([BEETLE_PAGE], "Himalopenetretus")
    long_line = cm.attribution_text(rec, max_chars=24)
    assert len(long_line) <= 24, f"屏上署名超宽: {len(long_line)} 字 → {long_line}"
    assert "…" in long_line, long_line
    assert long_line.endswith("CC BY 4.0"), f"署名可以缩, 许可证名不许被缩掉: {long_line}"
    # 不传上限时给全文(联络表/预览用), 短作者名不产生省略号
    assert "…" not in cm.attribution_text(cm.pick_candidate([PD_PAGE], "Changde Hunan"),
                                          max_chars=None)
    assert cm.attribution_text(rec, max_chars=None).startswith("图：Yan W")
    # 完整出处(进 credits.md / 视频简介)保留全文与来源页, 截断只发生在屏上那一行
    credit = cm.full_credit(rec)
    assert "ZooKeys" in credit and "commons.wikimedia.org" in credit, credit


def t_artist_placeholder_never_becomes_a_fake_name():
    # 实测(2026-09-29): 那幅 Changde PD 老照片的 Artist 模板展开成
    # "Unknown author Unknown author"(同一模板串重复两遍), 等值比较没抓住它,
    # 于是屏上出现「图：Unkno…」—— 一个被截断的英语占位词, 看着像人名却不是人名。
    # 这类值必须归一到"未署名"(空串), 且重复展开要折叠成一遍再判。
    for raw in ("Unknown author", "Unknown author Unknown author", "UNKNOWN AUTHOR",
                "unknown photographer", "Unknown Artist", "n/a", "N/A", "-", "—",
                "不明作者", "未知", "未知作者", "佚名", "{{PIL|Unknown}}", "{{unknown}}",
                "  ", ""):
        assert cm.normalize_artist(raw) == "", f"占位值没被归一: {raw!r}"
    assert cm.normalize_artist('  <span class="fn"> Chelong Chen</span> ') == "Chelong Chen"
    # 真名里含 "unknown" 词面时不能误杀(检索到过 "Unknown, Unknown" 之外还有
    # "Unkown Photos" 这类拼错的占位, 但 "Chang De Unknown" 是作品名不是占位)
    assert cm.normalize_artist("Museo de Unknown") == "Museo de Unknown"
    # 重复两遍的模板产物折叠成一遍(不能因为"看着像两个名字"就当真名放过)
    assert cm.normalize_artist("Chang De, Chang De") == "Chang De"


def t_screen_attribution_never_cuts_a_latin_word_in_half():
    # 屏上位置只够半个拉丁词时, 把 "Bureau" 削成 "Burea…" 等于凭空造出一个叫 Burea 的
    # 作者 —— 改署名比不署名更糟。这种情况许可证原样上屏, 完整出处指向 credits.md/简介。
    rec = {"artist": "Bureau of American Ethnology", "license": "Public domain"}
    line = cm.attribution_text(rec, max_chars=24)
    assert len(line) <= 24, f"屏上署名超宽: {len(line)} 字 → {line}"
    assert "Burea" not in line, f"把一个拉丁词切断了: {line}"
    assert "Public domain" in line, f"许可证不能因为放不下就消失: {line}"
    assert cm.CREDIT_POINTER_LABEL in line, f"省略了作者却要指向完整出处: {line}"
    # 放得下整词就按词截, 截点必须落在原串的分隔符上(不是词中间)
    full = "Yan W, Shi H, Liang H"
    kept = cm.attribution_text({"artist": full, "license": "CC BY 4.0"},
                               max_chars=24)
    assert "…" in kept and len(kept) <= 24, kept
    head = kept[len("图："):].split(" · ")[0].rstrip("…")
    assert full.startswith(head), kept
    assert full[len(head):len(head) + 1] in ("", " ", ",", "，", "、"), \
        f"截在词中间: {head!r} 后面接 {full[len(head):len(head) + 1]!r}"
    # 中文名没有词间空格, 按字截是正常排版, 不许退化成"见简介"
    cn = cm.attribution_text({"artist": "常德市博物馆征集藏", "license": "CC BY 4.0"},
                             max_chars=20)
    assert cm.CREDIT_POINTER_LABEL not in cn and "…" in cn, cn
    # 不传上限(联络表/预览)永远给全名
    assert cm.attribution_text(rec, max_chars=None).startswith("图：Bureau of American")


def t_api_retry_covers_throttle_but_not_policy_errors():
    # 逐镜检索是连续请求, Commons 对匿名脚本会偶发 429; 一次退避重试能把"整条片子没图"
    # 从常见故障变成小概率。但 404/403 重试不会变好 —— 那是鉴权与资源问题, 必须立刻降级。
    def http(status):
        return urllib.error.HTTPError("https://x", status, "reason", {}, None)

    assert cm.should_retry(http(429)) and cm.should_retry(http(503)), "限流/网关必须重试"
    assert cm.should_retry(urllib.error.URLError("timed out")), "连接类错误必须重试"
    assert not cm.should_retry(http(404)) and not cm.should_retry(http(403)), "策略错误不重试"
    assert not cm.should_retry(ValueError("bad json")), "解析错误重试多少次都是坏 JSON"
    assert cm.API_ATTEMPTS == 2, "重试次数必须是有上限的常数, 不能无限重"
    assert cm.RETRY_DELAY_SECONDS > 0


def t_public_api_functions_have_no_undocumented_name():
    assert cm.normalize_artist.__doc__, "公开函数要有说明: 法则靠注释留在原地"




# ---------------- 12 模板包存在性与基本形态自检 ----------------
def t_all_templates_in_constant():
    # 12 模板常量对齐: ALL_TEMPLATES 必须是 12 个且每个都有 pack_dirs/frame.md。
    assert len(pb.ALL_TEMPLATES) == 12, f"ALL_TEMPLATES 应有 12 个, 实际 {len(pb.ALL_TEMPLATES)}"
    expected = {
        "news-coral", "news-ink", "news-policy", "news-stat",
        "news-onsite", "news-bulletin", "news-explainer", "news-alert",
        "news-thread", "news-takes", "news-blast", "news-world",
    }
    assert set(pb.ALL_TEMPLATES) == expected, (
        f"ALL_TEMPLATES 集合不一致: 差 = "
        f"{set(pb.ALL_TEMPLATES) ^ expected}"
    )

def t_every_template_has_frame_md():
    # 每个 pack 目录必须有 frame.md (token 源)。host.html/compositions 可后补。
    missing = []
    for name in pb.ALL_TEMPLATES:
        frame = os.path.join(pb.TEMPLATE_ROOT, name, "frame.md")
        if not os.path.isfile(frame):
            missing.append(name)
    assert not missing, f"以下 pack 缺 frame.md: {missing}; 12 模板必须有设计系统契约"

def t_fully_loaded_packs_have_required_files():
    # 已带 host.html 的 pack (host.html 存在 ⇒ 视为"完整"), 必须真能 load。
    # 没有 host.html 的 pack (frame-only) 标记为 partial, 这里只核对加载过的能 load, 不报错。
    fully_loaded = [n for n, p in TEMPLATE_PACKS.items() if p is not None]
    for name in fully_loaded:
        pack = TEMPLATE_PACKS[name]
        assert pack["name"] == name
        assert "host" in pack and pack["host"], f"{name}: host 模板字符串为空"
        assert "layouts" in pack and pack["layouts"], f"{name}: 没有 compositions"

def t_partial_packs_logged():
    # 当前预期: news-coral 完整, 其余 11 个 frame-only。
    # 当所有 composition 都落地后, FRAME_ONLY_TEMPLATES 应为空, 此测会自动通过。
    # 现阶段只是"漏斗日志", 不做断言 (只要 frame.md 在 + host.html 不在就算正常)。
    for name in FRAME_ONLY_TEMPLATES:
        assert os.path.isfile(os.path.join(pb.TEMPLATE_ROOT, name, "frame.md")), (
            f"{name} 标为 partial 但连 frame.md 都没有"
        )

def t_default_style_matches_first_template():
    # DEFAULT_STYLE 必须是 ALL_TEMPLATES 的成员 (兼容存量稿件)。
    assert pb.DEFAULT_STYLE in pb.ALL_TEMPLATES, (
        f"DEFAULT_STYLE {pb.DEFAULT_STYLE!r} 不在 ALL_TEMPLATES 里"
    )

def t_full_loadability_progress():
    # 进度指标 = **有真版式因而可选出** 的 pack 数, 不是"能加载不抛" 的 pack 数。
    # 后者在 12 个包都放一个 placeholder.html 之后就永久 12/12(饱和指标等于没有指标),
    # 2026-09-29 审计就是这么被绕过去的; 现在两条口径必须互相印证。
    real = [name for name, pack in TEMPLATE_PACKS.items() if pack is not None]
    ready = pb.ready_packs()
    assert sorted(real) == sorted(ready), (
        f"口径不一致: 加载成功的 {sorted(real)} != 有真版式的 {sorted(ready)}"
    )
    for name, pack in TEMPLATE_PACKS.items():
        if pack is not None:
            assert pb.PLACEHOLDER_LAYOUT not in pack["layouts"], (
                f"{name} 的 layouts 里混进了占位版式 (D7 失效)"
            )
            assert pack["layouts"], f"{name} 加载成功但版式为空"
    print(f"      可渲染 pack (有真版式): {len(real)}/{len(pb.ALL_TEMPLATES)}"
          f" —— {', '.join(real) if real else '无'}")


def t_placeholder_pack_stops_at_load():
    # 只有占位壳的 pack 必须在 load_style_pack 就停机, 并点名当前谁能渲染。
    unready = [n for n in pb.ALL_TEMPLATES if not pb.pack_has_real_layout(n)]
    assert unready, "所有 pack 都有真版式了 —— 这条测要改成断言'无未就绪包'"
    msg = expect_error(pb.load_style_pack, unready[0])
    assert "还没有真版式" in msg, f"停机文案没说明原因: {msg}"
    assert "可渲染的 pack" in msg, f"停机文案没给出可用替代: {msg}"


# ---------------- AIGC 标识 (合规硬要求, 见 path_b_build 常量块) ----------------
# ASS 合规样式的列位由 path_b_build 的 [V4+ Styles] Format 行定死(23 字段,
# "Style: AIGC" 吃掉第 0 列): 下标错了不是断言失效, 就是 int() 崩在颜色串上。
S_FONT_SIZE = 2
S_BORDER_STYLE = 15
S_OUTLINE = 16      # 描边也画字, 算角标的视觉高度时必须一起算
S_SHADOW = 17
S_ALIGNMENT = 18
S_MARGIN_L = 19
S_MARGIN_R = 20
S_MARGIN_V = 21
D_LAYER = 0      # "Dialogue: <Layer>" 同格
D_START = 1
D_END = 2


def _aigc_ass(aigc_seconds=30.0):
    return pb.build_ass([(0.0, 2.0, "口播字幕")], 1080, 1920,
                        aigc_text=pb.AIGC_LABEL_TEXT, aigc_seconds=aigc_seconds)


def t_aigc_badge_event_covers_the_opening():
    # 显式标识: 一条 Layer 1、从第 0 秒起、只覆盖开场窗(AIGC_LABEL_ON_SECONDS)的
    # AIGC 事件, 且压在字幕层之上。《标识办法》§ 4-四 写"应当"的只有**起始画面**
    # 与**播放周边**, "末尾/全程"那半句是"可以" —— 所以开场窗满足的是"应当"那一半,
    # "周边"改由 mp4 隐式元数据 + 发布端自主声明承担(取舍记在 ARCHITECTURE D8)。
    ass = _aigc_ass(aigc_seconds=pb.AIGC_LABEL_ON_SECONDS)
    line = [ln for ln in ass.splitlines() if ln.startswith("Dialogue") and ",AIGC," in ln]
    assert len(line) == 1, f"AIGC 事件应恰好 1 条, 实得 {len(line)}: {line}"
    cols = line[0].split(",")
    assert cols[D_LAYER] == "Dialogue: 1", (
        f"AIGC 必须在 Layer 1(字幕层之上), 实得 {cols[D_LAYER]!r}")
    assert cols[D_START] == "0:00:00.00", (
        f"必须从第 0 秒起(起始画面要求), 实得 {cols[D_START]}")
    # ASS 时间戳只到百分之一秒, 允许这一档量化差。
    h_, m_, rest = cols[D_END].split(":")
    sec = int(h_) * 3600 + int(m_) * 60 + float(rest)
    assert abs(sec - pb.AIGC_LABEL_ON_SECONDS) <= 0.01, (
        f"开场窗应为 {pb.AIGC_LABEL_ON_SECONDS}s, 实得 {cols[D_END]}")
    assert sec >= pb.AIGC_LABEL_MIN_SECONDS, (
        f"开场窗 {sec}s 低于国标 {pb.AIGC_LABEL_MIN_SECONDS}s 持续线")


def t_aigc_badge_seconds_capped_at_on_seconds():
    # 长片只开 AIGC_LABEL_ON_SECONDS 秒; 比它短的片子角标跨全片 —— 事件终点不许越过
    # 最后一帧(这是算术, 不是取舍)。短到不足 2s 的**原样返回**, 挡在 mux_and_burn。
    assert pb.aigc_badge_seconds(59.3) == pb.AIGC_LABEL_ON_SECONDS
    assert pb.aigc_badge_seconds(pb.AIGC_LABEL_ON_SECONDS) == pb.AIGC_LABEL_ON_SECONDS
    assert pb.aigc_badge_seconds(3.0) == 3.0
    assert pb.aigc_badge_seconds(1.5) == 1.5, "1.5s 要原样交给停机判定, 这里不许夹"


def t_aigc_badge_absent_when_no_seconds():
    # aigc_seconds<=0 (全片时长没算出来) 时不许悄悄挂一条 0 秒标识;
    # 真正的挡在 mux_and_burn(<2s 停机), 这里只保证 build_ass 自身不产出空标。
    ass = _aigc_ass(aigc_seconds=0.0)
    assert ",AIGC," not in ass, "0 秒时长不该产出 AIGC 事件"


def t_aigc_badge_style_is_bottom_left_at_floor():
    # Alignment 1 = 左下; BorderStyle 1 = 描边+阴影(彩底上唯一稳妥的可读性来源);
    # 字号**擦在**国标 5% 线上: 字芯 ≥ 线, 又不超出线一整档(=1px em 的取整粒度)。
    style = [ln for ln in _aigc_ass().splitlines() if ln.startswith("Style: AIGC,")]
    assert len(style) == 1, f"缺 AIGC 样式行: {style}"
    cols = style[0].split(",")
    assert len(cols) == 23, f"v4.00 Style 应 23 列, 实得 {len(cols)}: {style[0]}"
    font_size = int(cols[S_FONT_SIZE])
    border_style = int(cols[S_BORDER_STYLE])
    alignment = int(cols[S_ALIGNMENT])
    assert alignment == 1, f"AIGC 角标 Alignment 应为 1(左下), 实得 {alignment}"
    assert border_style == 1, f"AIGC 角标 BorderStyle 应为 1(描边+阴影), 实得 {border_style}"
    # 边角性: 国标要求显式标识落在"边角", 边距必须是薄边而不是居中偏移。
    ml, mr, mv = int(cols[S_MARGIN_L]), int(cols[S_MARGIN_R]), int(cols[S_MARGIN_V])
    assert ml == int(1080 * pb.AIGC_LABEL_MARGIN_W_FRAC) == mr, f"左右边距不符: {ml}/{mr}"
    assert mv == pb.aigc_badge_margin_v(1080, 1920), (
        f"底边距不是从字幕几何推出来的: 实得 {mv}, 应为 {pb.aigc_badge_margin_v(1080, 1920)}")
    # 边角性: 国标要求显式标识落在"边角"。这层意思在两个方向上**不等价**:
    #   水平 —— MarginL 必须是薄边(48px), 不能是居中偏移;
    #   垂直 —— 底边距 303px 不是薄边, 它是为了让开两行字幕块(aigc_badge_margin_v),
    #           而"仍在画面底角"由 t_aigc_badge_sits_in_the_gap_between_content_and_
    #           subtitles 断言(角标整块落在底部 20cqh 带内, 视觉上就是左下角)。
    # 所以垂直只挡"别退到画面中间去": 超过底部四分之一(480px)就不叫边角了。
    assert ml < 1080 * 0.1, f"标识必须贴左边(薄边而非居中偏移), 实得 MarginL={ml}"
    assert mv < 1920 * 0.25, f"底边距越过底部四分之一, 已不是边角标识, 实得 MarginV={mv}"
    # FontSize 是 em 高, 国标量的是字芯高: 用实测字面率换算后才可比。
    glyph_h = font_size * pb.AIGC_LABEL_GLYPH_RATIO
    floor = min(1080, 1920) * pb.AIGC_LABEL_FLOOR_FRAC
    assert glyph_h >= floor, (
        f"字芯 {glyph_h:.1f}px < 国标线 {floor:.1f}px(最短边 5%): 不合规"
    )
    # 上界同样是合规语义: 字号每 +1px em, 字芯就 +0.729px。超过 floor + ratio 就
    # 意味着有人把"擦到最小"又换回了带余量的档位 —— 那条余量是旧实现的保险, 现在
    # 由用户明确退掉了, 留着断言是为了让下一次改动是被看见的, 不是悄悄发生的。
    assert glyph_h < floor + pb.AIGC_LABEL_GLYPH_RATIO, (
        f"字芯 {glyph_h:.1f}px 比 {floor:.1f}px 的线高出一整档字号: "
        f"「擦到最小」的要求被改回去了")
    assert font_size == pb.aigc_badge_font_size(1080, 1920), "样式字号与推导函数不一致"
    # 单行性: WrapStyle 0 会把溢出的第二行**居中**, 左下角标一旦折行就变成居中块,
    # 既不贴边也会压字幕。宽度用 2026-09-29 成片实测的推进量核, 不按"每字 1 em"估。
    advance = AIGC_LABEL_MEASURED_ADVANCE_EM / len(pb.AIGC_LABEL_TEXT)
    right_edge = ml + font_size * advance * len(pb.AIGC_LABEL_TEXT) * AIGC_LABEL_WIDTH_HEADROOM
    assert right_edge < 1080 - mr, (
        f"角标右边界 {right_edge:.0f}px 超出可用宽度 {1080 - mr}px → 会折行")


def t_aigc_badge_font_size_uses_short_side():
    # 竖屏按宽、横屏按高 —— 写死 height 会在横屏算小一档。
    assert pb.aigc_badge_font_size(1080, 1920) == pb.aigc_badge_font_size(1920, 1080), (
        "同一批像素的横竖屏字号必须相同(基准是最短边, 不是高度)"
    )
    assert pb.aigc_badge_font_size(720, 1280) < pb.aigc_badge_font_size(1080, 1920)


#: 2026-09-29 成片实测(1080×1920 / Microsoft YaHei / 量白色像素范围): FontSize 85 时
#: "AI 生成合成内容" 九字符横向占 522px → 总推进宽 522/85 = 6.14 em。取**每 em** 为单位
#: 是为了让它与字号无关(现在字号是 75, 乘回去就是 75×6.141/9/字 = 460px)。
#: 这一版之前这里按"每字 1 em"估, 算出 75.3cqw 就把**已经合规**的角标判成越界 ——
#: 估算模型也得跟成片对一次表, 否则测的是自己的假设而不是渲染结果。
AIGC_LABEL_MEASURED_ADVANCE_EM = 522 / 85
AIGC_LABEL_WIDTH_HEADROOM = 1.10
#: 左下角标与"版式内容下界 / 字幕块顶"两侧各必须留下的间隙(px), 与
#: `pb.AIGC_LABEL_BAND_GAP_PX` 同值(函数里第 5 行断言把两者钉在一起, 防止一头改了
#: 另一头不知道)。这条带总共只有 92px: 擦边字芯 54.7px 加描边阴影共 65.7px, 再加
#: 行盒下空白 8px, 取中后上下各剩 13px —— 所以这个数不是挑一个刚好能过的值, 而是
#: **报出这条带有多挤**: 谁改了字号、字幕行数或底边距而没重算带, 就会先在这里红掉,
#: 而不是等成片压字。
BADGE_BAND_MIN_GAP_PX = 8


def t_aigc_badge_sits_in_the_gap_between_content_and_subtitles():
    # 底部带是算出来的: 版式内容不许进 20cqh 以下(由 layout_selfcheck 的
    # CAPTION_RESERVE_INTRUDED 在发射前守着), 字幕块顶 = h − 字幕底边距 − 封顶行数
    # × 字幕字号(实测 1628)。左下角标连描边与阴影一起算, 必须整块夹在这两者中间 ——
    # 它替代旧的"左上角不撞壁纸序号"断言: 位置一换, 那条测的就是不存在的地带了。
    w, h = 1080, 1920
    cols = [ln for ln in _aigc_ass().splitlines() if ln.startswith("Style: AIGC,")][0].split(",")
    fs, ol, shadow = int(cols[S_FONT_SIZE]), int(cols[S_OUTLINE]), int(cols[S_SHADOW])
    mv = int(cols[S_MARGIN_V])
    content_floor = h * (1 - pb.layout_selfcheck.CAPTION_RESERVE_CQH / 100)
    subtitle_top = (h - int(h * pb.ASS_MARGIN_BOTTOM_H_FRAC)
                    - pb.CAPTION_MAX_LINES * pb.caption_font_size(h))
    # ASS 的 MarginV 量到的是**行盒底**, 既不是字芯底也不是墨迹底: 字芯下面还有
    # 下伸部空白(实测 8px, 见 AIGC_LABEL_LINE_SLACK_PX)。旧断言按"行盒底=字芯底"算,
    # 于是它跟着 aigc_badge_margin_v 一起自称"上下各 13px", 而真渲染上侧只剩 13−8=5px。
    glyph_bottom = h - mv - pb.AIGC_LABEL_LINE_SLACK_PX
    ink_top = glyph_bottom - fs * pb.AIGC_LABEL_GLYPH_RATIO - ol
    ink_bottom = glyph_bottom + ol + shadow
    assert pb.AIGC_LABEL_BAND_GAP_PX == BADGE_BAND_MIN_GAP_PX, "两处间隙常量已分叉, 判据不可信"
    assert ol == pb.aigc_badge_outline(fs), f"样式描边不是推导值: {ol} ≠ {pb.aigc_badge_outline(fs)}"
    assert shadow == pb.AIGC_LABEL_SHADOW_PX, f"样式阴影不是常量值: {shadow}"
    assert (ink_top, ink_bottom) == pb.aigc_badge_ink_bounds(w, h, mv), (
        "自测与 aigc_badge_ink_bounds 算出两条墨迹边界 → 有一处没跟上 ASS 语义")
    assert content_floor < ink_top < ink_bottom < subtitle_top, (
        f"角标 {ink_top:.0f}–{ink_bottom:.0f}px 没有落在内容下界({content_floor:.0f}px)"
        f"与字幕块顶({subtitle_top}px)之间")
    top_gap = ink_top - content_floor
    bottom_gap = subtitle_top - ink_bottom
    assert top_gap >= BADGE_BAND_MIN_GAP_PX and bottom_gap >= BADGE_BAND_MIN_GAP_PX, (
        f"与两侧间隙过窄: 上 {top_gap:.1f}px / 下 {bottom_gap:.1f}px"
        f"(线 {BADGE_BAND_MIN_GAP_PX}px; 整条带只有 {subtitle_top - content_floor:.0f}px)"
        " —— 改字号或字幕几何后必须重算 aigc_badge_margin_v")


def t_aigc_badge_landscape_band_yields_to_subtitles():
    # 横屏 1920×1080: 底部带只有 51px(字幕块顶 915 − 内容下界 864), 而角标墨迹连行盒
    # 下空白一共要 73.7px —— **装不下**, band_bounds 给 lo > hi。这里测的不是几何而是
    # 取舍方向: 宁可压进内容预留带, 也不压 burned 字幕。两层文字叠在一起两边都读不出,
    # 而预留带本来就是"版式内容不许进"的余量, 极端画面上侵占它比糊掉口播字幕轻。
    w, h = 1920, 1080
    lo, hi = pb.aigc_badge_band_bounds(w, h)
    assert lo > hi, (
        f"横屏这本该是「装不下」的样本, 实得 lo={lo} hi={hi}: 字幕几何或字号变了, 重看这条带")
    mv = pb.aigc_badge_margin_v(w, h)
    assert mv == lo, f"装不下时必须落在让开字幕的那一侧(lo), 实得 mv={mv}"
    subtitle_top = (h - int(h * pb.ASS_MARGIN_BOTTOM_H_FRAC)
                    - pb.CAPTION_MAX_LINES * pb.caption_font_size(h))
    content_floor = h * (1 - pb.layout_selfcheck.CAPTION_RESERVE_CQH / 100)
    ink_top, ink_bottom = pb.aigc_badge_ink_bounds(w, h, mv)
    assert ink_bottom <= subtitle_top - BADGE_BAND_MIN_GAP_PX, (
        f"退让后仍压字幕: 墨迹底 {ink_bottom:.1f} > 块顶 {subtitle_top} − 间隙")
    assert ink_top < content_floor, "侵占内容预留带是这条退让的**代价**, 必须看得见"
    assert mv < h * 0.25, f"横屏退让后角标已退出底角(mv={mv}), 不再是边角标识"


def t_aigc_metadata_shape_follows_gb45438():
    # 附录 E: 值 = {"AIGC":{七个要素}}, Label "1"=属于; 生产端三项传播字段留空占位。
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "silent.mp4")
        with open(f, "wb") as fh:
            fh.write(b"x" * 1024)
        raw = pb.aigc_metadata_json(pb.DEFAULT_AIGC_PRODUCER, f)
    meta = json.loads(raw)
    assert list(meta) == ["AIGC"], f"顶层必须只有 AIGC 一个键: {list(meta)}"
    inner = meta["AIGC"]
    assert set(inner) == {"Label", "ContentProducer", "ProduceID", "ReservedCode1",
                          "ContentPropagator", "PropagateID", "ReservedCode2"}, (
        f"要素集合不对: {sorted(inner)}")
    assert inner["Label"] == pb.AIGC_LABEL_VALUE == "1"
    assert inner["ContentProducer"] == pb.DEFAULT_AIGC_PRODUCER
    assert len(inner["ProduceID"]) == pb.AIGC_PRODUCE_ID_BYTES, (
        f"ProduceID 长度 {len(inner['ProduceID'])} != {pb.AIGC_PRODUCE_ID_BYTES}")
    assert len(inner["ReservedCode1"]) == pb.AIGC_INTEGRITY_CODE_BYTES
    assert inner["ContentPropagator"] == "" and inner["PropagateID"] == "" \
        and inner["ReservedCode2"] == "", "传播端三个字段生产方必须留空占位"


def t_aigc_metadata_is_ascii_only():
    # 值必须是 ASCII: 国标要求 GB 18030 字符集, ASCII 是其子集因此合法, 而中文直写
    # 一旦被搬进非 UTF-8 代码页就变成乱码字节 —— 乱码的标识等于没有标识。
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "s.mp4")
        with open(f, "wb") as fh:
            fh.write(b"y" * 64)
        raw = pb.aigc_metadata_json("某个中文主体名", f)
    assert raw.isascii(), f"元数据 JSON 含非 ASCII 字节: {raw[:80]}"
    assert " " not in raw, "JSON 里不许有空格(分隔符必须压掉, 命令行传输更稳)"
    # 中文主体名走 \uXXXX 转义: 落地字节全 ASCII, 但解析回来必须还是那几个字。
    # (反过来说: 断言"解析出来的值也 ASCII"是自欺 —— json.loads 早把转义还原了。)
    assert "\\u" in raw, f"非 ASCII 主体名未被转义: {raw[:80]}"
    assert json.loads(raw)["AIGC"]["ContentProducer"] == "某个中文主体名", (
        f"转义后语义丢失: {json.loads(raw)['AIGC']['ContentProducer']!r}")


def t_aigc_produce_id_is_content_derived():
    # ProduceID 取渲染产物内容哈希前缀: 同一片重跑稳定, 换片必变 —— 这才叫内容编号。
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        a, b = os.path.join(d, "a.mp4"), os.path.join(d, "b.mp4")
        with open(a, "wb") as fh:
            fh.write(b"same-bytes")
        with open(b, "wb") as fh:
            fh.write(b"other-bytes")
        j = lambda p: json.loads(pb.aigc_metadata_json("p", p))["AIGC"]["ProduceID"]
        assert j(a) == j(a), "同一内容哈希必须稳定"
        assert j(a) != j(b), "不同内容的 ProduceID 必须不同"


def t_aigc_label_cannot_be_turned_off():
    # 合规项不许有逃生门: 空 producer / 不足 2 秒, 都要停机而不是静默出无标片。
    msg = expect_error(pb.mux_and_burn, "s.mp4", [], [], "/tmp", "/tmp/f.mp4",
                       1080, 1920, aigc_badge_seconds=10.0, aigc_producer="")
    assert "不可关闭" in msg or "AIGC" in msg, f"停机文案不点名原因: {msg}"
    msg2 = expect_error(pb.mux_and_burn, "s.mp4", [], [], "/tmp", "/tmp/f.mp4",
                        1080, 1920, aigc_badge_seconds=1.5)
    assert "2" in msg2, f"短时长停机文案没说明国标 2 秒线: {msg2}"


def t_draft_badge_absent_but_subtitles_kept():
    # --draft 走的就是这条路: aigc_text=None ⇒ 一条 AIGC 事件都不挂, 而字幕照烧
    # (草稿要看的正是版式与字幕, 不该被顺手砍掉)。
    cues = [(0.0, 3.0, "第一屏\\N第二屏"), (3.0, 6.0, "另一句")]
    draft_ass = pb.build_ass(cues, 1080, 1920, aigc_text=None, aigc_seconds=4.0)
    assert ",AIGC," not in draft_ass, "草稿不许还挂着 AIGC 角标事件"
    assert draft_ass.count("Dialogue: 0,") == 2, (
        f"草稿必须照烧 {len(cues)} 条字幕, 实得 {draft_ass.count('Dialogue: 0,')}")
    full = pb.build_ass(cues, 1080, 1920, aigc_text=pb.AIGC_LABEL_TEXT, aigc_seconds=4.0)
    assert ",AIGC," in full, "非草稿必须挂上角标 —— 否则上面那条断言是空的"


def t_publish_gate_refuses_draft_and_missing_sidecar():
    # 发布闸门的判据表: 交付件(①② 都在)过, 草稿/无侧车/半成品全部拦下并点名缺哪件。
    deliverable = {
        "file": "final.mp4", "metadata_key": "AIGC",
        "implicit": {"AIGC": {"Label": "1"}},
        "explicit": {"burned_in": True, "text": pb.AIGC_LABEL_TEXT},
    }
    assert cpk.check(deliverable) == [], "齐活的交付件必须放行"
    assert cpk.check(None), "没有台账必须拦"
    draft = {"file": "probe.mp4", "draft": {"burned_in": False,
                                            "to_publish": "去掉 --draft 重渲"}}
    bad = cpk.check(draft)
    assert len(bad) == 1 and "draft" in bad[0], f"草稿要一条点名草稿的拦截: {bad}"
    # 半成品(有台账但没烧标 / 没元数据)各拦一条, 不许静默放行
    assert cpk.check({**deliverable, "explicit": {"burned_in": False}}), "未烧标必须拦"
    assert cpk.check({**deliverable, "metadata_key": None}), "无元数据台账必须拦"
    # 布尔位只认真 true: 字符串 "false" 与 1 都不算数(台账是 JSON 写的, 但老产物可能手改)
    assert cpk.check({**deliverable, "explicit": {"burned_in": "true"}}), "burned_in 必须是布尔 true"


def t_publish_gate_default_requires_declaration():
    # ③ 默认必带, 参数值必须是抖音弹窗**选项原文** —— 自己编一句「本视频由AI生成」
    # 平台上根本没有这个选项, 选了等于没选(上游只 warning 不阻断, 见 cli-contract.md)。
    assert cpk.DECLARATION_TEXT == "内容由AI生成", f"声明文案被改了: {cpk.DECLARATION_TEXT!r}"
    assert cpk.DECLARATION_PROOF == f"自主声明已选择「{cpk.DECLARATION_TEXT}」", (
        f"成功凭据与文案脱钩: {cpk.DECLARATION_PROOF!r}")
    # main() 里 --allow-undeclared 是唯一逃生门, 且默认关闭(用户口径: 默认都打开)
    import inspect
    src = inspect.getsource(cpk.main)
    assert '"--allow-undeclared"' in src and "action=\"store_true\"" in src, (
        "③ 的开关必须存在且默认 off")


def t_ffprobe_tag_entry_uses_format_tags():
    # 回归防线: `format=<键>` 取自定义元数据**不报错只返回空**, 拿它当核验等于
    # 核验永远失败。这里锁住命令行里用的是 format_tags。
    import inspect
    src = inspect.getsource(pb.ffprobe_format_tag)
    assert "format_tags=" in src, "ffprobe 取标签必须走 format_tags= 而不是 format="


# ---------------- 色板对比度审计(判据 6 的字面可读层) ----------------
def t_pack_contrast_docs_match_palette_math():
    # 每个 pack 的 frame.md 对比度表都必须能从 §2 色板原值复算出来。首次全量跑(2026-09-29)
    # 抓到 11 个包共 42 处手抄漂移, 最要命的是 news-blast: 文档写 `score / pitch 5.0`,
    # 真值 1.18, 而 §3 字阶据此把 22cqw 的主队比分染成红字压绿底 —— 审计拦的不是排版,
    # 是会播出看不清的巨号字的设计。
    bad = []
    for pack_dir in apc.discover_packs(apc.DEFAULT_PACKS_ROOT):
        _, findings = apc.audit_pack(pack_dir)
        bad += [f for f in findings if not f.warning]
    assert not bad, "frame.md 对比度表与色板复算不符: " + "; ".join(str(f) for f in bad[:6])


def t_contrast_auditor_catches_a_planted_wrong_ratio():
    # 反向判据: 上一条全绿也可能只是解析失效(读不到表就等于"没问题")。所以种一个错数,
    # 审计器自己必须被抓 —— 没有负例的校验器不算校验器。
    frame = (
        "## 2. 色板\n\n"
        "| token | 值 | 用途 |\n|---|---|---|\n"
        "| `ink` | `#1A1A1A` | 正文 |\n"
        "| `paper` | `#F5EFE3` | 底 |\n"
        "| `gold` | `#B8923E` | 强调 |\n\n"
        "| 组合 | 比值 | 判定 |\n|---|---|---|\n"
        "| ink / paper | 9.99 | ✓ 正文主力 |\n"
        "| gold / paper | 2.54 | ✓ 大字档 |\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        pack = Path(tmp) / "planted-pack"
        pack.mkdir()
        (pack / "frame.md").write_text(frame, encoding="utf-8")
        _, findings = apc.audit_pack(pack)
    rules = {f.rule for f in findings}
    assert "DOC_RATIO_DRIFT" in rules, f"抄错的比值没被抓出: {sorted(rules)}"
    assert "VERDICT_CONTRADICTS_ARITHMETIC" in rules, f"2.54 标成 ✓ 大字档没被抓出: {sorted(rules)}"


# ---------------- 自动选版词表(canonical 文件名词干) ----------------
def t_auto_layout_stems_are_the_only_vocabulary():
    # 词表 AUTO_LAYOUT_STEMS 是"文件名即版式身份"(决策 D9)的唯一出处。这里防的是**静默
    # 惰性**: 词表外的名(11 个 pack 的 frame.md §7 里那些 list-steps / score / diagram)
    # 既不会报错也永远选不到, 只有测试会让它当场红。
    import inspect
    src = inspect.getsource(pb.choose_layout)
    named = set(re.findall(r'\(\s*"([a-z][a-z_-]*)"\s*,', src))
    vocab = set(pb.AUTO_LAYOUT_STEMS)
    assert named <= vocab, f"choose_layout 把词表外的名放进了自动候选: {sorted(named - vocab)}"
    assert named == vocab, f"词表与形态优先级表脱节: 这些词干永不被优先点名 {sorted(vocab - named)}"
    for pack_name in pb.ready_packs():
        stems = set(pb.load_style_pack(pack_name)["layouts"])
        assert stems <= vocab, f"{pack_name} 交出自动模式选不到的版式: {sorted(stems - vocab)}"

if __name__ == "__main__":
    tests = [(name, fn) for name, fn in sorted(globals().items())
             if name.startswith("t_") and callable(fn)]
    print(f"[selftest] {len(tests)} 项 · style={PACK['name']}")
    for name, fn in tests:
        check(name, fn)
    if FAILURES:
        print(f"[selftest] 失败 {len(FAILURES)}/{len(tests)}")
        sys.exit(1)
    print(f"[selftest] 全绿 {len(tests)}/{len(tests)}")
