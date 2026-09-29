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
  (纯函数部分, 网络那一层由 --check-only 的真跑覆盖)。
"""

import json
import os
import re
import sys
import urllib.error  # 只用来造 HTTPError/URLError 实例喂 should_retry(不打网络)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
    """单个模板的 pack; frame.md 在但 host.html 缺则返回 None (= 待落地)。"""
    pack_dir = os.path.join(pb.TEMPLATE_ROOT, name)
    host_path = os.path.join(pack_dir, "host.html")
    if not (os.path.isdir(pack_dir) and os.path.isfile(host_path)):
        return None
    return pb.load_style_pack(name)

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
    # 报告当前已完整加载 (host<->compositions 都齐) 的 pack 数量, 便于看进度。
    full = sum(1 for p in TEMPLATE_PACKS.values() if p is not None)
    print(f"      12 pack 中已完整加载 (host.html 在位) 的: {full}/12")
    # 当前期望: 1 (只有 news-coral 完整)。后续 composition 落地后此值递增。

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
