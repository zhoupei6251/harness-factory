#!/usr/bin/env python3
"""发布前闸门: 照着 aigc.json 核"② 在、① 有交代", 再给出必须带的平台声明参数。

位置: skills/douyin-pro/scripts/check_publishable.py
读的是成片旁边的标识台账 aigc.json (由 path_b_build.py 写), 判据与
skills/douyin-upload/SKILL.md 的「三件套」表一一对应:

    ① 画面显式角标   → sidecar.explicit.burned_in 为 true, **或**为 false 且有 disabled_by
    ② 文件隐式元数据 → sidecar.metadata_key / implicit 必须存在 (发射器已 ffprobe 读回过)
    ③ 平台自主声明   → 本脚本把它需要的 `--declaration 内容由AI生成` 原样打出来

**判据在 2026-09-29 放宽过一次(ARCHITECTURE D14, 用户点头)**: 原先要求"交付件三件齐活",
所以"不要角标"只能得到一份**发不出去**的草稿。现在可发布的底线是 **② 齐活 + ① 有交代**:
① 由开关决定(渲染档 `no-badge` 或旗标 `--no-badge`), 代价是 **③ 从此必带** ——
画面没标、② 过抖音转码即失, ③ 是平台侧唯一活下来的那件, 所以关 ① 买不到"什么都不用说"。
`badge_burned()` / `requires_declaration()` 就是这条代价的两端。

**默认三件全开** (2026-09-29 用户口径: 「那还是默认都打开吧」), 但"现在想关"落在**姿态文件**
`routes/news/aigc-mode.json` (同日「先帮我把两开关先关了吧」), 由 `aigc_mode.py` 统一裁决:

    旗标 (--deliver / --no-badge / --draft / --allow-undeclared / --require-declaration)
      > 姿态文件 (render: full|no-badge|draft / declaration: required|undeclared)
        > 代码默认 (full / required)

- 渲染档 `draft`(旗标 `--draft` 或姿态 `render=draft`)⇒ 那份成片在这里就是**不可发布** ——
  草稿的台账**不含** metadata_key / implicit / explicit 三段, 缺什么记什么缺, 不写一堆 false
  装作"标识在只是没开"。**这条与发布层开关无关**: 姿态怎么改都买不到"没标但可发"。
- 渲染档 `no-badge` ⇒ 可发布, 但 `--allow-undeclared` 与 `declaration=undeclared` 都会
  在这里被**拒**(EXIT=1)并给出三条出路 —— 不静默替用户改姿态。
- ③ 由 `declaration` 决定默认给不给: `required`(默认) 必须带 `--declaration`,
  `undeclared` 不打必带参数, 但**一定**警告并要求在 `MEMORY.videos[].declaration` 留痕。

退出码: 0 = 可发布, 1 = 拒绝(打印缺的是哪一件 / ① 关了却不肯带 ③)或姿态文件本身有问题。

用法:
    python skills/douyin-pro/scripts/check_publishable.py <成片.mp4>
    python skills/douyin-pro/scripts/check_publishable.py .harness-news-runtime/videos/t001-v4/final.mp4
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import aigc_mode

#: 抖音发布页「自主声明」弹窗的**选项原文**, 不是我们自己编的话术。
#: 取值凭据(上游源码行号)见 skills/douyin-upload/references/cli-contract.md § 自主声明。
DECLARATION_TEXT = "内容由AI生成"
#: 上游选不上时只 warning、**不阻断发布**, 所以成功凭据是日志里这一行:
DECLARATION_PROOF = "自主声明已选择「内容由AI生成」"


def sidecar_for(video: str) -> str:
    """成片旁边的那份台账 —— 与 path_b_build.py 写它的位置同源(同目录)。"""
    return os.path.join(os.path.dirname(os.path.abspath(video)), "aigc.json")


def check(sidecar: dict | None) -> list[str]:
    """台账 → 违规清单(空即通过)。纯函数, 自测锁的就是这张表。

    判据按 **D14**(2026-09-29 用户点头放宽): 可发布的底线是 **② 在 + ① 有交代**,
    ① 可以是烧好的(`burned_in: true`), 也可以是点名关掉的(`false` + `disabled_by`),
    但不许是"没人交代过的空白"—— 那既可能是旧产物也可能是烧丢了, 拿它当交付件等于
    让台账自己说谎。draft 段仍然一票否决(渲染层关掉标识买到的是"发不出去")。
    """
    if sidecar is None:
        return ["没有 aigc.json —— ①② 无从谈起(无侧车的老成片一律重渲): "
                "path_b_build.py 重跑一次再发"]
    bad: list[str] = []
    if sidecar.get("draft"):
        # 草稿轨的产物: ①② 根本没做。这是渲染层"关掉标识"的落点, 代价就写在这里 ——
        # 不能发, 而不是"发出去没人知道是 AI 做的"。措辞用台账里那句**真原因**
        # (旗标 --draft 还是姿态文件 render=draft), 别在这里替用户猜是谁关的。
        draft = sidecar["draft"]
        cause = draft.get("reason") or "草稿渲染(① 角标与 ② 元数据都没写)"
        why = draft.get("to_publish") or "去掉 --draft 重渲"
        return [f"{cause} —— 不得发布: {why}"]
    if "explicit" not in sidecar:
        bad.append("① 段缺失(sidecar 没有 explicit) —— 台账不完整(旧产物或手改), 重渲")
    else:
        explicit = sidecar["explicit"] or {}
        if explicit.get("burned_in") is True:
            pass
        elif explicit.get("burned_in") is False and explicit.get("disabled_by"):
            # D14 的 no-badge: ① 是被开关点名关掉的, 台账记下了出处 —— 合法,
            # 代价由 requires_declaration() 结算(③ 从此必带)。
            pass
        else:
            bad.append("① 显式角标没烧且没交代 (explicit.burned_in != true, 又没有 "
                       "disabled_by 说明是谁关的) —— 按 D14 要么烧, 要么点名关掉, 重渲")
    if not sidecar.get("metadata_key") or not sidecar.get("implicit"):
        bad.append("② 隐式元数据台账缺失 (metadata_key / implicit 为空) —— "
                   "发射器没写过或没读回, 重渲(② 是可发布判据里唯一不许缺的那件)")
    return bad


def badge_burned(sidecar: dict | None) -> bool:
    """① 到底在不在画面里 —— 只认真 true, 台账没这段也算不在。"""
    return bool(sidecar) and (sidecar.get("explicit") or {}).get("burned_in") is True


def requires_declaration(sidecar: dict | None) -> bool:
    """这份产物是否**必须**带 ③ 平台自主声明 —— D14 的核心代价, 买不到豁免。

    ① 没烧 ⇒ ③ 必带: 画面上一件标识都没有, 而 ② 元数据过抖音转码即失,
    于是 ③ 是平台侧唯一活下来的那一件。这时候 `declaration=undeclared` 与
    `--allow-undeclared` 都不许放行 —— 关 ① 换不来"什么都不用说"。
    ① 烧着时仍按姿态走(用户可以只留警告 + 留痕), 这条不被本次放宽改动。
    """
    return not badge_burned(sidecar)


def main() -> int:
    ap = argparse.ArgumentParser(description="发布前核 AIGC 三件套")
    ap.add_argument("video", help="成片 .mp4 路径")
    ap.add_argument("--allow-undeclared", action="store_true",
                    help=f"不带 ③ 平台自主声明(--declaration {DECLARATION_TEXT})"
                         "仍然放行 —— 覆盖姿态文件里的 declaration=required; "
                         "用了要在 MEMORY.videos[].declaration 留痕。"
                         "① 没烧的产物(D14)不认这个旗标, 照样 EXIT=1")
    ap.add_argument("--require-declaration", action="store_true",
                    help=f"反向旗标: 本次强制必须带 ③(--declaration {DECLARATION_TEXT}), "
                         "用来盖掉 routes/news/aigc-mode.json 里的 declaration=undeclared; "
                         "与 --allow-undeclared 同时给 = 报错")
    args = ap.parse_args()

    try:
        posture = aigc_mode.load_mode()
        decl_mode, decl_cause = aigc_mode.resolve_declaration(
            posture, allow_undeclared=args.allow_undeclared,
            require_declaration=args.require_declaration)
    except aigc_mode.ModeError as exc:
        print(f"❌ ③ 的开关读不出来: {exc}")
        return 1

    path = sidecar_for(args.video)
    sidecar = None
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as fh:
                sidecar = json.load(fh)
        except ValueError as exc:
            print(f"❌ {path} 不是合法 JSON: {exc}")
            return 1
    elif not os.path.isfile(args.video):
        print(f"❌ 找不到成片: {args.video}")
        return 1
    else:
        # 与 check(None) 用同一句话: 无侧车 = ①② 无从谈起, 别让用户从两条措辞里猜哪条是真判据
        print(f"❌ 拒绝发布 {os.path.basename(args.video)}:")
        for line in check(None):
            print(f"   · {line}")
        return 1

    bad = check(sidecar)
    if bad:
        print(f"❌ 拒绝发布 {os.path.basename(args.video)}:")
        for line in bad:
            print(f"   · {line}")
        return 1

    print(f"{'✅ ①② 齐活' if badge_burned(sidecar) else '✅ 可发布(按 D14: ② 在、① 点名关掉)'}"
          f": {os.path.basename(args.video)}")
    exp = sidecar.get("explicit") or {}
    if exp.get("burned_in") is True:
        print(f"   ① 角标 {exp.get('text')} · {exp.get('position')} · "
              f"字芯 {exp.get('glyph_height_px')}px / 最短边 {exp.get('short_side_px')}px · "
              f"{exp.get('shown_seconds')}s")
    else:
        print(f"   ① 未烧 —— 出处 {exp.get('disabled_by') or '(台账没这段)'} · "
              f"开回来: {exp.get('to_enable') or '渲染时加 --deliver'}")
    print(f"   ② 元数据键 {sidecar.get('metadata_key')} · "
          f"Label={sidecar.get('implicit', {}).get('AIGC', {}).get('Label')}")

    if requires_declaration(sidecar) and decl_mode == "undeclared":
        # D14 的代价在这里结算: 画面没标 + 元数据过转码即失 ⇒ 平台侧只剩 ③ 这一件,
        # 所以姿态与 --allow-undeclared 都买不到"不发声明"。这里**停机**而不是悄悄
        # 把 undeclared 当 required 用 —— 替用户改姿态是最难查的那种"闸门自己拿主意"。
        print(f"❌ 这份 {os.path.basename(args.video)} 不许不带 ③ —— ① 没烧"
              f"(出处: {exp.get('disabled_by') or '台账没交代'}), 而 ② 过抖音转码即失, "
              f"③ 是唯一活到平台侧的那一件。开关取值 {decl_cause} 在这一档不适用。")
        print(f"   三选一: 加 --require-declaration 重跑本闸门并按打印的命令带 "
              f"--declaration {DECLARATION_TEXT}; 或把 routes/news/aigc-mode.json 的 "
              "declaration 改回 required; 或用 --deliver 重渲让 ① 回到画面上。")
        return 1
    if decl_mode == "undeclared":
        print(f"⚠️ ③ 平台自主声明不带 —— 开关取值: {decl_cause}。《标识办法》§ 4-四 的"
              "「应当」里, 元数据过抖音转码即失, ③ 是唯一活到平台侧的那一件。")
        print("   请在 routes/news/MEMORY.md 的 videos[].declaration 记 undeclared, "
              "谁决定的、什么时候, 事后能查。")
        print(f"   发布命令(无 --declaration): sau douyin upload-video "
              f"--account <账号> --file {args.video} --title … --desc … --tags …")
        return 0
    print(f"③ 必须带: --declaration {DECLARATION_TEXT}   (开关取值: {decl_cause})")
    print(f"   成功凭据 = 日志出现「{DECLARATION_PROOF}」, 没有这行按未声明处理")
    print(f"   发布命令: sau douyin upload-video --account <账号> --file {args.video} "
          f"--title … --desc … --tags … --declaration {DECLARATION_TEXT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
