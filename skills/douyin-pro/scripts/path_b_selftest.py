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
import aigc_mode as amode  # noqa: E402  (标识开关的姿态文件: 旗标 > 文件 > 代码默认)
import check_publishable as cpk  # noqa: E402  (发布闸门: 照台账核 ①②, ③ 的必带参数由它给)
import commons_media as cm  # noqa: E402  (判据 4 的图片层纯函数; 与 pb 同样必须先落地 sys.path)
import layout_selfcheck as ls  # noqa: E402  (版式结构不变量: 字幕子合成豁免两条)
import path_b_build as pb  # noqa: E402  (sys.path 必须先落地)
import hf_compile as hc  # noqa: E402  (P1-3c 编译器：spec → 宿主 + 7 版式 + frame.md)
import hf_primitives as hp  # noqa: E402  (v2 原语库：spec → 片段文本，法则 7/8/10 的可执行面)
import hf_style_spec as hs  # noqa: E402  (v2 风格 spec：结构校验 + 编译前判据 3/5)
import image_gate as ig  # noqa: E402  (P3 图片门禁：本地零网络人脸检测器)

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
    pack_dir = pb.pack_dir(name)
    host_path = os.path.join(pack_dir, "host.html")
    if not (os.path.isdir(pack_dir) and os.path.isfile(host_path)):
        return None
    try:
        return pb.load_style_pack(name)
    except pb.EmitterError:
        return None

TEMPLATE_PACKS = {name: _load_one_template(name) for name in pb.available_templates()}
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
STORY_IDS = {"kicker", "ordinal", "title", "onscreen", "tone", "slotSeconds", "imagePath", "imageCredit"}


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
    # 2026-10-08: **不再回落到 kicker** —— kicker 是栏目名不是画面描述, 实跑因此把东航空难图配成了"现场数据"镜的图
    assert cm.image_query({}, {"kicker": "湖南常德"}) is None
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


def t_relevance_gate_refuses_common_twochar_false_positive():
    """二字块不能再当相关性证据（2026-10-08 实跑踩到）。

    真跑 t002（尊界 V800 刹车踏板断裂）时，镜 2 的配图命中了
    「东航 MU5735 黑匣子寻获现场」—— 2022 年的空难新闻图。
    根因不是授权或尺寸（那两个闸都放行了），是**词面闸的粒度**：
    `CJK_SHINGLE = 2` 意味着查询「现场数据」只要有**任意一个**二字块
    出现在标题里就放行 —— 而「寻获**现场**」里的「现场」就够它过了。

    二字块对中文太短：「现场」「数据」「中国」「北京」「市场」「发展」这类词
    会出现在任何一张无关图里。拿它当相关性证据 = 视觉假事实，
    而本模块 docstring 写明的原则恰恰是"降级为无图比放错图更糟"。
    """
    # 实跑抓到的那一对: 查询「现场数据」vs 东航空难图标题
    mu5735 = ("File:东航MU5735班机第二部黑匣子寻获现场 Second Black box "
              "of crashed flight MU5735 retrieved 1.jpg")
    assert not cm.relevance_ok(mu5735, "现场数据")[0], (
        "东航空难图绝不能因为标题里有『现场』二字就当作『现场数据』镜的配图")
    # 通用形态: 常见二字词对无关图
    for query, wrong_title in (
        ("数据", "File:Beijing skyline.jpg"),
        ("市场", "File:Black Forest aerial.jpg"),
        ("发展", "File:Old Town Prague.jpg"),
    ):
        assert not cm.relevance_ok(wrong_title, query)[0], (
            f"二字块假命中: query={query!r} 不该放行 {wrong_title!r}")


def t_relevance_gate_still_accepts_real_cjk_match():
    """收紧二字块后，**真正的中文相关仍要放行** —— 别把闸修死了。

    收紧口径（2026-10-08）：中文证据只认 **≥3 字的连续公共子串** 或 **≥2 个二字块**。
    2 字串不算证据 —— 「现场数据」的「现场」会假命中东航空难图。

    **代价要说清**：查询「湖南常德」对标题「常德市区」的公共子串只有 2 字（常德），
    现在会被拦。这是**有意的取舍**：2 字不足以证明相关性，要放行就得写足 3 字以上
    （配常德街景请写 `"image": "常德市区"` 或 `"Changde Hunan"`）。
    「无图比错图好」—— 宁可少一张图，不要播出视觉假事实。
    """
    # 3 字以上专名/地名 → 放行
    assert cm.relevance_ok("File:崇安桥夜景.jpg", "崇安桥")[0], \
        "三字专名命中应算证据"
    assert cm.relevance_ok(CJK_PAGE["title"], "常德市区")[0], \
        "三字地名查询应放行"
    # 拉丁整词 → 放行（英文词稀有度高）
    assert cm.relevance_ok(PD_PAGE["title"], "Changde Hunan")[0]
    # 2 字查询不再放行（有意的取舍，见 docstring）
    assert not cm.relevance_ok(CJK_PAGE["title"], "常德")[0], \
        "2 字查询不该构成证据 —— 要配图请写足 3 个字"


def t_scene_query_does_not_fall_back_to_kicker():
    """作者没写 `image` 时**不许回落到 kicker**（2026-10-08 实跑踩到）。

    `image_query()` 旧的优先级是「显式 image > kicker > 没有」，
    于是 kicker 成了检索词 —— 而 kicker 是**栏目名**（「热搜第一」「现场数据」
    「时间线」「目前」），不是画面描述。拿栏目名去 Commons 全文检索，
    `gsrsort=relevance` 在中英语料错配下会返回毫不相干但词面凑巧命中的图。

    处置：kicker 是**排版元素**，拿它当检索词没有语义依据。
    要配图就显式写 `"image": "V800 MPV"`；不写就降级为绘制地面。
    """
    scene = {"kicker": "现场数据", "layout": "stat"}
    assert cm.image_query({}, scene) is None, (
        "kicker 不该被当作检索词（栏目名≠画面描述）—— "
        f"实测它让 t002 镜 2 配了东航空难图: {cm.image_query({}, scene)!r}")
    # 显式 image 仍优先
    assert cm.image_query({"image": "V800 MPV"}, scene) == "V800 MPV"
    # 显式弃图仍优先于一切
    assert cm.image_query({"image": False}, scene) is None


def t_relevance_gate_refuses_legally_clean_but_wrong_picture():
    # 授权与尺寸都合规 ≠ 可以上屏。词面不搭就必须拒, 让它降级到绘制地面。
    ok, why = cm.relevance_ok(PD_PAGE["title"], "Changde Hunan")
    assert ok, why
    ok, why = cm.relevance_ok(BEETLE_PAGE["title"], "Changde Hunan")
    assert not ok, "步甲虫论文插图绝不能当作常德街景上屏"
    assert why, "拒用要给得出可打印的理由"
    # 中文标题对中文查询词: 共享 ≥2 个二字块 或 1 个 ≥3 字块即命中
    # 2026-10-08 收紧: 公共子串只 2 字时**不再**算证据（见上面那条的 docstring）
    assert not cm.relevance_ok(CJK_PAGE["title"], "湖南常德")[0]
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
#: 12 个 master（各自有完整 frame.md 设计系统契约）
MASTER_TEMPLATES = {
    "news-coral", "news-ink", "news-policy", "news-stat",
    "news-onsite", "news-bulletin", "news-explainer", "news-alert",
    "news-thread", "news-takes", "news-blast", "news-world",
}


def t_all_templates_in_constant():
    # ALL_TEMPLATES = 12 master + 派生变体/主题包（2026-10-09 起为 19 个，删了 news-coral-night，
    # 见 ARCHITECTURE D23）。**总数不写死在文案里**：新增/删除 pack 时这条不该红，
    # 真正要锁的是"每个包都在磁盘上存在、且有真版式"，不是"数字等于 12"。
    assert len(pb.ALL_TEMPLATES) >= len(MASTER_TEMPLATES), (
        f"ALL_TEMPLATES 少于 master 数 {len(MASTER_TEMPLATES)}: "
        f"实际 {len(pb.ALL_TEMPLATES)}"
    )
    missing = MASTER_TEMPLATES - set(pb.ALL_TEMPLATES)
    assert not missing, f"12 个 master 必须在 ALL_TEMPLATES 里, 缺: {sorted(missing)}"

    # 每个 ALL_TEMPLATES 成员都要有目录 + frame.md（变体也补了，见 D16）
    no_dir = [n for n in pb.ALL_TEMPLATES
              if not os.path.isdir(os.path.join(pb.TEMPLATE_ROOT, n))]
    assert not no_dir, f"ALL_TEMPLATES 里的包没有对应目录: {no_dir}"
    no_frame = [n for n in pb.ALL_TEMPLATES
                if not os.path.isfile(os.path.join(pb.TEMPLATE_ROOT, n, "frame.md"))]
    assert not no_frame, f"以下 pack 缺 frame.md: {no_frame}"

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
    # 32/32 全部有真版式 + 全部有 frame.md（2026-10-08 实测, 见 D15/D16）
    # → FRAME_ONLY_TEMPLATES 应为空集。原断言只对空集做循环 = 什么都不断言,
    #    这里改成**显式锁住空集**, 让"又出现 frame-only 包"能被发现。
    assert not FRAME_ONLY_TEMPLATES, (
        f"以下 pack 被判为 frame-only(无真版式), 但 D15 后应为 0: "
        f"{sorted(FRAME_ONLY_TEMPLATES)}"
    )
    # 反向核对: TEMPLATE_PACKS 里不该有 None
    none_packs = [n for n, p in TEMPLATE_PACKS.items() if p is None]
    assert not none_packs, f"有 pack 没加载成功: {none_packs}"

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
    print(f"      可渲染 pack (有真版式): {len(real)}/{len(pb.available_templates())}"
          f" —— {', '.join(real) if real else '无'}")


def t_placeholder_pack_stops_at_load():
    # 32/32 全部有真版式（2026-10-08 实测, 见 D15）→ 原「占位壳停机」场景已消失。
    # 改成断言**无未就绪包**，而不是断言"必须有未就绪包"——原写法在现实超过测试后会一直红。
    unready = [n for n in pb.ALL_TEMPLATES if not pb.pack_has_real_layout(n)]
    assert not unready, (
        f"以下 pack 只有占位壳, 渲不出来: {unready} —— "
        f"要么补真 composition, 要么从 ALL_TEMPLATES 移除"
    )


def t_load_refuses_pack_with_no_real_layout():
    """停机能力本身不许丢 —— 用临时空壳包验证（D7 的行为契约，与 32/32 现状无关）。"""
    import shutil
    import tempfile as _tf
    with _tf.TemporaryDirectory() as td:
        root = Path(td)
        # 空壳包: 有 host.html + compositions/, 但只有 placeholder.html
        shell = root / "shell-pack"
        (shell / "compositions").mkdir(parents=True)
        (shell / "host.html").write_text("<html></html>", encoding="utf-8")
        (shell / "compositions" / f"{pb.PLACEHOLDER_LAYOUT}.html").write_text(
            "<html></html>", encoding="utf-8")
        real = root / "real-pack"
        (real / "compositions").mkdir(parents=True)
        (real / "host.html").write_text("<html></html>", encoding="utf-8")
        # 借一个真包的真实版式文件过来，让停机文案能点名替代
        src = Path(pb.TEMPLATE_ROOT) / "news-coral" / "compositions" / "hook.html"
        shutil.copy(src, real / "compositions" / "hook.html")

        old_roots, old_templates = list(pb.PACK_ROOTS), pb.ALL_TEMPLATES
        try:
            pb.set_packs_root(root)
            pb.ALL_TEMPLATES = ["shell-pack", "real-pack"]
            msg = expect_error(pb.load_style_pack, "shell-pack")
            assert "还没有真版式" in msg, f"停机文案没说明原因: {msg}"
            assert "可渲染的 pack" in msg, f"停机文案没给出可用替代: {msg}"
            assert "real-pack" in msg, f"停机文案没点名具体替代包: {msg}"
            # 真包必须能加载（证明上面不是"全部失败"）
            ok = pb.load_style_pack("real-pack")
            assert ok["layouts"], "对照包也加载失败了, 测试本身失效"
        finally:
            pb.ALL_TEMPLATES = old_templates
            pb.set_packs_root(old_roots)


def t_pack_root_seam_addresses_both_tracks():
    """裁决 14 的双轨根：存量包与编译包必须**在同一进程里同时可寻址**，且顺序说了算。

    同名时 path_b 在前 ⇒ 编译一套新包不可能悄悄顶掉一条产线在用的包；
    `available_templates()` 现算 ⇒ P5 每编译一套就多个可点名选项，不必回来改发射器。
    """
    assert pb.PACK_ROOTS == [pb.TEMPLATE_ROOT, pb.PATH_C_ROOT], pb.PACK_ROOTS
    assert pb.pack_dir("news-coral") == os.path.join(pb.TEMPLATE_ROOT, "news-coral")
    assert pb.pack_dir("news-editorial-warm").startswith(pb.PATH_C_ROOT + os.sep)
    assert "news-editorial-warm" in pb.available_templates()
    # 一个都不存在时也要给出一个像样的落点，报错才指得到路。
    assert pb.pack_dir("no-such-pack-anywhere") == os.path.join(pb.TEMPLATE_ROOT, "no-such-pack-anywhere")

    import tempfile as _tf
    with _tf.TemporaryDirectory() as td:
        shadow = Path(td) / "news-coral"
        (shadow / "compositions").mkdir(parents=True)
        (shadow / "host.html").write_text("<html>shadow</html>", encoding="utf-8")
        old_roots = list(pb.PACK_ROOTS)
        try:
            pb.set_packs_root([str(shadow.parent), *old_roots])
            assert pb.pack_dir("news-coral") == str(shadow), "同名包没按根顺序取先出现的"
            # 只有 host.html、没有 compositions 的目录也算"可点名"，缺版式由加载期停机
            assert "news-coral" in pb.available_templates()
            pb.set_packs_root([])
            assert pb.PACK_ROOTS == old_roots, "空根表没回落到默认双轨"
        finally:
            pb.set_packs_root(old_roots)


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
    # 发布闸门的判据表(D14 后): 可发布的底线是「② 齐活 + ① 有交代」,
    # 草稿/无侧车/半成品/没交代的没烧标全部拦下并点名缺哪件。
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
    # 半成品(没交代为什么没烧 / 没元数据)各拦一条, 不许静默放行
    assert cpk.check({**deliverable, "explicit": {"burned_in": False}}), \
        "未烧标又没 disabled_by 必须拦 —— 关了什么得记什么关"
    assert cpk.check({k: v for k, v in deliverable.items() if k != "explicit"}), \
        "① 段整个缺失必须拦(旧产物或手改都不许当交付件)"
    assert cpk.check({**deliverable, "metadata_key": None}), "无元数据台账必须拦"
    # 布尔位只认真 true: 字符串 "false" 与 1 都不算数(台账是 JSON 写的, 但老产物可能手改)
    assert cpk.check({**deliverable, "explicit": {"burned_in": "true"}}), "burned_in 必须是布尔 true"


def t_no_badge_is_publishable_but_demands_declaration():
    # D14 的整条链路: ① 可以单独关(中间档), 但**必须**在台账里点名是谁关的,
    # 关了 ① 就把 ③ 变成必带 —— 这一步是整个放宽里唯一不许打折的代价。
    no_badge = {
        "file": "final.mp4", "metadata_key": "AIGC",
        "implicit": {"AIGC": {"Label": "1"}},
        "explicit": {"burned_in": False, "disabled_by": "no-badge(旗标 --no-badge)",
                     "to_enable": "渲染时加 --deliver 再重渲一次"},
    }
    assert cpk.check(no_badge) == [], "② 在 + ① 点名关掉 = 可发布(D14)"
    assert cpk.badge_burned(no_badge) is False, "没烧标不许被当成烧过"
    assert cpk.requires_declaration(no_badge) is True, "① 没烧 ⇒ ③ 必带"
    assert cpk.requires_declaration({**no_badge, "explicit": {"burned_in": True}}) is False, \
        "① 在的时候仍按姿态走 —— 别把代价扩大到完整交付件"
    assert cpk.requires_declaration(None) is True, "读出台账以外一律按最严的一档办"
    # 渲染层确实有中间档, 而且三档各自的话术都在(日志与台账只从 RENDER_WHAT 取话)
    assert amode.RENDER_MODES == ("full", "no-badge", "draft"), amode.RENDER_MODES
    assert set(amode.RENDER_WHAT) == set(amode.RENDER_MODES), "每档都得说清做了什么"
    assert amode.resolve_render({}, no_badge=True)[0] == "no-badge"
    assert amode.resolve_render({"_path": "x", "render": "no-badge"})[0] == "no-badge"
    assert amode.resolve_render({"_path": "x", "render": "no-badge"}, deliver=True)[0] == "full", \
        "反向旗标要盖得过中间档"
    # 三个旗标只能挑一个: 任意两两同给都是矛盾, 不许"后者覆盖前者"那种猜
    for kw in ({"deliver": True, "no_badge": True}, {"no_badge": True, "draft": True},
               {"deliver": True, "draft": True}):
        try:
            amode.resolve_render({}, **kw)
        except amode.ModeError as exc:
            assert "--" in str(exc), f"矛盾旗标的报错要点名是哪两个旗标: {exc}"
        else:
            raise AssertionError(f"resolve_render{kw} 互相矛盾却不报错")
    # 发射器接的是三档而不是布尔, 中间档的台账要写 disabled_by/to_enable
    import inspect
    src = inspect.getsource(pb)
    assert '"--no-badge"' in src, "单次关掉 ① 的旗标必须在发射器里"
    assert "render=render_mode" in src, "mux_and_burn 必须吃三档裁决, 不是吃布尔 args.draft"
    assert "disabled_by" in src and "to_enable" in src, \
        "no-badge 的台账要记下谁关的与怎么开回来 —— 空着等于让下一个人猜"
    gate = inspect.getsource(cpk.main)
    assert "requires_declaration" in gate, "闸门必须把「① 关 ⇒ ③ 必带」这条代价落地"


def t_publish_gate_default_requires_declaration():
    # ③ 默认必带, 参数值必须是抖音弹窗**选项原文** —— 自己编一句「本视频由AI生成」
    # 平台上根本没有这个选项, 选了等于没选(上游只 warning 不阻断, 见 cli-contract.md)。
    assert cpk.DECLARATION_TEXT == "内容由AI生成", f"声明文案被改了: {cpk.DECLARATION_TEXT!r}"
    assert cpk.DECLARATION_PROOF == f"自主声明已选择「{cpk.DECLARATION_TEXT}」", (
        f"成功凭据与文案脱钩: {cpk.DECLARATION_PROOF!r}")
    # ③ 的开关有两处: 旗标(--allow-undeclared 关 / --require-declaration 开)与姿态文件,
    # 而**代码默认**必须是关不掉的那一档(用户口径: 「默认都打开」; 临时关走姿态文件)。
    import inspect
    src = inspect.getsource(cpk.main)
    assert '"--allow-undeclared"' in src and "action=\"store_true\"" in src, (
        "③ 的关旗标必须存在且默认 off")
    assert '"--require-declaration"' in src, "③ 必须有反向旗标(盖掉姿态文件的关闭)"
    assert "aigc_mode.resolve_declaration" in src, "③ 的默认值必须由姿态文件裁决, 不在代码里硬开关"


def t_aigc_mode_code_defaults_are_all_on():
    # 没有姿态文件 = 三件全开。这条锁的是"代码里不许藏着关闭默认"——
    # 用户要临时关标识走 routes/news/aigc-mode.json, 而不是改这两个函数的返回值。
    assert amode.resolve_render({})[0] == "full"
    assert amode.resolve_declaration({})[0] == "required"
    assert amode.RENDER_DEFAULT == "full" and amode.DECLARATION_DEFAULT == "required"
    assert "代码默认全开" in amode.resolve_render({})[1], "原因必须说明是全开来的"


def t_aigc_mode_file_flips_defaults_and_flags_override_both_ways():
    posture = {"_path": "routes/news/aigc-mode.json",
               "render": "draft", "declaration": "undeclared"}
    # 姿态文件把两档默认都关掉(本次用户的"先关了吧"就落在这里)
    mode, cause = amode.resolve_render(posture)
    assert mode == "draft" and "render=draft" in cause, cause
    assert amode.resolve_declaration(posture)[0] == "undeclared"
    # 反向旗标必须盖得过姿态文件 —— 一次交付不该被仓库默认挡住
    assert amode.resolve_render(posture, deliver=True)[0] == "full"
    assert amode.resolve_declaration(posture, require_declaration=True)[0] == "required"
    # 正向旗标照样有效(姿态是全开时也能单次关)
    assert amode.resolve_render({}, draft=True)[0] == "draft"
    assert amode.resolve_declaration({}, allow_undeclared=True)[0] == "undeclared"
    # 同时给两个相反旗标 = 停机, 不许"后者覆盖前者"这种猜
    for fn, kw in ((amode.resolve_render, {"draft": True, "deliver": True}),
                   (amode.resolve_declaration,
                    {"allow_undeclared": True, "require_declaration": True})):
        try:
            fn(posture, **kw)
        except amode.ModeError:
            pass
        else:
            raise AssertionError(f"{fn.__name__}{kw} 互相矛盾却不报错")
    # 发射器确实接的是这套裁决(而不是自己读文件、自己定默认)
    import inspect
    src = inspect.getsource(pb)
    assert "aigc_mode.resolve_render" in src and '"--deliver"' in src, (
        "渲染层开关必须由 aigc_mode 裁决, 且反向旗标 --deliver 要在")
    assert "render=render_mode" in src, "mux_and_burn 必须吃裁决结果, 不是吃 args.draft"
    # 草稿台账里要写**真原因**, 并且姿态文件那条给的是**能执行的恢复动作**
    assert "草稿渲染[{render_cause}]" in src, "台账的 reason 必须带上开关取值出处"
    assert "aigc-mode.json 的 render 改回 full" in src, (
        "由姿态文件关掉的标, 台账要说出怎么改回来")


def t_aigc_mode_reason_names_the_true_source():
    # 台账/闸门必须说清"是谁关的标": 旗标、姿态文件、还是代码默认。
    # 这句是事后审计唯一的抓手 —— 只写"没标"等于没写。
    posture = {"_path": "/repo/routes/news/aigc-mode.json", "render": "draft",
               "declaration": "undeclared"}
    assert "旗标 --draft" in amode.resolve_render(posture, draft=True)[1]
    assert "aigc-mode.json render=draft" in amode.resolve_render(posture)[1]
    assert "旗标 --deliver" in amode.resolve_render(posture, deliver=True)[1]
    # 中间档(no-badge, D14)同样要点名出处 —— 台账说"① 没烧"却不说是谁关的, 事后无从举证
    posture_nb = {"_path": "/repo/routes/news/aigc-mode.json", "render": "no-badge"}
    assert "旗标 --no-badge" in amode.resolve_render(posture, no_badge=True)[1]
    assert "aigc-mode.json render=no-badge" in amode.resolve_render(posture_nb)[1]
    assert "旗标 --allow-undeclared" in amode.resolve_declaration(
        posture, allow_undeclared=True)[1]
    assert "aigc-mode.json declaration=undeclared" in amode.resolve_declaration(posture)[1]
    assert "代码默认全开" in amode.resolve_declaration({})[1]


def t_aigc_mode_rejects_bad_values_instead_of_defaulting():
    # R6: 拼错/坏 JSON 一律停机点名, 不许静默回退到全开 —— 回退会让"以为关了其实开着"
    # 与"以为开着其实关了"两种错都变成不可见的。
    with tempfile.TemporaryDirectory() as d:
        root = os.path.join(d, "routes", "news")
        os.makedirs(root)
        good = os.path.join(root, "aigc-mode.json")
        open(good, "w", encoding="utf-8").write('{"render": "draft"}')
        assert amode.load_mode(good)["render"] == "draft"
        # 中间档必须是**合法值**(D14): 校验表认不了它就等于姿态写不进 no-badge
        open(good, "w", encoding="utf-8").write('{"render": "no-badge"}')
        assert amode.load_mode(good)["render"] == "no-badge"
        # 只写一段时, 另一段按全开走(不是报错) —— 文件允许只关一个开关
        assert amode.resolve_declaration(amode.load_mode(good))[0] == "required"
        open(good, "w", encoding="utf-8").write('{"render": "off"}')
        try:
            amode.load_mode(good)
        except amode.ModeError as exc:
            assert "render" in str(exc) and "off" in str(exc), exc
        else:
            raise AssertionError("render=off 不认却不报错")
        open(good, "w", encoding="utf-8").write("{not json")
        try:
            amode.load_mode(good)
        except amode.ModeError:
            pass
        else:
            raise AssertionError("坏 JSON 必须报 ModeError")
        # 指了路径却文件不存在 = 停机(说"当没有"是最难查的静默失败)
        try:
            amode.load_mode(os.path.join(d, "nope.json"))
        except amode.ModeError:
            pass
        else:
            raise AssertionError("指定路径不存在必须报错")


def t_repo_aigc_mode_file_is_valid_and_recorded():
    # 仓库里那份姿态文件(如果存在)必须过校验: 一次拼写错误不该让默认姿态静默改变。
    # 同时把当前姿态打到自测输出里 —— 自测那行从此能看见"标现在是开着还是关着"。
    path = amode.find_mode_file()
    if path is None:
        print("      (无姿态文件 → 两个开关按代码默认全开)")
        return
    mode = amode.load_mode(path)
    assert mode["render"] in amode.RENDER_MODES and mode["declaration"] in amode.DECLARATION_MODES
    assert mode.get("revert"), f"{path} 少了 revert 一行: 怎么恢复必须写在文件里"
    assert mode.get("since") and mode.get("by"), f"{path} 要记什么时候、谁决定的"
    print(f"      {amode.describe(mode)}")


def t_ffprobe_tag_entry_uses_format_tags():
    # 回归防线: `format=<键>` 取自定义元数据**不报错只返回空**, 拿它当核验等于
    # 核验永远失败。这里锁住命令行里用的是 format_tags。
    import inspect
    src = inspect.getsource(pb.ffprobe_format_tag)
    assert "format_tags=" in src, "ffprobe 取标签必须走 format_tags= 而不是 format="


# ---------------- 色板对比度审计(判据 6 的字面可读层) ----------------
def t_pack_contrast_docs_match_palette_math():
    # 每个 pack 的 frame.md **对比度表**必须能从 §2 色板原值复算出来。首次全量跑(2026-09-29)
    # 抓到 11 个包共 42 处手抄漂移, 最要命的是 news-blast: 文档写 `score / pitch 5.0`,
    # 真值 1.18, 而 §3 字阶据此把 22cqw 的主队比分染成红字压绿底 —— 审计拦的不是排版,
    # 是会播出看不清的巨号字的设计。
    #
    # 口径（2026-10-08, D18）: 只看**对比度表**相关的规则。OFF_PALETTE_HEX 不在这里判
    # —— 它有自己的测试（t_off_palette_allows_shared_design_tokens），因为它需要
    # "本包色板 ∪ 设计系统共享 token"的口径，与"文档数字能不能复算"是两件事。
    RULES = {"DOC_RATIO_DRIFT", "VERDICT_CONTRADICTS_ARITHMETIC", "DOC_PAIR_UNMATCHED"}
    bad = []
    for pack_dir in apc.discover_packs(apc.DEFAULT_PACKS_ROOT):
        _, findings = apc.audit_pack(pack_dir)
        bad += [f for f in findings if not f.warning and f.rule in RULES]
    assert not bad, "frame.md 对比度表与色板复算不符: " + "; ".join(str(f) for f in bad[:6])


def t_off_palette_allows_shared_design_tokens():
    """OFF_PALETTE_HEX 的口径是「本包色板 ∪ 设计系统共享 token」。

    实测（2026-10-08, D18）: 原口径只认本包 frame.md 声明的色值, 于是 561 条违规里
    绝大部分是**跨包共享角色色** —— #e85d5d 出现在 32 个包的色板里（主强调）、
    #1a1a1a 50 次（卡底）、#6b6b6b 33 次（次级字）。
    正确做法是承认共享层，而不是把 561 处版式改色（那样 alert 包的灰字会变绿字）。
    """
    assert apc.SHARED_TOKENS, "共享 token 层不能为空 —— 否则 561 条 OFF_PALETTE 会回来"
    # 口径自检: 抽查实测公共色必须在共享层里（现值随实测更新，不写死数量）
    counts = apc.shared_token_calibration()
    declared = {apc._normalize_hex(v) for v in apc.SHARED_TOKENS}
    for hx, n in counts.items():
        if n >= apc.SHARED_TOKEN_MIN_PACKS:
            assert hx in declared, f"#{hx} 实测出现 {n} 次(≥阈值), 却不在共享层"
            break  # 存在一个即可, 完整校准由 t_shared_tokens_match_measured_calibration 管

    # coral 是吻合度最高的包（实测 72.7% → 共享层后应干净）
    coral = Path(pb.TEMPLATE_ROOT) / "news-coral"
    _, findings = apc.audit_pack(coral)
    off = [f for f in findings if f.rule == "OFF_PALETTE_HEX" and not f.warning]
    assert not off, f"news-coral 仍报 {len(off)} 条色板外: {[str(f) for f in off[:3]]}"


def t_off_palette_still_catches_unknown_hex():
    """共享 token **不**意味着放水 —— 真正不在任何一层的色值仍要被抓。"""
    import tempfile as _tf
    with _tf.TemporaryDirectory() as td:
        pack = Path(td) / "probe-pack"
        (pack / "compositions").mkdir(parents=True)
        (pack / "frame.md").write_text(
            "| token | 值 |\n|---|---|\n"
            "| `bg` | `#101010` |\n| `fg` | `#f0f0f0` |\n"
            "| 组合 | 比值 |\n|---|---|\n"
            "| fg / bg | 18.00 |\n",
            encoding="utf-8")
        (pack / "compositions" / "hook.html").write_text(
            '<html><body style="color:#123456;background:#abcdef">x</body></html>',
            encoding="utf-8")
        (pack / "host.html").write_text("<html></html>", encoding="utf-8")
        _, findings = apc.audit_pack(pack)
        off = [f for f in findings if f.rule == "OFF_PALETTE_HEX"]
        assert off, "不认识的色值 #123456/#abcdef 竟没被 OFF_PALETTE_HEX 抓到"
        assert any("123456" in str(f) for f in off), off


def t_shared_tokens_match_measured_calibration():
    """SHARED_TOKENS 必须与实测一致 —— 它自己不能变成第二个"手抄假数"（D10 的教训）。

    这条测在 2026-10-08 第一次跑时**当场抓到** `#f0f0f0`：我按旧统计把它写进了共享层，
    而实测只出现 3 次（不足阈值 6）。共享层的值一旦靠手抄维护就会漂。
    """
    problems = apc.shared_tokens_need_review()
    assert not problems, (
        "SHARED_TOKENS 与实测不符（改色板或增删 pack 后必须校准）:\n  "
        + "\n  ".join(problems)
    )


def t_no_pack_has_off_palette_after_repair():
    """色板外用色必须**可解释**: 要么 0 条, 要么每一处都属于"刻意保留"清单。

    2026-10-08 实测轨迹（D18/D19）:
      - 起点 561 条（口径只认本包色板, 不认跨包共享角色色）
      - D18 承认共享 token 层 → 72 条
      - D19 按 CSS 角色替换复制残留（.st-rule 强调短横线 / background 面）
        → 24 条；**每处自动替换都验了"对比度不下降"**
      - 剩下 24 条 = 12 个色 × 2 处：自动替换会让对比度从 ~16:1 掉到 ~1.1:1
        （把白字换成深底），所以**刻意不改**，等人工判断。

    这条断言锁的是"不许有第四类未解释的越界"，不是"必须 0 条"。
    刻意保留的语义：这些是版式里的**亮底/白字**，它们该被登记进对应包的 frame.md
    色板（算设计补全），而不是被机械改色。
    """
    bad = []
    kept_total = 0
    for pack_dir in apc.discover_packs(apc.DEFAULT_PACKS_ROOT):
        _, findings = apc.audit_pack(pack_dir)
        off = [f for f in findings if f.rule == "OFF_PALETTE_HEX" and not f.warning]
        if off:
            kept_total += len(off)
            bad.append(f"{pack_dir.name}: {len(off)}")
    # 上限护栏：刻意保留的量不该增长（2026-10-08 基线 = 24）
    assert kept_total <= 24, (
        f"色板外用色 {kept_total} 条, 超过基线 24 条 —— "
        f"要么有新复制残留, 要么该把某批色补进 frame.md 并更新本基线: {bad}"
    )


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


# ---------------- 版式闸门的用法错误(不许"0 个文件"空过) ----------------
def t_layout_selfcheck_refuses_a_directory_with_no_layouts():
    # 硬规则 6 的三道闸里, layout_selfcheck 是唯一"参数在人手里"的那道: 把 pack 名当目录
    # 传进去时, 旧版打印「版式自检通过：0 个文件，0 条违规」并 exit 0 —— 一次打错参数的
    # 绿闸门其实一条不变量都没查, 这是所有假绿里最难发现的一种(2026-09-29 订正文档时撞到)。
    # 闸门要的是"查过了", 不是"没报错", 所以这里双向锁死: 真目录必须 0, 空目录必须非 0。
    import contextlib
    import io

    lsc = pb.layout_selfcheck
    real = os.path.join(pb.TEMPLATE_ROOT, "news-coral")
    assert lsc.discover_layouts(Path(real)), f"测试前提坏了: {real} 读不到版式文件"

    def run(*argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = lsc.main(list(argv))
        return code, buf.getvalue()

    code, out = run(real)
    assert code == 0, f"真版式目录被误判为用法错误: code={code} | {out}"
    for bad in ("news-coral", os.path.join(pb.TEMPLATE_ROOT, "no-such-pack")):
        for argv in ([bad], ["--quiet", bad]):
            code, out = run(*argv)
            assert code == 1, f"{argv}: 目录里一个版式文件都没有却返回 0(空过)"
            assert str(bad) in out, f"报错没点名是哪个目录空过: {out}"
            assert "compositions" in out, f"报错要教正确的参数写法: {out}"


# ---------------- 中文 @font-face 闸门（P0 实测的「假绿」补口） ----------------
#: 真文件 + 只动 `@font-face`，其余一字不改 —— 让字体规则成为唯一变量。
#: （2026-10-09 P0 附录就是这么测的；用合成文件会连 `MISSING_SLOT_VARIABLE`、
#:   `MISSING_CONTINUOUS_MOTION` 一起报，红得没有信息量。）
CJK_PROBE_PACK = "news-coral"


def _cjk_probe_write(text: str, name: str = "probe.html") -> Path:
    """把改造后的版式落到临时目录，返回路径（`check_layout` 按单文件走，不需要兄弟文件）。"""
    import tempfile as _tf
    td = _tf.mkdtemp(prefix="cjk-gate-")
    p = Path(td) / name
    p.write_text(text, encoding="utf-8")
    return p


def _cjk_gate_codes(text: str) -> set[str]:
    return {v.code for v in pb.layout_selfcheck.check_layout(_cjk_probe_write(text))}


def _hook_html() -> str:
    real = os.path.join(pb.TEMPLATE_ROOT, CJK_PROBE_PACK, "compositions", "hook.html")
    return Path(real).read_text(encoding="utf-8")


def t_cjk_gate_green_on_shipped_packs():
    """收紧字体的同时**不许把 31 套存量打红** —— 227 个版式文件必须仍 0 违规。

    这条是全组测试的地基：新规则若对 `HF Serif CJK`（news-policy 5 个版式已在用）
    或对它那些"装了但没用的候选 `local()` 名"过敏，P1 还没开工就先把产线闸弄坏。
    """
    lsc = pb.layout_selfcheck
    total, bad = 0, []
    for pack in pb.ALL_TEMPLATES:
        for path in lsc.discover_layouts(Path(pb.TEMPLATE_ROOT) / pack):
            total += 1
            bad.extend(str(v) for v in lsc.check_layout(path))
    assert total >= 200, f"测试前提坏了: 只发现 {total} 个版式文件"
    assert not bad, f"存量版式被字体闸打红 {len(bad)} 条:\n  " + "\n  ".join(bad[:5])


def t_cjk_gate_catches_family_used_but_not_declared():
    """P0 实测假绿 ①：正文用了一个中文族，文件里**根本没有这条 @font-face** —— 旧闸静默。

    `check_layout` 只问"有没有中文 face"，不问"用到的每个族都在不在"。所以版式写
    `font-family:"HF Serif CJK"` 而忘了带宋体声明时，浏览器按系统默认字回落，闸门全绿。
    这类正是裁决 7（杂志族宋体标题）最容易踩的：编译器少发一条 @font-face 就无声掉档次。

    反向也要锁死：**声明并使用** serif 是合法的（news-policy 5 个版式就这么干），不许误报。
    """
    base = _hook_html()
    assert _cjk_gate_codes(base) == set(), "测试前提坏了: 真 hook.html 本来就不干净"

    uses_serif = base.replace(
        'font-family: "HF CJK", sans-serif;',
        'font-family: "HF Serif CJK", serif;', 1)
    assert '"HF Serif CJK"' in uses_serif and "HF Serif CJK\";" not in uses_serif, (
        "测试前提坏了: 改动没落到正文用 serif 且仍无 serif 声明")
    codes = _cjk_gate_codes(uses_serif)
    assert "CJK_FAMILY_USED_NOT_DECLARED" in codes, (
        f"用了 HF Serif CJK 却没声明，闸门却没报（静默回落系统默认字）: {sorted(codes)}")

    green = uses_serif.replace(
        'font-family: "HF CJK";',
        'font-family: "HF CJK";\n'
        '        @font-face {\n'
        '          font-family: "HF Serif CJK";\n'
        '          src: local("Noto Serif SC"), local("SimSun");\n'
        '          font-weight: 100 900;\n'
        '        }', 1)
    assert _cjk_gate_codes(green) == set(), (
        "宋体+黑体双声明双使用被误报（裁决 7 的杂志族会被自己闸死）")


def t_cjk_gate_refuses_family_names_outside_the_registry():
    """P0 实测假绿 ②：判定写的是 `"HF CJK" in block`（**子串**），前缀式族名被吞。

    实测两种命名方向完全不同：`"HF CJK" in "HF CJK Serif"` 为 **True**（子串洞成立，
    整族不在设计体系里也放行），而 `"HF CJK" in "HF Serif CJK"` 为 **False**（产线现用名，
    单用会当场红）。P0-1 探针当时用的就是前缀式名，所以洞是真的、但**不能靠"放宽成集合"
    顺手把 news-policy 的宋体打进红区** —— 修法是按精确族名核，serif 名进白名单。
    """
    base = _hook_html()
    decl = re.compile(r'font-family:\s*"HF CJK";')
    assert len(decl.findall(base)) == 1, "测试前提坏了: 声明行锚点不是唯一一处"
    prefix = decl.sub('font-family: "HF CJK Serif";', base).replace(
        'font-family: "HF CJK", sans-serif;',
        'font-family: "HF CJK Serif", serif;', 1)
    codes = _cjk_gate_codes(prefix)
    assert "MISSING_CJK_FONT_FACE" in codes, (
        f"自造前缀式族名（不在设计体系里）被子串放行: {sorted(codes)}")


def t_cjk_gate_catches_local_names_that_resolve_to_nothing():
    """P0 实测的假绿 ②：`local()` 名全写错时**审计静默**，杂志族招牌宋体会悄悄回落。

    存量 face 的候选名里**本来就混着没装的**（`NotoSansSC-VF`、`PingFang SC` 等，实测
    本机 absent），所以规则只能是"**至少一个** `local()` 名在本机已装"，不能要求全装 ——
    否则 227 个文件当场全红。
    """
    base = _hook_html()
    for installed in ("Noto Sans SC", "Microsoft YaHei"):
        assert f'local("{installed}")' in base, f"测试前提坏了: {installed} 不在候选里"
    bogus = (base.replace('local("Noto Sans SC")', 'local("Noto Sans Nope")')
                 .replace('local("Microsoft YaHei")', 'local("Microsoft Nope")'))
    codes = _cjk_gate_codes(bogus)
    assert "CJK_FONT_LOCAL_NOT_INSTALLED" in codes, (
        f"全假 local() 名的中文 face 被放过（静默回落无衬线）: {sorted(codes)}")
    one_real = bogus.replace('local("Noto Sans Nope")', 'local("Noto Sans SC")')
    assert _cjk_gate_codes(one_real) == set(), "有一个已装候选名就该放行（不许要求全装）"


def t_cjk_gate_still_blocks_a_layout_with_no_cjk_face():
    """补口不许变成放水：整条中文 `@font-face` 删掉仍须报 `MISSING_CJK_FONT_FACE`。"""
    base = _hook_html()
    face = re.compile(r"@font-face\s*\{[^}]*font-family:\s*\"HF CJK\"[^}]*\}\s*", re.S)
    assert len(face.findall(base)) == 1, "测试前提坏了: @font-face 块锚点不是唯一一处"
    codes = _cjk_gate_codes(face.sub("", base))
    assert "MISSING_CJK_FONT_FACE" in codes, f"没有中文 face 却不再报错: {sorted(codes)}"


def t_work_dir_defaults_outside_system_temp():
    """渲染工作目录**不许默认落在系统 temp**（2026-10-08 实跑 t002 踩到）。

    实跑经过: `work = args.work_dir or tempfile.mkdtemp(prefix="pathb_")` 把它放进
    `%TEMP%\\pathb_xxxx`。渲染要 15 分钟（首次 `npx -y hyperframes` 联网拉包占掉大半），
    等包拉好时 Windows 临时目录已被自动清理 —— index.html 连同前 4 段的 mp3/vtt 一起消失，
    hyperframes 报 `No index.html file found`，而发射器只说「报告无法解析: check.json」。

    闸门失败的理由是真的（日志诚实地拒了渲染），但**用户拿不到原因**，
    只能看着"无法解析"猜 —— 这比失败本身更糟。

    处置: 默认落在项目内 `.harness-news-runtime/work/<pid-ish>`，跟其他产物同域、
    受 gitignore 保护、不被系统清理；`--work-dir` 仍然可以显式覆盖。
    """
    assert pb.DEFAULT_WORK_ROOT is not None, "必须显式声明默认工作目录根"
    tmp = pb.tempfile.gettempdir().replace("/", "\\").lower()
    assert tmp not in str(pb.DEFAULT_WORK_ROOT).lower(), (
        f"默认工作目录仍在系统 temp 下（会被自动清理）: {pb.DEFAULT_WORK_ROOT}")
    assert ".harness-news-runtime" in str(pb.DEFAULT_WORK_ROOT), (
        f"默认工作目录该与新闻域其他产物同域: {pb.DEFAULT_WORK_ROOT}")


def t_gate_failure_names_the_real_cause():
    """门禁失败要说出**真实原因**，不许只说"无法解析"（2026-10-08 实跑 t002 踩到）。

    hyperframes 门禁没过时，旧输出是：
        ❌ hyperframes check --strict 未通过, 已拒绝渲染
           check 输出尾部: 报告无法解析: .../check.json
        而真实的 stderr 是 `No index.html file found`（或 Node 版本过低、版面契约不合约）。
    判据: 门禁失败的输出里必须带 hyperframes 的**原始 stderr 片段**，
    否则用户只能猜 —— "假绿比红危险"的同一原则在红这一侧也成立。
    """
    import inspect
    # 精确定位门禁函数（dir 里带 "check" 的还有 summarize_check_json 等辅助）
    fn = getattr(pb, "gate_hyperframes_check", None)
    assert fn is not None, "找不到 gate_hyperframes_check"
    body = inspect.getsource(fn)
    assert "check.err" in body or "stderr" in body.lower(), (
        f"{fn.__name__} 读了 stderr 但没有把它并进失败输出")
    assert "无法解析" not in body or "err.txt" in body, (
        f"{fn.__name__} 还在只说'无法解析'而不给 stderr 原文")


def t_timed_records_stages_and_writes_json():
    """分段计时: 每个 stage 记一次耗时, write_timings 落 JSON 且合计 >= 0。"""
    import tempfile
    before = len(pb._TIMINGS)
    with pb.timed("demo-stage"):
        pass
    assert len(pb._TIMINGS) == before + 1, "timed 上下文退出后必须记一条"
    assert pb._TIMINGS[-1][0] == "demo-stage", "stage 名不许被改写"
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "timing.json")
        pb.write_timings(out)
        data = json.loads(open(out, encoding="utf-8").read())
        assert data["stages"], "timing.json 必须有 stages 数组"
        assert data["total_seconds"] >= 0
        assert any(s["stage"] == "demo-stage" for s in data["stages"])


def t_hyperframes_probe_order_and_fallback():
    """可执行定位: 旗标 > 项目 node_modules > npx 缓存 > 回落 npx -y, 每档带真出处。"""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = os.path.join(td, "proj")
        npx = os.path.join(td, "npx")
        os.makedirs(os.path.join(root, "node_modules", ".bin"))
        os.makedirs(os.path.join(npx, "h1", "node_modules", ".bin"))
        local_bin = os.path.join(root, "node_modules", ".bin", "hyperframes.cmd")
        cache_bin = os.path.join(npx, "h1", "node_modules", ".bin", "hyperframes.cmd")
        for p in (local_bin, cache_bin):
            open(p, "w").close()

        cands = pb.hyperframes_candidates(None, root=root, npx_root=npx)
        assert cands[0][0] == [local_bin], "项目 node_modules 必须排在 npx 缓存之前"
        assert any(c[0] == [cache_bin] for c in cands), "npx 缓存里的可执行必须被发现"
        assert all(c[1] for c in cands), "每档候选都要有真出处"

        forced = pb.hyperframes_candidates("X:/custom/hf", root=root, npx_root=npx)
        assert forced[0][0] == ["X:/custom/hf"], "旗标必须压过一切探测"
        assert "旗标" in forced[0][1]

        empty = os.path.join(td, "empty")
        os.makedirs(empty)
        argv, source = pb.resolve_hyperframes(None, root=empty, npx_root=empty)
        assert argv == ["npx", "-y", "hyperframes"], "探测全缺时回落 npx -y"
        assert "回落" in source


# ---------------- v2 风格 spec：结构校验 + 编译前判据 3/5 + D5 反算 ----------------
PATH_C_ROOT = pb.PATH_C_ROOT
FLAGSHIP_SPEC = os.path.join(PATH_C_ROOT, "news-editorial-warm", hs.SPEC_FILENAME)


def _flagship_raw() -> dict:
    """旗舰 spec 的**原始表**（深拷贝，随改随用）。读文件而不是在测试里抄一份 spec，
    否则测试通过只证明测试自己一致。"""
    import copy
    import tomllib
    with open(FLAGSHIP_SPEC, "rb") as handle:
        return copy.deepcopy(tomllib.load(handle))


def t_hf_style_spec_flagship_passes_every_compile_time_gate():
    """P1 决策门的**机判那一半**：旗舰 spec 必须过结构 + 全部编译前判据 + 四轴齐备。

    走 `precompile_violations()`（编译器取 spec 时跑的那一条），不在测试里另拼一遍
    子闸 —— 拼第二份清单迟早会漏掉新加的闸（判据 5 第四轴就是后加的）。
    """
    spec = hs.load_spec(Path(FLAGSHIP_SPEC))
    assert spec.family == "editorial" and spec.grammar == "asymmetric-columns"
    assert spec.layouts == list(hs.CANONICAL_LAYOUTS), f"版式清单偏离契约面: {spec.layouts}"
    assert hs.precompile_violations(spec) == [], (
        f"编译前门禁不过: {hs.precompile_violations(spec)}")
    assert len(spec.signature()) == 4
    assert len(spec.taboos) >= hs.MIN_TABOOS
    # 裁决 13：杂志族强调色是 #B45309，不是沿用现产的 #E85D5D（抬明度=降冲击）
    assert [a["hex"].lower() for a in spec.accents] == ["#b45309"], spec.accents


def t_hf_style_spec_contrast_gate_rejects_accent_as_body_text():
    """判据 3 真的在算数，不是摆设：强调橙当正文色必须被拒（实测 4.39 < 4.5）。

    这条同时解释 `spec.toml` 里 kicker 为什么只能挂 `size = "large"`、
    强调色 role 为什么是 `shape-or-large-text` —— 那是算出来的，不是选的。
    """
    raw = _flagship_raw()
    kicker = [pair for pair in raw["color"]["text"] if pair["role"] == "kicker"]
    assert len(kicker) == 1, "测试前提坏了: spec 里 kicker 应当正好一条"
    kicker[0]["size"] = "body"
    problems = hs.contrast_violations(hs.Spec(raw))
    assert len(problems) == 1, f"强调橙 4.39:1 当正文没被拒: {problems}"
    assert "4.39" in problems[0] and "4.5" in problems[0], problems[0]


def t_hf_style_spec_contrast_gate_rejects_accent_on_a_light_dark_ground():
    """P5 根治：强调色"翻不翻面"不是靠注释兜，是判据 3 逐对算出来的。

    P2 收官记了句"深底强调翻色留 P5 补"（琥珀压钴蓝 1.14 破线）。这条把它证伪成
    "根本编不出来"：旗舰 dark 面是**近黑墨 #1f1b16**，琥珀 on-ink-accent 实测 3.41 过
    大字线（基线零违规）；把同一份 spec 的 ink 面换成中彩度钴蓝 #1f3a68，那条琥珀强调
    立刻 2.24 < 3.0 → `contrast_violations` 拒编。⇒ "蓝底复用琥珀"这条路编译期就断，
    无需运行时按 tone 翻强调色的分支（YAGNI：没有已发布编译包踩得到，加了就是死代码）。
    真要出蓝底包，判据 3 会逼作者给该面配一个过线的强调色，而不是悄悄糊上去。
    """
    # 基线：旗舰真实墨面（近黑）下琥珀过大字线，on-ink-accent 不该出现在违规里
    base = hs.contrast_violations(hs.Spec(_flagship_raw()))
    assert not any("on-ink-accent" in p for p in base), \
        f"旗舰墨面琥珀该过 3.0，却被判违规: {base}"

    # 反证：把 ink 面改成中彩度钴蓝，同一琥珀强调必须跌破大字线
    raw = _flagship_raw()
    raw["color"]["surfaces"]["ink"] = "#1f3a68"
    problems = hs.contrast_violations(hs.Spec(raw))
    hit = [p for p in problems if "on-ink-accent" in p]
    assert len(hit) == 1, f"钴蓝墨面上的琥珀强调没被拒: {problems}"
    assert "2.24" in hit[0] and "3.0" in hit[0], hit[0]


def t_hf_style_spec_caption_reserve_reproduces_the_measured_constant():
    """D5 根治：禁入区从 spec 几何**反算**，且必须等于手量的 20.0 —— 不等就是有人在
    没签字的情况下把 227 个现存版式的闸口放宽或收紧了。
    """
    subtitle = hs.load_spec(Path(FLAGSHIP_SPEC)).subtitle
    reserve = hs.caption_reserve_cqh(subtitle)
    assert reserve == pb.layout_selfcheck.CAPTION_RESERVE_CQH, (
        f"反算值 {reserve} ≠ layout_selfcheck.CAPTION_RESERVE_CQH "
        f"{pb.layout_selfcheck.CAPTION_RESERVE_CQH}，spec 驱动与现存闸口分家了")
    # 口径可动：发射器把每条封顶 2 行（CAPTION_MAX_LINES=2，两行顶边实测 ≈1628px），
    # 按 2 行算就只需要 17cqh —— 说明 20 是按"最坏 3 行 + 1 个整数 cqh 余量"留出来的。
    two_lines = hs.caption_reserve_cqh({**subtitle, "worst-case-lines": 2})
    assert two_lines == 17.0, f"2 行口径应当反算出 17.0，读到 {two_lines}"
    assert two_lines < reserve, "行数越少禁入区反而越大，反算公式坏了"


def t_hf_style_spec_chroma_is_not_hsl_saturation():
    """`-S` 的口径锁死在彩度 (max−min)/255，**不许**有人"顺手修正"成 HSL 的 S。

    实测：暖纸地 #f5efe3 的 HSL S = 0.474，比阈值 accent-min-S(0.45) 还高，而强调橙
    #B45309 的 HSL S 才 0.905 —— 用 HSL 判，暖纸会被算成强调色，support-max-S(0.15)
    这条闸对每个纸面色板都恒红，等于没有。
    """
    import colorsys
    paper, accent = "#f5efe3", "#B45309"
    assert hs.chroma(paper) < 0.15 < hs.chroma(accent), (
        f"彩度口径变了: paper={hs.chroma(paper)} accent={hs.chroma(accent)}")
    body = paper.lstrip("#")
    hsl_s = colorsys.rgb_to_hls(*[int(body[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])[2]
    assert hsl_s > 0.45, f"HSL S 竟然没炸（说明本测试的立项理由没了，去更新口径注释）: {hsl_s}"


def t_hf_style_spec_refuses_broken_structure_with_pointed_reasons():
    """每种坏法都要**点名**到哪一层 —— "有 N 条问题"式的断言会在改报错文案时静默失效。"""
    mutations = [
        ("schema 走错", lambda r: r.__setitem__("schema", "hf-style/2"), "schema"),
        ("整层缺失", lambda r: r.pop("grid"), "缺层 'grid'"),
        ("语法不在有限集", lambda r: r["grid"].__setitem__("grammar", "my-vibes"), "不在有限集"),
        ("族与语法不配对", lambda r: r["grid"].__setitem__("grammar", "twelve-column"), "一对一"),
        ("id 不是 kebab", lambda r: r.__setitem__("id", "News_Editorial"), "kebab-case"),
        ("族不在 9 族", lambda r: r.__setitem__("family", "magazine"), "不在 9 族"),
        ("版式少一个", lambda r: r.__setitem__("layouts", r["layouts"][:6]), "必须正好"),
        ("文字坐在没有的面", lambda r: r["color"]["text"][0].__setitem__("on", "moon"), "不是已声明的面"),
        ("尺寸档写错", lambda r: r["color"]["text"][0].__setitem__("size", "huge"), "只能是"),
        ("面色不是 6 位", lambda r: r["color"]["surfaces"].__setitem__("paper", "#fff"), "#rrggbb"),
        ("色对清单空", lambda r: r["color"].__setitem__("text", []), "至少一条"),
        ("饱和阈值留间隙", lambda r: r["color"]["saturation-budget"].__setitem__("accent-min-S", 0.1),
         "必须 > support-max-S"),
        ("阶梯不够三级", lambda r: r["color"].__setitem__("value-ladder", [96, 91]), "至少 3 级"),
        ("阶梯乱序", lambda r: r["color"].__setitem__("value-ladder", [93, 81, 85, 10]), "严格递减"),
        ("阶梯两档同明度", lambda r: r["color"].__setitem__("value-ladder", [93, 93, 85, 10]),
         "严格递减"),
        ("招牌时长没写", lambda r: r["motion"].pop("entrance-seconds"), "entrance-seconds"),
        ("招牌时长短于自家下限",
         lambda r: r["motion"].__setitem__("entrance-seconds", 0.2), "比自家下限还短"),
        ("缓动偏好空表", lambda r: r["motion"]["easing"].__setitem__("allowed", []), "非空列表"),
        ("禁忌少于三条", lambda r: r.__setitem__("taboos", r["taboos"][:2]), "至少 3 条"),
        ("禁忌重名", lambda r: r["taboos"].append(dict(r["taboos"][0])), "重复"),
        ("禁忌没写为什么", lambda r: r["taboos"][0].__setitem__("why", ""), "why 必填"),
        ("安全区没写 bottom", lambda r: r["grid"]["safe"].pop("bottom"), "bottom 必填"),
        ("漂移取值越界", lambda r: r["motion"].__setitem__("drift", "sometimes"), "keep/none"),
    ]
    pristine = hs.validate(_flagship_raw(), source="t")
    assert pristine == [], f"测试前提坏了: 旗舰 spec 本身不合法 {pristine}"
    for name, mutate, keyword in mutations:
        raw = _flagship_raw()
        mutate(raw)
        problems = hs.validate(raw, source="t")
        assert any(keyword in p for p in problems), (
            f"{name}: 没有报出带 '{keyword}' 的问题（全部问题: {problems}）")


def t_hf_style_spec_distinctness_gate_counts_axes_not_vibes():
    """判据 5：四轴里相同 ≤2 才算不同。同族 4 变体的可行排布也在这里证掉。

    这条不是走流程 —— 它锁的是裁决 6 与判据 5 咬合后的**算术**：同族 grammar 必同，
    三轴两两距离 ≥2，4 个变体在 3 维立方里只有奇偶一类放得下（000/011/101/110）。
    P5 铺 31 套时必须按这个排布选参数，靠"感觉不一样"过不了闸。
    """
    def variant(display, motion, ladder):
        raw = _flagship_raw()
        raw["id"] = f"v-{motion}-{str(ladder[0])}"
        raw["type"]["display"] = display
        raw["motion"]["signature"] = motion
        raw["color"]["value-ladder"] = ladder
        return hs.Spec(raw)

    A, B = "HF Serif CJK/900", "HF CJK/900"
    M, N = "clip-rise-char", "rule-pull-numeral"
    L, P = [96, 91, 85, 12], [94, 88, 40, 15]
    base = variant(A, M, L)
    assert hs.distinctness_violations([base, variant(A, M, L)]) != [], (
        "四轴全同的两套（复制粘贴包）没被拦 —— 判据 5 是空的")
    assert hs.distinctness_violations([base, variant(B, M, L)]) != [], (
        "只差一轴（换标题字重）不够，判据 5 要求 ≥2")
    assert hs.distinctness_violations([base, variant(B, N, L)]) == [], (
        "差两轴应当放行却被拒 —— 闸口比 spec 还严会把 31 套逼成 12 套")

    # 奇偶排布：三轴当成 3 维立方，4 变体取偶校验子集 {000,011,101,110} 才两两距离 2。
    # 反例先验一次：000 与 001 只差 ladder，同族摆在一起必报红。
    assert hs.distinctness_violations([variant(A, M, L), variant(A, M, P)]) != [], (
        "测试前提坏了: 只差 ladder 一轴的两个变体应当报红")
    parity = [variant(A, M, L), variant(A, N, P), variant(B, M, P), variant(B, N, L)]
    assert hs.distinctness_violations(parity) == [], (
        f"合法的 4 变体排布被误拒: {hs.distinctness_violations(parity)}")
    # 从奇偶集里挪一个到错位置（(A,M,L) 与 (A,M,P) 相遇），闸口必须立刻抓到。
    broken = [variant(A, M, L), variant(A, N, P), variant(B, M, P), variant(A, M, P)]
    assert hs.distinctness_violations(broken) != [], (
        "奇偶排布被破坏（两变体只差 ladder）却没报 —— 判据 5 抓不住 P5 的错误选参")


def t_hf_style_spec_value_ladder_must_be_the_actual_surfaces():
    """判据 5 第四轴不许是装饰数字：`value-ladder` 必须与色板**两个方向都对得上**。

    立项理由：结构闸只能证它递减、够三级。`[99, 50, 1]` 这种"看着像阶梯"的表能过结构闸，
    然后 P5 拿它当"这一套第四轴已经不同"的证据铺 31 套 —— 区分度是纸上的。
    实测四档（HSL L）：纸 92.55 / 面板 85.29 / 分隔线 80.78 / 墨 10.39 ⇒ `[93, 85, 81, 10]`。
    """
    spec = hs.load_spec(Path(FLAGSHIP_SPEC))
    assert hs.value_ladder_violations(spec) == [], hs.value_ladder_violations(spec)

    def ladder_problems(ladder, extra_surface=None):
        raw = _flagship_raw()
        raw["color"]["value-ladder"] = ladder
        if extra_surface:
            raw["color"]["surfaces"].update(extra_surface)
        return hs.value_ladder_violations(hs.Spec(raw))

    # 方向一：阶梯与面色分家（阶梯挪走了，面板/分隔线的明度没人接住）
    off = ladder_problems([93, 50, 12, 4])
    assert any("85.3" in p for p in off), f"面色对不上阶梯却没抓到: {off}"
    # 方向二：凭空多一档（写了 50 这一档，色板上没有这个明度）
    invented = ladder_problems([93, 85, 81, 50, 10])
    assert any("没有任何面色" in p for p in invented), f"凭空档没被拒: {invented}"
    # 补一个真的坐在 50 档上的面 ⇒ 凭空档变成合法档（证明闸数的是色板，不是白名单）
    filled = ladder_problems([93, 85, 81, 50, 10], extra_surface={"band": "#8f8378"})
    assert filled == [], f"色板已补齐却仍被拒: {filled}"
    # 强调色不参与阶梯：#B45309 明度 37.06 离任何一档都超容差 ——
    # 说明"跳过强调色"这一支是真在起作用，不是恰好没报错
    assert [a["hex"] for a in spec.accents] == ["#B45309"]
    accent_l = hs.hsl_lightness("#B45309")
    assert min(abs(accent_l - step) for step in spec.value_ladder) > hs.LADDER_TOLERANCE, accent_l


def t_hf_primitives_token_bundle_reads_the_spec():
    """原语的每个数都从 spec 来（`tokens_from_spec`），版式里不许再抄一份。

    尤其 `ease` 取 `motion.easing.allowed[0]`（口径：招牌缓动），以及
    `entrance_seconds/entrance_min` —— 这两个是 P1 新加的字段，没有它们就得在版式里
    写死 1.4/0.5，那就是第 N 个手抄假数（D10 那一类）。
    """
    spec = hs.load_spec(Path(FLAGSHIP_SPEC))
    reserve = hs.caption_reserve_cqh(spec.subtitle)
    tok = hp.tokens_from_spec(spec, reserve)
    assert tok.ease == spec.motion["easing"]["allowed"][0] == "power3.out", tok.ease
    assert (tok.entrance_seconds, tok.entrance_min) == (1.4, 0.5)
    assert tok.safe_left == 6.0 and tok.safe_right == 6.0 and tok.reserve_bottom == reserve
    assert (tok.display_family, tok.display_weight) == ("HF Serif CJK", 900), tok.display_family
    assert (tok.body_family, tok.body_weight) == ("HF CJK", 400)
    # 拉丁位必须是引擎捆绑族（`hf_style_spec.LATIN_CANONICAL_FAMILIES`）；这一条读的是
    # spec 真源，所以它同时也是"旗舰包没有写一个会触发 error 的族名"的证明。
    assert tok.latin_display == "Playfair Display", tok.latin_display
    assert tok.latin_display in hs.LATIN_CANONICAL_FAMILIES
    # 换 ease_index 取第二偏好（变体之间靠这个换缓动口味，不靠改代码）
    assert hp.tokens_from_spec(spec, reserve, ease_index=1).ease == "power2.out"
    # 认不到的角色/面必须**点名**可用值：静默回退到某个默认色就是第二个 OFF_PALETTE 后门
    try:
        tok.pair("no-such-role")
        raise AssertionError("坏角色没抛")
    except KeyError as exc:
        assert "display" in str(exc), f"KeyError 没列出可用角色: {exc}"
    try:
        tok.face("moon")
        raise AssertionError("坏面名没抛")
    except KeyError as exc:
        assert "paper" in str(exc), f"KeyError 没列出可用面: {exc}"


#: 12 个原语各自的最小合法调用（关键字参数按各自签名，覆盖 unit_var/serif 分支）
PRIMITIVE_CALLS = {
    "clip-wipe-up": dict(top=20.0, height=30.0),
    "char-rise": dict(var_id="title", role="display", top=12.0, size=9.0),
    "rule-pull": dict(top=30.0),
    "hairline": dict(top=40.0),
    "block-chip": dict(var_id="kickerLabel", role="on-accent", top=50.0, size=3.2),
    "giant-numeral": dict(value_var="statValue", unit_var="statUnit", role="display", top=20.0),
    "cue-fade": dict(var_id="supportBody", role="secondary", top=60.0, size=3.6),
    "keyword-tint": dict(var_id="onscreenKeyword", role="kicker", top=70.0, size=8.0),
    "photo-duotone": dict(path_var="imagePath", credit_var="imageCredit"),
    "photo-local-crop": dict(path_var="imagePath", top=10.0, height=30.0),
    "ken-burns-in": dict(),
    "drift-y": dict(),
}


def _flagship_tok() -> hp.Tok:
    spec = hs.load_spec(Path(FLAGSHIP_SPEC))
    return hp.tokens_from_spec(spec, hs.caption_reserve_cqh(spec.subtitle))


def t_hf_primitives_all_twelve_render_seek_safe_fragments():
    """P0 十二个原语逐个渲染，必须**零法则违规**，且几何全走 cq 单位。

    这是 P1-3b 的验收面：原语是编译器的唯一词汇表，它自己不过法则 7/8/10/D3，
    后面 31 套就没有一套能过闸 —— 所以这里数的是"每个原语各自干净"，不是抽样。
    """
    assert hp.P0_NAMES == tuple(hp.PRIMITIVES) and len(hp.P0_NAMES) == 12, hp.P0_NAMES
    # 元数据值集闭合：编译器要按这些名字取数，词表一旦散开就没人认得了
    dims = set()
    for name, prim in hp.PRIMITIVES.items():
        assert prim.seek_safe == "by-construction", f"{name}: {prim.seek_safe}"
        assert prim.contrast in hp.CONTRAST_KINDS, f"{name}: {prim.contrast}"
        for entry in prim.budget:
            dim, sep, value = entry.partition(":")
            assert sep and value and dim in hp.BUDGET_DIMENSIONS, \
                f"{name}: budget 词条 {entry!r} 不是 '维度:值' 形状"
            dims.add(dim)
    assert dims == set(hp.BUDGET_DIMENSIONS), f"预算维度词表与实际用量分家: {sorted(dims)}"
    tok = _flagship_tok()
    for index, name in enumerate(hp.P0_NAMES):
        prim = hp.PRIMITIVES[name]
        args = PRIMITIVE_CALLS[name]
        ident = f"e{index}"
        frag = prim.render(tok, ident, **args)
        assert frag.primitive == name, f"{name}: render 回了 {frag.primitive}"
        problems = hp.fragment_violations(frag)
        assert problems == [], f"{name}: 法则违规 {problems}"
        # 预算标签必须与**渲染出来的行为**一致 —— 否则它只是第二条散文标签（同 `ground` 那一删）
        continuous = "driftDur" in frag.js
        assert ("motion:continuous" in prim.budget) == continuous, \
            f"{name}: motion:continuous 与是否挂 driftDur 分家"
        assert ("dom:chars" in prim.budget) == ("Array.from(" in frag.js), \
            f"{name}: dom:chars 与是否按码点切字分家"
        # frames:1 的口径 = 一条补间、不膨胀 DOM（char-rise 用 dom:chars 顶掉它）
        assert ("frames:1" in prim.budget) == (
            len(frag.tweens) == 1 and "dom:chars" not in prim.budget and not continuous), \
            f"{name}: frames:1 与补间条数/DOM 膨胀分家"
        for tween in frag.tweens:
            assert tween.startswith(("tl.fromTo(", "tl.to(")), f"{name}: 补间起法 {tween[:24]}"
        assert "px" not in frag.css, f"{name}: CSS 里有 px 排版（PX_TYPOGRAPHY 会拒）"
        # 确定性：同 ident 同参数两次渲染逐字节一致（法则 10 的另一半 —— 不许有墙钟/随机）
        again = prim.render(tok, ident, **args)
        assert (again.css, again.html, again.js) == (frag.css, frag.html, frag.js), \
            f"{name}: 两次渲染不一致，说明内部有不可复现的取数"
    # 编译器实际用的 ident 是 kebab（`ew-hk-top`）：拿它再扫一遍，必须同样干净。
    # 起因是引擎侧的 `invalid_inline_script_syntax`（error 级）—— Python 三道闸不解析 JS，
    # `const ew-hk-topChars = …` 这种拼法只有 Node 报得出来，所以在这里前移。
    for name in hp.P0_NAMES:
        frag = hp.PRIMITIVES[name].render(tok, "ew-hk-top-a", **PRIMITIVE_CALLS[name])
        problems = hp.fragment_violations(frag)
        assert problems == [], f"{name}: kebab ident 产出非法 JS 标识符 {problems}"
    assert hp.js_name("ew-hk-top") == "ewHkTop", hp.js_name("ew-hk-top")
    assert hp.js_name("1st") and hp.JS_IDENT_RE.match(hp.js_name("1st")), hp.js_name("1st")


def t_hf_primitives_face_never_fades_and_names_are_namespaced():
    """法则 8 的结构性避开：带 background 的原语一律 clip-path/scaleX，没有一个 opacity。

    同时核 ident 命名空间：一个版式里两次用同一原语时，id 必须各走各的（否则第二条
    补间会改到第一个元素上）。
    """
    tok = _flagship_tok()
    faced = []
    for name in hp.P0_NAMES:
        frag = hp.PRIMITIVES[name].render(tok, f"el-{name}", **PRIMITIVE_CALLS[name])
        if frag.face:
            faced.append(name)
            assert "opacity" not in frag.js, f"{name}: 有色面里出现 opacity（法则 8）"
    assert set(faced) == {"clip-wipe-up", "rule-pull", "hairline", "block-chip"}, faced
    one = hp.PRIMITIVES["hairline"].render(tok, "line-a", top=40.0)
    two = hp.PRIMITIVES["hairline"].render(tok, "line-b", top=60.0)
    assert "#line-a" in one.css and "#line-b" in two.css and "line-a" not in two.css


def t_hf_primitives_budget_block_satisfies_the_structure_gate():
    """动量预算块与结构闸的契约：常数名、可渲染、且真的有人用 driftDur。

    `layout_selfcheck` 的 MAGIC_BUDGET_VALUE/MISSING_DRIFT_DURATION 认的是**名字**
    （`BUDGET_CONSTANTS`），改数字可以改名不行 —— 这块模板是原语库唯一碰得到那条闸的地方，
    所以它在编译前就要核住，而不是等版式落盘后由闸反推。
    """
    constants = pb.layout_selfcheck.BUDGET_CONSTANTS
    for constant in constants:
        assert f"const {constant} = {{{constant.lower()}}}" in hp.BUDGET_JS, \
            f"预算块没有具名声明 {constant}（结构闸会报 MAGIC_BUDGET_VALUE）"
    rendered = hp.BUDGET_JS.format(intro_end=hp.BUDGET_INTRO_END, min_drift=hp.BUDGET_MIN_DRIFT)
    assert f"const INTRO_END = {hp.BUDGET_INTRO_END};" in rendered, rendered
    assert "const MIN_DRIFT = 0.6;" in rendered and "const driftDur = " in rendered
    # 连续位移必须真挂在 driftDur/driftStart 上，否则 MISSING_CONTINUOUS_MOTION
    tok = _flagship_tok()
    users = [name for name in hp.P0_NAMES
             if "driftDur" in hp.PRIMITIVES[name].render(tok, "z", **PRIMITIVE_CALLS[name]).js]
    assert set(users) == {"ken-burns-in", "drift-y"}, users


def t_hf_primitives_detector_rejects_every_death_mode():
    """`fragment_violations` 每条分支都要被真的坏写法触发一次 —— 否则它是装饰代码。

    分支清单：禁写 token（Math.random/onUpdate）、GSAP `.from(`、有色面 opacity、
    `.to(` 没挂 driftDur、CSS transform 与补间打架。
    最后一条负例证 ``Array.from(`` 的豁免：它是切字，不是 tween。
    """
    cases = [
        ("法则 10", hp.Fragment(primitive="probe",
                               pre_js=("const j = Math.random();",)),
         "Math.random("),
        ("D3 回调", hp.Fragment(primitive="probe",
                              tweens=('tl.to("#p", { x: 1, onUpdate: tick });',)),
         "onUpdate"),
        ("GSAP .from(", hp.Fragment(primitive="probe",
                                   tweens=('tl.from("#p", { y: 14 }, 0);',)),
         "fromTo"),
        ("法则 8 面淡入", hp.Fragment(
            primitive="probe", css="#p { background: #e8dfcb; }", face=True,
            tweens=('tl.fromTo("#p", { opacity: 0 }, { opacity: 1, duration: 0.6 }, 0);',),
        ), "法则 8"),
        ("to() 失步", hp.Fragment(
            primitive="probe",
            tweens=('tl.to("#p", { yPercent: -3, duration: 2.0, ease: "none" }, 1.5);',),
        ), "driftDur"),
        ("法则 7 transform", hp.Fragment(
            primitive="probe", css="#p { transform: translateY(10cqh); }",
            tweens=('tl.fromTo("#p", { y: 14 }, { y: 0, duration: 0.7 }, 0);',),
        ), "法则 7"),
        ("非法 JS 名", hp.Fragment(
            primitive="probe", pre_js=("const ew-hk-topChars = 1;",),
        ), "非法 JS 标识符"),
    ]
    for label, frag, keyword in cases:
        problems = hp.fragment_violations(frag)
        assert any(keyword in p for p in problems), (
            f"{label}: 没报出含 '{keyword}' 的问题（全部: {problems}）")
    # 负例：Array.from 是按码点切字，合法；误伤它 = 招牌原语自己过不了自己的闸
    assert hp.fragment_violations(hp.Fragment(
        primitive="probe",
        pre_js=('const chars = Array.from(String(vars.title || "")).length;',))) == []


def t_hf_primitives_gate_image_and_accent_preconditions():
    """P3 之后：`image-gate-ready` 是唯一编译期闸门；`asset` 已迁到 CALLSITE。

    裁决 3（P3 之前）：取图类原语一律拒编。P3 切片 3 之后：门由 `capability_ok()`
    运行时决定；`asset`（本镜有没有图）编译期拿不到，交给构建期的"空路径塌槽"兜
    （hf_primitives.py:474-478 的 `path_var` 分支）。同一条检查还要拦"强调色当正文
    坐字上"，并且任何没人实现的 requires 名字也要拦。
    """
    gated = {name for name in hp.P0_NAMES
             if hp.GATED_REQUIRES & set(hp.PRIMITIVES[name].requires)}
    assert gated == {"photo-duotone", "photo-local-crop", "ken-burns-in"}, (
        f"挂在图片门禁后的原语与预期不符: {sorted(gated)}")
    for name in sorted(gated):
        problems = hp.check_preconditions(name, ground="paper")
        assert any("图片门禁" in p for p in problems), f"{name}: P3 门未开却放行 {problems}"
    # 门开：只由 image_gate_ready 决定；asset 是 CALLSITE，编译期不查（P3 §4）
    assert hp.check_preconditions("photo-duotone", ground="paper",
                                  image_gate_ready=True) == [], (
        "asset 迁到 CALLSITE 后，门开就够；这一支还被拦说明 asset 仍留在 CHECKED")
    assert hp.check_preconditions("ken-burns-in", ground="paper",
                                  image_gate_ready=True) == []
    # 形状类要实色地面：坐在图上（ground="photo"）时边缘对比不可算
    assert any("实色地面" in p for p in hp.check_preconditions("hairline", ground="photo"))
    assert hp.check_preconditions("hairline", ground="paper") == []
    # 强调色只许当形状时，keyword-tint 拒
    assert hp.check_preconditions("keyword-tint", accent_roles=("shape-only",)) != []
    assert hp.check_preconditions("keyword-tint",
                                 accent_roles=("shape-or-large-text",)) == []
    assert hp.check_preconditions("no-such-primitive") != []
    # requires 值集闭合：每个名字要么能判，要么点名了强制它的闸
    all_requires = {req for prim in hp.PRIMITIVES.values() for req in prim.requires}
    assert all_requires <= set(hp.CHECKED_REQUIRES) | set(hp.CALLSITE_REQUIRES), all_requires
    for require in hp.CHECKED_REQUIRES:
        assert any(require in prim.requires for prim in hp.PRIMITIVES.values()), \
            f"{require} 没有任何原语用 —— 删掉它或让某个原语真需要它"
    for name, enforcer in hp.CALLSITE_REQUIRES.items():
        assert enforcer.strip(), f"{name}: 前置条件没写谁强制它（散文）"
    # 未登记的 requires 名字必须被拒，不能被 elif 链静默放过
    probe = hp.Primitive("__probe__", ("my-vibes",), "none", "x", (),
                         render=lambda tok, ident: hp.Fragment(primitive="__probe__"))
    hp.PRIMITIVES["__probe__"] = probe
    try:
        assert any("没有任何实现" in p for p in hp.check_preconditions("__probe__"))
    finally:
        hp.PRIMITIVES.pop("__probe__")


def t_hf_primitives_bake_jitter_is_compile_time_and_reproducible():
    """法则 10：抖动在编译期烘焙成字面量。同入参必得同串，且幅值不越界。

    这条不等价于"跑两次相等"就完 —— 还要证 count/amplitude 任一变了串就变（否则
    种子实际没编进 key，两个不同需求会撞出同一串偏移）。
    """
    a = hp.bake_jitter(9, 0.6)
    assert a == hp.bake_jitter(9, 0.6) == list(hp.bake_jitter(9, 0.6))
    assert len(a) == 9 and all(abs(v) <= 0.6 for v in a), a
    assert a != hp.bake_jitter(10, 0.6) and a != hp.bake_jitter(9, 0.7)
    assert a != hp.bake_jitter(9, 0.6, seed=hp.BAKE_SEED + 1)
    assert hp.bake_jitter(0, 1.0) == []
    # 真随机过一遍：整串偏移全相等的可能约等于零，说明 seed key 真的在起作用
    assert len(set(a)) > 1, a


def t_hf_primitives_char_rise_honours_the_entrance_floor():
    """法则 13：逐字时长按 `max(下限, 招牌/2)` 算，短招牌也不会把入场压穿下限。

    旗舰包：max(0.5, 1.4/2) = 0.7s（P0-1 实测值）。另造一个 entrance-seconds=0.6 的包：
    max(0.5, 0.3) = 0.5s —— 若按裸 `招牌/2` 会算出 0.3s，正好犯杂志族自家禁忌。
    """
    frag = hp.PRIMITIVES["char-rise"].render(_flagship_tok(), "title",
                                            **PRIMITIVE_CALLS["char-rise"])
    assert "duration: 0.7" in frag.tweens[0], frag.tweens[0]
    assert "stagger: 0.045" in frag.tweens[0]
    raw = _flagship_raw()
    raw["motion"]["entrance-seconds"] = 0.6
    tight = hp.tokens_from_spec(hs.Spec(raw), 20.0)
    tight_frag = hp.PRIMITIVES["char-rise"].render(tight, "title",
                                                   **PRIMITIVE_CALLS["char-rise"])
    assert "duration: 0.5" in tight_frag.tweens[0], tight_frag.tweens[0]


def t_hf_primitives_var_text_container_must_be_childless():
    """法则 16：`data-var-text` 容器不得有元素子节点，除非脚本自己摘掉属性。

    起因是 P1-3e 的出帧缺陷：`char-rise` 的占位 span 让容器 `childElementCount===1`，
    引擎的写入函数（`hyperframe-runtime.js:350` 的 `_1`）于是**不**走 `textContent=t`
    替换支路，改为往第一个 TEXT_NODE 写、没有就 `insertBefore(createTextNode…)`，
    已有的 span 全留着 ⇒ 每个逐字标题都渲染两遍。四道闸当时全绿，只有摊开帧才看得见。
    这条断言把同一个缺陷形状变成编译期拒编，P5 铺 31 套时不必再靠肉眼。
    """
    tok = _flagship_tok()
    frag = hp.PRIMITIVES["char-rise"].render(tok, "ew-hk-top", **PRIMITIVE_CALLS["char-rise"])
    # ① 占位 span 还在（结构闸 MISSING_TWEEN_TARGET 要它在真标签上）
    assert hp.VAR_TEXT_TAG_RE.search(frag.html) and hp.ELEMENT_CHILD_RE.search(
        hp.VAR_TEXT_TAG_RE.search(frag.html).group("inner")), frag.html
    # ② 脚本摘了属性 ⇒ 放行（这就是 A1 的修复本身，摘掉它就回到重复渲染）
    assert 'removeAttribute("data-var-text")' in frag.js, frag.js
    assert hp.var_text_shape_violations(frag) == [], frag.js
    # ③ 反例：同样写法但不摘属性 —— 必须报，且消息要点名根因
    bad = hp.Fragment(primitive="char-rise-like", html=frag.html, pre_js=(
        f'const box = document.getElementById("ew-hk-top");',
        'box.textContent = "";',))
    hits = hp.var_text_shape_violations(bad)
    assert len(hits) == 1, hits
    assert "两遍" in hits[0] and "hyperframe-runtime.js:350" in hits[0], hits[0]
    # ④ 空容器带属性是合法主用法，不许被这条误伤（否则等于禁了变量上屏）
    ok = hp.Fragment(primitive="cue-fade-like",
                     html='<div id="a" data-var-text="headTop"></div>', pre_js=())
    assert hp.var_text_shape_violations(ok) == []
    # ⑤ 只认纯文本子节点（引擎在 childElementCount===0 时替换 textContent，安全）
    texty = hp.Fragment(primitive="x", html='<div id="a" data-var-text="k">占位</div>')
    assert hp.var_text_shape_violations(texty) == []
    # ⑥ 生产形状：七套版式编译出来的每个 data-var-text 容器，带子元素的必须已被摘属性
    for layout, text in _compiled_texts().items():
        released = bool(hp.VAR_TEXT_RELEASE_RE.search(text))
        for match in hp.VAR_TEXT_TAG_RE.finditer(text):
            if hp.ELEMENT_CHILD_RE.search(match.group("inner")):
                assert released, f"{layout}: 容器 {match.group('inner').strip()[:40]!r} 有子元素却没摘属性"


def t_hf_style_spec_layout_contract_matches_the_emitter():
    """§6.3 的降风险项：版式名不变。spec 层抄的七件套必须与发射器的 `AUTO_LAYOUT_STEMS`
    逐项相等 —— 一旦分家，`choose_layout()`/`MOUNT_TPL` 会挑到 spec 里不存在的版式。"""
    assert sorted(hs.CANONICAL_LAYOUTS) == sorted(pb.AUTO_LAYOUT_STEMS), (
        f"spec 层 {hs.CANONICAL_LAYOUTS} ≠ 发射器 {pb.AUTO_LAYOUT_STEMS}")


def t_hf_style_spec_grammar_set_is_nine_one_to_one():
    """9 族 ↔ 9 语法一对一（Q2 的答案落在代码里，不是文档里）。"""
    assert len(hs.FAMILY_GRAMMARS) == 9, sorted(hs.FAMILY_GRAMMARS)
    assert len(set(hs.FAMILY_GRAMMARS.values())) == 9, "两族共用同一语法 → 判据 5 第一轴失效"
    assert hs.GRID_GRAMMARS == tuple(sorted(hs.FAMILY_GRAMMARS.values()))


def t_no_call_site_hardcodes_npx():
    """check / render / doctor 三处调用点不许再写死 npx -y hyperframes。"""
    import inspect
    gate_src = inspect.getsource(pb.gate_hyperframes_check)
    main_src = inspect.getsource(pb.main)
    for name, src in (("gate_hyperframes_check", gate_src), ("main", main_src)):
        assert '"-y", "hyperframes"' not in src, f"{name} 还在写死 npx -y hyperframes"
    assert 'hf_argv("check"' in gate_src, "gate_hyperframes_check 必须走 hf_argv"
    assert 'hf_argv("render"' in main_src, "渲染命令必须走 hf_argv"


def t_render_argv_defaults_to_software_raster():
    """判据 4a（同稿同片）由渲染 argv 的**默认支**保证：不加参数就走软件光栅。

    P1-3e 在最终几何上重跑（数字见证据 §J4；**同轮早先那版注释里的 398/1291 与
    `c6ef377a…` 出自一个静默失效的 framehash 解析器，已作废**）：同一次发射在硬件
    路径（ANGLE / 本机 Intel Arc）渲染两遍，1290 帧里编译包差 464 帧、存量包差 710 帧，
    两次流哈希也不同；换 `--no-browser-gpu` 两遍逐帧 md5 全同（`354ecc6f…` / `4e336c26…`）。
    软件更慢（render 段 61.4/59.9s vs 硬件 57.2/48.9s）但硬件自身抖动就有 17%，
    而确定性是门禁、时长只是预算 —— 故默认取软件，见裁决 16。
    存量包同样复现，所以这不是编译包引入的，但口径必须由发射器钉住，
    不能靠"这台机器今天碰巧稳定"。断言取整条三元式：两条支都在，且默认那条是软件。
    """
    import inspect
    main_src = inspect.getsource(pb.main)
    assert 'render_cmd.append("--browser-gpu" if args.gpu else "--no-browser-gpu")' in main_src, \
        "渲染 argv 的默认支不再是软件光栅 → 判据 4a 会随机失败"


# ---------------- P2-1/P2-2 字幕轨取数面：词级 cues ----------------

#: P2-0 探针（edge-tts 7.2.8 / zh-CN-XiaoxiaoNeural）在真稿正文上量到的原值，
#: 证据见 `routes/news/evidence/2026-10-10-template-v2-p2-captions.md` §K1/§K2。
#: 三个数全部是 `wb.json` 里的**服务原单位（100ns tick）**照抄 —— 不写回换算后的秒：
#: 把 tick 当秒是最容易写错、又最难从画面看出来的一处（差 7 个数量级，字幕会在第一帧
#: 之前就全部跑完），而用打印出来四舍五入过的秒反推 tick，会造出一批"看着真实、算出来
#: 差一毫秒"的假数据（本fixture 第一版就是这么写的，`执行` 的右沿因此从 2.812 变成 2.813）。
PROBE_TEXT = "门诊新规，10月起全国执行。探针第一镜，只为量出角标的真实像素几何。"
PROBE_SECONDS = 7.848
PROBE_RAW = [
    (1000000, 3750000, "门诊"), (4875000, 5000000, "新规"),
    (12375000, 3375000, "10月"), (15750000, 2625000, "起"),
    (18625000, 3875000, "全国"), (22625000, 5500000, "执行"),
    (33875000, 4000000, "探针"), (38000000, 3500000, "第一"),
    (41500000, 2750000, "镜"), (46750000, 1750000, "只"),
    (48500000, 1500000, "为"), (50125000, 3625000, "量出"),
    (54000000, 3875000, "角标"), (57875000, 1125000, "的"),
    (59250000, 3875000, "真实"), (63250000, 4000000, "像素"),
    (67375000, 5375000, "几何"),
]


def _probe_events():
    return [{"type": "WordBoundary", "offset": o, "duration": d, "text": t}
            for o, d, t in PROBE_RAW]


def t_caption_norm_is_the_only_shape_words_and_script_share():
    """词序列**不含标点**（探针：丢字数 == 正文标点数），所以比对必须先归一化。

    不归一化的后果不是"匹配差一点"，而是"永远匹配不上"：`onscreenAccent` 与
    「数字+单位」这类强调源都是从稿子上切下来的，天然带 `，。`，而词里没有。
    """
    assert pb.caption_norm(PROBE_TEXT) == "".join(t for _, _, t in PROBE_RAW)
    assert pb.caption_norm("全国执行。") == "全国执行" == pb.caption_norm("全国 执行")
    # 归一化不许动数字与单位（「10月」是一个词，压成「月」就毁掉判据）
    assert pb.caption_norm("10月）全国") == "10月全国"


def t_word_events_become_monotonic_second_based_words():
    """取数面负责 tick→秒 + 夹单调 + 丢空词与越界词。

    真稿的形状是**相切不是重叠**：P2-1 按 tick 复算五镜 106 个间隙，min 0.000000、负数 0 处、
    恰相切 33 处（证据 §K9）。所以 `角标` 与 `的` 都落在 5.7875s、四舍五入后相等 —— 真值这一
    半证明"相等不许当错误"；夹取那一支今天没有实测负空隙作依据，属防御性，因此由一条
    **合成**的重叠事件单独证明它会执行。防御性不等于可以不断言：不夹的话，服务一改切分，
    一条 `fromTo` 的 start 就排进前一条的退场里，逐词入场变成乱序闪烁，而且只在个别镜上
    发生，抽帧很容易漏。
    """
    words = pb.words_from_events(_probe_events(), PROBE_SECONDS)
    assert len(words) == 17
    assert [w["w"] for w in words] == [t for _, _, t in PROBE_RAW]
    assert all("s" in w and "e" in w for w in words)
    assert words[0]["s"] == 0.1 and words[-1]["e"] == 7.275
    for prev, cur in zip(words, words[1:]):
        assert cur["s"] >= prev["e"], f"{cur['w']} 排在 {prev['w']} 退场之前: {prev} {cur}"
    assert words[12]["w"] == "角标" and words[13]["w"] == "的"
    assert words[13]["s"] == words[12]["e"] == 5.787, \
        "tick→秒的取整口径变了：同一点的两次换算算出了两个数"
    # 合成一条负空隙：把 `的` 的 offset 回拨 2ms（真稿 §K9 实测 0 处，所以这一支是防御性的，
    # 只能靠造出来的数据证明它真的会执行）。start 必须抬到前词 end，而右沿跟着自己的
    # offset+duration 走（5.898）—— 夹的是左边界不是时长。
    overlap = _probe_events()
    overlap[13] = dict(overlap[13], offset=overlap[13]["offset"] - 20000)
    clamped = pb.words_from_events(overlap, PROBE_SECONDS)[13]
    assert clamped["s"] == 5.787 and clamped["e"] == 5.898, \
        f"重叠没被夹住: {clamped}"
    assert all(0.0 <= w["s"] < w["e"] <= PROBE_SECONDS for w in words)
    # 空词与越界词都得丢，但不能靠"碰巧没有"
    junk = _probe_events() + [{"type": "WordBoundary", "offset": round(9.9e7),
                               "duration": 1000, "text": "越界"},
                              {"type": "WordBoundary", "offset": 0, "duration": 1000,
                               "text": " "}]
    assert [w["w"] for w in pb.words_from_events(junk, PROBE_SECONDS)] == \
        [t for _, _, t in PROBE_RAW]



def t_words_group_into_cues_by_exact_char_consumption():
    """cue（句子级条）由**精确消费字符数**归组，不用比例猜 —— 比例是法则 5 禁的东西。

    文本取原文那一段（带标点，那是给人读的），时间取该段首词 start / 末词 end。
    探针正文两句 ⇒ 6 词 + 11 词。
    """
    words = pb.words_from_events(_probe_events(), PROBE_SECONDS)
    cues = pb.cues_from_words(PROBE_TEXT, words, PROBE_SECONDS)
    assert [c["text"] for c in cues] == ["门诊新规，10月起全国执行。",
                                         "探针第一镜，只为量出角标的真实像素几何。"]
    assert cues[0]["start"] == round(0.100, 3) and cues[0]["end"] == round(2.812, 3)
    assert cues[1]["start"] == round(3.388, 3) and cues[1]["end"] == round(7.275, 3)
    assert [len(c["words"]) for c in cues] == [6, 11]
    for cue in cues:
        assert pb.caption_norm(cue["text"]) == "".join(w["w"] for w in cue["words"]), \
            "归组把词吞掉或多分了 —— 这条 cue 上屏的字与实际念的字不是同一串"
    # 末词右沿比音频早 0.573s：取数面要把它如实交出去，不许悄悄拉长到镜尾
    assert cues[-1]["end"] < PROBE_SECONDS


def t_char_fallback_degrades_timing_only():
    """降级只降级**时序**：没有服务数据时按字符数比例分，词表与强调一个都不能少。

    与法则 5 的分界要写清楚：这里按比例分的是"没有外部时序时的兜底切分"，
    被禁止的是"猜哪个词该被强调"。所以降级支上强调匹配仍必须工作。
    """
    words = pb.words_from_text(PROBE_TEXT, PROBE_SECONDS)
    assert words, "降级支不能交出空词表 —— 空表等于字幕整条消失"
    assert "".join(w["w"] for w in words) == pb.caption_norm(PROBE_TEXT)
    for prev, cur in zip(words, words[1:]):
        assert cur["s"] >= prev["e"]
    assert words[0]["s"] >= 0.0 and words[-1]["e"] <= PROBE_SECONDS + 1e-6
    # 时序是估的，但"念到哪"的相对次序不能反：句尾词的 start 必须晚于句首词
    assert pb.match_accent(words, "全国执行") and pb.match_accent(words, "像素几何")
    cues = pb.cues_from_words(PROBE_TEXT, words, PROBE_SECONDS)
    assert [c["text"] for c in cues] == ["门诊新规，10月起全国执行。",
                                         "探针第一镜，只为量出角标的真实像素几何。"]


def t_accent_matching_is_exact_and_never_guesses():
    """强调三源与词表做**精确子串匹配**；匹配不上就不高亮，禁止按比例猜。

    反例形状：给一个不存在的强调串，实现若"按比例挑几个词"就会返回非空 ——
    那等于在画面上把强调挂到没念过的词上。
    """
    words = pb.words_from_events(_probe_events(), PROBE_SECONDS)
    hits = pb.match_accent(words, "全国执行")
    assert [w["w"] for w in hits] == ["全国", "执行"]
    # 带标点的源要先归一化再匹配（探针：词里没有标点）
    assert [w["w"] for w in pb.match_accent(words, "全国执行。")] == ["全国", "执行"]
    assert pb.match_accent(words, "门诊新规，10月起全国执行") == words[:6]
    assert pb.match_accent(words, "角标的真实") == words[12:15]
    assert pb.match_accent(words, "") == []
    assert pb.match_accent(words, "全国执行明天") == [], "跨不过去的源必须整条不亮"
    assert pb.match_accent(words, "国执") == [], "词内切不是子串匹配的语义"
    assert pb.match_accent([], "全国") == []


def t_the_accent_marker_is_not_a_spoken_character():
    """`｜` 是作者写的**标记**，不是会被念出来的字。

    漏掉这一条的后果不是"字幕多个竖线"：`caption_norm` 若不剥它，归组时这一段就比词表
    多 1 个字，`cues_from_words` 必然失配 —— 于是每条点了强调的稿子都走退化支，⚠️ 日志
    刷屏，而真正的降级原因（作者的排版习惯）和实现一点关系都没有。
    """
    assert pb.caption_norm("门诊新规｜全国执行") == "门诊新规全国执行"
    marked = "门诊新规｜全国执行。"
    words = pb.words_from_text(marked, 4.0)
    assert "".join(w["w"] for w in words) == "门诊新规全国执行"
    cues = pb.cues_from_words(marked, words, 4.0)   # 不许抛"归组对不上"
    assert len(cues) == 1 and len(cues[0]["words"]) == len(words)


def t_caption_accent_prefers_the_authors_mark_then_the_number_then_the_screen():
    """一条 cue 的强调源按 `｜` → 数字+单位 → 屏句强调段 取**第一个匹配得上的**。

    优先级抄 `pick_accent`（屏上位就是这么定的），字幕轨不许自定另一套 —— 两处口径不同
    的表现是同一支片子里标题亮"10月"、字幕亮别的词，看着像 bug 但每处单看都对。
    """
    pipe_words = pb.words_from_text("门诊新规｜全国执行。", 4.0)
    pipe_cue = pb.cues_from_words("门诊新规｜全国执行。", pipe_words, 4.0)[0]
    assert "".join(w["w"] for w in pb.cue_accent_words(pipe_cue, {})) == "全国执行", \
        "作者点的名必须赢"
    # ② 没有 ｜ 时看"数字+单位"：探针正文里的 `10月` 就是这一支
    ev_words = pb.words_from_events(_probe_events(), PROBE_SECONDS)
    ev_cues = pb.cues_from_words(PROBE_TEXT, ev_words, PROBE_SECONDS)
    assert "".join(w["w"] for w in pb.cue_accent_words(ev_cues[0], {})) == "10月"
    # ③ 两者都没有 ⇒ 用屏句的强调段，但它**只有真被念出来**才亮
    plain = pb.cues_from_words("探针第一镜。", pb.words_from_text("探针第一镜。", 3.0), 3.0)[0]
    # 注意粒度：字符支上"词"就是单个字，所以比的是**亮起来的这串字**而不是词的切法
    assert "".join(w["w"] for w in pb.cue_accent_words(plain, {"onscreenAccent": "第一镜"})) == \
        "第一镜"
    assert pb.cue_accent_words(plain, {"onscreenAccent": "没念过的词"}) == [], \
        "屏句没进正文就不亮 —— 挂在没念过的词上等于字幕和配音对不上"
    assert pb.cue_accent_words(plain, {}) == [] and pb.cue_accent_words(plain, None) == []


def t_caption_accent_never_changes_the_text_on_screen():
    """强调是**词的属性**，不是对文本的再切分：取完强调，上屏那串字必须一字不差。

    这条盯的是旧实现的老毛病（`text[-4:]` 兜底切尾巴造出词中间的珊瑚片）：只要
    `cue_accent_words` 里出现任何"改写/裁掉 cue 文本"的动作，这个断言就会红。
    降级支（字符时序）与真支（词级时序）都必须过同一份断言 —— 裁决只换时序不换"亮哪个字"。
    """
    for words in (pb.words_from_events(_probe_events(), PROBE_SECONDS),
                  pb.words_from_text(PROBE_TEXT, PROBE_SECONDS)):
        for cue in pb.cues_from_words(PROBE_TEXT, words, PROBE_SECONDS):
            accent = pb.cue_accent_words(cue, {"onscreenAccent": "像素几何"})
            assert "".join(w["w"] for w in cue["words"]) == pb.caption_norm(cue["text"])
            assert all(w in cue["words"] for w in accent), "强调词必须来自这条 cue 自己"
            assert cue["text"].count("｜") == 0
    # 同一份稿子，两条支上亮起来的**那串字**必须一致（词的切法可以不同：字符支按字切，
    # 词级支按服务给的词切 —— 观众看到的是哪些字变颜色，不是我们内部怎么分词）
    a = pb.cue_accent_words(pb.cues_from_words(
        PROBE_TEXT, pb.words_from_events(_probe_events(), PROBE_SECONDS), PROBE_SECONDS)[0], {})
    b = pb.cue_accent_words(pb.cues_from_words(
        PROBE_TEXT, pb.words_from_text(PROBE_TEXT, PROBE_SECONDS), PROBE_SECONDS)[0], {})
    assert "".join(w["w"] for w in a) == "".join(w["w"] for w in b) == "10月"



def t_synthesize_audio_reuses_cues_json_without_the_service():
    """`cues.json` 是可复现输入：命中 (归一化正文, voice) 哈希就**不碰服务**。

    落盘的真理由（§6.4 订正后）：① 降级支与真支时序不同，不落盘就证明不了一支片子
    走的哪条；② 配音段实测 12.1–12.9s 是网络往返，重跑门禁不该再花一次，
    更不该在微软服务抖动时把已合格的稿子变成失败。
    哈希不匹配必须重配 —— 拿旧 cues 配新稿会让字幕与配音对不上而**两边都还是绿的**。
    """
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        doc = {"schema": "hf-cues/1", "scenes": [{
            "index": 1, "voice": "zh-CN-XiaoxiaoNeural",
            "key": pb.cue_cache_key(PROBE_TEXT, "zh-CN-XiaoxiaoNeural"),
            "text": PROBE_TEXT, "seconds": PROBE_SECONDS, "mode": "word",
            "mp3": "scene_1.mp3",
            "words": [{"w": w["w"], "s": w["s"], "e": w["e"]}
                      for w in pb.words_from_events(_probe_events(), PROBE_SECONDS)],
        }]}
        pb.write_json(os.path.join(d, "cues.json"), doc)
        open(os.path.join(d, "scene_1.mp3"), "wb").write(b"\x00" * 128)

        def boom(*a, **k):
            raise AssertionError("缓存命中还去问服务 = 重跑不可复现，也白花 12s 网络")

        real = pb.tts_word_events
        pb.tts_word_events = boom
        try:
            scenes = [{"body": PROBE_TEXT}]
            mp3s, cues, durations = pb.synthesize_audio(scenes, "zh-CN-XiaoxiaoNeural", d)
        finally:
            pb.tts_word_events = real
        assert durations == [PROBE_SECONDS]
        assert mp3s == [os.path.join(d, "scene_1.mp3")]
        assert [c["text"] for c in cues[0]] == ["门诊新规，10月起全国执行。",
                                               "探针第一镜，只为量出角标的真实像素几何。"]

        # 改一个字 ⇒ 缓存必须失效：这里 cues.json 里留的还是 PROBE_TEXT 那一份的键，
        # 而交进来的稿子只剩四个字 —— 键对不上，必须重新问服务（同一个 mp3 路径不算依据）。
        assert pb.cue_cache_key(PROBE_TEXT, "zh-CN-XiaoxiaoNeural") != \
            pb.cue_cache_key(PROBE_TEXT + "改", "zh-CN-XiaoxiaoNeural")
        assert pb.cue_cache_key(PROBE_TEXT, "zh-CN-YunxiNeural") != \
            pb.cue_cache_key(PROBE_TEXT, "zh-CN-XiaoxiaoNeural")
        called = {}

        def fake(text, voice, mp3_path):
            called["text"] = text
            return _probe_events(), 128

        pb.tts_word_events = fake
        try:
            pb.synthesize_audio([{"body": "换了稿子"}], "zh-CN-XiaoxiaoNeural", d)
        finally:
            pb.tts_word_events = real
        assert called.get("text") == "换了稿子", "哈希不匹配却没重配 = 字幕配错音"


def t_collect_cues_shifts_scenes_without_reparsing_files():
    """`collect_cues` 的入参从"逐镜字幕文件"换成取数面交出的 cue —— 一处真源。

    旧实现读 `scene_i.vtt` 再 `CUE_RE` 解析：那个文件其实是 **SRT 体**
    （7.2.8 的 `SubMaker` 只有 `get_srt`），文件名一直在骗人，spec §6.4 早期就被它
    带偏过一次。平移口径不变：第 n 镜的 cue 加上前 n-1 镜时长之和，且夹在本镜区间内。
    """
    words = pb.words_from_events(_probe_events(), PROBE_SECONDS)
    scene_a = pb.cues_from_words(PROBE_TEXT, words, PROBE_SECONDS)
    scene_b = pb.cues_from_words("第二镜正文。", pb.words_from_text("第二镜正文。", 4.0), 4.0)
    cues = pb.collect_cues([scene_a, scene_b], [PROBE_SECONDS, 4.0], 15)
    assert cues, "平移后一条都不剩 = 字幕轨空转"
    starts = [s for s, _, _ in cues]
    assert starts == sorted(starts), f"跨镜后 cue 乱序: {starts}"
    assert cues[0][0] == round(0.100, 3)
    assert all(e - s >= 0.15 for s, e, _ in cues), "零时长 cue 会让 fromTo 退化成跳变"
    assert cues[-1][1] <= PROBE_SECONDS + 4.0 + 1e-6
    assert all("\\N" not in t or len(t.split("\\N")) <= 2 for _, _, t in cues), \
        "行数控的是 ASS 的禁入区下界，超行等于把正文压进禁入区"


# ---------------- P1-3c 编译器：spec.toml → 宿主 + 7 版式 + frame.md ----------------

FLAGSHIP_PACK_DIR = os.path.join(PATH_C_ROOT, "news-editorial-warm")


def _flagship_tokens():
    spec = hs.load_spec(Path(FLAGSHIP_SPEC))
    return spec, hp.tokens_from_spec(spec, hs.caption_reserve_cqh(spec.subtitle))


def _compiled_texts() -> dict:
    """七套版式当前编译出来的文本（不落盘，直接从 `composition_html` 取）。"""
    spec, tok = _flagship_tokens()
    return {layout: hc.composition_html(spec, tok, layout)
            for layout in hs.CANONICAL_LAYOUTS}


def _compile_twice(spec_path: str):
    """编译两遍到同一个临时目录，返回 `{包内相对路径: 文本}` 两份（确定性 + 落盘形状）。"""
    import tempfile
    runs = []
    with tempfile.TemporaryDirectory() as td:
        for _ in range(2):
            files = hc.compile_pack(Path(spec_path), out_root=Path(td), write=True)
            runs.append({str(Path(f).relative_to(Path(td) / "news-editorial-warm"))
                         .replace(os.sep, "/"): Path(f).read_text(encoding="utf-8")
                         for f in files})
    return runs


def t_hf_compile_variable_ids_are_emitter_derivable():
    """契约 §F.3：版式只许声明**发射器推得出来**的变量 id，且每个声明都得真上屏。

    为什么必须是断言而不是注释：发射器按 id 词表取数（`DERIVERS` + `INDEXED_VAR_RE`），
    词表外的 id 装包时不报错，只在发射那一镜拿到 None 或回落 default —— 屏上凭空出现
    一句没人写过的话，而三道闸与 `check --strict` 都看不见（文本是运行时才进来的）。
    同理，声明了却没人渲染的 id 是死契约：P5 铺 31 套时会照单填数据，白填。
    """
    assert sorted(hc.CONTRACTS) == sorted(hs.CANONICAL_LAYOUTS), \
        f"CONTRACTS 的键与契约面分家: {sorted(hc.CONTRACTS)}"
    assert sorted(hc.CONTRACTS) == sorted(pb.AUTO_LAYOUT_STEMS), \
        "发射器能选出的版式名与编译器产出的不是同一套"
    derivable = set(pb.DERIVERS) | {"imagePath", "imageCredit"}
    for layout, ids in hc.CONTRACTS.items():
        assert "slotSeconds" in ids, f"{layout}: 没声明 slotSeconds → 动量预算取不到秒数"
        for var_id in ids:
            assert var_id in derivable or pb.INDEXED_VAR_RE.match(var_id), \
                f"{layout}: 变量 {var_id!r} 不在发射器词表里（新 id 先加推导器）"
    # 占位词表闭合：没人声明的默认值就是死数据，早晚与 CONTRACTS 分家
    used = {v for ids in hc.CONTRACTS.values() for v in ids} - {"slotSeconds"}
    assert set(hc._VAR_DEFAULTS) == used, (
        f"默认值表与契约用的 id 分家 —— 多: {sorted(set(hc._VAR_DEFAULTS) - used)}, "
        f"少: {sorted(used - set(hc._VAR_DEFAULTS))}")
    # P3 已接线：story 版式声明 imagePath（photo-local-crop 纹理图位，无图塌槽）。
    # 图位仍只许在 story —— 其余六套不声明图位（裁决：先在一套版式打通含图端到端）。
    image_slots = {layout: [v for v in ids if v in ("imagePath", "imageCredit")]
                   for layout, ids in hc.CONTRACTS.items()
                   if any(v in ("imagePath", "imageCredit") for v in ids)}
    assert image_slots == {"story": ["imagePath"]}, \
        f"P3 图位只该落在 story 的 imagePath，实际: {image_slots}"
    for layout, text in _compiled_texts().items():
        for var_id in hc.CONTRACTS[layout]:
            # 取用形式有三种：文字位 `data-var-text="id"`、点取 `vars.id`、
            # 取图路径这类非文字位用方括号 `vars["id"]`（photo-local-crop 的 pre_js）。
            bound = (f'data-var-text="{var_id}"' in text or f"vars.{var_id}" in text
                     or f'vars["{var_id}"]' in text)
            assert bound, f"{layout}: 声明了 {var_id} 却没有任何元素/脚本取用它"


def t_hf_compile_is_deterministic_and_the_tracked_files_are_compile_output():
    """同 spec 编译两次逐字节相同，且**仓库里躺着的那 9 个文件就是编译产物**。

    两次相等证法则 10（抖动全部编译期烘焙，落盘没有墙钟/随机）；与仓库文件相等证
    没有人手改过产物 —— 手改产物是 D10/D20 那条老路的第一步，而 `frame.md` 头上
    写着"勿手改"却没有闸时，那句话就是散文。
    """
    first, second = _compile_twice(FLAGSHIP_SPEC)
    assert first == second, "两次编译产物不一致：产物里有不可复现的取数"
    assert len(first) == 9, f"应当写 9 个文件（host + frame.md + 7 版式），实际 {len(first)}"
    assert {k for k in first if k.startswith("compositions/")} == {
        f"compositions/{layout}.html" for layout in hs.CANONICAL_LAYOUTS}
    for relative, text in first.items():
        tracked = Path(FLAGSHIP_PACK_DIR) / relative
        assert tracked.is_file(), f"仓库缺产物 {relative}（跑一次 hf_compile.py）"
        assert tracked.read_text(encoding="utf-8") == text, (
            f"{relative} 与编译输出不一致 —— 产物被手改过，或 spec 改完没重编译")
    assert "勿手改" in first["frame.md"], "frame.md 没声明自己是编译产物"


def t_hf_compile_pack_loads_through_the_real_emitter():
    """编译产物必须能被**发射器本体**装起来 —— 不是被我照抄一遍的正则装起来。

    这条走 `pb.load_style_pack` / `pb.emit_host` 真函数，且**不改任何全局量**：P1-3d 的
    pack 根接缝（`PACK_ROOTS` 先 path_b 后 path_c）本来就是为了让他俩在同一进程里
    同时可寻址，所以这里现成的默认根就是被测对象。契约 JSON、根节点 id、`#root`
    地面登记、六个宿主占位符，任何一样缺了都会在那里停机。
    """
    resolved = pb.pack_dir("news-editorial-warm")
    assert resolved.endswith(os.path.join("hyperframes_path_c", "news-editorial-warm")), resolved
    pack = pb.load_style_pack("news-editorial-warm")
    assert sorted(pack["layouts"]) == sorted(hs.CANONICAL_LAYOUTS)
    spec, _tok = _flagship_tokens()
    prefix = hc.pack_prefix(spec.id)
    for layout, entry in pack["layouts"].items():
        assert entry["composition_id"] == f"{prefix}-{layout}", entry["composition_id"]
        assert entry["ground_hex"] == spec.surfaces[hc.GROUNDS[layout]].lower()
        assert [v["id"] for v in entry["variables"]] == hc.CONTRACTS[layout], \
            f"{layout}: 发射器解析出的契约与 CONTRACTS 不同"
    tones = {entry["ground_tone"] for entry in pack["layouts"].values()}
    assert tones == {pb.TONE_LIGHT, pb.TONE_DARK}, \
        f"包里只有一个明暗面，`_tone` 的翻面与相邻镜换地面都无从可判: {tones}"
    # story 的翻面必须三样齐：CSS 覆盖、根节点属性初值、脚本改 dataset（news-coral 实测形状）
    story = pack["layouts"]["story"]
    text = Path(story["path"]).read_text(encoding="utf-8")
    assert 'data-tone="light"' in text and '#root[data-tone="dark"]' in text \
        and "rootEl.dataset.tone" in text
    for suffix, role in hc.TONE_FLIPS["story"].items():
        assert f'#root[data-tone="dark"] #{prefix}{suffix}' in text, f"{suffix} 没换色"
        assert f"{spec.surfaces['ink'].lower()}" in text.lower()
    # 宿主：六个占位符一个不缺（少一个 `emit_host` 当场停机），填完不留残余
    mounts = ['<div class="clip" data-composition-src="compositions/hook.html"></div>'] * 2
    audios = ['<audio id="voice-1"></audio>', '<audio id="voice-2"></audio>']
    filled = pb.emit_host(pack, mounts, audios, 9.5, hc.WIDTH, hc.HEIGHT)
    assert "{{" not in filled and f'data-composition-id="{pb.HOST_COMPOSITION_ID}"' in filled
    assert filled.count('data-composition-src="compositions/') == 2


def t_hf_compile_recipes_fill_the_frame():
    """法则 17（填幅）：每套版式的最重内容下沿必须离内容区下沿足够近。

    P1-3e 出帧实测：未约束时七套空出 3.5–14.6cqh，竖屏下半部空转是"模板感"的主要来源，
    而四道闸没有一条看得见（法则 1 只管"不许怼进字幕区"，不管"怼得不够"）。
    这条把判据 1 的一部分变成机判：口径是配方的**最坏占位**，见 `MAX_BOTTOM_DEAD_CQH`。
    """
    spec, tok = _flagship_tokens()
    limit = 100.0 - tok.reserve_bottom - hc.CONTENT_FLOOR_MARGIN_CQH
    for layout in hs.CANONICAL_LAYOUTS:
        steps = hc._steps(layout, tok, hc.pack_prefix(spec.id))
        placed = [s.kwargs["top"] + s.height_cqh for s in steps if "top" in s.kwargs]
        dead = limit - max(placed)
        assert dead <= hc.MAX_BOTTOM_DEAD_CQH, \
            f"{layout}: 内容下沿距 {limit:.1f}cqh 还空 {dead:.2f}cqh（上限 {hc.MAX_BOTTOM_DEAD_CQH}）"
        assert hc.geometry_violations(spec, tok, layout) == [], layout
    # 反例：把 closer 最重的两条抽掉 ⇒ 下半部空出来，必须报且点名法则 17
    real = hc._steps

    def sparse(layout, tok_, p):
        steps = real(layout, tok_, p)
        return [s for s in steps if not s.ident.endswith("-channel")
                and not s.ident.endswith("-bar")] if layout == "closer" else steps

    hc._steps = sparse
    try:
        hits = hc.geometry_violations(spec, tok, "closer")
        assert len(hits) == 1 and "法则 17" in hits[0], hits
        assert hc.geometry_violations(spec, tok, "hook") == [], "误伤了别的版式"
    finally:
        hc._steps = real


def t_hf_compile_text_positions_have_columns_and_never_touch():
    """法则 18（横向）：每个文字位声明栏宽，且任意两位的盒不得相交。

    起因是 P1-3e 的并排帧：眉标片（带底色）与标题行盒交 0.59cqh，出帧上有一道
    强调色横穿标题 —— 四道闸当时全绿。根因不是"没人看出会碰上"，而是**没有横向口径**：
    绝对定位只写 `left` 时盒宽是收缩量，右沿取决于文案长短，编译期无从判定。
    所以这条闸分三支，缺一支就是假绿：
      ① 声明了栏宽（没声明 ⇒ 右沿未知，直接拒编）；
      ② 栏宽落在 spec 的安全幅里（写得出但贴出画布的数一样是错的）；
      ③ 两两盒不相交（重叠判定只在 ①② 都成立时才有意义）。
    另外必须核到**产物 CSS 里真的有 `max-width`** —— 只在配方表里写个数而原语不落
    CSS，浏览器仍按收缩盒排版，那条闸就只是纸面数字（法则 13 说的"可执行"就是这个）。
    """
    spec, tok = _flagship_tokens()
    text_total = 0
    for layout in hs.CANONICAL_LAYOUTS:
        steps = [s for s in hc._steps(layout, tok, hc.pack_prefix(spec.id)) if s.text]
        text_total += len(steps)
        assert steps, f"{layout} 没有文字位 —— 配方被改空了"
        for step in steps:
            assert "max_width" in step.kwargs, f"{step.ident} 没声明栏宽"
        assert hc.overlap_violations(spec, tok, layout) == [], layout
    assert text_total >= 41, f"文字位总数从 41 掉到 {text_total}，配方被动过"

    # 栏宽真的进了 CSS：片的盒 = 内容宽 + 2×pad_h，大数字的右沿从实测字宽推。
    hook_css = hc.composition_html(spec, tok, "hook")
    assert f"max-width: {hp._num(hc.kicker_width(2.8))}cqw" in hook_css, "眉标片的栏宽没落进 CSS"
    rail_css = hc.composition_html(spec, tok, "rail")
    ordinal_w = hc.numeral_width(16.0)
    assert f"left: {hp._num(94.0 - ordinal_w)}cqw" in rail_css, "镜序的左沿不是从字宽推出来的"
    assert f"max-width: {hp._num(ordinal_w)}cqw" in rail_css, "镜序的栏宽没落进 CSS"

    real = hc._steps

    def patched(suffix, mutate):
        def _steps(layout, tok_, p):
            steps = real(layout, tok_, p)
            for step in steps:
                if step.ident.endswith(suffix):
                    mutate(step)
            return steps
        return _steps

    def try_with(suffix, mutate, layout):
        hc._steps = patched(suffix, mutate)
        try:
            return (hc.overlap_violations(spec, tok, layout),
                    hc.overlap_violations(spec, tok, "hook"))
        finally:
            hc._steps = real

    # ① 把标题顶边推回眉标片的盒里（就是本次修掉的那个缺陷的形状）
    hits, other = try_with("-rl-title", lambda s: s.kwargs.update(top=13.0), "rail")
    assert len(hits) == 1 and "相交" in hits[0] and "法则 18" in hits[0], hits
    assert other == [], f"改的是 rail，hook 跟着报错说明闸不作用域化: {other}"

    # ② 抽掉栏宽：收缩盒的右沿未知，必须点名拒编而不是跳过
    hits, _ = try_with("-rl-title", lambda s: s.kwargs.pop("max_width"), "rail")
    assert any("没声明 max_width" in p for p in hits), hits

    # ③ 栏宽写出安全幅外（94 是 spec.grid.safe 算出来的右沿）
    hits, _ = try_with("-sy-title", lambda s: s.kwargs.update(max_width=90.0), "story")
    assert any("越出安全幅" in p for p in hits), hits


def t_hf_build_step_index_is_structural_not_data():
    """`stepNIndex`（01/02/03）是**行号**不是文案：行存在就必然有这个号，不吃分镜字段。

    发射器因此不需要为编译包多写任何数据，同一份分镜稿仍能并排喂两套（P1-3e 的口径）。
    行数不够时返回 None ⇒ 上层判"这个版式填不满"，而不是屏上凭空多出一个 03。
    """
    assert pb.INDEXED_VAR_RE.match("step3Index") and pb.INDEXED_VAR_RE.match("item1Index"), \
        "词表形态没放行 Index —— 编译器会声明发射器填不出来的 id"
    assert not pb.INDEXED_VAR_RE.match("step0Index") and not pb.INDEXED_VAR_RE.match("step1Nope")
    items = [{"label": f"标{i}", "body": f"说明{i}", "value": f"值{i}"} for i in range(1, 4)]
    three, two = {"items": items}, {"items": items[:2]}
    pb.register_indexed_derivers(["step1Index", "step3Index"])
    assert pb.DERIVERS["step1Index"](three, {}, {}) == "01"
    assert pb.DERIVERS["step3Index"](three, {}, {}) == "03"
    assert pb.DERIVERS["step3Index"](two, {}, {}) is None, "只有两行却给出第三行的号"
    # 编译包契约里 catalog 确实声明了这三个 id，且默认值是同一个号（单文件预览不撒谎）
    for i in (1, 2, 3):
        assert f"step{i}Index" in hc.CONTRACTS["catalog"]
        assert hc._VAR_DEFAULTS[f"step{i}Index"][1] == f"{i:02d}"


def t_hf_compile_refuses_every_broken_recipe():
    """编译器的每条拒编分支都要被真的坏写法触发 —— 空转的闸比没有闸更危险。

    分支清单：禁入区几何（法则 1 的编译期版本）、大字档色对被缩小（判据 3 的暗道）、
    前置条件（强调色只当形状）、契约词表（陌生 id / 缺 slotSeconds / 键不闭合）、
    配方表外的版式名、呼吸位移把内容层顶出裁剪区（含全幅图层那条）。
    全部用 spec/常量的真变异，不在测试里重抄一份判定。
    """
    spec = hs.load_spec(Path(FLAGSHIP_SPEC))
    assert hc.compile_violations(spec) == [], hc.compile_violations(spec)

    # ① 禁入区从 spec 反算：把最坏行数从 3 抬到 8，下沿上移，靠下的元素必须报。
    raw = _flagship_raw()
    raw["subtitle"]["worst-case-lines"] = 8
    grown = hc.compile_violations(hs.Spec(raw))
    assert any("超过内容下沿" in p for p in grown), \
        f"禁入区变大却没拦住压进区里的元素: {grown[:2]}"
    assert any("由 spec.subtitle 反算" in p for p in grown), "报错没给口径来源"

    # ② 大字档下限：抬高 LARGE_MIN_CQW，强调色(kicker, size=large)那几处就该被拒。
    original_floor = hc.LARGE_MIN_CQW
    try:
        hc.LARGE_MIN_CQW = 50.0
        shrunk = [p for layout in hs.CANONICAL_LAYOUTS
                  for p in hc.contrast_floor_violations(
                      spec, hp.tokens_from_spec(spec, hs.caption_reserve_cqh(spec.subtitle)),
                      layout)]
    finally:
        hc.LARGE_MIN_CQW = original_floor
    assert any("大字档色对" in p and "kicker" in p for p in shrunk), shrunk[:2]
    assert hc.contrast_floor_violations(
        spec, hp.tokens_from_spec(spec, hs.caption_reserve_cqh(spec.subtitle)), "hook") == []

    # ③ 前置条件：强调色降回 shape-only，坐在字上的 keyword-tint 必须拒编（不是渲染后才发现）。
    raw = _flagship_raw()
    raw["color"]["accents"][0]["role"] = "shape-only"
    shape_only = hc.compile_violations(hs.Spec(raw))
    assert any("keyword-tint 被拒" in p for p in shape_only), shape_only[:2]

    # ④ 契约词表：陌生 id / 缺 slotSeconds / 键不闭合，三条各报一次。
    def contract_problems_with(mutate):
        snapshot = {k: list(v) for k, v in hc.CONTRACTS.items()}
        try:
            mutate(hc.CONTRACTS)
            return hc.contract_violations(spec)
        finally:
            hc.CONTRACTS.clear()
            hc.CONTRACTS.update(snapshot)

    assert any("不在发射器词表里" in p for p in contract_problems_with(
        lambda c: c["hook"].append("myVibes"))), "陌生 id 被放行"
    assert any("没声明 slotSeconds" in p for p in contract_problems_with(
        lambda c: c["stat"].remove("slotSeconds"))), "缺 slotSeconds 没报"
    assert any("不等于 CANONICAL_LAYOUTS" in p for p in contract_problems_with(
        lambda c: c.pop("closer"))), "契约键少一个版式却没报"

    # ⑤ 配方表只认七个名字：拼错的版式不许静默出空文件。
    try:
        hc._steps("hooks", *([None] * 2))
        raise AssertionError("未知版式名没抛 CompileError")
    except hc.CompileError as exc:
        assert "hooks" in str(exc), exc

    # ⑥ 呼吸位移的上边界：位移按内容层高数，抬大量必须撞上"顶边离开裁剪区"。
    #    这条不是洁癖 —— `container_overflow` 是 info 级，不影响 `--strict` 退出码，
    #    31 套一起刷同一条噪音时，真越界就没有信号了。
    tok = hp.tokens_from_spec(spec, hs.caption_reserve_cqh(spec.subtitle))
    assert [p for layout in hs.CANONICAL_LAYOUTS
            for p in hc.geometry_violations(spec, tok, layout)] == []
    original_drift = hc.DRIFT_Y_PERCENT
    try:
        hc.DRIFT_Y_PERCENT = -20.0
        lifted = [p for layout in hs.CANONICAL_LAYOUTS
                  for p in hc.geometry_violations(spec, tok, layout)]
    finally:
        hc.DRIFT_Y_PERCENT = original_drift
    assert any("呼吸位移" in p for p in lifted), lifted[:2]
    assert hc.geometry_violations(spec, tok, "hook") == [], "恢复默认位移量后 hook 仍报几何问题"

    # ⑦ 全幅图层（P3 才出现的形态）叠呼吸位移是已知冲突：点名，不许静默出噪音。
    real_steps = hc._steps
    try:
        hc._steps = lambda layout, t, p: [hc.Step("drift-y", "x", {}, 0.0)]
        bleed = hc.geometry_violations(spec, tok, "hook")
    finally:
        hc._steps = real_steps
    assert any("container_overflow" in p for p in bleed), bleed[:2]


def t_hf_compile_taboo_registry_executes_every_declared_check():
    """法则 13 的可执行那一半：spec 声明的每条禁忌都得真跑，且每条都能被真坏写法触发。

    分支：①取不到实现的禁忌名 = 散文，直接拒编（不许"写了就当防住了"）；
    ②过冲缓动（招牌缓动改成 `back.out` 的合法 spec）被 forbidden 和 `no-overshoot` 双点；
    ③入场下限：把 `motion.entrance-min-seconds` 调到 0.2，原语的 `max(下限,…)` 就跟着
    放低，`entrance-not-faster-than-0p5s` 必须抓住 —— 这条同时证明禁忌名里的参数是真读的；
    ④圆角：产物里没有，注入一段才测得到（不在测试里重抄判定，只喂输入）；
    ⑤入场形状被改坏（位置参数换成命名变量）⇒ 计数漏网必须冒出来，否则 ③ 是假绿。
    """
    spec = hs.load_spec(Path(FLAGSHIP_SPEC))
    texts = _compiled_texts()
    # 基线：当前产物既不含禁用缓动、也不越禁忌（⑥⑦ 的变异都以这条为对照）。
    assert hc.easing_violations(spec, texts) == [], hc.easing_violations(spec, texts)
    assert hc.taboo_violations(spec, texts) == [], hc.taboo_violations(spec, texts)

    # ① 陌生禁忌名：实现取不到就拒编，且报错带上 spec 的原话。
    raw = _flagship_raw()
    raw["taboos"].append({"check": "no-tilt", "why": "手绘歪斜是街采族的词汇"})
    orphan = hc.compile_violations(hs.Spec(raw))
    assert any("no-tilt" in p and "没有实现" in p for p in orphan), orphan[:2]
    assert any("街采族的词汇" in p for p in orphan), f"报错没带回 spec 原话: {orphan[:2]}"

    # ② 过冲：allowed[0] 是原语取用的招牌缓动，换成 back.out 后两份文件都会带上它。
    raw = _flagship_raw()
    raw["motion"]["easing"]["allowed"][0] = "back.out(2.8)"
    overshoot = hc.compile_violations(hs.Spec(raw))
    assert any("犯了自家禁忌 'no-overshoot'" in p for p in overshoot), overshoot[:2]
    assert any("本族禁用的缓动" in p for p in overshoot), \
        f"forbidden 那半没跑（hf_primitives 模块注释就成了假话）: {overshoot[:2]}"

    # ③ 入场下限 0.2s：0.4/0.45 那两处会掉到本族 0.5s 下限之下。
    raw = _flagship_raw()
    raw["motion"]["entrance-min-seconds"] = 0.2
    fast = hc.compile_violations(hs.Spec(raw))
    assert any("entrance-not-faster-than-0p5s" in p and "0.4s < 本族下限 0.5s" in p
               for p in fast), f"短入场被放行（参数没解析或原语没抬）: {fast[:2]}"
    assert any("kicker" in p for p in fast), f"报错没点出是哪条补间: {fast[:2]}"

    # ④ 圆角：真产物一条没有，注入才测得动。
    radius_free = hc.taboo_violations(spec, texts)
    assert radius_free == []
    rounded = {k: v.replace("inset: 0;", "inset: 0; border-radius: 1.4cqw;", 1)
               for k, v in texts.items()}
    assert rounded != texts, "测试前提坏了: 产物里没有 `inset: 0;` 可注入"
    hits = hc.taboo_violations(spec, rounded)
    assert any("犯了自家禁忌 'no-border-radius'" in p for p in hits), hits[:2]

    # ⑤ 形状漏网：命名位置的 fromTo 不是入场，但计数对不上时必须自己报案。
    renamed = dict(texts)
    renamed["hook"] = texts["hook"].replace("}, 0.25);", "}, kickerStart);", 1)
    assert renamed["hook"] != texts["hook"], "测试前提坏了: hook 里没有 `}, 0.25);`"
    misses = hc.taboo_violations(spec, renamed)
    assert any("入场形状认不出" in p for p in misses), misses[:2]
    # 同一条改坏不许让 ③ 那种违规静默消失：漏网本身就要报，不靠下游断言兜。
    assert hc.scan_entrances(renamed)[1], "scan_entrances 没记这次漏网"


def t_hf_compile_lint_runs_the_real_structure_gate():
    """`lint_composition` 必须真的把产物喂给 `layout_selfcheck`（否则它是装饰代码）。

    正例：当前七套版式全部零问题。反例：从 hook 里抽掉衬线 `@font-face` —— 版式仍然
    用 `HF Serif CJK`，结构闸的 CJK 支路（P1-1 修的那条假绿）必须点名报出来。
    """
    texts = _compiled_texts()
    for layout, text in texts.items():
        assert hc.lint_composition(text, f"{layout}.html") == [], \
            f"{layout}: 编译产物过不了结构闸"
    hook = texts["hook"]
    stripped = re.sub(r"@font-face \{[^}]*HF Serif CJK[^}]*\}", "", hook, flags=re.S)
    assert stripped != hook, "测试前提坏了: hook 里没有衬线 @font-face 可抽"
    found = hc.lint_composition(stripped, "hook.html")
    assert any("HF Serif CJK" in problem for problem in found), \
        f"抽掉中文族声明却没被闸抓到（假绿复发）: {found}"
    # 整段脚本（含模板自带的 `const vars/tl/rootEl` 与各原语的切字局部名）必须词法合法：
    # `invalid_inline_script_syntax` 是 error 级，Python 三道闸不解析 JS，只能这样前移。
    for layout, text in texts.items():
        script = re.search(r"<script>(.*?)</script>", text, re.S).group(1)
        for match in hp.JS_DECL_NAME_RE.finditer(script):
            assert hp.JS_IDENT_RE.match(match.group(1)), \
                f"{layout}: 非法 JS 标识符 {match.group(1)!r}"


def t_hf_compile_frame_md_passes_the_contrast_audit():
    """第三个闸（`audit_pack_contrast`）必须**真的审得到**编译产物，而不是空转。

    它对包只认两件事：`| token | 值 |` 色板表 + `| 组合 | 比值 | 判定 |` 对比度表
    （表头指纹），外加"版式 HTML 里不许出色板外的 hex"。所以 frame.md 的表头形状
    就是本包受审的接口 —— 改列名不会报错，只会让这个包从此没有色板出处可查。
    """
    pack_dir = Path(FLAGSHIP_PACK_DIR)
    frame = (pack_dir / "frame.md").read_text(encoding="utf-8")
    palette = apc.parse_palette(frame)
    spec = hs.load_spec(Path(FLAGSHIP_SPEC))
    # 色板表覆盖 spec 的每个面与每条文字色（否则 OFF_PALETTE_HEX 会假违规）
    declared = set(palette.values())
    for hex_value in list(spec.surfaces.values()) + [p["hex"] for p in spec.text_pairs]:
        assert apc._normalize_hex(hex_value) in declared, \
            f"{hex_value} 没进 frame.md 色板表（审计闸会判出色板外）"
    claims = apc.parse_ratio_claims(frame)
    assert len(claims) == len(spec.text_pairs), \
        f"对比度表条数与 spec 色对分家: {len(claims)} vs {len(spec.text_pairs)}"
    _matrix, findings = apc.audit_pack(pack_dir)
    assert findings == [], f"色板审计不过: {[str(f) for f in findings]}"


def t_hf_style_spec_latin_names_are_engine_supplied():
    """拉丁位是一个**闭集**，不是自由字符串 —— spec §5 原写"拉丁侧无上限"，P1 实测已推翻并订正。

    实测出处：`node_modules/hyperframes/dist/chunk-HBBJFK6I.js:33-135` 打的是 18 个
    捆绑族的下载清单，`chunk-WY5OODN5.js:6064` 把集合外的 `font-family` 判成
    `font_family_without_font_face`（severity **error**）。所以 `check --strict` 会直接
    拒收，而字面本身还会静默回落成通用族 —— 31 套里每一套都受影响，必须编译期拦。
    """
    assert len(hs.LATIN_CANONICAL_FAMILIES) == 18, hs.LATIN_CANONICAL_FAMILIES
    spec = hs.load_spec(Path(FLAGSHIP_SPEC))
    for name in spec.raw["type"]["latin"]:
        assert name in hs.LATIN_CANONICAL_FAMILIES, f"旗舰 spec 用了集合外族名: {name}"
    # 大小写/空白不敏感：族名匹配按 CSS 是不区分大小写的，比对不能靠 `.title()`
    # （那样会把 "EB Garamond" 改写成 "Eb Garamond"，把合法名字判成非法）。
    loose = _flagship_raw()
    loose["type"]["latin"] = ["  playfair display ", "EB Garamond"]
    assert hs.validate(loose, source="t") == [], hs.validate(loose, source="t")
    bogus = _flagship_raw()
    bogus["type"]["latin"] = ["Libre Bodoni"]
    problems = hs.validate(bogus, source="t")
    assert any("font_family_without_font_face" in p for p in problems), \
        f"引擎不供的族名被放行: {problems}"


# ---------------- P2-3/P2-4 字幕收进 HyperFrames（裁决 2）：发射器 + 版式自检豁免 ----------------

def _probe_scene():
    """取数面交出的**真词级 cue** 一镜（PROBE_TEXT 两句 → 两条 cue，各带 words）。"""
    words = pb.words_from_events(_probe_events(), PROBE_SECONDS)
    return pb.cues_from_words(PROBE_TEXT, words, PROBE_SECONDS)


def t_subtitle_pieces_never_changes_the_on_screen_text():
    """切片是"把上屏串按词切开 + 标点接到前一个词"，一个字都不许增删改。

    这是整条字幕链路的核心不变量：服务给的 `words` 没有标点，而观众要看见标点。
    `_subtitle_pieces` 把标点接回**前一个词**的尾巴，拼回去必须与 `caption_display_text`
    完全相等。只要有任何一次"改写/丢掉字符"，这条就红 —— 而画面上的错字自检看不见。
    """
    for cue in _probe_scene():
        display = pb.caption_display_text(cue["text"])
        pieces = pb._subtitle_pieces(cue, display)
        assert "".join(text for _, text in pieces) == display, (
            f"切片拼回不等于上屏串: {[t for _, t in pieces]!r} vs {display!r}")
        # 标点必须**跟着前面的词**（不许自己成一片、也不许跑到下一个词头上）
        for word, text in pieces:
            assert text.startswith(word["w"]), f"词片没以该词开头: {text!r} / {word['w']!r}"
        # 每个词都得出现，且顺序与词表一致
        assert [w["w"] for w, _ in pieces] == [w["w"] for w in cue["words"]]


def t_subtitle_scene_cues_marks_accent_without_touching_text():
    """强调是词的**着色标记**，取完强调上屏那串字一字不差；退场时刻夹在本 cue 区间内。

    强调口径与屏上位**同一套** `cue_accent_words`：探针正文有「10月」这个数字+单位，
    它优先级高于 `onscreenAccent`（见该函数三源顺序），所以亮的是「10月」而不是「全国执行」。
    这正是字幕轨不许自定第二套口径的意义 —— 与标题亮同一个词。
    """
    scene_cue = _probe_scene()
    scene = {"onscreenAccent": "全国执行"}
    cues = pb.subtitle_scene_cues(scene_cue, scene, PROBE_SECONDS, 15)
    assert len(cues) == 2, f"两句应折成两条 cue，实际 {len(cues)}"
    flat = [span["t"] for cue in cues for line in cue["lines"] for span in line]
    assert "".join(flat) == "".join(pb.caption_display_text(c["text"]).replace(" ", "")
                                    for c in scene_cue)
    accent_spans = [span["t"] for cue in cues for line in cue["lines"] for span in line
                    if span["accent"]]
    assert "".join(accent_spans) == "10月", accent_spans
    # 退场：非末条从 cue.end 起、且不越过下一条开头；末条贴着 slot 尾收
    assert cues[0]["exit_at"] == round(scene_cue[0]["end"], 3)
    assert cues[0]["exit_at"] + cues[0]["exit_dur"] <= cues[1]["start"] + 1e-6, "首条退场盖住了次条"
    assert cues[-1]["exit_at"] >= PROBE_SECONDS - pb.SUBTITLE_EXIT_SECONDS - 1e-6
    assert cues[-1]["exit_dur"] == pb.SUBTITLE_EXIT_SECONDS


def t_subtitle_composition_is_a_valid_subcomposition_and_selfchecks_clean():
    """字幕子合成必须是**合法子合成**（根 id==timeline 键、有 template、有契约面），
    并且**能被真正的版式自检放过** —— 但只放过它的两条豁免项，其余照查。
    """
    cues = pb.subtitle_scene_cues(_probe_scene(), {"onscreenAccent": "全国执行"},
                                  PROBE_SECONDS, 15)
    comp_id = f"{pb.SUBTITLE_FILE_PREFIX}-1"
    text = pb.emit_subtitle_composition(comp_id, cues, PROBE_SECONDS, 1080, 1920, "dark")
    # 子合成契约三件套
    assert "<template>" in text and "</template>" in text
    assert f'data-composition-id="{comp_id}"' in text
    assert f'window.__timelines["{comp_id}"]' in text
    assert 'background: transparent' in text, "#root 必须透明，否则 2 轨会把版式糊住"
    # 每个补间目标都要在同一文件里找得到元素（否则 GSAP 打空目标警告、字幕不出）
    for target in re.findall(r'tl\.\w+\("#([a-z0-9-]+)"', text):
        assert f'id="{target}"' in text, f"补间目标 #{target} 没有对应元素"
    # 过真自检：写进临时目录，文件名前缀命中豁免
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "compositions"))
        p = Path(d) / "compositions" / f"{comp_id}.html"
        p.write_text(text, encoding="utf-8")
        violations = ls.check_layout(p)
        assert not violations, [str(v) for v in violations]


def t_subtitle_composition_is_deterministic():
    """同一份 cue 编译两次逐字节相同 —— 判据 4a：字幕烤进视频流后，流哈希不许因重跑而抖。"""
    cues = pb.subtitle_scene_cues(_probe_scene(), {}, PROBE_SECONDS, 15)
    comp_id = f"{pb.SUBTITLE_FILE_PREFIX}-1"
    a = pb.emit_subtitle_composition(comp_id, cues, PROBE_SECONDS, 1080, 1920, "dark")
    b = pb.emit_subtitle_composition(comp_id, cues, PROBE_SECONDS, 1080, 1920, "dark")
    assert a == b, "字幕子合成不可复现：里面混进了墙钟/随机"
    # 时间全部烤成绝对秒，运行时不读 Date.now / Math.random
    assert "Date.now" not in a and "Math.random" not in a


def t_subtitle_fill_flips_with_ground_tone_to_pass_contrast():
    """字幕填充色随地面翻面：浅地面用墨字白描边、深地面用白字黑描边（裁决：随地面翻色）。

    起因是 `check --strict` 实测：白字(#fff)在旗舰暖纸浅地面 rgb(234,229,217) 上对比
    1.26:1，不过 WCAG AA 3:1（深地面则过）。所以"统一白字"被推翻，改成按本镜真实地面
    tone 取色。两条都断言（缺一条就是假绿）：
      ① light → 墨字 #1f1b16 + 白描边；dark → 白字 #fff + 黑描边；
      ② 强调色两 tone 都固定 #B45309（在旗舰所有地面上都 ≥3，实测见证据 K16）。
    """
    cues = pb.subtitle_scene_cues(_probe_scene(), {}, PROBE_SECONDS, 15)
    comp_id = f"{pb.SUBTITLE_FILE_PREFIX}-1"
    light = pb.emit_subtitle_composition(comp_id, cues, PROBE_SECONDS, 1080, 1920, "light")
    dark = pb.emit_subtitle_composition(comp_id, cues, PROBE_SECONDS, 1080, 1920, "dark")
    # ① 浅地面：填充=墨、描边=白；深地面：填充=白、描边=黑
    assert f"color: {pb.SUBTITLE_INK_COLOR};" in light, light
    assert f"color: {pb.SUBTITLE_LIGHT_COLOR};" in dark, dark
    assert f"em 0 {pb.SUBTITLE_OUTLINE_COLOR}," in light, "浅地面描边没翻成白"
    assert f"em 0 {pb.SUBTITLE_STROKE_COLOR}," in dark, "深地面描边没保持黑"
    # ② 强调两 tone 同色
    assert f"color: {pb.SUBTITLE_ACCENT_COLOR};" in light
    assert f"color: {pb.SUBTITLE_ACCENT_COLOR};" in dark
    # 翻面后浅地面不再是白字（防回退到被推翻的"统一白字"）
    assert "color: #ffffff;" not in light, "浅地面还在用白字，对比度闸会重新报红"
    # 字幕是故意落在 lower-third 禁入区的，必须自带豁免标记，否则 check 报 caption_zone_collision
    assert "data-layout-allow-caption-zone" in light and "data-layout-allow-caption-zone" in dark


def t_subtitle_mount_uses_track_two_and_points_at_generated_file():
    """字幕挂 2 轨（压在 1 轨版式之上），指向发射器同镜写出的 `subtitle-<i>.html`。"""
    mount = pb.emit_subtitle_mount(3, 10.0, 4.0, 1080, 1920)
    assert 'data-track-index="2"' in mount
    assert 'data-composition-src="compositions/subtitle-3.html"' in mount
    assert 'data-composition-id="subtitle-3"' in mount
    assert "data-variable-values" not in mount, "字幕数据烤在子合成里，挂载不再传变量"


def t_selfcheck_exempts_subtitle_only_for_the_two_invariants():
    """豁免只去掉两条（动量预算 / 底部禁入区），契约 / 空目标 / 字体 / px 照查不误。

    反证：把根 id 改成和 timeline 键分家，自检必须仍然报 CONTRACT_ID_MISMATCH ——
    如果我把整个字幕文件跳过了，这条会假绿。
    """
    cues = pb.subtitle_scene_cues(_probe_scene(), {}, PROBE_SECONDS, 15)
    good = pb.emit_subtitle_composition(f"{pb.SUBTITLE_FILE_PREFIX}-1", cues,
                                        PROBE_SECONDS, 1080, 1920, "dark")
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "compositions"))
        p = Path(d) / "compositions" / f"{pb.SUBTITLE_FILE_PREFIX}-1.html"
        p.write_text(good, encoding="utf-8")
        assert ls.check_layout(p) == []
        # 字幕文件确实带 bottom 侵入 + 无 driftDur，靠豁免项才被放过（去掉豁免就会红两条）
        assert "bottom:" in good and "driftDur" not in good
        # 破契约：根 id 改坏，豁免不许掩护它
        broken = good.replace('data-composition-id="subtitle-1"',
                              'data-composition-id="subtitle-X"')
        p.write_text(broken, encoding="utf-8")
        codes = {v.code for v in ls.check_layout(p)}
        assert "CONTRACT_ID_MISMATCH" in codes, codes


def t_flagship_compiled_pack_mounts_subtitle_through_the_real_emitter():
    """旗舰编译包跑一次真发射：每镜多出 `subtitle-<i>.html` + 2 轨挂载，宿主计数仍自洽。

    走 `pb.emit_composition` 真函数（不改全局），证明 scene_cues 接缝、字幕落盘、
    `emit_host` 的挂载计数三处一起成立。存量手发包不传 scene_cues ⇒ 一个字幕文件都不生成。
    """
    pack = pb.load_style_pack("news-editorial-warm")
    assert pack["compiled"] is True
    # story 契约要 领句(title) + 屏句(onscreen)，缺一 choose_layout 就落选（与本测无关，
    # 只是把镜头喂成旗舰真能排版的一镜）。
    scene = {"title": "门诊新规", "body": PROBE_TEXT, "onscreen": "没人告诉他，他一直没问",
             "onscreenAccent": None}
    with tempfile.TemporaryDirectory() as d:
        shots = pb.emit_composition(pack, [scene], [PROBE_SECONDS], d,
                                    {"overrides": {}}, 1080, 1920,
                                    [], [None], scene_cues=[_probe_scene()])
        assert len(shots) == 1
        comp = Path(d) / "compositions" / f"{pb.SUBTITLE_FILE_PREFIX}-1.html"
        assert comp.is_file(), "编译包没落字幕子合成"
        index = Path(d, "index.html").read_text(encoding="utf-8")
        assert index.count('data-track-index="2"') == 1, "字幕轨没挂上"
        assert index.count('data-composition-src="compositions/') == 2, "宿主挂载计数与 mounts 分家"
        # 存量包（无 spec.toml）不生成字幕文件
    warm = pb.load_style_pack(pb.DEFAULT_STYLE)
    assert warm["compiled"] is False, f"存量包被误判成编译包: {warm['dir']}"


def t_mux_retires_ass_subtitles_for_compiled_pack_only():
    """编译包 ⇒ ASS 只剩 AIGC 角标（字幕已烤进画面）；存量包 ⇒ ASS 仍带字幕条。

    `mux_and_burn` 的 `if not cues and not burn_badge` 支路必须靠 burn_badge 兜住：
    cue 传空但 full 档要烧角标时仍走滤镜，否则合规标识被静默丢掉。这里用 build_ass 的
    产物形状核这一点（不打 ffmpeg）：空 cue + 有角标 ⇒ 有 AIGC Dialogue 无 Default Dialogue。
    """
    subtitle_lines = pb.collect_cues([_probe_scene()], [PROBE_SECONDS], 15)
    assert subtitle_lines, "探针该有字幕条"
    # 存量：cue 进 ASS
    legacy_ass = pb.build_ass(subtitle_lines, 1080, 1920, aigc_text="AI生成", aigc_seconds=4.0)
    assert "Style,,0" not in legacy_ass and legacy_ass.count("Dialogue") > 1
    # 编译：cue 传空，只剩角标
    badge_only = pb.build_ass([], 1080, 1920, aigc_text="AI生成", aigc_seconds=4.0)
    assert badge_only.count("Dialogue:") == 1, badge_only
    assert ",AIGC,," in badge_only, "空 cue 时角标事件必须还在"
    assert ",Default,," not in badge_only


# ---- P3 图片门禁（image_gate）判据 P3-1/2/3 ---------------------------------
# 一张有脸 + 一张纯机械的测试图入库到
# `routes/news/evidence/2026-10-10-p3-probe/`；这里跑同一份实现，
# 保证"探针绿 == 产线绿"，不留第二条检测路径。

_P3_FIXTURE_DIR = (Path(__file__).resolve().parents[3]
                   / "routes" / "news" / "evidence" / "2026-10-10-p3-probe")


def t_p3_detector_capability_ok():
    """cv2 + 白名单两张 cascade 都可加载 —— 门能开的前提。"""
    assert ig.capability_ok(), (
        "image_gate 能力未就绪：cv2 或 haarcascade_frontalface_alt2/profileface 缺失。"
        "产线会维持'photo-* 一律拒编'的默认状态，但探针必须显式失败，不能静默。")


def t_p3_face_fixture_hits_four_channel_union():
    """P3-1：入库人脸图在四通道并集下至少一路命中 → floor=G0。"""
    face = _P3_FIXTURE_DIR / "face-01.jpg"
    assert face.is_file(), f"缺 face 测试图 {face}"
    result = ig.detect_faces(face)
    assert result.detector_available
    assert result.floor == "G0", f"入库人脸应判 G0，实际 floor={result.floor} hits={len(result.faces)}"
    assert len(result.faces) >= 1, "四通道并集一次也没命中，检测器或参数漂了"


def t_p3_gear_fixture_hits_nothing_on_whitelist():
    """P3-1（另一半）：齿轮图四通道并集全零 → floor=None。分离度是门禁可信的根。"""
    gear = _P3_FIXTURE_DIR / "gear-01.jpg"
    assert gear.is_file(), f"缺 gear 测试图 {gear}"
    result = ig.detect_faces(gear)
    assert result.detector_available
    assert not result.hit, f"齿轮上白名单不该有命中，实际 hits={len(result.faces)} boxes={result.faces}"
    assert result.floor is None


def t_p3_blacklist_denials_are_not_decorative():
    """P3-2 反-反例：齿轮图跑黑名单必报假阳 —— 证明显式拒绝不是"没被选中"的另一种说法。

    设计 §2 硬法则 2：`frontalface_default`（锈螺栓圈误报）、`upperbody`（人物躯干过检）。
    这条断言反过来用：如果这两张在齿轮上都不误报，那"显式拒绝"就是空规则 —— 必须失败。
    """
    gear = _P3_FIXTURE_DIR / "gear-01.jpg"
    result = ig.detect_faces(gear, cascade_names=ig._DENIED_CASCADES)
    assert result.detector_available
    assert result.hit, (
        "黑名单在齿轮上零命中 —— 显式拒绝这条规则没有实测反例支撑，"
        "要么换一张更锈的测试图，要么把 §2 里那条『齿轮误报』从 prose 降级为未证。")


def t_p3_probe_artifact_is_committed():
    """P3-3：探针产物（两张测试图 + probe-result.json）都在 evidence 目录里 —— 不只是 prose。"""
    for name in ("face-01.jpg", "gear-01.jpg", "probe-result.json"):
        p = _P3_FIXTURE_DIR / name
        assert p.is_file() and p.stat().st_size > 0, f"探针入库缺 {name}"
    payload = json.loads((_P3_FIXTURE_DIR / "probe-result.json").read_text(encoding="utf-8"))
    assert payload.get("capability_ok") is True
    primary = {row["file"]: row for row in payload.get("primary", [])}
    assert primary["face-01.jpg"]["floor"] == "G0"
    assert primary["gear-01.jpg"]["floor"] is None
    assert payload["blacklist_control"][0]["hits"] > 0, (
        "落盘的反-反例 hits 为 0 —— 与本地重跑不一致，检测器参数或图变了；"
        "重跑 `python skills/douyin-pro/scripts/p3_probe.py` 刷新 evidence。")


def t_p3_detector_is_deterministic_on_same_bytes():
    """检测器必须是图字节的纯函数 —— 判据 4a 的静态锚：同图两次跑 grade 一致。"""
    gear = _P3_FIXTURE_DIR / "gear-01.jpg"
    a = ig.detect_faces(gear)
    b = ig.detect_faces(gear)
    assert [x.to_tuple() for x in a.faces] == [x.to_tuple() for x in b.faces], (
        "同图两次 detect_faces 结果不一致 —— 检测器引入了状态或时间，判据 4a 会破。")


# ---- P3 grade 合成（设计 §3）判据 P3-4 / P3-5 --------------------------------

def _gr(designator: str) -> ig.GradeResult:
    """构造一个 GradeResult 只用于合成测试 —— 不跑检测器。"""
    if designator == "face":
        return ig.GradeResult(detector_available=True,
                              faces=(ig.Box(0, 0, 100, 100),), floor="G0")
    if designator == "clean":
        return ig.GradeResult(detector_available=True, faces=(), floor=None)
    if designator == "unavailable":
        return ig.GradeResult(detector_available=False, faces=(), floor=None)
    raise ValueError(designator)


def t_p3_synth_grade_matrix_four_combinations():
    """P3-4：`max(author, floor)` 四组合全对（序 G0>G1>G2）。"""
    # 作者 G2 + 检出脸 → G0（机器抬）
    assert ig.synth_grade("material", _gr("face")) == "G0"
    # 作者 G1 + 无脸 → G1（作者声明就是终档）
    assert ig.synth_grade("scene", _gr("clean")) == "G1"
    # 作者 G2 + 无脸 → G2
    assert ig.synth_grade("material", _gr("clean")) == "G2"
    # 未声明 + 无脸 → G1（默认 scene，不是 G0；避免"漏标一次永久丢图"）
    assert ig.synth_grade(None, _gr("clean")) == "G1"


def t_p3_synth_grade_refuses_author_g0_and_typos():
    """作者不能声明 G0，也不能拼错 —— 静默回落会把合同缺陷藏成生产数据。"""
    for bad in ("G0", "g0", "scene-typo", "",  # 空串（未声明应用 None）
                "material ", "person"):
        try:
            ig.synth_grade(bad, _gr("clean"))
        except ValueError:
            continue
        raise AssertionError(f"imageGrade={bad!r} 应抛 ValueError，实际静默通过")


def t_p3_synth_grade_unavailable_detector_bumps_to_g0():
    """P3-5：检测器不可用 → 保守 G0 —— 与"作者档"无关（作者 G2 也抬到 G0）。

    §6.5 硬规则 3：不能相信"没测到脸"。测得用齿轮图（作者声明 material，检测器坏）
    → 仍 G0，证明保守来自"失效"而不是"内容"，也证明 synth_grade 不读图字节。
    """
    assert ig.synth_grade("material", _gr("unavailable")) == "G0"
    assert ig.synth_grade("scene", _gr("unavailable")) == "G0"
    assert ig.synth_grade(None, _gr("unavailable")) == "G0"


def t_p3_synth_grade_g0_is_only_from_face_or_unavailable():
    """G0 只有两种来源：检出脸 或 检测器失效。作者声明永远拿不到 G0。"""
    # 反证：三种作者档 × "clean" 全不产生 G0
    for author in (None, "scene", "material"):
        assert ig.synth_grade(author, _gr("clean")) != "G0", (
            f"author={author!r}+clean 却出了 G0 —— G0 泄漏到作者合同，"
            "会让'作者漏标一次就永久丢图'变成设计事实")
    # 只有 face / unavailable 能给 G0
    assert ig.synth_grade("material", _gr("face")) == "G0"
    assert ig.synth_grade("material", _gr("unavailable")) == "G0"


def t_p3_resolve_shot_image_writes_grade_record():
    """`_resolve_shot_image` 取图成功后必须把 `{grade, detector_available, faces, person, namedSubject}` 落到 record —— 设计 §3 的单点事实源。"""
    face_fixture = _P3_FIXTURE_DIR / "face-01.jpg"
    assert face_fixture.is_file()

    # 打桩：cm.resolve_shot_image 直接返回一个指向 fixture 的假 record（无网络）。
    original = cm.resolve_shot_image
    def fake(query, dest, log=None):
        import shutil
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(face_fixture, dest)
        return {"local_path": str(dest), "title": "fake", "width": 1280, "height": 1742,
                "license": "CC BY 3.0", "artist": "test", "thumb_url": None,
                "image_url": None, "source_url": None, "license_reason": None,
                "relevance": 1, "bytes": dest.stat().st_size, "query": query}
    cm.resolve_shot_image = fake
    try:
        with tempfile.TemporaryDirectory() as work:
            scene = {"image": "test-face", "imageGrade": "material",
                     "person": True, "namedSubject": False}
            rec = pb._resolve_shot_image(work, 1, scene, {})
    finally:
        cm.resolve_shot_image = original
    assert rec is not None, "打桩后 _resolve_shot_image 不该返回 None"
    # face-01 检出脸 → 即使作者声明 material，floor 抬 G0
    assert rec["grade"] == "G0", f"face fixture + author=material 应合成 G0，实际 {rec['grade']}"
    assert rec["detector_available"] is True
    assert len(rec["faces"]) >= 1, "face-01 该有命中"
    assert rec["person"] is True and rec["namedSubject"] is False, "作者 flag 必须原样进 record"
    assert rec["local_path"].startswith("media/") or "\\" not in rec["local_path"], \
        f"local_path 应 work_dir 相对正斜杠，实际 {rec['local_path']}"


def t_p3_resolve_shot_image_refuses_bad_author_grade():
    """作者把 imageGrade 拼成 'G0' / 'g1' / 空串 —— `_resolve_shot_image` 抛 ValueError 而不是静默。"""
    face_fixture = _P3_FIXTURE_DIR / "face-01.jpg"
    original = cm.resolve_shot_image
    def fake(query, dest, log=None):
        import shutil
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(face_fixture, dest)
        return {"local_path": str(dest), "title": "fake", "width": 1280, "height": 1742,
                "license": "CC BY 3.0", "artist": "test", "thumb_url": None,
                "image_url": None, "source_url": None, "license_reason": None,
                "relevance": 1, "bytes": dest.stat().st_size, "query": query}
    cm.resolve_shot_image = fake
    try:
        with tempfile.TemporaryDirectory() as work:
            for bad in ("G0", "g1", "", "person"):
                scene = {"image": "x", "imageGrade": bad}
                try:
                    pb._resolve_shot_image(work, 1, scene, {})
                except ValueError:
                    continue
                raise AssertionError(f"imageGrade={bad!r} 应抛 ValueError")
    finally:
        cm.resolve_shot_image = original


def t_p3_scene_contract_preflight_catches_bad_author_fields():
    """P3 §3 作者合同的预检必须提前抓 —— 别等到 `_resolve_shot_image` 才炸。"""
    import sys
    news_scripts = Path(__file__).resolve().parents[3] / "routes" / "news" / "scripts"
    if str(news_scripts) not in sys.path:
        sys.path.insert(0, str(news_scripts))
    import check_scene_contract as csc
    pack = pb.load_style_pack("news-coral")
    lay = dict(pack["layouts"])["hook"]
    lay["_name"] = "hook"
    lay["_row_capacity"] = pb.row_capacity(lay)
    bad_grade = csc.check_scene(
        {"body": "有正文", "title": "有标题", "image": "x", "imageGrade": "G0"}, lay, 1)
    assert any("imageGrade" in p for p in bad_grade), f"G0 应预检报错，实际 {bad_grade}"
    bad_flag = csc.check_scene(
        {"body": "有正文", "title": "有标题", "image": "x", "person": "true"}, lay, 1)
    assert any("person" in p and "bool" in p for p in bad_flag), \
        f"person 非 bool 应预检报错，实际 {bad_flag}"
    clean = csc.check_scene(
        {"body": "有正文", "title": "有标题", "image": "x", "imageGrade": "scene",
         "person": True, "namedSubject": False}, lay, 1)
    assert not any("imageGrade" in p or "namedSubject" in p for p in clean), \
        f"合法合同不该误报：{clean}"


# ---- P3 开闸迁移（设计 §4）判据 P3-6 ---------------------------------------

def t_p3_asset_migrated_to_callsite_bucket():
    """P3-6 结构性检查：asset 在 CALLSITE，不在 CHECKED；has_asset 形参已删。"""
    assert "asset" not in hp.CHECKED_REQUIRES, \
        f"asset 仍留在 CHECKED_REQUIRES={hp.CHECKED_REQUIRES}，编译期拿不到这个事实"
    assert "asset" in hp.CALLSITE_REQUIRES, "asset 必须点名强制它的闸（空路径塌槽）"
    # 兜底覆盖：requires 名字闭合规则仍然拦住"任何既不在 CHECKED 也不在 CALLSITE"的
    # 假接口 —— asset 迁过去后由 CALLSITE 一侧接住，不会掉进"没有任何实现"分支。
    import inspect
    sig = inspect.signature(hp.check_preconditions)
    assert "has_asset" not in sig.parameters, (
        f"check_preconditions 仍有 has_asset 形参（{list(sig.parameters)}）—— "
        "P3 §4 明确要求删；留着就是恒 False 的假接口，P3 之前那条评论")


def t_p3_capability_gate_open_when_cv2_ready():
    """P3-6 端到端开闸：`hf_compile._IMAGE_GATE_READY` 由 `image_gate.capability_ok()` 决定。

    本机装了 cv2 + cascade → True；photo-* 在 `image_gate_ready=True` 下不再被
    `check_preconditions` 拒。反证：模拟 `capability_ok=False` 时 photo-duotone 仍拒编。
    """
    assert ig.capability_ok() is True
    assert hf_compile_image_gate_ready() is True, (
        "hf_compile 的 _IMAGE_GATE_READY 应跟着 capability_ok 走；False 说明 import 失败或"
        "常量没被刷新，photo-* 会被无端拒编")
    # 反证：显式关闸（模拟 cv2 缺失环境）
    for name in ("photo-duotone", "photo-local-crop", "ken-burns-in"):
        problems = hp.check_preconditions(name, ground="paper", image_gate_ready=False)
        assert any("图片门禁" in p for p in problems), f"{name} 关闸却不拒: {problems}"


def hf_compile_image_gate_ready() -> bool:
    """从 hf_compile 取运行时能力常量 —— 不在 selftest 里重跑 capability_ok 判断，
    确保"编译入口用的值"和"检测器给的值"是同一份。"""
    import hf_compile as _hc
    return bool(_hc._IMAGE_GATE_READY)


# ---- P3 grade⟷原语映射（设计 §5）判据 P3-7 ---------------------------------

def t_p3_grade_primitive_matrix_matches_design():
    """§5 表：G2 可用三原语 · G1 只能 photo-local-crop · G0 三个都不行。"""
    assert ig.GRADE_ALLOWED_PRIMITIVES["photo-duotone"] == frozenset({"G2"}), \
        "photo-duotone 只能 G2 —— 满屏 duotone 会把 G1 场景变成可指认的图"
    assert ig.GRADE_ALLOWED_PRIMITIVES["ken-burns-in"] == frozenset({"G2"}), \
        "ken-burns-in 是满屏推镜，同 duotone 一档"
    assert ig.GRADE_ALLOWED_PRIMITIVES["photo-local-crop"] == frozenset({"G1", "G2"}), \
        "photo-local-crop 是唯一 G1 允许（25-35% 局部裁掉指认性）"


def t_p3_check_layout_grade_catches_g1_with_full_bleed():
    """P3-7 核心：作者声明 scene(G1) 却用了 photo-duotone → 返回冲突不空。

    设计 §5 的"新增一致校验"就是这一条。这里直接测纯函数：反证若把 photo-duotone
    的允许档从 {G2} 放宽到 {G1,G2}，本条必红 —— 语义"G1 只能走 local-crop"是硬约束。
    """
    problems = ig.check_layout_grade(
        primitives=["hairline", "photo-duotone", "cue-fade"], final_grade="G1")
    assert any("photo-duotone" in p for p in problems), \
        f"G1 + photo-duotone 应报冲突，实际: {problems}"
    # G1 + local-crop 允许
    assert ig.check_layout_grade(["photo-local-crop"], "G1") == []
    # G2 + 三原语都允许
    assert ig.check_layout_grade(
        ["photo-duotone", "photo-local-crop", "ken-burns-in"], "G2") == []
    # G0 + 任一取图原语都拒（G0 走 §7 落位弃图，不进 photo-*）
    for prim in ig.GRADE_ALLOWED_PRIMITIVES:
        problems = ig.check_layout_grade([prim], "G0")
        assert any(prim in p for p in problems), f"G0 遇 {prim} 应拒，实际放行"


def t_p3_check_layout_grade_ignores_non_photo_primitives():
    """与 grade 无关的原语（hairline / char-rise / block-chip / giant-numeral …）不误报。

    反证：把这张判据放宽就等于把"grade 只管取图三兄弟"的合同抹掉，将来 grade 会
    去拦不该拦的东西。
    """
    assert ig.check_layout_grade(
        ["hairline", "block-chip", "char-rise", "keyword-tint",
         "rule-pull", "cue-fade", "giant-numeral", "clip-wipe-up",
         "drift-y"], "G1") == []


def t_p3_check_layout_grade_rejects_unknown_grade():
    """grade 只能是三档字符串；拼错/None/数字都抛 ValueError 而不是静默放行。"""
    for bad in (None, "", "G3", "g1", 1, "G0 "):
        try:
            ig.check_layout_grade(["photo-duotone"], bad)
        except ValueError:
            continue
        raise AssertionError(f"grade={bad!r} 应抛 ValueError，实际静默通过")


# ---- P3 示意标注（schematic-tag）判据 P3-8 ----------------------------------

def _p3_fake_image_record(grade, *, local_path="media/shot_01.jpg", faces=None):
    """造一条**像产线出品**的 image_record：有 local_path、给定终档、带署名所需字段。

    `attribution_text` 只读 `license`/`artist`，故这两条必须有；`grade` 由调用方钉死
    （产线里它是 `synth_grade` 出来的，本测只测标注触发，不重复测合成）。`faces` 供 §7
    落位禁令复检用（产线里是 `[[x,y,w,h],…]`），默认无脸。
    """
    return {"local_path": local_path, "grade": grade, "detector_available": True,
            "faces": list(faces or []), "person": False, "namedSubject": False,
            "title": "示意测试图", "artist": "Jane Doe", "license": "CC BY 4.0",
            "source_url": "https://commons.example/f"}


def t_p3_schematic_needed_predicate_three_branches():
    """P3-8 判据本体：三态必测，缺一即假绿 —— 无图/真图不挂，纹理图必挂。"""
    # ① 无图（record 为 None，含 image:false / 取图失败）→ 不注入
    assert pb.schematic_needed(None) is False
    # ② 有 record 但图被 §7 弃用（local_path 空）→ 屏上无图，不注入
    assert pb.schematic_needed({"local_path": "", "grade": "G1"}) is False
    # ③ 本尊照（grade=real）→ 不是纹理示意，不注入
    assert pb.schematic_needed(_p3_fake_image_record(ig.REAL_GRADE)) is False
    # ④ 纹理图（G1/G2）在屏 → 必注入（无开关无例外）
    assert pb.schematic_needed(_p3_fake_image_record("G1")) is True
    assert pb.schematic_needed(_p3_fake_image_record("G2")) is True


def t_p3_schematic_composition_is_valid_and_selfchecks_clean():
    """标注子合成必须是合法子合成 + 过真自检（豁免只放底部叠加层两条，其余照查）。"""
    rec = _p3_fake_image_record("G2")
    comp_id = f"{pb.SCHEMATIC_FILE_PREFIX}-1"
    text = pb.emit_schematic_composition(comp_id, rec, PROBE_SECONDS, 1080, 1920, "light")
    # 子合成契约三件套
    assert "<template>" in text and "</template>" in text
    assert f'data-composition-id="{comp_id}"' in text
    assert f'window.__timelines["{comp_id}"]' in text
    assert "background: transparent" in text, "#root 必须透明，否则 3 轨会把字幕/版式糊住"
    # 文案两级都在（主句 + 附属署名，署名从 Commons 字段拼出）
    assert pb.SCHEMATIC_LEAD_TEXT in text, "免责主句没进 HTML"
    assert "Jane Doe" in text and "CC BY 4.0" in text, "附属署名没拼出作者+许可证"
    # 每个 #id 补间目标都能在文件里解析到元素
    for target in re.findall(r'tl\.\w+\("#([a-zA-Z0-9_-]+)"', text):
        assert f'id="{target}"' in text, f"补间目标 #{target} 没有对应元素"
    # 浅地面墨字 / 深地面白字：复用 _subtitle_palette 翻色口径（不新造对比）。
    # 核的是 `color:` 这一条（填充），不是子串存在 —— 白字色 #ffffff 在浅档会作为**描边**出现，
    # 用"contains 白"判会假阳，必须钉到填充属性上。
    light = pb.emit_schematic_composition(comp_id, rec, PROBE_SECONDS, 1080, 1920, "light")
    dark = pb.emit_schematic_composition(comp_id, rec, PROBE_SECONDS, 1080, 1920, "dark")
    assert f"color: {pb.SUBTITLE_INK_COLOR};" in light, "浅地面填充应是墨字"
    assert f"color: {pb.SUBTITLE_LIGHT_COLOR};" in dark, "深地面填充应是白字"
    # 过真自检：文件名前缀命中底部叠加层豁免（动量/禁入区两条），其余不变量仍核
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "compositions"))
        p = Path(d) / "compositions" / f"{comp_id}.html"
        p.write_text(text, encoding="utf-8")
        violations = ls.check_layout(p)
        assert not violations, [str(v) for v in violations]


def t_p3_schematic_composition_is_deterministic():
    """同一份 record 编译两次逐字节相同 —— 判据 4a：标注烤进视频流后不许因重跑而抖。"""
    rec = _p3_fake_image_record("G2")
    comp_id = f"{pb.SCHEMATIC_FILE_PREFIX}-1"
    a = pb.emit_schematic_composition(comp_id, rec, PROBE_SECONDS, 1080, 1920, "dark")
    b = pb.emit_schematic_composition(comp_id, rec, PROBE_SECONDS, 1080, 1920, "dark")
    assert a == b, "标注子合成不可复现：里面混进了墙钟/随机"
    assert "Date.now" not in a and "Math.random" not in a


def t_p3_schematic_tag_emitted_at_highest_track_when_texture_image():
    """端到端 P3-8：编译包里有一镜带纹理图 → 成片宿主必挂 schematic-tag 且 track 序最高(3)；
    无图那镜不挂。存量手发包（compiled=False）一镜都不挂。
    """
    pack = pb.load_style_pack("news-editorial-warm")
    assert pack["compiled"] is True
    scene_txt = {"title": "门诊新规", "body": PROBE_TEXT,
                 "onscreen": "没人告诉他，他一直没问", "onscreenAccent": None}
    scene_img = dict(scene_txt, image="示意测试图")
    rec_img = _p3_fake_image_record("G2")
    with tempfile.TemporaryDirectory() as d:
        shots = pb.emit_composition(pack, [scene_txt, scene_img],
                                    [PROBE_SECONDS, PROBE_SECONDS], d,
                                    {"overrides": {}}, 1080, 1920,
                                    [], [None, rec_img],
                                    scene_cues=[_probe_scene(), _probe_scene()])
        assert len(shots) == 2
        # 有图那镜（i=2）落 schematic-2.html，无图那镜不落
        comp2 = Path(d) / "compositions" / f"{pb.SCHEMATIC_FILE_PREFIX}-2.html"
        comp1 = Path(d) / "compositions" / f"{pb.SCHEMATIC_FILE_PREFIX}-1.html"
        assert comp2.is_file(), "带纹理图的镜没生成 schematic-tag 子合成"
        assert not comp1.is_file(), "无图的镜不该生成 schematic-tag"
        index = Path(d, "index.html").read_text(encoding="utf-8")
        assert index.count('data-track-index="3"') == 1, "标注轨(3)没挂上或挂多了"
        assert index.count(f'compositions/{pb.SCHEMATIC_FILE_PREFIX}-2.html') == 1
        # track 序最高：字幕(2)也在，标注(3)压在其上
        assert index.count('data-track-index="2"') == 2, "两镜都该有字幕轨"
        assert index.count('data-track-index="1"') == 2, "两镜都该有版式轨"
        # 宿主挂载计数自洽：2 版式 + 2 字幕 + 1 标注 = 5 个 composition-src
        assert index.count('data-composition-src="compositions/') == 5
    # 存量手发包（compiled=False）：带图也不生成标注
    legacy = pb.load_style_pack(pb.DEFAULT_STYLE)
    assert legacy["compiled"] is False
    with tempfile.TemporaryDirectory() as d:
        pb.emit_composition(legacy, [scene_img], [PROBE_SECONDS], d,
                            {"overrides": {}}, 1080, 1920, [], [rec_img])
        comp = Path(d) / "compositions" / f"{pb.SCHEMATIC_FILE_PREFIX}-1.html"
        assert not comp.is_file(), "存量手发包被误加了 schematic-tag"


# ---- P3 落位禁令 + crop_and_recheck 判据 P3-9 --------------------------------

def t_p3_image_deprecated_predicate():
    """`image_deprecated` 判决分支穷举（设计 §7）：非 G0 一律留、四路禁令位弃、普通镜看复检。"""
    # 非 G0（纹理 G1/G2 与本尊 real）永不参与落位弃 —— 落位禁令只针对"可指认的脸"
    assert pb.image_deprecated("G1", is_first=True, layout_name="closer",
                                person=True, named_subject=True,
                                recheck_still_hit=True) is None
    assert pb.image_deprecated(ig.REAL_GRADE, is_first=True, layout_name="closer",
                               person=True, named_subject=True,
                               recheck_still_hit=True) is None
    # 自动半：首镜 / closer 片尾 —— 指认性由位置定, 机器必判
    assert pb.image_deprecated("G0", is_first=True, layout_name="story",
                               person=False, named_subject=False,
                               recheck_still_hit=False) is not None
    assert pb.image_deprecated("G0", is_first=False, layout_name="closer",
                               person=False, named_subject=False,
                               recheck_still_hit=False) is not None
    # 声明半：作者打了 person / namedSubject —— 尊重声明即弃
    assert pb.image_deprecated("G0", is_first=False, layout_name="story",
                               person=True, named_subject=False,
                               recheck_still_hit=False) is not None
    assert pb.image_deprecated("G0", is_first=False, layout_name="story",
                               person=False, named_subject=True,
                               recheck_still_hit=False) is not None
    # 普通镜（中段、未标人物/专名、非 closer）：复检仍命中才弃, 掩干净则留
    assert pb.image_deprecated("G0", is_first=False, layout_name="story",
                               person=False, named_subject=False,
                               recheck_still_hit=True) is not None
    # ★ 判据 P3-9 反面：未声明标记的普通镜 G0、复检干净 → 不弃图（仍出标注, 但落位禁令不触发）
    assert pb.image_deprecated("G0", is_first=False, layout_name="story",
                               person=False, named_subject=False,
                               recheck_still_hit=False) is None


def t_p3_g0_placement_ban_wired_at_build_time():
    """端到端 P3-9：首镜 G0 被置空塌槽、普通镜 G0 复检干净则留(带标注)、复检命中则弃。

    `crop_and_recheck` 打桩（不碰 cv2/文件），保证判决路径与调用次数可机判：
    - 分镜1 首镜 G0 → 禁令位弃, **不该**触发复检（禁令不依赖复检, 省一次检测）。
    - 分镜2 中段 G0 + 复检 False → 留图 → 出标注。
    - 分镜3 中段 G0 + 复检 True → 弃 → 不出标注。
    - 分镜4 无图 → 不进弃图路径。
    """
    pack = pb.load_style_pack("news-editorial-warm")
    assert pack["compiled"] is True
    base = {"title": "门诊新规", "body": PROBE_TEXT,
            "onscreen": "没人告诉他，他一直没问", "onscreenAccent": None}

    rec_a = _p3_fake_image_record("G0", local_path="media/shot_01.jpg")
    rec_b = _p3_fake_image_record("G0", local_path="media/shot_02.jpg", faces=[[10, 10, 40, 40]])
    rec_c = _p3_fake_image_record("G0", local_path="media/shot_03.jpg", faces=[[10, 10, 40, 40]])
    scenes = [dict(base), dict(base), dict(base), dict(base)]
    records = [rec_a, rec_b, rec_c, None]

    calls: list[str] = []

    def fake_recheck(image_path, faces):
        calls.append(os.path.basename(image_path))
        return "shot_03" in image_path      # 分镜3 掩完仍命中→弃；分镜2 干净→留

    original = ig.crop_and_recheck
    ig.crop_and_recheck = fake_recheck
    try:
        with tempfile.TemporaryDirectory() as d:
            pb.emit_composition(pack, scenes, [PROBE_SECONDS] * 4, d,
                                {"overrides": {}}, 1080, 1920, [], records,
                                scene_cues=[_probe_scene()] * 4)
    finally:
        ig.crop_and_recheck = original

    # 禁令位（首镜）不弃在复检上：shot_01 不该被复检；只有两个普通镜 G0 走复检
    assert "shot_01.jpg" not in calls, "首镜 G0 应直接按落位禁令弃, 不该付复检代价"
    assert set(calls) == {"shot_02.jpg", "shot_03.jpg"}, f"复检只该落在非禁令位的普通镜: {calls}"

    # 弃图动作 = 置空 local_path（复用 §4 塌槽）：首镜与复检命中镜被置空, 干净镜保留
    assert rec_a["local_path"] == "", "首镜 G0 该被置空"
    assert rec_c["local_path"] == "", "复检仍命中的普通镜 G0 该被置空"
    assert rec_b["local_path"] == "media/shot_02.jpg", "复检干净的普通镜 G0 不该被落位禁令误弃"

    # 标注只在"图真留在屏上"的镜出现：只有分镜2
    with tempfile.TemporaryDirectory() as d:
        ig.crop_and_recheck = fake_recheck
        try:
            pb.emit_composition(pack, [dict(base, **{}) for _ in scenes],
                                [PROBE_SECONDS] * 4, d,
                                {"overrides": {}}, 1080, 1920,
                                [], [_p3_fake_image_record("G0", local_path="media/shot_01.jpg"),
                                     _p3_fake_image_record("G0", local_path="media/shot_02.jpg", faces=[[1, 1, 4, 4]]),
                                     _p3_fake_image_record("G0", local_path="media/shot_03.jpg", faces=[[1, 1, 4, 4]]),
                                     None],
                                scene_cues=[_probe_scene()] * 4)
        finally:
            ig.crop_and_recheck = original
        comp_dir = Path(d) / "compositions"
        assert not (comp_dir / f"{pb.SCHEMATIC_FILE_PREFIX}-1.html").is_file(), "被弃的首镜不该出标注"
        assert (comp_dir / f"{pb.SCHEMATIC_FILE_PREFIX}-2.html").is_file(), "留下的普通镜 G0 该出标注"
        assert not (comp_dir / f"{pb.SCHEMATIC_FILE_PREFIX}-3.html").is_file(), "复检命中被弃的镜不该出标注"


def t_p3_g0_person_declared_slot_is_banned():
    """声明半端到端：作者标 `person` 的普通位 G0 → 置空弃图（尊重声明）；未标的普通位 G0 不触发落位弃。"""
    pack = pb.load_style_pack("news-editorial-warm")
    base = {"title": "门诊新规", "body": PROBE_TEXT,
            "onscreen": "没人告诉他，他一直没问", "onscreenAccent": None}
    # 分镜2 中段（非首非尾）person=True → 落位禁令; 复检不该被调用
    rec_person = _p3_fake_image_record("G0", local_path="media/shot_02.jpg")
    rec_person["person"] = True
    calls: list[str] = []

    def fake_recheck(image_path, faces):
        calls.append(os.path.basename(image_path))
        return False

    original = ig.crop_and_recheck
    ig.crop_and_recheck = fake_recheck
    try:
        with tempfile.TemporaryDirectory() as d:
            pb.emit_composition(pack, [dict(base), dict(base)], [PROBE_SECONDS] * 2, d,
                                {"overrides": {}}, 1080, 1920, [],
                                [None, rec_person],
                                scene_cues=[_probe_scene()] * 2)
    finally:
        ig.crop_and_recheck = original
    assert rec_person["local_path"] == "", "person 普通镜 G0 该按声明半弃图"
    assert calls == [], "person 已被落位禁令判弃, 不该再付复检代价"


def t_p3_grade_primitive_gate_fires_before_emit():
    """端到端 P3-7/P3-10：发射前把「作者声明档 × 本版式取图原语」核一遍，误配即 EmitterError。

    真实旗舰 story 带的是 photo-local-crop（允许 {G1,G2}），作者默认 scene(=G1) 永远过 ——
    这条测的是**闸本身会不会咬**，所以把 story 的原语就地换成 photo-duotone（只允许 {G2}）：
    - scene(=G1) × photo-duotone → 冲突 → 拒绝发射（文案点名 photo-duotone 与 G1）。
    - material(=G2) × photo-duotone → 自洽 → 正常出片（证明不是恒真的假闸）。
    判据用**作者声明档**不是检测器终档：G0 落位弃在上面 §7 已处理，§5 只管合同级误配。
    """
    pack = pb.load_style_pack("news-editorial-warm")
    assert pack["compiled"] is True
    # 先钉住真实旗舰 recipe 用的是 local-crop（不然后面换错了对象也测不到）
    assert "photo-local-crop" in pack["layouts"]["story"]["primitives"], \
        f"旗舰 story 原语应为 local-crop，实际: {pack['layouts']['story']['primitives']}"
    assert "photo-duotone" not in pack["layouts"]["story"]["primitives"], \
        "满屏 duotone 会被 drift-y 几何闸拒；旗舰不该带它"

    # 就地造一个"作者想要满屏 duotone"的版式：local-crop → duotone
    pack["layouts"]["story"]["primitives"] = tuple(
        "photo-duotone" if p == "photo-local-crop" else p
        for p in pack["layouts"]["story"]["primitives"]
    )
    scene_txt = {"title": "门诊新规", "body": PROBE_TEXT,
                 "onscreen": "没人告诉他，他一直没问", "onscreenAccent": None}
    rec = _p3_fake_image_record("G2")   # 纹理档，§7（只碰 G0）不动它 → 残留进 §5 闸

    # ① 误配支：scene 默认声明(=G1) × photo-duotone(仅 G2) → 停机
    scene_g1 = dict(scene_txt, image="示意测试图")
    with tempfile.TemporaryDirectory() as d:
        msg = expect_error(
            lambda: pb.emit_composition(pack, [dict(scene_g1)],
                                        [PROBE_SECONDS], d,
                                        {"overrides": {}}, 1080, 1920, [],
                                        [dict(rec)], scene_cues=[_probe_scene()]))
    assert "photo-duotone" in msg and "G1" in msg, f"停机文案没点名冲突项: {msg}"
    assert scene_g1.get("imageGrade", None) is None, "默认即 scene 档, 不该被写进 scene"

    # ② 自洽支：material(=G2) × photo-duotone(允许 G2) → 正常出片
    scene_g2 = dict(scene_txt, image="示意测试图", imageGrade="material")
    with tempfile.TemporaryDirectory() as d:
        shots = pb.emit_composition(pack, [scene_g2], [PROBE_SECONDS], d,
                                    {"overrides": {}}, 1080, 1920, [],
                                    [dict(rec)], scene_cues=[_probe_scene()])
        assert len(shots) == 1, "material×duotone 该放行而非误拒"
        assert (Path(d) / "compositions" / f"{pb.SCHEMATIC_FILE_PREFIX}-1.html").is_file(), \
            "过闸后标注轨该照常生成"


def _p3_emit_tree(work_dir: str) -> dict[str, str]:
    """把发射产物整棵树读成 {相对路径: 文本}，供逐字节比对（判据 4a 的发射侧口径）。"""
    root = Path(work_dir)
    tree = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            tree[p.relative_to(root).as_posix()] = p.read_text(encoding="utf-8")
    return tree


def t_p3_emitter_photo_flow_is_deterministic():
    """端到端 P3-10：同一含图旗舰发射两次，整棵产物逐字节相同，且图真绑进宿主、无墙钟/随机。

    判据 4a 在发射侧的下界 —— 真渲染之前先证明"喂进去的字节是确定的"：
    - story 版式的 photo 层把真实 local_path 填进 index.html 的 values（图真上屏，非塌槽）。
    - schematic-tag 子合成同批生成（纹理图必标注）。
    - 两次发射的**文件集合**与**每个文件字节**全等（抖动 = 重跑变样，这里必须为 0）。
    - 产物里不出现 Date.now / Math.random（法则 10：时序抖动编译期烘焙，落盘无墙钟）。
    """
    pack = pb.load_style_pack("news-editorial-warm")
    assert pack["compiled"] is True
    import shutil
    scene = {"title": "门诊新规", "body": PROBE_TEXT,
             "onscreen": "没人告诉他，他一直没问", "onscreenAccent": None,
             "image": "示意测试图"}
    # local_path 每次调用造新 dict，避免两次发射共享同一 record 被就地改动
    trees, dirs = [], []
    for _ in range(2):
        d = tempfile.mkdtemp()
        dirs.append(d)
        rec = _p3_fake_image_record("G2", local_path="media/shot_01.jpg")
        pb.emit_composition(pack, [dict(scene)], [PROBE_SECONDS], d,
                            {"overrides": {}}, 1080, 1920, [], [rec],
                            scene_cues=[_probe_scene()])
        trees.append(_p3_emit_tree(d))

    # ① 含图那镜：photo 层的真实路径绑进了宿主 values（非塌槽空串）
    index = trees[0]["index.html"]
    assert "media/shot_01.jpg" in index, "含图旗舰没把 local_path 填进宿主 —— 图塌成无图态了"
    assert f"compositions/{pb.SCHEMATIC_FILE_PREFIX}-1.html" in trees[0], "纹理图那镜该生成 schematic-tag"

    # ② 两次发射逐字节全等（文件集合 + 内容）
    assert trees[0].keys() == trees[1].keys(), \
        f"两次发射文件集合不同: {set(trees[0]) ^ set(trees[1])}"
    for rel in trees[0]:
        assert trees[0][rel] == trees[1][rel], f"重跑抖了：{rel} 两次内容不一致"

    # ③ 产物无墙钟/随机（判据 4a 前因；真渲染再补视频流哈希）
    for rel, text in trees[0].items():
        assert "Date.now" not in text and "Math.random" not in text, \
            f"{rel} 里混进了墙钟/随机，重跑必抖"

    for d in dirs:
        shutil.rmtree(d, ignore_errors=True)


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
