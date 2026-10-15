#!/usr/bin/env python3
"""分镜契约预检：在**渲染之前**说出"这句稿子会被吃掉"。

背景（2026-10-08 实跑 t002 踩到）:
  我给镜 2 写了 `title: "断在第几次"`、镜 5 写了 `title: "目前"`，
  而 news-coral 的 `stat` / `closer` / `quote` **没有标题位**。
  `title` 不进配音、又没有版式变量接住它 ⇒ 这两句话**既不上屏也不出声**。
  path_b_build 会打一条 ⚠，但那是**渲染 15 分钟之后**的事。

本脚本把这件事挪到写稿那一刻：读 scenes.json + 版式契约，逐镜列出
「哪些字段没有落点」「点名的版式哪些变量填不出来」，并给出可执行的修法。
**只读，不改任何东西。** 判据与发射器同源 —— 输入走同一个 `parse_input`，
变量走同一个 `resolve_variable`，所以这里报的和渲染时报的不会是两个答案。

用法:
    python routes/news/scripts/check_scene_contract.py <scenes.json> \
        --template news-coral --source <渲染命令同款署名>
    python routes/news/scripts/check_scene_contract.py --demo        # 用内置反例自检
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills" / "douyin-pro" / "scripts"))

import path_b_build as pb  # noqa: E402


def scene_layout(scene: dict) -> str | None:
    """分镜点名的版式；没点名就返回 None（由发射器自动选，自动模式会填满所有版式）。"""
    lay = scene.get("layout")
    if isinstance(lay, str) and lay.strip():
        return lay.strip()
    return None


def unfillable_variables(scene: dict, layout: dict, ctx: dict) -> list[tuple[str, str]]:
    """点名版式下"填不出来的变量"，逐条带原因。

    判据**直接复用发射器同一个 `resolve_variable`** —— 预检自己重写一套规则就会和
    发射器各说各话。2026-10-15 实测踩过：本脚本对 t003 打了 ✅ 通过，发射器紧接着
    报 `点名版式 hook 缺这些变量: headAccent`（标题第二段既没有 `｜` 也没有数字+单位，
    `split_headline` 切不出强调段）。假绿比没有绿更坏：它让人以为已经查过了。
    """
    out = []
    for var in layout.get("variables", []):
        try:
            pb.resolve_variable(var, layout, scene, ctx)
        except pb.EmitterError as exc:
            out.append((var["id"], str(exc)))
        except Exception as exc:                      # noqa: BLE001 —— 预检不替发射器兜 bug
            out.append((var["id"], f"{type(exc).__name__}: {exc}"))
    return out


def check_scene(scene: dict, layout: dict, index: int, ctx: dict | None = None,
                raw: dict | None = None) -> list[str]:
    """返回这一镜的问题清单（空 = 干净）。

    `scene` 是 **parse_input 之后**的形态（和发射器看到的一致）；`raw` 是作者写进
    JSON 的原始那一镜。只有第 3 条需要 raw —— 它防的是"你显式传的 onscreenAccent
    会被 parse_input 覆盖掉"，而覆盖这件事本身就让解析后的数据看不出问题。
    """
    problems = []
    ids = pb.contract_ids(layout)
    has_title_slot = bool(ids & pb.TITLE_LANDING_VARS)

    # 1) 标题：没落点就静默消失
    title = scene.get("title")
    if isinstance(title, str) and title.strip() and not has_title_slot:
        problems.append(
            f"镜{index}: title「{title.strip()[:20]}」没有落点 —— "
            f"{layout.get('_name', '该版式')} 没有标题位(title/headTop/headBottomLead/headAccent)，"
            f"而 title 不进配音 ⇒ 这句话既不上屏也不出声。"
            f"修法: 并进 body，或换一个有标题位的版式(catalog/hook/rail/story)")

    # 2) 条目超行：末尾条目静默丢
    if layout.get("_row_capacity"):
        cap = layout["_row_capacity"]
        items = scene.get("items") or []
        if cap and len(items) > cap:
            problems.append(
                f"镜{index}: {len(items)} 条条目但该版式只放得下 {cap} 行 ⇒ "
                f"末尾 {len(items) - cap} 条不会上屏。修法: 拆镜或换版式")

    # 3) 屏句：显式 onscreenAccent 会被 parse_input 覆盖（只看原始输入）
    raw_scene = raw if raw is not None else scene
    if (raw_scene.get("onscreen") and "|" not in str(raw_scene["onscreen"])
            and "｜" not in str(raw_scene["onscreen"]) and raw_scene.get("onscreenAccent")):
        problems.append(
            f"镜{index}: 传了 onscreenAccent 但 onscreen 没有 ｜ 分隔标记 ⇒ "
            f"强调段会被 parse_input 覆盖。修法: onscreen 写成「前段｜强调段」，"
            f"别另传 onscreenAccent")

    # 4) stat 六元组不齐（有就查，没有不算错）
    if layout.get("_name") == "stat" or scene.get("layout") == "stat":
        need = ("value", "unit", "label")
        missing = [k for k in need if not scene.get(k)]
        if scene.get("stat") and missing:
            problems.append(
                f"镜{index}: stat 镜缺 {missing} —— stat 的数据位(value/unit/label)缺了会留空")

    # 5) 空正文：edge-tts 会直接停机（提前说，别等 15 分钟）
    body = scene.get("body")
    if not (isinstance(body, str) and body.strip()):
        problems.append(f"镜{index}: body 为空 —— 配音会直接停机（无话可配）")

    # 6) P3 §3 作者合同：imageGrade / person / namedSubject 的合法形状。
    #    image 缺省/False 时不查（无图，这几条无意义）；imageGrade 只能 scene|material，
    #    写 G0 或拼错都会到 `_resolve_shot_image` 里抛 ValueError——预检提前说。
    if scene.get("image") not in (None, False, ""):
        grade = scene.get("imageGrade")
        if grade is not None and grade not in ("scene", "material"):
            problems.append(
                f"镜{index}: imageGrade={grade!r} 不在 'scene'/'material'/缺省三选一里 —— "
                "G0 只能由检测器给，作者不能声明；渲染会在 `_resolve_shot_image` 抛 ValueError")
        for flag in ("person", "namedSubject"):
            v = scene.get(flag)
            if v is not None and not isinstance(v, bool):
                problems.append(
                    f"镜{index}: {flag}={v!r} 不是 bool —— 落位禁令(§7)按 `is True` 判，"
                    "非 bool 会被 Python 视为真值或忽略，语义就漂了")

    # 7) 标题与屏句是同一句话 ⇒ 屏幕上并排出现两遍（2026-10-15 t003 镜2 实跑踩到：
    #    title「两次提示，一句没事」+ onscreen「两次提示｜一句没事」，去掉 ｜ 后同串）。
    #    story 的 title 与 onscreen 是两个独立变量位，发射器不会替作者去重。
    onscreen_raw = (raw if raw is not None else scene).get("onscreen")
    if isinstance(title, str) and isinstance(onscreen_raw, str):
        def squash(s: str) -> str:
            return re.sub(r"[，,、。：:；;｜|\s]", "", s)
        if squash(title) and squash(title) == squash(onscreen_raw):
            problems.append(
                f"镜{index}: title 与 onscreen 去掉标点后是同一句话「{title.strip()[:18]}」⇒ "
                f"版式会把同一句在领句位和屏句位各打一遍。修法: 屏句换一个角度说"
                f"（时间/数字/落点），或删掉 onscreen")

    # 8) 点名版式的每个变量都得填得出 —— 判据就是发射器那条 resolve_variable，
    #    不在预检里另立一套口径（另立 = 两边各说各话 = 假绿）。
    if ctx is not None:
        for vid, reason in unfillable_variables(scene, layout, ctx):
            problems.append(
                f"镜{index}: 点名版式 {layout.get('_name', '该版式')} 填不出变量 {vid} —— "
                f"{reason}（发射器会在 emit 阶段用同一个判据停机）")

    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description="分镜契约预检（渲染前）")
    ap.add_argument("scenes", nargs="?", help="scenes.json 路径")
    ap.add_argument("--template", default="news-coral", help="版式包名")
    ap.add_argument("--source", default=None,
                    help="渲染时会给的来源/频道署名 —— 收口版式(closer)拿它填 source。"
                         "不传就可能把'渲染时会有的值'判成缺失，请与渲染命令保持一致。")
    ap.add_argument("--kicker", default=None, help="全片眉标（渲染命令同款），镜内 kicker 优先")
    ap.add_argument("--demo", action="store_true", help="用内置反例自检")
    args = ap.parse_args()

    if args.demo:
        return _demo()

    if not args.scenes:
        ap.error("要给 scenes.json，或用 --demo")
    path = Path(args.scenes)
    if not path.is_file():
        print(f"  ! 找不到 {path}", file=sys.stderr)
        return 1

    text = path.read_text(encoding="utf-8")
    scenes = pb.parse_input(text)
    if not scenes:
        print("  ! 没解析出任何分镜", file=sys.stderr)
        return 1
    # 第 3 条要看作者原始写法；markdown 稿没有"显式 onscreenAccent"这条路（屏: 行自带
    # ｜ 标记），所以只有 JSON 稿能拿到 raw，拿不到就退回解析后的形态（该条自然不触发）。
    try:
        raw_scenes = json.loads(text)
        if not isinstance(raw_scenes, list):
            raw_scenes = []
    except ValueError:
        raw_scenes = []

    pack = pb.load_style_pack(args.template)
    layouts = dict(pack["layouts"])
    for name, lay in layouts.items():
        lay["_name"] = name
        lay["_row_capacity"] = pb.row_capacity(lay)
    # 与发射器同一步：带序号的条目类推导器要先注册，否则预检会报一堆"填不出 itemLabel2"
    pb.register_indexed_derivers(
        set().union(*(pb.contract_ids(l) for l in layouts.values()))
    )

    all_problems = []
    ctx = {"kicker": args.kicker, "source": args.source, "layout": None, "overrides": {},
           # 发射器按每镜配音秒数覆盖它（path_b_build 里 ctx["slot_seconds"]），
           # 预检没有音频、给个合法值让它过 —— 这条不是作者能填的东西。
           "slot_seconds": pb.MIN_SLOT_SECONDS}
    for i, sc in enumerate(scenes, 1):
        name = scene_layout(sc)
        if name is None:
            continue                     # 自动选版式：发射器会填满，不预检
        lay = layouts.get(name)
        if lay is None:
            all_problems.append(f"镜{i}: 点了不存在的版式 {name!r} "
                                f"(可用: {', '.join(sorted(layouts))})")
            continue
        ctx["shot_ordinal"] = f"{i:02d}"   # 发射器按镜号注入（path_b_build.py:2876）
        raw = raw_scenes[i - 1] if len(raw_scenes) >= i else None
        all_problems.extend(check_scene(sc, lay, i, ctx, raw=raw))

    if not all_problems:
        print(f"✅ 契约预检通过: {len(scenes)} 镜 · {args.template}")
        return 0

    print(f"❌ 契约预检发现 {len(all_problems)} 个问题（渲染前, 不花那 15 分钟）:\n")
    for p in all_problems:
        print(f"  · {p}")
    print("\n提示: 上面每条都会在渲染时变成「静默丢内容」或直接停机。")
    return 1


def _demo() -> int:
    """内置反例：必须报出 4 个问题（标题无落点 / 条目超行 / 空正文 / 点名版式填不出变量）。"""
    pack = pb.load_style_pack("news-coral")
    layouts = dict(pack["layouts"])
    for name, lay in layouts.items():
        lay["_name"] = name
        lay["_row_capacity"] = pb.row_capacity(lay)
    pb.register_indexed_derivers(
        set().union(*(pb.contract_ids(l) for l in layouts.values()))
    )
    ctx = {"kicker": "湖南常德", "source": "测试来源", "layout": None, "overrides": {},
           "slot_seconds": pb.MIN_SLOT_SECONDS, "shot_ordinal": "01"}

    got = check_scene({"title": "断在第几次", "body": "三台车分别第3、4、2次断裂"},
                      layouts["stat"], 2, ctx)
    assert any("没有落点" in p for p in got), f"标题无落点没报出来: {got}"
    got2 = check_scene({"body": "x", "items": [{"label": "a", "value": "b"}] * 5},
                       layouts["rail"], 3, ctx)
    assert any("条目" in p for p in got2), f"条目超行没报出来: {got2}"
    got3 = check_scene({"body": ""}, layouts["hook"], 4, ctx)
    assert any("body 为空" in p for p in got3), f"空正文没报出来: {got3}"
    # 2026-10-15 t003 真实踩到的假绿：标题第二段既没 `｜` 也没数字+单位，
    # split_headline 切不出 headAccent，发射器当场停机，而当时的预检说 ✅。
    got4 = check_scene({"title": "千万嫁妆房，交付后一直空着",
                        "body": "宁波一套上千万的精装房，买给女儿当嫁妆。",
                        "onscreen": "上千万的嫁妆｜没人住"}, layouts["hook"], 1, ctx)
    assert any("填不出变量 headAccent" in p for p in got4), \
        f"hook 切不出强调段没被预检拦住(这条就是当天的假绿): {got4}"
    # t003 镜2 实跑：title 与 onscreen 只差一个标点 ⇒ 同一句在屏上打两遍
    got5 = check_scene({"title": "两次提示，一句没事", "body": "六月申请当租客，九月才发现被拆。",
                        "onscreen": "两次提示｜一句没事"}, layouts["story"], 2, ctx)
    assert any("同一句话" in p for p in got5), f"标题=屏句的重复没报出来: {got5}"
    # 干净稿不该误报
    clean = check_scene({"title": "拾荒21年，账户里42万",
                         "body": "湖南常德，71岁老人捡了21年废品。",
                         "onscreen": "他自己完全不知道",
                         "onscreenAccent": None}, layouts["hook"], 1, ctx)
    assert not clean, f"干净稿被误报: {clean}"
    print("✅ demo 自检通过（5 个反例都报出, 1 个干净稿不误报）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
