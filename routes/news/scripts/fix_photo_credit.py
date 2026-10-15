#!/usr/bin/env python3
"""fix_photo_credit —— 让「图源」署名只在真有图时出现（2026-10-15）。

背景：v006 cinematic 化时把 `<figcaption class="xx-photo-credit">` 从 `<figure>` 里
搬了出来（为了破除 stacking context），而"无图时整块隐藏"的规则写的是
`.xx-photo{display:none}` —— 管不到已经出去的兄弟节点。于是**无图镜照样显示
「图源：Wikimedia Commons」**，227 份 composition 里 212 份中招、覆盖 31/31 个 pack。
这不只是难看：画面声称图来自第三方许可库而实际没有图，是一份假的许可指向。

改法两半，缺一都不算修好（`path_b_selftest.t_imageless_shots_never_show_photo_credit`
就是按这两半机检的）：
  ① CSS 里给 `.xx-photo-credit` 补 `display: none;` —— 默认态就是"不显示"，
     运行时 JS 出错也不会退回"露出假署名"；
  ② `if (hasPhoto)` 分支里显式点亮 `credit.style.display = "block"`。

不往回搬 figcaption —— 它移出 figure 是为破 stacking context（v006 的实测结论），
搬回去等于把那个问题再引入一次。

用法（仓库根执行）：
    python routes/news/scripts/fix_photo_credit.py           # 改
    python routes/news/scripts/fix_photo_credit.py --check    # 只报告，不写
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKS = ROOT / "skills/douyin-pro/templates/hyperframes_path_b"

CREDIT_TAG_RE = re.compile(r'<figcaption[^>]*class="([a-z]+)-photo-credit"')
CREDIT_RULE_RE = r"\.{pre}-photo-credit\s*\{{[^}}]*\}}"


def fix_one(path: Path, write: bool) -> str:
    """返回该文件的处置结果（用于汇总打印）。逐行插入，缩进跟着被跟随的那行走。"""
    text = path.read_text(encoding="utf-8")
    tag = CREDIT_TAG_RE.search(text)
    if not tag:
        return "skip"                       # 这个版式没有图注板，本来就不该显示
    pre = tag.group(1)
    nl = "\r\n" if "\r\n" in text else "\n"
    figure_on = f'document.getElementById("{pre}-photo").style.display = "block";'
    credit_on = f'document.getElementById("{pre}-credit").style.display = "block";'

    rule = re.search(CREDIT_RULE_RE.format(pre=re.escape(pre)), text)
    if not rule or figure_on not in text:
        raise SystemExit(
            f"❌ {path}: 找不到 {'credit CSS 规则' if not rule else ''}"
            f"{' / ' if not rule and figure_on not in text else ''}"
            f"{'hasPhoto 点亮语句' if figure_on not in text else ''} —— "
            "结构与其余 212 份不一致，脚本不敢猜，请手工改。")

    need_css = "display: none" not in rule.group(0)
    need_js = credit_on not in text
    if not (need_css or need_js):
        return "already"

    anchor_css = f".{pre}-photo-credit"
    out, done = [], {"css": not need_css, "js": not need_js}
    for ln in text.splitlines(keepends=True):
        out.append(ln)
        stripped = ln.strip()
        ws = ln[: len(ln) - len(ln.lstrip())]
        if need_css and not done["css"] and stripped.startswith(anchor_css) \
                and stripped.endswith("{"):
            out.append(f"{ws}  display: none;{nl}")
            done["css"] = True
        elif need_js and not done["js"] and figure_on in ln:
            out.append(f"{ws}{credit_on}{nl}")
            done["js"] = True
    if not all(done.values()):
        missing = [k for k, v in done.items() if not v]
        raise SystemExit(f"❌ {path}: 锚点没找全（缺 {missing}），已放弃该文件。")

    new = "".join(out)
    if write:
        path.write_text(new, encoding="utf-8", newline="")
    return "fixed" if write else "would-fix"


def main() -> int:
    ap = argparse.ArgumentParser(description="无图镜不许显示图源署名（幂等）")
    ap.add_argument("--check", action="store_true", help="只报告要改哪些，不落盘")
    args = ap.parse_args()

    tally = {"fixed": 0, "would-fix": 0, "already": 0, "skip": 0}
    files = sorted(PACKS.glob("*/compositions/*.html"))
    # 扫到 0 个文件 = 路径根写错（本脚本踩过一次），不许它退化成"待改=0"这种假绿
    if not files:
        raise SystemExit(f"❌ {PACKS} 下没扫到任何 composition —— 路径根不对，不是没有要改的")
    for path in files:
        tally[fix_one(path, write=not args.check)] += 1

    verb = "待改" if args.check else "已改"
    print(f"[fix_photo_credit] {verb}={tally['fixed'] + tally['would-fix']} "
          f"已到位={tally['already']} 无图注板={tally['skip']}")
    if not args.check and tally["fixed"]:
        print("下一步必过：path_b_selftest.py（含 t_imageless_shots_never_show_photo_credit）"
              " + layout_selfcheck.py + audit_pack_contrast.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
