#!/usr/bin/env python3
"""分镜契约预检：在**渲染之前**说出"这句稿子会被吃掉"。

背景（2026-10-08 实跑 t002 踩到）:
  我给镜 2 写了 `title: "断在第几次"`、镜 5 写了 `title: "目前"`，
  而 news-coral 的 `stat` / `closer` / `quote` **没有标题位**。
  `title` 不进配音、又没有版式变量接住它 ⇒ 这两句话**既不上屏也不出声**。
  path_b_build 会打一条 ⚠，但那是**渲染 15 分钟之后**的事。

本脚本把这件事挪到写稿那一刻：读 scenes.json + 版式契约，逐镜列出
「哪些字段没有落点」，并给出可执行的修法。**只读，不改任何东西。**

用法:
    python routes/news/scripts/check_scene_contract.py <scenes.json> [--template news-coral]
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


def check_scene(scene: dict, layout: dict, index: int) -> list[str]:
    """返回这一镜的问题清单（空 = 干净）。"""
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

    # 3) 屏句：onscreen 的强调段会被覆盖
    if scene.get("onscreen") and "|" not in str(scene["onscreen"]) and scene.get("onscreenAccent"):
        problems.append(
            f"镜{index}: 传了 onscreenAccent 但 onscreen 没有 ｜ 分隔标记 ⇒ "
            f"强调段会被 parse_input 覆盖。修法: onscreen 写成「前段｜强调段」")

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

    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description="分镜契约预检（渲染前）")
    ap.add_argument("scenes", nargs="?", help="scenes.json 路径")
    ap.add_argument("--template", default="news-coral", help="版式包名")
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

    scenes = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(scenes, list):
        print("  ! 顶层必须是数组（每镜一个对象）", file=sys.stderr)
        return 1

    pack = pb.load_style_pack(args.template)
    layouts = dict(pack["layouts"])
    for name, lay in layouts.items():
        lay["_name"] = name
        lay["_row_capacity"] = pb.row_capacity(lay)

    all_problems = []
    for i, sc in enumerate(scenes, 1):
        name = scene_layout(sc)
        if name is None:
            continue                     # 自动选版式：发射器会填满，不预检
        lay = layouts.get(name)
        if lay is None:
            all_problems.append(f"镜{i}: 点了不存在的版式 {name!r} "
                                f"(可用: {', '.join(sorted(layouts))})")
            continue
        all_problems.extend(check_scene(sc, lay, i))

    if not all_problems:
        print(f"✅ 契约预检通过: {len(scenes)} 镜 · {args.template}")
        return 0

    print(f"❌ 契约预检发现 {len(all_problems)} 个问题（渲染前, 不花那 15 分钟）:\n")
    for p in all_problems:
        print(f"  · {p}")
    print("\n提示: 上面每条都会在渲染时变成「静默丢内容」或直接停机。")
    return 1


def _demo() -> int:
    """内置反例：必须报出 3 个问题（标题无落点 / 条目超行 / 空正文）。"""
    pack = pb.load_style_pack("news-coral")
    layouts = dict(pack["layouts"])
    for name, lay in layouts.items():
        lay["_name"] = name
        lay["_row_capacity"] = pb.row_capacity(lay)

    got = check_scene({"title": "断在第几次", "body": "三台车分别第3、4、2次断裂"},
                      layouts["stat"], 2)
    assert any("没有落点" in p for p in got), f"标题无落点没报出来: {got}"
    got2 = check_scene({"body": "x", "items": [{"label": "a", "value": "b"}] * 5},
                       layouts["rail"], 3)
    assert any("条目" in p for p in got2), f"条目超行没报出来: {got2}"
    got3 = check_scene({"body": ""}, layouts["hook"], 4)
    assert any("body 为空" in p for p in got3), f"空正文没报出来: {got3}"
    # 干净稿不该误报
    clean = check_scene({"title": "拾荒21年，账户里42万",
                         "body": "湖南常德，71岁老人捡了21年废品。",
                         "onscreen": "他自己完全不知道",
                         "onscreenAccent": None}, layouts["hook"], 1)
    assert not clean, f"干净稿被误报: {clean}"
    print("✅ demo 自检通过（3 个反例都报出, 1 个干净稿不误报）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
