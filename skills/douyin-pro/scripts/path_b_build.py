#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Path B 全链路串联脚本 · 抖音短视频生产专家团
============================================================
把"优化好的脚本文字"变成带 AI 配音 + 字幕的竖屏 MP4，全程零云费:

    脚本文本 ──▶ ① 分段            (按空行 / JSON 场景)
              ──▶ ② edge-tts 配音   (免费, 微软接口) → 每段 .mp3 + 词级 cues.json
              ──▶ ③ 发射合成 HTML    (读 --style 设计系统包, 逐镜挂子合成)
              ──▶ ④ 版式自检        (layout_selfcheck: 结构不变量, 渲染前)
              ──▶ ⑤ check 门禁      (hyperframes check --strict: 不过就不渲染)
              ──▶ ⑥ HyperFrames 渲染 → silent.mp4 (画面)
              ──▶ ⑦ 动量审计        (scdet: 每镜尾段必须仍在变化, 判据 3)
              ──▶ ⑧ ffmpeg 合成      → 拼音频 + 烧 ASS 字幕(含 AIGC 角标)
                                        + 写 AIGC 元数据 → final.mp4 + aigc.json
              ──▶ ⑨ 联络表          (contact-sheet.jpg: 每镜一帧, 供人工验收)

画面不再由本脚本内联拼 HTML(那是旧版"丑"的根源: px 排版 + 单层纯文字 + 无设计系统)。
本版只读 **设计系统包** ``templates/hyperframes_path_b/<style>/``:
``host.html`` 是宿主骨架(占位符), ``compositions/*.html`` 是自带时间轴的子合成版式,
``frame.md`` 是 token 与法则的唯一事实源。每个版式用 ``data-composition-variables``
声明自己的变量契约, 本脚本按契约填值, 填不出就报错停下(禁止用编造的事实补版面)。

依赖 (先跑 install_path_b_deps.py 装好):
    - Python >= 3.10
    - edge-tts          (pip install edge-tts · 词级时序只在其 Python API 上)
    - Node.js >= 22     (https://nodejs.org)
    - hyperframes       (npm install -g hyperframes)
    - ffmpeg + ffprobe  (https://ffmpeg.org)
    - Chrome            (npx hyperframes browser ensure)

用法:
    python path_b_build.py --input script.txt --output final.mp4
    python path_b_build.py --input scenes.json --style news-coral --source 央视新闻
    python path_b_build.py --input script.txt --check-only      # 只发射+自检+门禁, 不渲染
    python path_b_build.py --input script.txt --skip-render     # 只出音频+HTML
    python path_b_build.py --doctor                             # 只做环境自检

输入格式:
    A) 纯文本/Markdown: 用空行分段, 每段 = 一个分镜。段首短行(<=18字且非标点句)
       自动当标题, 其余当正文。版式由脚本按分镜形态自动挑(见 choose_layout)。
    B) JSON: [{"title": "...", "body": "...", "voice": "..."}, ...]
       或    [{"text": "整段旁白"}, ...]
       JSON 场景可以直接点名版式与变量, 优先级永远高于自动推导:
       {"layout": "stat", "kicker": "数据", "value": "1.2", "unit": "万亿",
        "label": "全年出口额", "compareValue": "0.9", "compareUnit": "万亿",
        "compareLabel": "上年", "items": [{"label": "第一步", "value": "..."}]}
"""

import argparse
import glob
import hashlib
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import timedelta
from pathlib import Path

import aigc_mode
import layout_selfcheck
import commons_media as cm


# ------------------------- 常量 (禁止魔法值) -------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_ROOT = os.path.join(os.path.dirname(SCRIPT_DIR), "templates", "hyperframes_path_b")
DEFAULT_STYLE = "news-coral"

#: 节目包 (设计系统 = 模板 = style; 三者同义, --template 与 --style 都接这同一组值)。
#: **这里不写总数** —— 数量一律 `len(ALL_TEMPLATES)` 现算 (决策 D20: 手抄 pack 数会悄悄过期)。
#: 顺序按"用途+情绪"二维分组, 默认 DEFAULT_STYLE 仍为 news-coral (人物故事型, 兼容存量稿件)。
#: 增加新模板只动这里 + templates/hyperframes_path_b/<name>/ 落地, 不动发射器主逻辑。
ALL_TEMPLATES = (
    # master pack (T1-T12, 主气质)
    "news-coral",         # T1  人物故事
    "news-ink",           # T2  调查
    "news-policy",        # T3  政策
    "news-stat",          # T4  数据
    "news-onsite",        # T5  现场
    "news-bulletin",      # T6  速报
    "news-explainer",     # T7  科普
    "news-alert",         # T8  警示
    "news-thread",        # T9  纪念
    "news-takes",         # T10 观点
    "news-blast",         # T11 体育
    "news-world",         # T12 国际
    # 派生变体 (气质派生)
    "news-coral-mono",    "news-ink-graphite",
    "news-policy-bold",   "news-stat-grid",
    "news-onsite-urgent", "news-bulletin-strip",
    "news-explainer-blueprint", "news-alert-warning",
    "news-thread-tribute","news-takes-column",
    "news-blast-score",   "news-world-globe",
    # 主题包 (T13-T19)
    "news-mosaic",        "news-dawn",
    "news-dusk",          "news-noir",
    "news-paper",         "news-podcast",
    "news-polarity",      # T19 极简高反差黑白对比 (2026-09-30)
)
#: --style / --template 选择映射; 选模板看 news-workflow/SKILL.md 的"模板决策树"或
#: routes/news/MEMORY.md videos[].template 字段 (ALL_TEMPLATES 里任何一个都合法)。

# ------------------------- pack 根（裁决 14 双轨） -------------------------
#: 编译产物包（`hf_compile.py` 从 spec.toml 出）落在隔壁根，老包原地不动：
#: 同稿并排比水位（P1-3e）要求两代包**同时可寻址**，而不是把老包迁走或让新包挤进老目录。
PATH_C_ROOT = os.path.join(os.path.dirname(SCRIPT_DIR), "templates", "hyperframes_path_c")

#: 查找顺序 = 可寻址范围。老的 path_b 根永远在前，所以两边同名时**存量优先**，
#: 编译包不可能悄悄顶掉一条产线在用的包。
PACK_ROOTS = [TEMPLATE_ROOT, PATH_C_ROOT]


def set_packs_root(roots) -> None:
    """换 pack 根的查找范围（测试与工具用；传单个字符串或路径列表都行）。

    存在性在 `pack_dir()` 里逐根查，不在这张表上 —— 根目录不存在不是错误，
    只是那一代包还没有。传空表回落到默认两根，避免"忘了配"表现为"哪个包都不在"。
    """
    if isinstance(roots, (str, os.PathLike)):
        roots = [roots]
    PACK_ROOTS[:] = [os.fspath(r) for r in roots] or [TEMPLATE_ROOT, PATH_C_ROOT]


def pack_dir(style: str) -> str:
    """包目录：`PACK_ROOTS` 里第一个**存在**的 `<root>/<style>`。

    一个都不存在时返回第一个根下的路径，好让 `load_style_pack` 的报错指着一个
    真实合理的落点说"这个包不存在"，而不是说"没找着"。
    """
    for root in PACK_ROOTS:
        candidate = os.path.join(root, style)
        if os.path.isdir(candidate):
            return candidate
    return os.path.join(PACK_ROOTS[0], style)


def available_templates() -> list[str]:
    """现在能被 `--template` 点名的 pack：**手写名单在前，编译包按目录自动补在后**。

    编译包不进 `ALL_TEMPLATES`：那张表是存量包的决策树顺序（T1–T19），P5 每铺一套
    都要回来加一行的话，就等于"加新模板只改目录、不动发射器主逻辑"（`:80` 的口径）失效。
    目录里有 `host.html` 才算数 —— 只有 `spec.toml` 还没编译的半成品不该变成一个
    能选、但一选就停在 `load_style_pack` 的选项。
    """
    names = list(ALL_TEMPLATES)
    for root in PACK_ROOTS:
        if not os.path.isdir(root):
            continue
        for entry in sorted(os.listdir(root)):
            if entry in names or not os.path.isdir(os.path.join(root, entry)):
                continue
            if os.path.isfile(os.path.join(root, entry, "host.html")):
                names.append(entry)
    return names


#: 占位 composition 的文件名(=版式名)。每个新 pack 先放它凑齐三层目录, 但它
#: **不是版式**: `load_style_pack` 直接跳过它, 于是"只有占位"的 pack 会在加载阶段
#: 就报"没有可用版式", 而不是渲染到第 1 镜才抛"填不满任何版式"(决策 D7)。
PLACEHOLDER_LAYOUT = "placeholder"

# ------------------------- AIGC 标识 (合规硬要求) -------------------------
#: 依据: 《人工智能生成合成内容标识办法》(2025-09-01 施行) § 4/§ 5 +
#: 强制性国标 GB 45438-2025《网络安全技术 人工智能生成合成内容标识方法》。
#: 显式标识 (§ 4-四) 里写"**应当**"的只有两处: 视频**起始画面**与视频**播放周边**;
#: "末尾/整个播放期间"那半句的措辞是"可以"。国标对视频另给量化线: **持续时长不应
#: 少于 2 秒**(标准正文摘录可见), **文字高度 ≥ 画面最短边的 5%**(5% 这句在标准里
#: 逐字见于**图片**条款, 视频条款由两处合规解读转述为同一口径, 本仓按此实现)。
#: 本实现取"**开场 AIGC_LABEL_ON_SECONDS 秒 + 左下角 + 字芯擦在 5% 线上**":
#: 起始画面与 ≥2s 持续由角标满足; **放弃全程常驻**, "播放周边"这一条改由 mp4
#: 元数据(隐式标识)与发布端 `--declaration 内容由AI生成` 承担 —— 这是相对旧实现
#: (贯穿全片左上角)刻意收窄的姿态, 记在 routes/news/ARCHITECTURE.md D8。
#: 隐式标识 (§ 5 + 国标附录): 文件元数据里加**字段名含 AIGC** 的扩展字段, 值是 JSON:
#:   {"Label","ContentProducer","ProduceID","ReservedCode1",
#:    "ContentPropagator","PropagateID","ReservedCode2"}
#: Label "1" = 属于人工智能生成合成内容; ContentProducer/ProduceID 必填,
#: ContentPropagator/PropagateID 是**传播平台**上传时回填的, 生产端留空占位。
#: ⚠️ 值一律转义成 ASCII (`ensure_ascii=True`): 国标要求要素值使用 GB 18030-2022
#:    字符集, ASCII 是其子集因此合法; 而中文直写实测能原样读回(shell=False + UTF-8
#:    落 mdta, 见 2026-09-29 探针), 但一旦有人把这条命令搬进 cmd.exe/PowerShell
#:    或非 UTF-8 代码页的环境, 中文就会变成乱码字节 —— 乱码的标识等于没有标识。
AIGC_METADATA_KEY = "AIGC"
AIGC_LABEL_VALUE = "1"
#: 生成合成服务提供者的名称或编码。标准允许写名称; 27 位编码是网信办《实践指南》
#: 给备案主体的规则(第 3 位主体类型 / 4 位绑定方式 / 5-22 位代码), 个人创作者没有
#: 统一社会信用代码, **不要**把身份证号写进公开文件的元数据 —— 所以默认写管线名,
#: 由 --aigc-producer 覆盖成你自己的频道/主体名。
DEFAULT_AIGC_PRODUCER = "harness-news-pathb"
AIGC_LABEL_TEXT = "AI 生成合成内容"
#: 国标量的"文字高度"是**字形实际高度**, ASS 的 FontSize 是 em 高度, 两者差一个
#: 字面率。2026-09-29 端到端成片实测(Microsoft YaHei / 1080×1920 / 取整帧量白色
#: 字芯): FontSize 70 → 字芯 51px, 即 ratio = 0.729 —— 而 5% 线要的是 54px,
#: 所以"字号按 5% 取"当场不合规。字号 = ⌈线 / ratio⌉(见 aigc_badge_font_size)。
#: ⚠️ 0.729 只对 ASS_HEADER 里 pin 住的那个字体成立, 而擦边字号**没有余量**兜它:
#:    换字体、或渲染机上没有该字体让 libass 静默回退到字面率更低的 CJK 字体时,
#:    字芯会掉到线以下, 且三道闸一道都不会红。旧实现乘 1.15 买的就是这个保险,
#:    现在按"擦到最小"的要求把余量退了回去 —— 改字体或换机器必须重量一次。
AIGC_LABEL_GLYPH_RATIO = 0.729
AIGC_LABEL_FLOOR_FRAC = 0.05
#: 显式角标在**开场常驻**的时长(秒)。国标线是 2s, 取 4s = 线的两倍: 第 1 镜常常
#: 短于 4s, 多出来的这一档让角标跨进第 2 镜, 不至于"刚出现就跟着切镜没了"。
AIGC_LABEL_ON_SECONDS = 4.0
AIGC_LABEL_MARGIN_W_FRAC = 0.045     # 距左边 = 宽 * 0.045
#: 角标墨迹与**内容禁入线**、**字幕块顶**各侧至少留出的高(像素)。整条带只有 92px
#: 而墨迹(字芯+描边+阴影)占 65px, 所以这个数不是装饰而是**报出这条带有多挤**: 谁改了
#: 字号、字幕行数或底边距而没重算带, 先在这里红, 不要等成片压字。
AIGC_LABEL_BAND_GAP_PX = 8
#: 实测(Microsoft YaHei / FontSize 75 / 黑底单烧 ASS 只留 AIGC 一条, 取当前 mv=303):
#: 白色字芯占 y 1555–1609, 而 MarginV 定义的"行盒底"在 y=1920−303=1617 ——
#: 字芯下面还有 **8px 下伸部空白**。底边距不扣这一档, 画出来的角标就比模型高 8px。
#: 2026-09-29 复测的真错: 旧推导没扣, 于是模型报"上侧留 13px", 按 8px 反算实画只剩
#: 5px(角标几乎贴上内容下界 1536)。上面那三个 y 全部可用 `verify_aigc_badge.py` 重取。
#: ⚠️ 这一档**随字号缩放**(实测约 0.10 em: 75 号→8px, 60 号→7px), 不是普适常数。
#: 现在只在 AIGC 字号那一个点用它; 改 AIGC_LABEL_FLOOR_FRAC 或改最短边基准后必须
#: 用 `verify_aigc_badge.py` 重量一遍, 它会把实测与模型逐侧差报出来。
AIGC_LABEL_LINE_SLACK_PX = 8
#: AIGC 样式的阴影厚度; ASS_HEADER 用 {aigc_sh} 取它, 阴影只朝右下各扩这一档。
AIGC_LABEL_SHADOW_PX = 1
#: 角标描边 = round(字号 / 本值) → 75 号给 5px。与字幕描边(ASS_OUTLINE_H_FRAC,
#: 按画面高算)是两套: 角标描边要跟字高一起缩放, 按画面高算会在横屏上粗过字本身。
AIGC_LABEL_OUTLINE_EM_DIV = 16
AIGC_PRODUCE_ID_BYTES = 32           # 内容编号取渲染产物哈希的前 N 位十六进制
AIGC_INTEGRITY_CODE_BYTES = 40       # ReservedCode1 取哈希的前 N 位十六进制
#: 显式标识最短持续时长(秒)。国标对视频显式标识的量化线: 文字高度 ≥ 最短边 5%、
#: 持续 ≥ 2 秒。角标虽只开 4 秒, **仍要挡**住"片长不足 2 秒"的极端输入 ——
#: 那种片子必须补时长或改人工加标, 不能假装合规。
AIGC_LABEL_MIN_SECONDS = 2.0

#: 自动选版式与推导文案时用的尺度, 全部按"竖屏 9:16 一行能放几个中文字"定
HOOK_LINE_CHARS = 7          # 主标题一行最多几字 (10cqw 字号下 ≈7)
ROW_LABEL_MAX_CHARS = 14     # catalog 行小标题 5cqw, 容器 74cqw → 一行 ≈14 字
#: 行说明的上限 = **两行**的字数, 不是三行。catalog 的说明是 3.4cqw(37.7px), 盒宽
#: 74cqw(800px) → 一行约 21 字 ⇒ 21×2 = 42。旧值 64 允许 4 行, 三行清单最坏要
#: 4×49+65+17 ≈ 278px/行 × 3 = 834px, 而行区只有 38cqh−20cqh = 730px —— 按 64 排版
#: 必然怼进字幕禁入区(frame.md 法则 1)。42 同时是法则 6 的下半句: 行式位装不进
#: 口播整句(新闻正文一句通常 >42 字), 屏上的整句只能来自屏句。
ROW_BODY_MAX_CHARS = 42
RAIL_VALUE_MAX_CHARS = 8     # rail 行右值是 5cqw 大字且 max-width 44cqw → 只放短值
MIN_RAIL_ITEMS = 3           # rail/catalog 固定三行, 少于 3 条不选它
MIN_STAT_FACTS = 2           # stat 有对比块, 少于 2 个数字会编造对比 (frame.md 法则 5)
QUOTE_MIN_CHARS = 8          # 引文短于此就不当引文

#: markdown 里"段首短行当标题"的宽度上限(沿用旧行为的 18 字, 提成名字是为了不在
#: 代码里裸写数字; 改它会影响所有存量脚本, 所以单独一行、单独说明)。
TITLE_LINE_MAX_CHARS = 18
#: 屏句 = 屏幕上那一句**整句**, 也是整句型屏上位(story 屏句位 / hook 辅助行 /
#: closer 行动句)唯一的取材处。上下限都来自字阶实测:
#: story 屏句位 4.4cqw(47.5px) 在 88cqw(950px) 盒里一行约 20 字, 取 16 留换行余量;
#: 下限 5 字以下就不成"一句陈述", 那种内容属于版式自己的小标题位。
ONSCREEN_MIN_CHARS = 5
ONSCREEN_MAX_CHARS = 16
#: 屏句/标题里点强调段的标记(全角竖线)。有它就按作者的意思切, 没有它就只在
#: "数字+单位"处切; **绝不再按固定字数切尾巴** —— 旧 `pick_accent` 的 `text[-4:]`
#: 把 "困住半辈子" 切成 "困"/"住半辈子", 那种病句断点就是 t001 丑的一半原因。
ONSPLIT = "｜"
#: 强调段少于 2 字在珊瑚片上像一个没打完的字符。
ONSPLIT_ACCENT_MIN = 2
#: markdown 的屏句行前缀(`屏:` / `屏：`), 与 JSON 的 `"onscreen"` 同义。
ONSCREEN_LINE_RE = re.compile(r"^屏\s*[:：]\s*(?P<text>.+)$")
#: 标题行可以下刀的位置: 真标点 + 强调标记。标记**只在代码里当断点用, 不上屏** ——
#: 只剥 `"，,、"` 的话, "没人告诉他｜他一直没问" 会把竖线留在第一行显示出来。
HEAD_BREAK_CHARS = "，,、" + ONSPLIT
#: 自动选版认的**唯一**词表 = composition 的**文件名词干**；本元组的顺序是**兜底顺序**
#: (整句型优先 → 条目/数据型 → 首尾专用型最后，因为 hook/closer 的书挡几何不该出现在中段)。
#: "这一镜写成什么形态"的先决优先级在 `choose_layout` 的 (stem, fits) 表里，与这里不同。
#: pack 里出现别的名（`list-steps` / `score` / `diagram` …）时，显式 `"layout"` 点名能用，
#: 自动模式**永远选不到** —— 10 个未落地 pack 的 frame.md §7 就是这么计划版式的（16 个词干
#: 全在词表外），照那些名字建文件会得到一个"看着齐备、实际惰性"的版式。写新 pack 先落这 7 个名。
AUTO_LAYOUT_STEMS = ("story", "stat", "quote", "catalog", "rail", "closer", "hook")
#: `title` 里属于"小节标签位"的版式: 作者没写标题时允许回落版式自带 default。
#: story 不在这里 —— 它的 title 是**领句**, 回落预览词就是替新闻下结论(见 `_title`)。
TITLE_LABEL_LAYOUTS = frozenset({"rail", "catalog"})
#: 会把作者标题行**用上**的变量名。判定"标题有没有落点"必须看这一整组:
#: `headTop/headBottomLead/headAccent` 是 hook 用 `split_headline(title)` 切出来的三段,
#: 只认 `title` 这个 id 会把 hook 误报成丢稿(t001-v3 实测喊过一次)。
TITLE_LANDING_VARS = frozenset({"title", "headTop", "headBottomLead", "headAccent"})

#: story 版式的双地面值: 相邻镜头轮换明暗, 这是"三段混调"落成的机械规则
TONE_LIGHT = "light"
TONE_DARK = "dark"

#: 配音时长下限: 版式契约 slotSeconds.min 也是 1, 两头必须一致
MIN_SLOT_SECONDS = 1.0

#: 门禁与渲染参数
#: 底部字幕禁入区, 与 frame.md 法则 1 / `layout_selfcheck.CAPTION_RESERVE_CQH` 同源
#: (20cqh, 1920 高 → 384px → y0 = 1 − 0.20 = 0.80)。取 20 的实测理由见
#: `caption_line_chars` 与本文件 CAPTION_MAX_LINES 上方注释。
CAPTION_ZONE = "x0=0;y0=0.80;x1=1;y1=1;severity=error"
DEFAULT_FPS = 30
DEFAULT_QUALITY = "delivery"
QUALITY_CHOICES = ("draft", "looks", "delivery")

#: 动量审计 (判据 3): 每镜后 1/4 的平均帧间变化量下限
TAIL_FRACTION = 0.25
MIN_TAIL_MOTION = 0.002

#: 联络表
CONTACT_SHEET_COLS = 3
CONTACT_SHEET_CELL_W = 320

HOST_PLACEHOLDERS = ("{{COMPOSITION_ID}}", "{{W}}", "{{H}}", "{{TOTAL}}",
                     "{{SCENES}}", "{{AUDIOS}}")
HOST_COMPOSITION_ID = "news"

VARIABLE_ATTR_RE = re.compile(
    r"data-composition-variables\s*=\s*(?P<q>[\"'])(?P<json>.*?)(?P=q)", re.S
)
ROOT_COMPOSITION_ID_RE = re.compile(
    r'<div[^>]*\bid="root"[^>]*data-composition-id="(?P<id>[^"]+)"', re.S
)
#: 版式的地面 = 它自己 ``#root`` 上的 background。发射器用它决定相邻镜头要不要
#: 换明暗 ("三段混调"里唯一可机械判定的部分: 同一套设计系统, 逐镜换地面)。
#: 只认 ``#root { … }`` 本体, 带属性选择器的 ``#root[data-tone=…] {`` 不当地面看。
ROOT_GROUND_RE = re.compile(
    r"#root\s*\{[^{}]*?background:\s*(?P<hex>#[0-9a-fA-F]{6})\s*[;}]", re.S
)
#: 设计系统色板 → 地面明暗。新版式用了没登记的颜色会在装包时就停机,
#: 而不是让"相邻镜地面必不同"静默退化 —— 未登记的色板是设计系统的破口, 不是小事。
GROUND_TONE_BY_HEX = {
    # 原有 6 个 (news-coral cream + news-policy paper + cobalt)
    "#f5f0e8": TONE_LIGHT,   # cream 主地面
    "#e8e0d4": TONE_LIGHT,   # cream-dark 引用块地面
    "#1a1a1a": TONE_DARK,    # ink 地面
    "#f5efe3": TONE_LIGHT,   # paper 主地面
    "#e8dfcb": TONE_LIGHT,   # paper-dark 卡衬地面(条目卡底)
    "#1f3a68": TONE_DARK,    # cobalt 地面(暗面翻面 + closer 书挡)
    "#1f1b16": TONE_DARK,    # 暖纸杂志族的墨面(spec color.surfaces.ink, HSL L 10.39)
    "#000000": TONE_DARK,    # auto-extended (polarity 极简纯黑)
    "#080808": TONE_DARK,    # auto-extended (0.03 L)
    "#0a0a0a": TONE_DARK,    # auto-extended (0.04 L)
    "#0a0a0d": TONE_DARK,    # auto-extended (0.04 L)
    "#0c0a08": TONE_DARK,    # auto-extended (0.04 L)
    "#0a0a0e": TONE_DARK,    # auto-extended (0.04 L)
    "#0a0a14": TONE_DARK,    # auto-extended (0.04 L)
    "#0c0a14": TONE_DARK,    # auto-extended (0.04 L)
    "#0e0a14": TONE_DARK,    # auto-extended (0.05 L)
    "#080c14": TONE_DARK,    # auto-extended (0.05 L)
    "#1a0808": TONE_DARK,    # auto-extended (0.05 L)
    "#0a0c14": TONE_DARK,    # auto-extended (0.05 L)
    "#0c0c10": TONE_DARK,    # auto-extended (0.05 L)
    "#0c0c14": TONE_DARK,    # auto-extended (0.05 L)
    "#1a0a08": TONE_DARK,    # auto-extended (0.05 L)
    "#0e0e12": TONE_DARK,    # auto-extended (0.06 L)
    "#0a1018": TONE_DARK,    # auto-extended (0.06 L)
    "#101012": TONE_DARK,    # auto-extended (0.06 L)
    "#0a1408": TONE_DARK,    # auto-extended (0.07 L)
    "#08131c": TONE_DARK,    # auto-extended (0.07 L)
    "#0a1419": TONE_DARK,    # auto-extended (0.07 L)
    "#1a1408": TONE_DARK,    # auto-extended (0.08 L)
    "#181818": TONE_DARK,    # auto-extended (0.09 L)
    "#1c1c1f": TONE_DARK,    # auto-extended (0.11 L)
    "#e8e6e1": TONE_LIGHT,    # auto-extended (0.90 L)
    "#ece8df": TONE_LIGHT,    # auto-extended (0.91 L)
    "#f3efe6": TONE_LIGHT,    # auto-extended (0.94 L)
    "#f0f0f0": TONE_LIGHT,    # auto-extended (0.94 L)
    "#fef3c7": TONE_LIGHT,    # auto-extended (0.95 L)
    "#f0f4fa": TONE_LIGHT,    # auto-extended (0.96 L)
    "#f0f5fa": TONE_LIGHT,    # auto-extended (0.96 L)
    "#f8f4ee": TONE_LIGHT,    # auto-extended (0.96 L)
    "#f5f5f0": TONE_LIGHT,    # auto-extended (0.96 L)
    "#f5f5f5": TONE_LIGHT,    # auto-extended (0.96 L)
    "#f8f5ee": TONE_LIGHT,    # auto-extended (0.96 L)
    "#f9f5ed": TONE_LIGHT,    # auto-extended (0.96 L)
    "#fff7ed": TONE_LIGHT,    # auto-extended (0.97 L)
    "#faf8f5": TONE_LIGHT,    # auto-extended (0.97 L)
    "#fff8e7": TONE_LIGHT,    # auto-extended (0.97 L)
    "#f5f9fc": TONE_LIGHT,    # auto-extended (0.97 L)
    "#faf9f6": TONE_LIGHT,    # auto-extended (0.98 L)
    "#f0fdf4": TONE_LIGHT,    # auto-extended (0.98 L)
    "#fafaf6": TONE_LIGHT,    # auto-extended (0.98 L)
    "#f8fafc": TONE_LIGHT,    # auto-extended (0.98 L)
    "#fbfaf5": TONE_LIGHT,    # auto-extended (0.98 L)
    "#fcfaf6": TONE_LIGHT,    # auto-extended (0.98 L)
    "#fbfbf6": TONE_LIGHT,    # auto-extended (0.98 L)
    "#f5fdf4": TONE_LIGHT,    # auto-extended (0.98 L)
    "#fefefe": TONE_LIGHT,    # auto-extended (1.00 L)
    "#ffffff": TONE_LIGHT,    # auto-extended (1.00 L)
}
#: 色板里出现过的地面明暗集合, 用来校验可变地面版式填出来的值合法。
GROUND_TONES = frozenset(GROUND_TONE_BY_HEX.values())
#: 可变地面版式 (story) 声明"这一镜落在哪个地面"的契约变量名。
#: 发射器按镜头读它来决定下一镜翻不翻面 —— 写死字符串 "tone" 就是魔法值。
TONE_VAR_ID = "tone"
#: 数字后面的中文单位。年/月/日/周 必须收进来 —— "账户里42万，那是21年" 这类
#: 时间数字没有单位位就等于没有，stat 版式会整条不可用 (实测 t001 第 4 镜)。
#: 长单位必须排在短单位前面: Python 交替式取**先出现**的分支, "万亿"排在"亿"之后
#: 就永远只能匹到"万", 数值单位当场错一个数量级。
NUMBER_UNIT_RE = re.compile(
    r"([+-]?\d[\d,]*(?:\.\d+)?)\s*"
    r"(亿元|万元|万亿|千万|百万|亿|万|千|百|%|％|元|块|毛|人次|人|天|年|月|周|日|号|岁|倍"
    r"|个|条|次|分钟|秒|小时|公里|吨|平方米|起|件|例|家)?"
)
CLAUSE_SPLIT_RE = re.compile(r"[。！？!?；;\n]+")
LABEL_SPLIT_RE = re.compile(r"[，,、:：\-—]+")
SENTENCE_END = ("。", "，", "、", "：")
QUOTE_OPENERS = ("“", "\"", "「", "『")
QUOTE_CLOSERS = ("”", "\"", "」", "』")

#: scdet 每帧可能按色平面打多条分数, 取每帧最大值
MOTION_PTS_RE = re.compile(r"pts_time:([0-9.]+)")
MOTION_SCORE_RE = re.compile(r"lavfi\.[\w.]*score=([0-9.eE+-]+)")

#: 烧录字幕几何(全部按输出尺寸推导, 不写死像素; 1920×1080 竖屏下的实际取值
#: 与逐行像素实测见 CAPTION_MAX_LINES 上方注释)。
ASS_FONT_H_FRAC = 32.0            #: 字号 = h/32 → 1920 高时 60px
ASS_OUTLINE_H_FRAC = 640.0        #: 描边 = h/640 → 1920 高时 3px
ASS_MARGIN_W_FRAC = 0.06          #: 左右边距 = w*0.06 → 1080 宽时 64px
ASS_MARGIN_BOTTOM_H_FRAC = 0.09   #: 底边距 = h*0.09 → 1920 高时 172px, 避开抖音右侧点赞栏
#: 每条字幕的视觉行数上限。实测(t001-v2 final.mp4 逐行像素扫描, Alignment 2 +
#: ScaledBorderAndShadow ⇒ 块底 = h - mv = 1748、行距 = 字号 = 60px):
#:   三行顶边 ≈ 1568px(81.7cqh)、两行顶边 ≈ 1628px。
#: frame.md 法则 1 的 20cqh 禁入区(1536px)只有在 ≤2 行时才真有 90px 余量,
#: 所以超长的口播条在这里**按时长切成多条**, 而不是让它折成三行压到画面上。
CAPTION_MAX_LINES = 2
#: 每行最少几个字: 宽度极窄的输出(测试用)也不许切成 3 字一行的面条
CAPTION_MIN_LINE_CHARS = 8

ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
ScaledBorderAndShadow: yes
WrapStyle: 0
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{fs},&H00FFFFFF,&H000000FF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,{ol},1,2,{ml},{mr},{mv},134
Style: AIGC,{font},{aigc_fs},&H00FFFFFF,&H000000FF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,{aigc_ol},{aigc_sh},1,{aml},{amr},{amv},134

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

MOUNT_TPL = (
    '      <div id="{mount_id}" class="clip"'
    ' data-composition-id="{composition_id}"'
    ' data-composition-src="compositions/{file_name}"'
    ' data-variable-values="{values}"'
    ' data-start="{start}" data-duration="{dur}" data-track-index="1"'
    ' data-width="{w}" data-height="{h}"></div>'
)
#: 画面走 1 轨 (MOUNT_TPL 里写死), 配音单独走 0 轨: 两条轨互不遮挡,
#: 时间轴上配音与画面**同一起点**就是"这句话配这一镜"; 终点各留一点余量,
#: 见 AUDIO_MOUNT_HEADROOM_SECONDS。
AUDIO_TRACK_INDEX = 0
#: 配音窗比画面窗短的余量。为什么必须短: 引擎的重叠判据 (lintDuplicateAudioTracks)
#: 是 `b.start < a.end`, 而 a.end 由它自己做浮点加法 `data-start + data-duration` 得出 ——
#: 实测 t001-v3 的 11.88 + 11.808 = 23.688000000000002, 比下一镜起点 23.688 大 2e-15,
#: 于是首尾**严丝合缝**的两条窗被判成叠放, duplicate_audio_track 以 warning 触发,
#: 而 `check --strict` 把 warning 升级成失败 ⇒ 整条链路拒绝渲染。
#: 50ms 的取法: 比浮点进位(1e-14 量级)高十个数量级, 比一个 mp3 帧(实测 edge-tts
#: 输出 24kHz, 1152 样本 = 48ms)长, 又落在人对句尾停顿的分辨门槛之下。
AUDIO_MOUNT_HEADROOM_SECONDS = 0.05
AUDIO_TPL = (
    '      <audio id="{audio_id}" src="{src}"'
    ' data-start="{start}" data-duration="{dur}"'
    ' data-track-index="{track}" data-volume="1"></audio>'
)

# ---------------- 字幕轨（HyperFrames 原生，裁决 2 / 20 / 22） ----------------
#: 画面走 1 轨 (MOUNT_TPL)，配音走 0 轨 (AUDIO_TRACK_INDEX)，字幕单独走 2 轨：
#: 三层互不遮挡，字幕永远压在版式之上 —— 这是"字幕收进合成"的物理形态。
SUBTITLE_TRACK_INDEX = 2
#: 生成字幕子合成的文件名词干。真源在 `layout_selfcheck.SUBTITLE_FILE_STEM`（自检靠它认字幕
#: 文件并豁免两条不变量），发射器引用同一个串拼 `comp_id` / 文件名 / 挂载 —— 两处分家 = 字幕
#: 文件既挂上了又没被自检认出豁免，或反过来。
SUBTITLE_FILE_PREFIX = layout_selfcheck.SUBTITLE_FILE_STEM
#: 字幕几何全部从本文件已有的 ASS 常数推导 —— 不再开第二份真源。spec.toml `[subtitle]`
#: 写的是同一组比值（margin-bottom-frac=0.09=9cqh、line-height-frac=1/32=3.125cqh、
#: frame.md 左右 6cqw），改任何一处三处都要一起改，所以这里只从常数算，不手抄像素。
SUBTITLE_BOTTOM_CQH = round(ASS_MARGIN_BOTTOM_H_FRAC * 100, 4)        # 块底 = 9cqh
SUBTITLE_FONT_CQH = round(100.0 / ASS_FONT_H_FRAC, 4)                 # 字号 = 3.125cqh
SUBTITLE_SIDE_CQW = round(ASS_MARGIN_W_FRAC * 100, 4)                 # 左右边距 = 6cqw
SUBTITLE_MAX_WIDTH_CQW = round(100.0 - 2 * SUBTITLE_SIDE_CQW, 4)      # 盒宽 = 88cqw
#: 描边按字号的 em 比例给（ASS 描边 = h/640 ≈ 3px、字号 h/32=60px ⇒ 0.05em 同口径），
#: 用 text-shadow 的八向偏移画一圈黑：软件光栅下逐像素确定，且比 -webkit-text-stroke 更贴
#: ASS 的"字芯 + 外描边"形状（描边长在字外面，不啃字）。
SUBTITLE_OUTLINE_EM = round(ASS_FONT_H_FRAC / ASS_OUTLINE_H_FRAC, 4)   # (h/32)/(h/640)=20 → 1/20=0.05em
#: 强调是"词的着色"（裁决：统一白字 + 黑描边，强调词换成固定高亮色且同样描边）。
#: 高亮色取杂志族强调 #B45309：与黑描边在一起在任何地面上都够跳（描边把字与地面隔开）。
SUBTITLE_TEXT_COLOR = "#ffffff"
SUBTITLE_ACCENT_COLOR = "#B45309"
SUBTITLE_STROKE_COLOR = "#000000"
#: 字幕不呼吸、不做连续位移（帧自检的 drift/budget 两条对字幕文件豁免），但入场用
#: 词级 fromTo、退场用整条 cue 淡出。单词淡入下限与退场时长是有理由的具名常数：
SUBTITLE_ENTRANCE_MIN = 0.1          # 单字淡入不短于此（太短读成跳变，非"亮起来"）
SUBTITLE_EXIT_SECONDS = 0.3          # 一条 cue 淡出时长（末条贴着 slot 尾收）

#: 字幕子合成挂在 2 轨的 clip 模板（与 MOUNT_TPL 同形状，只有 track-index 与无变量不同：
#: 字幕的文本与时间轴在**编译期烤进**子合成，挂载不再传 data-variable-values）。
SUBTITLE_MOUNT_TPL = (
    '      <div id="{mount_id}" class="clip"'
    ' data-composition-id="{composition_id}"'
    ' data-composition-src="compositions/{file_name}"'
    ' data-start="{start}" data-duration="{dur}" data-track-index="{track}"'
    ' data-width="{w}" data-height="{h}"></div>'
)

#: 一镜字幕子合成的骨架。**六个占位符**由 `emit_subtitle_composition` 填：合成 id、本镜秒数、
#: 底/字号/边距/盒宽（cqh/cqw，全部从 ASS_* 常数推导）、逐 cue 容器、逐词+逐 cue 补间。
#: `#root` 透明、`.sc-cue` 无背景 —— 版式自检的 SURFACE_OPACITY_TWEEN 只挡带背景的面淡入，
#: 这里是纯文字带描边，opacity 补间合法（实测旧 ASS 出口也是描边字，几何一致）。
SUBTITLE_COMP_TPL = '''<!doctype html>
<html lang="zh-CN" data-composition-variables='[
    {{"id": "slotSeconds", "type": "number", "label": "本镜可见秒数", "default": {slot}, "min": 1}}
  ]'>
  <head>
    <meta charset="UTF-8" />
  </head>
  <body>
    <template>
      <style>
@font-face {{
  font-family: "HF CJK";
  src: local("Noto Sans SC"), local("Microsoft YaHei"), local("DengXian");
  font-weight: 100 900;
}}

#root {{ position: absolute; inset: 0; overflow: hidden; background: transparent; }}

#sc-wrap {{ position: absolute; left: {side}cqw; width: {maxw}cqw; bottom: {bottom}cqh;
  font-family: "HF CJK", sans-serif; font-size: {font}cqh; font-weight: 700;
  line-height: 1.24; text-align: center; color: {text};
  text-shadow: {outline}em {outline}em 0 {stroke}, -{outline}em {outline}em 0 {stroke},
    {outline}em -{outline}em 0 {stroke}, -{outline}em -{outline}em 0 {stroke},
    0 {outline}em {outline}em rgba(0,0,0,0.35); }}

.sc-cue {{ position: relative; }}
.sc-row {{ display: block; }}
.sc-w {{ display: inline-block; }}
.sc-acc {{ color: {accent}; }}
      </style>
      <div id="root" data-composition-id="{comp_id}" data-width="{w}" data-height="{h}">
        <div id="sc-wrap">{body}</div>
      </div>
      <script>
        const tl = gsap.timeline({{ paused: true }});
{tweens}
        window.__timelines["{comp_id}"] = tl;
      </script>
    </template>
  </body>
</html>
'''

SUBTITLE_COMP_TPL = SUBTITLE_COMP_TPL.replace("{text}", SUBTITLE_TEXT_COLOR) \
    .replace("{stroke}", SUBTITLE_STROKE_COLOR).replace("{accent}", SUBTITLE_ACCENT_COLOR)


class EmitterError(RuntimeError):
    """发射器停机的唯一原因: 数据不足以诚实地填满足够好的版面。"""


# ------------------------- 工具函数 -------------------------
def log(msg: str):
    print(f"[path_b] {msg}", flush=True)


def run(cmd, **kw):
    """运行命令, 返回 CompletedProcess; 出错时按 check 决定抛不抛。

    ⚠️ 跨平台关键：Windows 下 npx/npm/hyperframes/ffmpeg 有的是 .cmd 包装
    (npx/npm/hyperframes) 有的是 .exe (ffmpeg/ffprobe)。统一用 list 传入时，
    原生 Windows 的 CreateProcess 无法直接启动 .cmd，会抛 FileNotFoundError/
    WinError 193。所以 Windows 下必须 shell=True + list2cmdline 走 cmd.exe。
    （Git Bash 里能直接跑 npx 是 bash 自己解析了；用户用 python 在
    cmd/PowerShell 跑脚本时若不处理就会崩溃。）
    """
    if isinstance(cmd, str):
        cmd_list = cmd.split()
        display = cmd
    else:
        cmd_list = [str(c) for c in cmd]
        display = " ".join(cmd_list)
    log("▶ " + display)
    if sys.platform == "win32":
        s = subprocess.list2cmdline(cmd_list)
        return subprocess.run(s, shell=True, **kw)
    return subprocess.run(cmd_list, **kw)


def run_exe(cmd, **kw):
    """启动 **必须是 .exe** 的命令, 且绕开 cmd.exe: Windows 下走 shell=False。

    为什么需要第二条路: `run()` 在 win32 下用 `shell=True` 是为了能启动
    npx/npm/hyperframes 这些 .cmd 包装, 代价是参数要过 cmd.exe 这道重新解析 ——
    而 `-metadata AIGC={"AIGC":{"Label":"1"}}` 这种值里既有 `"` 又有 `{}`:
    cmd.exe 把成对双引号**从命令行里删掉**(自己的引号语法), 到 ffmpeg 手里
    JSON 就已经碎了。ffmpeg/ffprobe 都是 .exe, CreateProcess 能直接起,
    不需要 shell —— 那就让带 JSON 的那一条命令不过 shell。
    """
    cmd_list = [str(c) for c in cmd]
    log("▶ " + " ".join(cmd_list))
    if sys.platform == "win32":
        # 传 list(shell=False): CPython 内部用 list2cmdline 拼命令行,
        # MSVCRT 的 argv 解析正好是它的逆运算, `"` 会原样回到 argv 里。
        return subprocess.run(cmd_list, **kw)
    return subprocess.run(cmd_list, **kw)


# ------------------------- 分段计时 (提速实测基线, 规格 2026-10-09) -------------------------
_TIMINGS: list[tuple[str, float]] = []


class timed:
    """阶段计时上下文: with timed("dub"): ... → 退出时把 (stage, 秒) 记进 _TIMINGS。"""

    def __init__(self, stage: str):
        self.stage = stage

    def __enter__(self):
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        _TIMINGS.append((self.stage, time.perf_counter() - self.t0))
        return False


def write_timings(out_path: str) -> None:
    """把分段计时落 JSON 并打一行摘要。"""
    total = sum(t for _, t in _TIMINGS)
    payload = {
        "stages": [{"stage": s, "seconds": round(t, 2)} for s, t in _TIMINGS],
        "total_seconds": round(total, 2),
    }
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    write_text(out_path, json.dumps(payload, ensure_ascii=False, indent=2))
    log("⏱ 分段计时: " + " | ".join(f"{s}={t:.1f}s" for s, t in _TIMINGS)
        + f" | 合计 {total:.1f}s → {out_path}")


# ------------------------- hyperframes 可执行定位 (提速组件①, 规格 2026-10-09) -------------------------
_HF_PREFIX: list[str] | None = None
_HF_SOURCE: str = ""


def hyperframes_candidates(force_bin: str | None = None,
                           root: str | None = None,
                           npx_root: str | None = None) -> list[tuple[list[str], str]]:
    """候选调用前缀, 按优先级: 旗标 > 项目 node_modules > npx 缓存(逐个)。全空 = 空表。"""
    out: list[tuple[list[str], str]] = []
    if force_bin:
        out.append(([force_bin], f"旗标 --hyperframes-bin={force_bin}"))
    root = root or os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
    for name in ("hyperframes.cmd", "hyperframes"):
        cand = os.path.join(root, "node_modules", ".bin", name)
        if os.path.isfile(cand):
            out.append(([cand], f"项目 node_modules ({name})"))
            break
    npx_root = npx_root or os.path.join(os.environ.get("LOCALAPPDATA", ""),
                                        "npm-cache", "_npx")
    for name in ("hyperframes.cmd", "hyperframes"):
        for b in sorted(glob.glob(os.path.join(npx_root, "*", "node_modules", ".bin", name))):
            out.append(([b], f"npx 缓存 ({b})"))
    return out


def resolve_hyperframes(force_bin: str | None = None,
                        root: str | None = None,
                        npx_root: str | None = None) -> tuple[list[str], str]:
    """返回 (调用前缀, 真出处)。探测全缺时回落 npx -y(现场拉包, 每次 5-15 分钟)。"""
    cands = hyperframes_candidates(force_bin, root=root, npx_root=npx_root)
    if cands:
        return cands[0]
    return ["npx", "-y", "hyperframes"], "回落 npx -y hyperframes (每次重装, 慢)"


def hf_init(force_bin: str | None = None) -> list[str]:
    """初始化并缓存调用前缀; 每次真跑只打一行出处日志。"""
    global _HF_PREFIX, _HF_SOURCE
    if _HF_PREFIX is None or force_bin:
        _HF_PREFIX, _HF_SOURCE = resolve_hyperframes(force_bin)
        log(f"[hf] hyperframes 出处: {_HF_SOURCE}")
    return _HF_PREFIX


def hf_argv(*args: str) -> list[str]:
    return hf_init() + [str(a) for a in args]


def which(tool: str) -> str | None:
    return shutil.which(tool) or shutil.which(tool + ".exe")


def read_text(path: str, errors: str = "strict") -> str:
    with open(path, encoding="utf-8", errors=errors) as f:
        return f.read()


def write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def read_json(path: str):
    """读一份 JSON；不存在或读不出都返回 `None`，由调用方按"没有这份输入"处理。

    容忍坏文件不是偷懒：`cues.json` 写在一次 12 秒的网络往返之后，中途断掉就会留下
    半截 JSON。那种情况下正确的行为是**重新配音**，而不是让整条产线卡在一个解析错误上。
    """
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def write_json(path: str, doc) -> None:
    write_text(path, json.dumps(doc, ensure_ascii=False, indent=1) + "\n")


def fmt_secs(value: float) -> str:
    """时间点一律三位小数, 与 data-duration 的解析精度对齐。"""
    return f"{value:.3f}"


def ffprobe_duration(path: str) -> float | None:
    """用 ffprobe 取音频时长(秒); 取不到返回 None。"""
    ff = which("ffprobe")
    if not ff:
        return None
    try:
        out = subprocess.check_output(
            [ff, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        return float(out)
    except (subprocess.SubprocessError, ValueError):
        return None


def ffprobe_format_tag(path: str, key: str) -> str | None:
    """读容器(format)级元数据的一个键; 不存在或 ffprobe 不可用时返回 None。

    和 ffprobe_duration 一样属于"探测", 探不到不当失败 —— 是否要停机由调用方决定
    (AIGC 标识那条就必须停机, 见 mux_and_burn)。

    ⚠️ 入口名必须是 `format_tags=<键>` 而不是 `format=<键>`: `format=` 只认 ffprobe
    自己的固定字段(duration/format_name/…), 自定义元数据键走它**不报错、只返回空**,
    实测本机 N-122527 就是这种静默假阴性 —— 拿它当核验等于"核验永远失败",
    反过来若写反了(拿 format_tags 去取 duration)也一样取不到。
    """
    ff = which("ffprobe")
    if not ff:
        return None
    try:
        out = subprocess.check_output(
            [ff, "-v", "error", "-show_entries", f"format_tags={key}",
             "-of", f"default=noprint_wrappers=1:nokey=1", path],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", errors="replace").strip()
    except (subprocess.SubprocessError, ValueError):
        return None
    return out or None


def estimate_duration(text: str) -> float:
    """没有 ffprobe 时的兜底估算: 中文约 4.5 字/秒, 英文约 2.5 词/秒。"""
    cn = len(re.findall(r"[一-鿿]", text))
    en = len(re.findall(r"[A-Za-z]+", text))
    secs = cn / 4.5 + en / 2.5
    return max(MIN_SLOT_SECONDS, secs + 0.6)


def ffmpeg_sub_path(p: str) -> str:
    """把任意路径转成 ffmpeg subtitles 过滤器里安全的写法。

    ffmpeg 的 filtergraph 里 ':' 是选项分隔符、'\\' 是转义符、空格等需转义；
    Windows 用户的临时目录常带空格(如 'C:\\Users\\John Doe\\...')，直接塞进去
    渲染会报找不到字幕文件。这里统一: 反斜杠→正斜杠, 特殊字符转义, 整段单引号包住。
    """
    p = p.replace("\\", "/")
    p = p.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    return "'" + p + "'"


def vtt_time(secs: float) -> str:
    td = timedelta(seconds=secs)
    h, rem = divmod(td.seconds + td.days * 86400, 3600)
    m, s = divmod(rem, 60)
    ms = int(td.microseconds / 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def ass_time(secs: float) -> str:
    """ASS 时间戳: H:MM:SS.cc (百分之一秒)"""
    secs = max(0.0, secs)
    cs = int(round(secs * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def caption_font_size(h: int) -> int:
    """字幕字号 = 输出高 / ASS_FONT_H_FRAC (1920 → 60px)。"""
    return int(round(h / ASS_FONT_H_FRAC))


def caption_line_chars(w: int, h: int) -> int:
    """一行放几个字 = (输出宽 − 左右字幕边距) / 字幕字号, 向下取整。

    必须按真实可用宽度算, 因为 libass 在 `WrapStyle: 0` 下会拿这个宽度**自己再折一次**。
    实测旧算法(宽度的 2% → 1080 给 21 字)比可用宽度(952px / 60px ≈ 15 字)宽出 40%,
    于是每条字幕被"按 21 字切断 + 再按 15 字折行": 两行变四行, 块顶从 1628 抬到 1568,
    正好压在旧 16cqh 禁入区(1613)里的正文上 —— t001-v2 第 3/5 镜就是这么撞的。
    """
    usable = w - 2 * int(w * ASS_MARGIN_W_FRAC)
    return max(CAPTION_MIN_LINE_CHARS, int(usable / caption_font_size(h)))


def caption_lines(text: str, line_chars: int) -> list[str]:
    """按行宽把字幕切成行: 中文按字切, 英文单词与数字不拆。"""
    lines, buf = [], ""
    for token in re.findall(r"[A-Za-z0-9]+|\s+|.", text):
        if len(buf) + len(token) > line_chars and buf:
            lines.append(buf.strip())
            buf = token.strip()
        else:
            buf += token
    if buf.strip():
        lines.append(buf.strip())
    return lines


def split_cue(start: float, end: float, text: str, line_chars: int,
              max_lines: int) -> list[tuple[float, float, str]]:
    """一条字幕最多 `max_lines` 行, 超了就按时长切成多条。

    时长按各条的字数分摊 —— 读多长的字就该占多长的时间, 平均切会让短句在屏上干等。
    为什么切条而不是放行数: 块底固定在 h − MarginV, 每多一行块顶就抬高一个字号,
    行数没有上限 ⇒ 底部禁入区(frame.md 法则 1)就没有可保证的下界。
    """
    lines = caption_lines(text, line_chars)
    if len(lines) <= max_lines:
        return [(start, end, "\\N".join(lines))]
    chunks = [lines[i:i + max_lines] for i in range(0, len(lines), max_lines)]
    weights = [len("".join(c)) for c in chunks]
    total = sum(weights) or len(chunks)
    span = max(0.0, end - start)
    cues, acc = [], 0
    for i, chunk in enumerate(chunks):
        s = start + span * (acc / total)
        acc += weights[i]
        e = end if i == len(chunks) - 1 else start + span * (acc / total)
        cues.append((s, e, "\\N".join(chunk)))
    return cues


# ---------------- 词级 cues 的取数面（P2-1 · spec §6.4 / 裁决 17） ----------------

#: edge-tts 的 `WordBoundary` 事件直传服务原值，单位是 **100ns tick**（`/1e7` 才是秒）。
#: 差七个数量级的错误不会报错，只会让字幕在第一帧之前就全部跑完 —— 所以换算只许在这一处做。
TTS_TICK_PER_SECOND = 1e7

#: 归一化口径。**词序列不含标点**（P2-0 实测：每镜丢的字数 == 正文里的标点数），
#: 所以"词 vs 稿子"的一切比对都必须先压到同一个形状上。不归一化的后果不是"差一点"，
#: 而是强调源（天然带 `，。`）**永远匹配不上** ⇒ 字幕上永远没有高亮，且没人报警。
#: 竖线 `｜` 也必须在这里剥：它是作者点强调的**标记**，服务不念它 —— 实测
#: `门诊新规｜全国执行。` 只回 4 个词（`_pipe_probe` 探针），留着它就比词表多 1 个字，
#: 于是每一条点了强调的稿子都必然归组失配、整片掉进退化支。
CAPTION_PUNCT_RE = re.compile(
    r"[\s，。、！？；：,.!?;:“”‘’\"'()（）【】《》〈〉~—–\-·・｜\|]+")

#: 句子级 cue 的切分点。逗号**不**断条：一条 cue 要能读完一个完整语义，
#: 逗号处断会让每句变成两到三次跳动，读的人眼睛要一直找。
SENTENCE_END_RE = re.compile(r"[。！？；!?;]")

#: 兜底切分（拿不到服务时序时）的词形：拉丁词与数字串成一节，其余一字一节。
FALLBACK_TOKEN_RE = re.compile(r"[A-Za-z0-9]+|.")


def caption_norm(text: str) -> str:
    """压成"词序列的形状"：去掉空白与标点，其余原样（`10月` 不许被压成 `月`）。"""
    return CAPTION_PUNCT_RE.sub("", text or "")


def _tick_to_sec(ticks) -> float:
    return round(float(ticks) / TTS_TICK_PER_SECOND, 3)


def words_from_events(events, duration):
    """服务原值 → `[{w, s, e}]`：tick 换算、夹单调、丢空词与越界词。

    两处要在取数面处理掉的形状，不能留给下游假设"数据是干净的"：
      · **相切**（P2-1 tick 级复算：五镜 106 个间隙里 33 处 `gap = 0.000000`，负数 0 处）——
        相邻词背对背排布是正常形状，所以夹的是 `s = max(s, prev_e)` 而不是加安全间隔。
        这一支今天**没有实测负空隙作依据**，属防御性：服务若改切分让词重叠，一条 `fromTo`
        的 start 就会排进前一条的退场里，逐词入场变成乱序闪，而且只在个别镜上发生。
        它在自测里由一条标注为合成的重叠事件证明会执行（`path_b_selftest.py`）；
      · 末词右沿比音频早 0.56–0.68s —— 这里**不**把末词拉长到镜尾，尾段留不给字幕，
        那是版式的事（法则 17 的底部留白口径），不是取数面的事。

    ``duration`` 给 `None` 表示"没有可信的音频时长"（ffprobe 不可用时的估算值不算可信），
    此时只夹单调不夹上界 —— 拿估算值去裁真数据会成批丢词。
    """
    out = []
    floor = 0.0
    for ev in events or []:
        word = (ev.get("text") or "").strip()
        if not word:
            continue
        ticks = int(ev.get("offset") or 0)
        start = max(_tick_to_sec(ticks), floor)
        end = _tick_to_sec(ticks + int(ev.get("duration") or 0))
        if duration is not None:
            end = min(end, float(duration))
        if end <= start:
            continue
        out.append({"w": word, "s": start, "e": end})
        floor = end
    return out


def words_from_text(text: str, duration: float) -> list:
    """降级支：**只降级时序，不降级"哪个词"**。

    词表由正文自己切（拉丁/数字成串、其余一字一节），时长按字符数比例摊到整段音频上。
    这里的"比例"和法则 5 禁止的那个"比例"不是一回事：这里分的是**没有外部时序数据时
    每个词该占多长**，被明令禁止的是**猜哪个词该被强调** —— 后者在两条支上都走同一个
    `match_accent`，所以降级不会改变画面上亮起来的是哪几个字。
    """
    tokens = FALLBACK_TOKEN_RE.findall(caption_norm(text))
    total = sum(len(t) for t in tokens)
    if not total:
        return []
    out, acc = [], 0.0
    span = float(duration)
    for i, tok in enumerate(tokens):
        start = round(acc, 3)
        acc += span * len(tok) / total
        end = round(acc, 3) if i < len(tokens) - 1 else round(span, 3)
        if end <= start:
            continue
        out.append({"w": tok, "s": start, "e": end})
    return out


def cues_from_words(text: str, words, duration: float) -> list:
    """把词按**原文句子标点**归成 cue：`{text, start, end, words}`。

    文本取原文那一段（带标点 —— 那是给人读的），时间取该段首词 start / 末词 end。
    归组用**精确消费字符数**：一段 cue 的归一化长度必须 == 它吞掉的词的归一化长度之和。
    对不上就抛，不许按比例猜着分：猜开的结果是一条 cue 上屏的字和实际念的字不是同一串，
    而两边看起来都还是绿的（法则 5 同一立场）。
    """
    if not words:
        return []
    segments, buf = [], ""
    for ch in text:
        buf += ch
        if SENTENCE_END_RE.match(ch):
            segments.append(buf)
            buf = ""
    if buf.strip():
        segments.append(buf)
    cues, i = [], 0
    for seg in segments:
        need = len(caption_norm(seg))
        if not need:
            continue
        picked, got = [], 0
        while i < len(words) and got < need:
            picked.append(words[i])
            got += len(words[i]["w"])
            i += 1
        if got != need:
            raise EmitterError(
                f"字幕归组对不上：这一段 {seg!r} 归一化 {need} 字，词表给到 {got} 字 —— "
                "词序列与稿子不是同一份（缓存脏了或服务切分变了），不能猜着分")
        cues.append({"text": seg.strip(), "start": picked[0]["s"], "end": picked[-1]["e"],
                     "words": picked})
    if i != len(words):
        raise EmitterError(
            f"词表多出 {len(words) - i} 个词没有归属的 cue（稿子末尾没有句读？）—— "
            "这些字上了屏也没人念，宁可拒编")
    return cues


def match_accent(words, source: str) -> list:
    """强调三源（`onscreenAccent` / `｜` 切分 / 数字+单位）与词表做**精确子串匹配**。

    匹配不上返回空 = 不高亮。**禁止按比例猜**（法则 5）：猜中的强调会挂在没念过的词上，
    画面与配音对不上而两道门禁都还是绿的。
    两条口径细则：① 源要先归一化（词里没有标点，源里通常有）；② **词内不切** ——
    源必须被整词覆盖，`国执` 不算命中 `全国执行`，因为半个字的强调比没有更难看。
    """
    needle = caption_norm(source)
    if not needle:
        return []
    hay = "".join(w["w"] for w in words)
    pos = hay.find(needle)
    if pos < 0:
        return []
    out, acc = [], 0
    for word in words:
        nxt = acc + len(word["w"])
        if acc >= pos and nxt <= pos + len(needle):
            out.append(word)
        acc = nxt
    return out


def cue_accent_words(cue, scene) -> list:
    """一条 cue 里该亮起来的词 —— 三个来源，取**第一个匹配得上的**，匹配不上就不亮。

    优先级抄 `pick_accent`（屏上位用的就是这一套）：① 作者点的 `｜`，② 原文里的
    "数字+单位"，③ 屏句的强调段。字幕轨不许自定第二套口径 —— 两处不一致的表现是同一支
    片子里标题亮 `10月`、字幕亮别的词，每一处单看都"合理"，合起来像 bug 而无法归因。

    ③ 只在**屏句真被这一镜念出来**时才亮：`onscreen` 不进正文（`synthesize_audio` 只念
    `body`），所以大多数稿子里它匹配不上，返回空是正常结果而不是失败。
    只在 `cue["words"]` 这一段里匹配，不在整镜词表里匹配 —— 否则同一个短语在两句里出现，
    亮的是第一句而第二句也跟着亮。
    """
    words = (cue or {}).get("words") or []
    if not words:
        return []
    text = (cue or {}).get("text") or ""
    if ONSPLIT in text:
        head, tail = (part.strip("，,、 ：:") for part in text.split(ONSPLIT, 1))
        if head and tail:
            hits = match_accent(words, tail)
            if hits:
                return hits
    m = NUMBER_UNIT_RE.search(text)
    if m and m.group(2):
        hits = match_accent(words, m.group(0))
        if hits:
            return hits
    source = caption_norm((scene or {}).get("onscreenAccent") or "")
    return match_accent(words, source) if source else []


def cue_cache_key(text: str, voice: str) -> str:
    """缓存键 = (归一化正文, 音色)。改一个字、换一个音色都必须重配 ——
    拿旧 cues 配新稿会让字幕和配音对不上，而 mp3 与 cues.json **两边都还是绿的**。
    """
    digest = hashlib.sha256(f"{caption_norm(text)}|{voice}".encode("utf-8")).hexdigest()
    return digest[:16]


CUES_NAME = "cues.json"
CUES_SCHEMA = "hf-cues/1"


def collect_cues(scene_cues, durations, line_chars, max_lines=CAPTION_MAX_LINES):
    """把逐镜 cue 平移成全片 `(start, end, text)` 列表，交给 ASS / WebVTT 两条出口。

    入参从"逐镜字幕文件"换成取数面交出的结构 —— 一处真源。旧实现读 `scene_i.vtt`
    再按时间轴行正则解析，那个文件其实是 **SRT 体**（7.2.8 的 `SubMaker` 只有 `get_srt`），
    文件名一直在骗人。行宽与行数上限见 `caption_line_chars` / `split_cue`。
    """
    cues = []
    start = 0.0
    for scene, dur in zip(scene_cues, durations):
        for cue in scene:
            # 平移后夹到本分镜区间内, 防止跨场景字幕重叠
            s = min(start + cue["start"], start + max(0.0, dur - 0.2))
            e = min(start + cue["end"], start + dur)
            if e - s < 0.15:
                e = min(s + 0.8, start + dur)
            cues.extend(split_cue(s, e, caption_display_text(cue["text"]),
                                  line_chars, max_lines))
        start += dur
    return cues


def caption_display_text(text: str) -> str:
    """上屏文本：把服务不发的标点里**该显示**的那些留着，压掉连续空白与强调标记。

    单独一个函数是因为 cue 的 `text` 来自原文（带标点），而词序列不带 —— 两者不能混用，
    混用的表现是字幕少了逗号句号，读起来像电报。
    `｜` 反过来要**去掉**：它既不进词表（服务不念）也不该上屏（观众看字幕不需要知道
    作者在哪里点了强调）。cue 自己的 `text` 保留它 —— `cue_accent_words` 那一支 ① 要读。
    """
    return " ".join((text or "").replace(ONSPLIT, "").split())



def aigc_badge_font_size(w: int, h: int) -> int:
    """AIGC 角标字号 = ⌈画面**最短边** × 5% ÷ 实测字面率⌉, 也就是"擦到线上"。

    两条容易踩空的量纲, 都在这里处理:

    1. **按最短边, 不按高度**。国标写的是"画面最短边的 5%": 竖屏 1080×1920 最短边是
       宽 1080(线 = 54px), 横屏 1920×1080 最短边反过来是**高** 1080 —— 拿高度当基准
       写死会在横屏上算错。
    2. **字号 ≠ 字高**。ASS 的 FontSize 是 em 高度, 国标量的是字形实际高度, 中间差
       一个实测字面率(0.729, 见 AIGC_LABEL_GLYPH_RATIO)。1080 短边 → 54px 线 →
       FontSize = ⌈54 / 0.729⌉ = **75** → 字芯 54.7px = 最短边 **5.06%**。

    **为什么是 ceil 而不是 round**: round(54 / 0.729) = 74 → 字芯 53.9px, 比线低
    0.1px。取整风格在这里不是审美问题, 四舍五入会直接把片子弹到合规线以下,
    而且不报错 —— 擦边只许向上。

    残余风险(如实写): 0.729 是**这一台机器、这一个字体、这一个分辨率**上量来的,
    不是通用常数。现在字号贴线, 一旦字体回退就没人兜住(见 AIGC_LABEL_GLYPH_RATIO
    的 ⚠️); 换 pack / 换字体 / 换机器后必须重量一次(成片取一帧, 量左下角白色字芯的
    纵向像素数 ÷ FontSize)。`aigc.json` 里落了 font_size_px / glyph_height_px /
    short_side_px / margin_v_px, 对着 contact-sheet.jpg 第 1 镜就能核。
    """
    return max(1, math.ceil(min(w, h) * AIGC_LABEL_FLOOR_FRAC / AIGC_LABEL_GLYPH_RATIO))


def aigc_badge_outline(fs: int) -> int:
    """角标描边厚度 = round(字号 / AIGC_LABEL_OUTLINE_EM_DIV), 下限 1px。

    从 build_ass 的内联表达式提成函数, 不是为好看: **自测要用同一个数算墨迹边界**
    (aigc_badge_ink_bounds), 描边既是画出来的东西也是几何量, 两处各写一遍迟早会
    算出两个答案。
    """
    return max(1, int(round(fs / AIGC_LABEL_OUTLINE_EM_DIV)))


def aigc_badge_ink_bounds(w: int, h: int, mv: int) -> tuple[float, float]:
    """底边距为 mv 时, 角标**墨迹**(字芯 + 描边 + 阴影)的 y 上界与下界。

    ASS 对底部对齐的 MarginV 指的是**行盒底到画面底**, 既不是字芯底也不是墨迹底,
    这三层换算全部在这里做, 不许在调用方各补一次:

    ```
    行盒底 = h − mv
    字芯底 = 行盒底 − 下伸部空白(实测 8px, 见 AIGC_LABEL_LINE_SLACK_PX)
    字芯顶 = 字芯底 − 字号 × 字面率
    墨迹顶 = 字芯顶 − 描边            墨迹底 = 字芯底 + 描边 + 阴影(阴影只朝右下)
    ```

    模型对真渲染复测过(2026-09-29, news-policy 1080×1920, **当前取值** mv=303, 命令见
    `verify_aigc_badge.py` 与其验证记录 §2.3): 同一份 ASS 烧与不烧同一帧相减, 实测墨迹
    y **1549–1615**、白色字芯 **1555–1609**(55px); 本函数报 1549.3–1615.0 —— 上侧差
    0.3px(抗锯齿)、下侧 0.0px。**不扣下伸部空白**的旧模型在同一个 mv 上报 1557.3–1623.0,
    整整低 8px —— 旧实现就是带着这 8px 选出 mv=311, 自称"上侧留 13px"而实画只有 5px。
    """
    fs = aigc_badge_font_size(w, h)
    ol = aigc_badge_outline(fs)
    glyph_bottom = h - mv - AIGC_LABEL_LINE_SLACK_PX
    return (glyph_bottom - fs * AIGC_LABEL_GLYPH_RATIO - ol,
            glyph_bottom + ol + AIGC_LABEL_SHADOW_PX)


def aigc_badge_band_bounds(w: int, h: int) -> tuple[int, int]:
    """把角标整块墨迹塞进"内容禁入线之下、字幕块顶之上"这条带, 解出 mv 的上下界。

    返回 (下界 lo, 上界 hi) —— **是像素底边距的允许区间, 不是 y 坐标**; hi < lo 就是
    这条带装不下(横屏必然如此, 见 aigc_badge_margin_v)。

    ```
    字幕块顶 = h − 字幕底边距 − 封顶行数 × 字幕字号
    内容下界 = h × (1 − layout_selfcheck.CAPTION_RESERVE_CQH/100)      # 20cqh → 0.80
    带顶约束 墨迹顶 ≥ 内容下界 + G  →  mv ≤ h − 空白 − 字芯 − 描边 − 内容下界 − G
    带底约束 墨迹底 ≤ 字幕块顶 − G  →  mv ≥ h − 空白 + 描边 + 阴影 − 字幕块顶 + G
    ```

    取整一律向带内收(hi 向下取整、lo 向上取整): 边界算窄了角标只是挪几个像素,
    算宽了就是压字。
    """
    fs = aigc_badge_font_size(w, h)
    ol = aigc_badge_outline(fs)
    glyph = fs * AIGC_LABEL_GLYPH_RATIO
    gap = AIGC_LABEL_BAND_GAP_PX
    content_floor = h * (1 - layout_selfcheck.CAPTION_RESERVE_CQH / 100)
    subtitle_top = (h - int(h * ASS_MARGIN_BOTTOM_H_FRAC)
                    - CAPTION_MAX_LINES * caption_font_size(h))
    lo = math.ceil(h - AIGC_LABEL_LINE_SLACK_PX + ol + AIGC_LABEL_SHADOW_PX
                   - subtitle_top + gap)
    hi = math.floor(h - AIGC_LABEL_LINE_SLACK_PX - glyph - ol - content_floor - gap)
    return lo, hi


def aigc_badge_margin_v(w: int, h: int) -> int:
    """左下角标距**画面底边**的 MarginV —— 由带上下界取中, 不许手填像素。

    竖屏 1080×1920 用实测常量全程解(aigc_badge_band_bounds, 与 build_ass 烧的同一套):

    ```
    字幕块顶 1628 · 内容下界 1536 · 可用带 92px
    角标自身  字芯 54.675 + 上下描边 10 + 阴影 1 = 65.7px, 再加行盒下空白 8px
    lo = 1920 − 8 + 5 + 1 − 1628 + 8 = 298      hi = 1920 − 8 − 54.675 − 5 − 1536 − 8 = 308
    mv = (298 + 308) / 2 = 303  →  墨迹 1549.3–1615, 上侧 13px / 下侧 13px
    ```

    **取中而不是贴边**: 带内只有 10px 可调, 贴任何一侧就把那一侧压到判据线 8px 上
    (抗锯齿再吃 1px 即红), 而另一侧白送 10px; 取中让两侧各 13px, 离红线都有 5px 缓冲,
    也让自测能锁住"两侧各 ≥ AIGC_LABEL_BAND_GAP_PX"这个真判据。

    旧值 311 是"字幕块顶 − 固定间隙"直接反推出来的, 没扣行盒下空白, 于是模型里的
    13px 在画面上只有 5px(1549.3 − 8 = 实画 1541, 距内容下界 1536)。2026-09-29 复测改正。

    带装不下时(横屏 1920×1080: 带 51px < 墨迹 65.7px, lo=171 > hi=140)返回 **lo** ——
    即"宁可压进底部 20cqh 的内容预留带, 也不压 burned 字幕": 字幕压角标是两层文字
    叠在一起、两边都读不出, 而内容预留带本来就允许在极端画面上被侵占(代价写进
    `build_ass` 与本函数返回值的实测记录, 不靠注释兜)。
    """
    lo, hi = aigc_badge_band_bounds(w, h)
    if lo > hi:
        return lo
    return (lo + hi) // 2


def aigc_badge_seconds(total_seconds: float) -> float:
    """角标持续时长 = min(AIGC_LABEL_ON_SECONDS, 全片时长)。

    截到开场 4 秒是取舍; **向片长取小**不是取舍而是算术 —— 事件终点不许越过最后一
    帧。不足 AIGC_LABEL_MIN_SECONDS 的短片这里原样返回, 由 mux_and_burn 在唯一出口
    停机, 免得两条路径各挡一遍、各说一套。
    """
    return min(AIGC_LABEL_ON_SECONDS, total_seconds)


def build_ass(cues, w: int, h: int, font: str = "Microsoft YaHei",
              aigc_text: str | None = AIGC_LABEL_TEXT,
              aigc_seconds: float = 0.0) -> str:
    """显式写 PlayRes, 字号按输出高度推导。

    ⚠️ 不要用 subtitles 的 force_style 调字号: libass 读 VTT 时脚本坐标默认
    只有 288 高, FontSize=36 会被放大到画面 12% 高, 竖屏上直接溢出屏幕。

    AIGC 显式标识: `aigc_text` 非空且 `aigc_seconds` > 0 时, 额外挂一条**开场**的
    `AIGC` 样式事件(Alignment 1 = 左下角, Layer 1 压在字幕之上), 满足《标识办法》
    § 4-四 的"起始画面"与国标"持续 ≥ 2 秒"; 时长由调用方按 aigc_badge_seconds() 给。
    为什么落左下角(实测 news-coral / news-policy 各版式): 底部 20cqh 是 frame.md
    法则 1 给字幕留的禁入带, `layout_selfcheck` 以 CAPTION_RESERVE_INTRUDED 守它,
    所以 y≥1536 **从来没有版式内容**; 两行字幕块顶实测 1628 —— 1536–1628 这 92px
    是全片唯一既不属于内容也不属于字幕的空档(推导见 aigc_badge_margin_v)。
    代价(如实写): 左下角正是抖音标题/头像那一层的叠加区, 平台 UI 会盖在角标上面
    —— 旧实现落左上角避开的就是这一层, 现在按用户取舍换过来了。
    换 pack / 换字号 / 改字幕行数后这条带要重算, 别默认它永远不撞。
    """
    aigc_fs = aigc_badge_font_size(w, h)
    header = ASS_HEADER.format(
        w=w, h=h, font=font,
        fs=caption_font_size(h),
        ol=max(2, int(round(h / ASS_OUTLINE_H_FRAC))),
        ml=int(w * ASS_MARGIN_W_FRAC), mr=int(w * ASS_MARGIN_W_FRAC),
        mv=int(h * ASS_MARGIN_BOTTOM_H_FRAC),
        aigc_fs=aigc_fs,
        aigc_ol=aigc_badge_outline(aigc_fs),
        aigc_sh=AIGC_LABEL_SHADOW_PX,
        aml=int(w * AIGC_LABEL_MARGIN_W_FRAC), amr=int(w * AIGC_LABEL_MARGIN_W_FRAC),
        amv=aigc_badge_margin_v(w, h),
    )
    events = [
        f"Dialogue: 0,{ass_time(s)},{ass_time(e)},Default,,0,0,0,,{text}"
        for s, e, text in cues
    ]
    if aigc_text and aigc_seconds > 0:
        events.insert(0, f"Dialogue: 1,{ass_time(0)},{ass_time(aigc_seconds)},"
                         f"AIGC,,0,0,0,,{aigc_text}")
    return header + "\n".join(events) + "\n"


# ------------------------- 场景解析 -------------------------
def parse_input(text: str):
    """返回场景列表: [{"title", "body", "voice", "onscreen", "onscreenAccent", ...extras}]

    JSON 场景里的其它键原样透传, 供变量显式覆盖与 --layout 点名; `"onscreen"` 与
    markdown 的 `屏:` 行同义, 两条路都过 `check_onscreen`(不接受只校验一半的来源)。

    `屏:` 行**不进正文**: 正文会被配音逐字念出来(见 `synthesize_audio`), 屏句只上屏。
    把它混进正文就等于把同一句话既念一遍又打一遍 —— 判据 5 要从结构上成立,
    取材处就必须先分成两条通道。
    """
    text = text.strip()
    if not text:
        return []
    # 尝试 JSON
    if text.lstrip().startswith("["):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = None  # 不是合法 JSON, 落到纯文本分支
        if data is not None:
            scenes = []
            for index, item in enumerate(data, start=1):
                if not isinstance(item, dict):
                    raise EmitterError(f"JSON 场景必须是对象, 收到: {item!r}")
                scene = dict(item)
                scene["body"] = scene.get("body") or scene.get("text") or ""
                scene["title"] = scene.get("title")
                scene.setdefault("voice", None)
                scenes.append(normalize_onscreen(scene, index))
            return scenes

    scenes = []
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block:
            continue
        lines = [l.rstrip() for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        shot_no = len(scenes) + 1
        marked = [(i, m.group("text")) for i, l in enumerate(lines)
                  if (m := ONSCREEN_LINE_RE.match(l.strip()))]
        if len(marked) > 1:
            raise EmitterError(
                f"第 {shot_no} 镜写了 {len(marked)} 条 屏: 行, 只许一条: 屏句是这一镜"
                f"屏幕上那**一句**话。第 {marked[0][0] + 1} 行 {marked[0][1]!r} 与"
                f"第 {marked[1][0] + 1} 行 {marked[1][1]!r} 请先合成一句, 或者拆成两镜"
            )
        if marked:
            at, raw = marked[0]
            lines = lines[:at] + lines[at + 1:]
            if not lines:
                raise EmitterError(
                    f"第 {shot_no} 镜只有屏句没有正文: 屏句不进配音, 这一镜会没有可读的台词"
                )
        # 段首短行当标题
        if len(lines) > 1 and len(lines[0]) <= TITLE_LINE_MAX_CHARS \
                and not lines[0].endswith(SENTENCE_END):
            scene = {"title": lines[0], "body": "\n".join(lines[1:]), "voice": None,
                     "onscreen": marked[0][1] if marked else None}
        else:
            scene = {"title": None, "body": "\n".join(lines), "voice": None,
                     "onscreen": marked[0][1] if marked else None}
        scenes.append(normalize_onscreen(scene, shot_no))
    return scenes


# ------------------------- 文案推导 (只切真句, 不造事实) -------------------------
def clauses(text: str) -> list[str]:
    return [c.strip() for c in CLAUSE_SPLIT_RE.split(text or "") if c.strip()]


def flatten(text: str) -> str:
    return " ".join((text or "").split())


def strip_quotes(text: str) -> str:
    stripped = (text or "").strip()
    if stripped and stripped[0] in QUOTE_OPENERS:
        stripped = stripped[1:]
    if stripped and stripped[-1] in QUOTE_CLOSERS:
        stripped = stripped[:-1]
    return stripped.strip()


def phrase_label(clause: str, label_max: int, body_max: int) -> tuple[str, str]:
    """把一个分句切成 (小标题, 说明) —— 只在**真标点**处切, 而且两头都得能读。

    切不出合规两头时返回 ("", 整句), 调用方据此判定这句不适合行式版式。
    绝不截断句子、也不替作者写小标题来凑一行 (frame.md 法则 5: 不编造)。
    """
    parts = LABEL_SPLIT_RE.split(clause, maxsplit=1)
    if len(parts) == 2:
        head, body = parts[0].strip(), parts[1].strip()
        if head and body and len(head) <= label_max and len(body) <= body_max:
            return head, body
    return "", clause


def sub_phrases(clause: str) -> list[str]:
    """把分句按句内标点再切一层, 只留非空小句 —— 数字说明行的取材单位。"""
    return [p for p in (s.strip("，,、 ") for s in LABEL_SPLIT_RE.split(clause)) if p]


#: stat 小标题的下限长度 —— 短于此就不是"标题", 只是半截词
STAT_LABEL_MIN_CHARS = 3
#: 不能用作小标题开头的字(连接词/副词/指示词/介词)。以它们开头, 说明这段文字是
#: 被数字切断后剩下的半截句子, 上屏会读成病句 —— t001 第 4 镜实测:
#: "比42万更可惜的" 砍掉数字得到 "更可惜的", 正是这一类。
DANGLING_HEAD_CHARS = "比更最较越才就也还又只但而或和与及把被的是那这其之"


def stat_label(clause: str, token: str) -> str | None:
    """这个数字的屏侧小标题 = 含该数字的小句里**去掉数字本身**后的一段连续原文。

    三条硬规则, 任何一条不满足就返回 `None`(上层据此判"这一镜进不了 stat"):

    1. 不许含这个数字。stat 会把数字用 30cqw 打在旁边, 小标题里再写一遍就是同一
       句话讲两次(t001 实测: 巨号"42万"下面写着"比42万更可惜的")。
    2. 必须是连续一段。数字前后都有余文时只取一侧, 绝不把两侧粘起来 —— 粘出来
       就是改写原文("比42万更可惜的" 粘不出句子)。
    3. 长度与开头见 `STAT_LABEL_MIN_CHARS` / `DANGLING_HEAD_CHARS`。

    优先取数字**后面**那段: 中文新闻里数字后面跟的往往是它的名词
    ("3700元养老金" → "养老金"), 后面为空才取前面("账户累计42万" → "账户累计")。
    """
    for phrase in sub_phrases(clause) + [clause]:
        at = phrase.find(token)
        if at < 0:
            continue
        for side in (phrase[at + len(token):], phrase[:at]):
            side = side.strip("，,、 ")
            if len(side) >= STAT_LABEL_MIN_CHARS and side[0] not in DANGLING_HEAD_CHARS:
                return side
    return None


def split_number(token: str) -> tuple[str, str]:
    """'1.2万亿' → ('1.2', '万亿'); 没单位就留空。"""
    m = NUMBER_UNIT_RE.search(token)
    if not m:
        return "", ""
    return m.group(1), (m.group(2) or "")


def extract_facts(text: str) -> list[dict]:
    """从文本里取**源数据自带**的数字: [{value, unit, label}]。

    label 由 `stat_label` 从原文切, 切不出合规小标题时是 `None` —— 这时这个数字
    仍然算"事实"(计数、报错信息都用它), 但 stat 版式会因为填不出 `label` 而落选。
    宁可少一个数据版式, 也不在屏上把同一个数字写两遍, 更不替当事人编一个小标题。
    """
    facts = []
    seen = set()
    for clause in clauses(text):
        for m in NUMBER_UNIT_RE.finditer(clause):
            value = m.group(1)
            if value in seen:
                continue
            seen.add(value)
            facts.append({"value": value, "unit": m.group(2) or "",
                          "label": stat_label(clause, m.group(0))})
    return facts


def scene_fact_text(scene: dict) -> str:
    """找数字的范围 = 标题 + 正文。新闻标题往往装着全文最狠的那个数字
    (t001 第 4 镜标题"比42万更可惜的，是那21年"、正文里一个数字都没有),
    只看正文会让 stat 版式对这种分镜永久失效。用句号拼接保证分句边界不糊。

    注意: 从标题取到数字 ≠ 一定能上 stat —— stat 还要每个数字配得出独立小标题
    (见 stat_label)。t001 第 4 镜的两个数字都配不出, 所以那一镜最终落到 story,
    这是"少一个数据版式"与"屏上把 42 万写两遍"之间的取舍, 取前者。"""
    return "。".join(flatten(scene.get(key)) for key in ("title", "body")
                     if flatten(scene.get(key)))


def check_onscreen(raw, shot_no: int) -> tuple[str, str | None]:
    """校验并切开屏句, 返回 (整句, 强调段|None)。这是判据 5 的结构闸门。

    屏句 = 屏幕上那一句**整句**陈述, 也是所有整句型屏上位(story 屏句位、hook 辅助
    行、closer 行动句)唯一的取材处。正文走配音、屏句走上屏, 两条通道不交叉 ⇒
    屏上的整句永远不可能是被念出来的那一句。

    每一条不合规都**停机**而不是回落默认值: 屏句是作者的话, 发射器替作者挑一句
    就是替当事人决定"这条新闻的结论是什么"。
    """
    text = flatten(raw)
    if not text:
        raise EmitterError(f"第 {shot_no} 镜写了 屏: 但内容是空的")
    marks = text.count(ONSPLIT)
    if marks > 1:
        raise EmitterError(
            f"第 {shot_no} 镜屏句 {text!r} 有 {marks} 个 {ONSPLIT} 标记, 只许一个: "
            "它点出的是这一镜唯一要贴在珊瑚片上的那段词"
        )
    if marks:
        # 标记两侧的标点会被吃掉(屏上 lead 与珊瑚片是紧贴的两段), 所以要点在不含
        # 标点的词界上: "今天查一下｜社保" ✓, "没人告诉他，｜他一直没问" 会丢一个逗号。
        head, accent = (part.strip("，,、 ：:") for part in text.split(ONSPLIT, 1))
        if not head:
            raise EmitterError(
                f"第 {shot_no} 镜屏句 {text!r} 的 {ONSPLIT} 点在句头: 前面必须有词, "
                "整句都贴珊瑚片等于没有重点"
            )
        if len(accent) < ONSPLIT_ACCENT_MIN:
            raise EmitterError(
                f"第 {shot_no} 镜屏句的强调段 {accent!r} 少于 {ONSPLIT_ACCENT_MIN} 字: "
                f"珊瑚片里一个字符看着像没打完。把词点全, 或去掉 {ONSPLIT} 用整句"
            )
        whole, accent_out = head + accent, accent
    else:
        whole, accent_out = text, None
    if len(whole) < ONSCREEN_MIN_CHARS:
        raise EmitterError(
            f"第 {shot_no} 镜屏句 {whole!r} 只有 {len(whole)} 字, 不足 {ONSCREEN_MIN_CHARS} 字: "
            "这么短的东西是标签位(小标题/数值)的活儿, 不是一句屏上陈述"
        )
    if len(whole) > ONSCREEN_MAX_CHARS:
        raise EmitterError(
            f"第 {shot_no} 镜屏句 {whole!r} 有 {len(whole)} 字, 超过 {ONSCREEN_MAX_CHARS} 字: "
            "屏句位 4.4cqw 两行读完一句的容量就在这里, 再长就变成『读一段』。"
            "挑短句, 或者这一镜改用 catalog/rail 的行式位分条呈现"
        )
    return whole, accent_out


def normalize_onscreen(scene: dict, shot_no: int) -> dict:
    """把屏句写回场景: `onscreen` = 去标记整句, `onscreenAccent` = 强调段|None。

    作者没写屏句 ⇒ 两个键都是 None ⇒ 整句型屏上位填不满 ⇒ 这一镜自动不进
    story/hook 辅助行/closer 行动句(见 `choose_layout`), 由条目或数字版式接手。
    """
    raw = scene.get("onscreen")
    if raw is None:
        scene["onscreen"] = None
        scene["onscreenAccent"] = None
    else:
        scene["onscreen"], scene["onscreenAccent"] = check_onscreen(raw, shot_no)
    return scene


def pick_accent(text: str) -> tuple[str, str]:
    """挑出强调段, 返回 (余下部分, 强调段)。断点只有三个来源, 且都落在真词界上:

    1. 作者点的 `｜`(屏句与标题行共用这一个标记);
    2. 原文里的"数字+单位"(数字天然是这一镜的重点);
    3. 两者都没有 ⇒ `(整句, "")`, 由上层判定"这一镜没有可强调的一段"。

    第 3 条是本次修正的核心。旧实现到这里兜底切固定字数尾巴(`text[-4:]`), 把
    "困住半辈子" 切成 "困" + 珊瑚片里的 "住半辈子" —— 切在词中间的珊瑚片正是
    t001 最难看的一处。宁可不贴片, 也不制造病句断点。
    """
    if not text:
        return "", ""
    if ONSPLIT in text:
        head, accent = (part.strip("，,、 ：:") for part in text.split(ONSPLIT, 1))
        if head and accent:
            return head, accent
    m = NUMBER_UNIT_RE.search(text)
    if m and m.group(2):
        accent = text[m.start(): m.end()]
        lead = (text[: m.start()] + text[m.end():]).strip("，,、 ")
        if lead:
            return lead, accent
    return text, ""


def split_headline(text: str) -> tuple[str, str, str] | None:
    """把标题切成 (第一行, 第二行前段, 第二行强调)。切不出两行就返回 None。"""
    head = flatten(text)
    if len(head) <= HOOK_LINE_CHARS:
        return None
    cut = HOOK_LINE_CHARS
    # 在第一行窗口里找最后一个自然断点, 避免把词拦腰切断
    for i in range(min(len(head), HOOK_LINE_CHARS + 2), 1, -1):
        if head[i - 1] in HEAD_BREAK_CHARS:
            cut = i
            break
    top = head[:cut].strip(HEAD_BREAK_CHARS)
    rest = head[cut:].strip(HEAD_BREAK_CHARS)
    if not rest:
        return None
    lead, accent = pick_accent(rest)
    return top, lead, accent


def scene_items(scene: dict) -> list[dict]:
    """取条目列表: JSON 的 items 优先, 否则把**能诚实切成 (小标题, 说明)** 的分句做成条目。

    切不出小标题的分句不进条目候选 —— 它只适合 story/stat 这类整句版式。
    rail/catalog 的行内已经印死了 01/02/03, 所以行标题必须是原文里真有的短语。
    """
    raw = scene.get("items")
    if isinstance(raw, list) and raw:
        items = []
        for entry in raw:
            if not isinstance(entry, dict):
                raise EmitterError(f"items 元素必须是对象, 收到: {entry!r}")
            items.append({"label": flatten(entry.get("label")), "value": flatten(entry.get("value"))})
        return items
    items = []
    for clause in clauses(scene.get("body", "")):
        head, body = phrase_label(clause, ROW_LABEL_MAX_CHARS, ROW_BODY_MAX_CHARS)
        if head:
            items.append({"label": head, "value": body})
    return items


def rail_ready(items: list[dict]) -> bool:
    """rail 的右值是 5cqw 大字且 max-width 44cqw (≈8 字): 长句会撑破, 只放短键值对。"""
    return len(items) >= MIN_RAIL_ITEMS and all(
        len(item["value"]) <= RAIL_VALUE_MAX_CHARS for item in items
    )


# ------------------------- 设计系统包 -------------------------
def pack_has_real_layout(style: str) -> bool:
    """这个 pack 有没有**真版式**(placeholder.html 之外至少一个 compositions/*.html)。

    只查文件在不在, 不解析契约 —— 给"哪些 pack 能渲染"这类盘点用, 未落地的 pack
    调 `load_style_pack` 会直接停机, 拿它做批量统计不合适。
    """
    comp_dir = os.path.join(pack_dir(style), "compositions")
    if not os.path.isdir(comp_dir):
        return False
    return any(f.endswith(".html") and f != f"{PLACEHOLDER_LAYOUT}.html"
               for f in os.listdir(comp_dir))


def ready_packs() -> list[str]:
    """当前可选出真版式的 pack 名单(顺序跟 `available_templates()`)。"""
    return [s for s in available_templates() if pack_has_real_layout(s)]


def load_style_pack(style: str) -> dict:
    """读 `<pack 根>/<style>/`: 宿主骨架 + 各版式契约（根按 `PACK_ROOTS` 顺序找，见 `pack_dir`）。

    ``placeholder.html`` 不进 ``layouts`` (D7): 它只是把三层目录凑齐的壳, 不是版式。
    跳掉之后若一个版式都不剩, 就在这里停 —— 报"这个 pack 还没有真版式 + 现在哪些有",
    而不是等配完音、发射到第 1 镜才抛"填不满任何版式"(那要白跑一趟网络与渲染)。
    """
    root_dir = pack_dir(style)
    host_path = os.path.join(root_dir, "host.html")
    comp_dir = os.path.join(root_dir, "compositions")
    if not os.path.isdir(root_dir):
        raise EmitterError(f"设计系统包不存在: {root_dir}")
    if not os.path.isfile(host_path) or not os.path.isdir(comp_dir):
        raise EmitterError(f"{root_dir} 缺少 host.html 或 compositions/")
    layouts = {}
    for file_name in sorted(os.listdir(comp_dir)):
        if not file_name.endswith(".html"):
            continue
        if file_name == f"{PLACEHOLDER_LAYOUT}.html":
            continue
        text = read_text(os.path.join(comp_dir, file_name))
        attr = VARIABLE_ATTR_RE.search(text)
        root = ROOT_COMPOSITION_ID_RE.search(text)
        if not attr:
            raise EmitterError(f"{file_name} 没有 data-composition-variables 契约")
        if not root:
            raise EmitterError(f'{file_name} 根节点缺少 <div id="root" data-composition-id="…">')
        try:
            contract = json.loads(html.unescape(attr.group("json")))
        except json.JSONDecodeError as exc:
            raise EmitterError(f"{file_name} 的变量契约不是合法 JSON: {exc}") from exc
        ground = ROOT_GROUND_RE.search(text)
        if not ground:
            raise EmitterError(
                f'{file_name} 的 #root 没有 `background: #rrggbb` 声明 —— '
                "发射器靠它判定地面明暗, 相邻镜头不换地面就会整片雷同"
            )
        ground_hex = ground.group("hex").lower()
        if ground_hex not in GROUND_TONE_BY_HEX:
            raise EmitterError(
                f'{file_name} 的地面色 {ground_hex} 不在设计系统色板里 (已知: '
                + ", ".join(sorted(GROUND_TONE_BY_HEX))
                + ")。要么把它加进 GROUND_TONE_BY_HEX 并说明归明/归暗, "
                  "要么改回色板色 —— 未登记的地面会让逐镜换色失效。"
            )
        layouts[file_name[: -len(".html")]] = {
            "name": file_name[: -len(".html")],
            "file_name": file_name,
            "path": os.path.join(comp_dir, file_name),
            "composition_id": root.group("id"),
            "ground_hex": ground_hex,
            "ground_tone": GROUND_TONE_BY_HEX[ground_hex],
            "variables": contract,
        }
    if not layouts:
        ready = ready_packs()
        raise EmitterError(
            f"{style} 还没有真版式: compositions/ 里只有 placeholder.html(占位壳)。"
            "占位版式不参与选择, 所以这一包现在**不可渲染**。"
            + (f"当前可渲染的 pack: {', '.join(ready)}。" if ready
               else "当前没有任何 pack 有真版式。")
            + " 处理: 换用可渲染的 pack, 或按 frame.md 的设计契约补出真 composition。"
        )
    # 编译包（path_c，带 spec.toml）走 HyperFrames 原生字幕轨；存量手发包（path_b）
    # 维持烧录 ASS。字幕收进合成是裁决 2 的落地，只对编译包开放，31 套存量片子节不变。
    return {"name": style, "dir": root_dir, "host": read_text(host_path),
            "compositions_dir": comp_dir, "layouts": layouts,
            "compiled": os.path.isfile(os.path.join(root_dir, "spec.toml"))}


def row_capacity(layout: dict) -> int:
    """版式固定行数: 契约里 itemN*/stepN* 的最大 N; 没有条目类变量就是 0。"""
    capacity = 0
    for var in layout["variables"]:
        match = INDEXED_VAR_RE.match(var["id"])
        if match:
            capacity = max(capacity, int(match.group(2)))
    return capacity


def contract_ids(layout: dict) -> set[str]:
    return {var["id"] for var in layout["variables"]}


# ------------------------- 变量填充 -------------------------
def fill_variables(layout: dict, scene: dict, ctx: dict) -> dict:
    """按版式契约逐条求值。任何一条填不出来 → EmitterError(说清是哪个版式哪个变量)。"""
    values = {}
    for var in layout["variables"]:
        values[var["id"]] = resolve_variable(var, layout, scene, ctx)
    return values


def resolve_variable(var: dict, layout: dict, scene: dict, ctx: dict):
    var_id = var["id"]
    # imagePath 是机器解析变量(commons_media 取图), 不走作者词链路: 有图给
    # work_dir 相对路径, 没图给空串(布局据此收起图位)。空串不落 coerce —— coerce
    # 拦的是"作者词填成空", 而"这一镜无图"是合法状态, 不是填不出来。
    if var_id == "imagePath":
        record = ctx.get("image_record")
        return flatten(str(record["local_path"])) if record else ""
    if var_id == "imageCredit":
        # 屏上署名行由 commons_media.attribution_text 拼: 作者 + 许可证, 24 字封顶,
        # 只削作者名且只削在词边界; 削不出整词就退到许可证 + 指向完整出处。
        record = ctx.get("image_record")
        return flatten(cm.attribution_text(record)) if record else ""
    # 1) 显式覆盖: JSON 场景里直接写了同名键, 或 CLI 给了同名 channel/source
    if var_id in scene and scene[var_id] is not None:
        return coerce(var, flatten(str(scene[var_id])), layout, var_id)
    if var_id in ctx.get("overrides", {}) and ctx["overrides"][var_id] is not None:
        return coerce(var, flatten(str(ctx["overrides"][var_id])), layout, var_id)

    # 2) 结构化推导
    derived = DERIVERS[var_id](scene, ctx, layout) if var_id in DERIVERS else None
    if derived is None:
        raise EmitterError(
            f"版式 {layout['name']} 的变量 “{var_id}”({var.get('label', '')}) 填不出来: "
            f"分镜文本没有足够信息, 又没在 JSON 里显式给出。"
            f"请给该分镜补 \"{var_id}\": \"…\", 或改用别的 --layout。"
        )
    return coerce(var, derived, layout, var_id)


def coerce(var: dict, value, layout: dict, var_id: str):
    """按契约声明的类型收口, 类型不符就停机(不静默兜 default, 避免假通过)。"""
    if var["type"] == "number":
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise EmitterError(f"{layout['name']}.{var_id} 需要数字, 得到 {value!r}") from exc
        bound = var.get("min")
        if bound is not None and number < float(bound):
            raise EmitterError(
                f"{layout['name']}.{var_id}={number} 小于契约下限 {bound} —— "
                "这一镜太短, 请合并分镜或加长文案"
            )
        bound = var.get("max")
        if bound is not None and number > float(bound):
            raise EmitterError(f"{layout['name']}.{var_id}={number} 大于契约上限 {bound}")
        return number
    text = flatten(str(value))
    if not text:
        raise EmitterError(f"{layout['name']}.{var_id} 的值是空字符串")
    return text


# ---- 各变量推导器: 返回 None 表示"填不出来", 由上层报错停机 ----
def _slot_seconds(scene, ctx, layout):
    return ctx["slot_seconds"]


def _ordinal(scene, ctx, layout):
    return ctx["shot_ordinal"]


def _kicker(scene, ctx, layout):
    return scene.get("kicker") or ctx.get("kicker") or layout_default(layout, "kicker")


def _title(scene, ctx, layout):
    """`title` 有两种身份, 回落规则必须分开, 不能一条规则盖两个位。

    - **story 的领句**: 只认作者写的标题行。旧回落"从正文偷第一句当标题"已删
      (那是把念出来的话再打一遍, 判据 5); 也不许回落到版式 `default` —— `default` 是
      "标题位长这样"的单文件预览词, 拿它当领句等于发射器替这条新闻下了结论。
      作者没写 ⇒ 返回 None ⇒ story 这一镜落选, 由条目/数字版式接手。
    - **rail / catalog 的小节标签**: 「三个数」「三步做完」这类是**版式词汇**而不是事实,
      允许回落 `default`(README §2 "设计词"那一行说的就是这两个位 + `kicker`/`tone`)。
    """
    authored = flatten(scene.get("title"))
    if authored:
        return authored
    if layout["name"] in TITLE_LABEL_LAYOUTS:
        return layout_default(layout, "title")
    return None


def _headline_parts(scene: dict):
    """hook 的三行大字 = 作者标题行的切分结果(只看标题, 不碰正文)。三个推导器共用。"""
    return split_headline(scene.get("title") or "")


def _head_top(scene, ctx, layout):
    parts = _headline_parts(scene)
    return parts[0] if parts else None


def _head_bottom_lead(scene, ctx, layout):
    parts = _headline_parts(scene)
    return parts[1] if parts and parts[1] else None


def _head_accent(scene, ctx, layout):
    parts = _headline_parts(scene)
    return parts[2] if parts and parts[2] else None


def _scene_facts(scene: dict) -> list[dict]:
    """本镜可用数字全集 (标题+正文)。六个数字类推导器共用, 不各写一遍取法。"""
    return extract_facts(scene_fact_text(scene))


def _fact_field(facts: list[dict], index: int, field: str):
    """取第 index 个数字的某个字段, 空串与越界一律返回 None。

    返回 None 会让上层判定"这个版式填不满"从而换版式或停机 ——
    宁可不选 stat, 也不给没有单位的数字安一个假单位。
    """
    if len(facts) <= index:
        return None
    return facts[index][field] or None


def _onscreen_phrase(scene, ctx, layout):
    """整句型屏上位的唯一取材处 = 屏句(frame.md 法则 6)。

    取代旧的 `_first_body_clause`(support/lead)与 `_detail`(story 支撑句): 那两个
    都从正文取整句, 而正文会被配音念完 —— hook 辅助行与 story 支撑句因此一直在
    把字幕内容二次上屏。给不出屏句就返回 None, 发射器不去正文里挑一句冒充。
    """
    return scene.get("onscreen")


def _tone(scene, ctx, layout):
    """story 的地面明暗 = 与上一镜**相反**。

    为什么不用镜头奇偶: 奇偶只数镜号, 而固定地面的版式(catalog/closer=ink,
    rail/stat=cream)本身就会占掉某一奇偶 —— 实测会出现"暗底 catalog 后接暗底
    story", 相邻两镜一片雷同。跟着上一镜的实际地面翻转, 才是"三段混调"里
    唯一可机械判定的那部分 (frame.md §5 三段混调: 同一系统换地面, 不做三套 token)。
    第一镜没有上一镜 → 用主地面 cream 开场, 与 hook 的 ink 形成第一处反差。
    """
    prev = ctx.get("prev_ground_tone")
    if prev == TONE_LIGHT:
        return TONE_DARK
    if prev == TONE_DARK:
        return TONE_LIGHT
    return TONE_LIGHT


def _value(scene, ctx, layout):
    return _fact_field(_scene_facts(scene), 0, "value")


def _unit(scene, ctx, layout):
    """单位必须来自原文。版式自带的 default("元") 只是单版式预览用占位,
    链路里绝不能拿它兜底 —— 给没有单位的数字安上"元"就是编造事实。"""
    return _fact_field(_scene_facts(scene), 0, "unit")


def _label(scene, ctx, layout):
    return _fact_field(_scene_facts(scene), 0, "label")


def _compare_value(scene, ctx, layout):
    return _fact_field(_scene_facts(scene), 1, "value")


def _compare_unit(scene, ctx, layout):
    return _fact_field(_scene_facts(scene), 1, "unit")


def _compare_label(scene, ctx, layout):
    return _fact_field(_scene_facts(scene), 1, "label")


def _quote_body(scene, ctx, layout):
    """引文只认作者写的 `quote` 键。

    旧写法在没写 quote 时拿正文兜底, 再靠 `looks_quoted` 看首字符像不像引号来"自动
    认领"引文卡 —— 那等于把整段口播词裱进白卡, 判据 5 第一个破在这里。
    """
    source = scene.get("quote")
    if not source:
        return None
    text = strip_quotes(flatten(source))
    return text if len(text) >= QUOTE_MIN_CHARS else None


def _attribution(scene, ctx, layout):
    """归属只能来自数据: JSON 的 source/attribution, 或 --source, 或破折号后的落款。"""
    explicit = scene.get("attribution") or scene.get("source") or ctx.get("source")
    if explicit:
        return flatten(str(explicit))
    m = re.search(r"[—\-]{1,2}\s*([^—\-\n]+)$", scene.get("body", ""))
    return m.group(1).strip() if m else None


def _channel(scene, ctx, layout):
    return _attribution(scene, ctx, layout)


def _cta(scene, ctx, layout):
    """收口行动句主体 = 屏句去掉强调段的前半。

    旧实现取"正文末句"再 `pick_accent`, 于是最后一镜一边念着末句、一边把同一句
    打在屏上, 而且尾切还会造出词中间断开的珊瑚片。现在 closer 与 hook/story
    共用同一个取材处(屏句), 强调段只可能落在作者点的 ｜ 上。
    没写屏句 ⇒ None ⇒ 最后一镜进不了 closer; 写了屏句但没点强调段 ⇒ `ctaAccent`
    填不满 ⇒ 停机并点名 ctaAccent。
    """
    onscreen = scene.get("onscreen")
    if not onscreen:
        return None
    accent = scene.get("onscreenAccent")
    return onscreen[: len(onscreen) - len(accent)] if accent else onscreen


def _cta_accent(scene, ctx, layout):
    return scene.get("onscreenAccent")


def _indexed_item(var_id: str, slot: int):
    """生成 itemNLabel / itemNValue / stepNLabel / stepNBody 一类的推导器。"""
    key = "label" if var_id.endswith("Label") else "value"

    def derive(scene, ctx, layout):
        items = scene_items(scene)
        if len(items) <= slot:
            return None
        return items[slot][key] or None

    return derive


def _indexed_index(slot: int):
    """条目结构标号 stepNIndex（01/02/03）：不取场景数据，行存在就必然有这个号。

    与 ``_indexed_item`` 同一条"行不存在 ⇒ None"的口径，缺行时由版式选择器换版式，
    而不是屏上凭空多出一个没人对应的 03。
    """
    def derive(scene, ctx, layout):
        if len(scene_items(scene)) <= slot:
            return None
        return f"{slot + 1:02d}"

    return derive


def layout_default(layout: dict, var_id: str):
    """版式自带 default: 只用于设计系统自己的标签词, 不用于事实。"""
    for var in layout["variables"]:
        if var["id"] == var_id and var.get("default") is not None:
            return str(var["default"])
    return None


#: 精确 id → 推导器。带序号的条目类单独注册(见 register_indexed_derivers)。
DERIVERS = {
    "slotSeconds": _slot_seconds,
    "ordinal": _ordinal,
    "kicker": _kicker,
    "title": _title,
    "headTop": _head_top,
    "headBottomLead": _head_bottom_lead,
    "headAccent": _head_accent,
    # 整句型屏上位共用一个取材处: story 的屏句位、hook 的辅助行、closer 的行动句。
    # `lead`/`detail`(旧 story 领句/支撑句)随 story 契约一起删除 —— 它们的取材处是
    # 正文, 而正文会被念出来, 保留就是死代码。
    "support": _onscreen_phrase,
    "onscreen": _onscreen_phrase,
    "tone": _tone,
    "value": _value,
    "unit": _unit,
    "label": _label,
    "compareValue": _compare_value,
    "compareUnit": _compare_unit,
    "compareLabel": _compare_label,
    "quoteBody": _quote_body,
    "attribution": _attribution,
    "channel": _channel,
    "cta": _cta,
    "ctaAccent": _cta_accent,
}

#: 条目类变量名的形态: item1Label / step2Body / step3Index / …
INDEXED_VAR_RE = re.compile(r"^(item|step)([1-9])(Label|Value|Body|Index)$")


def register_indexed_derivers(variable_ids) -> None:
    """按需把 itemN*/stepN* 的推导器挂上表(新增版式不必改这张表)。"""
    for var_id in variable_ids:
        match = INDEXED_VAR_RE.match(var_id)
        if not match:
            continue
        slot = int(match.group(2)) - 1
        deriver = (_indexed_index(slot) if match.group(3) == "Index"
                   else _indexed_item(var_id, slot))
        DERIVERS.setdefault(var_id, deriver)


def missing_variables(layout: dict, scene: dict, ctx: dict) -> list[str]:
    """试填一遍, 返回填不出来的变量 id —— 自动选版式靠它, 不打印噪音。"""
    missing = []
    for var in layout["variables"]:
        try:
            resolve_variable(var, layout, scene, ctx)
        except EmitterError:
            missing.append(var["id"])
    return missing


# ------------------------- 版式选择 -------------------------
def dedupe(items: list[str]) -> list[str]:
    """按首次出现去重 —— 候选版式的顺序就是优先级。"""
    seen, out = set(), []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def title_needs_slot(scene: dict, layout: dict) -> bool:
    """作者写了标题行、但这个版式没有 ``title`` 变量 ⇒ 这句话会静默消失。

    `parse_input` 把段首短行摘出来当 title(**不进 body ⇒ 不进配音**), 而
    `stat` / `closer` / `quote` 的契约里没有标题位。两头都不接, 稿子就既不上屏
    也不出声 —— 排版难看是可以商量的, 悄悄吃稿不行(与 `emit_composition` 里
    "条目超出行数" 那条 ⚠ 同一个立场)。
    """
    return bool(flatten(scene.get("title"))) and not (contract_ids(layout) & TITLE_LANDING_VARS)


def choose_layout(pack: dict, scene: dict, ctx: dict) -> str:
    """点名优先; 否则按分镜形态选一个**填得满**的版式。都不满足 → 停机。"""
    explicit = scene.get("layout") or ctx.get("layout")
    if explicit:
        if explicit not in pack["layouts"]:
            raise EmitterError(
                f"点名版式 {explicit!r} 不在 {pack['name']} 家族里; 可选: "
                + ", ".join(sorted(pack["layouts"]))
            )
        layout = pack["layouts"][explicit]
        register_indexed_derivers(contract_ids(layout))
        missing = missing_variables(layout, scene, ctx)
        if missing:
            raise EmitterError(f"点名版式 {explicit} 缺这些变量: {', '.join(missing)}")
        return explicit

    items = scene_items(scene)
    facts = _scene_facts(scene)
    candidates = []
    # 优先级 = "作者写过的话 > 机器切得出的话"(frame.md 法则 6 的两级取材)。
    # 首尾书挡先占位; 中段先给屏句(story), 再给标注齐备的数字(stat)、作者写的
    # 引文(quote)、切得出的条目(catalog/rail)。
    # 写屏句等于宣布"这一镜的任务是一句陈述", 所以它会压过 stat/catalog:
    # 数字镜头别写 屏:, 想让巨号数字上屏就显式点名 "layout": "stat"。
    for stem, fits in (
        ("hook", ctx["is_first"]),
        ("closer", ctx["is_last"]),
        ("story", bool(scene.get("onscreen"))),
        ("stat", len(facts) >= MIN_STAT_FACTS),
        ("quote", bool(scene.get("quote"))),
        ("catalog", len(items) >= MIN_RAIL_ITEMS),
        ("rail", rail_ready(items)),
    ):
        if fits:
            candidates.append(stem)
    # 兜底顺序: 整句版式优先(story), 条目/数据版式次之, 首尾专用版式最后
    candidates += list(AUTO_LAYOUT_STEMS)
    for name in dedupe(candidates):
        layout = pack["layouts"].get(name)
        if not layout:
            continue
        register_indexed_derivers(contract_ids(layout))
        if not missing_variables(layout, scene, ctx):
            return name
    raise EmitterError(
        f"第 {ctx['shot_no']} 镜填不满任何版式。这一镜现在有 "
        f"{'1 条屏句' if scene.get('onscreen') else '0 条屏句(整句型屏上位全部落选)'}、"
        f"{'1 行作者标题' if flatten(scene.get('title')) else '0 行作者标题(领句位全部落选)'}、"
        f"{len(facts)} 个带单位数字(其中 {sum(1 for f in facts if f['label'])} 个"
        f"配得出 stat 要的小标题)、{len(items)} 个能切成小标题的分句。"
        '处理: 给这一段加一行 `屏: ……`(16 字内的整句)或标题行; '
        '或写 "items"(结构化条目)/"quote"(引文); '
        '或在 JSON 里显式点名 "layout" 并补齐各变量。'
    )


def _resolve_shot_image(work_dir: str, shot_index: int, scene: dict,
                        ctx: dict, log=print):
    """为这一镜取一张真实图片(Wikimedia Commons); 任何环节失败都降级为无图。

    查询词复用 commons_media.image_query 的优先级: scene.image 显式(作者写
    false ⇒ 跳过该镜, 不许回落 kicker) > scene.kicker; 再回落 ctx.kicker
    (--kicker 全局眉标)。返回的 record["local_path"] 是相对 work_dir 的
    相对路径, 让 HTML 直接当 src 用, 不依赖引擎加载根。
    """
    if scene.get("image") is False:
        return None
    query = cm.image_query(scene, scene)
    if not (isinstance(query, str) and query.strip()):
        fallback = ctx.get("kicker")
        query = fallback.strip() if isinstance(fallback, str) and fallback.strip() else None
    if not query:
        return None
    media_dir = Path(work_dir) / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    dest = media_dir / f"shot_{shot_index:02d}.jpg"
    record = cm.resolve_shot_image(query, dest, log=log)
    if record is None:
        return None
    # 绝对路径转 work_dir 相对(正斜杠), HTML 引用方便
    record["local_path"] = os.path.relpath(record["local_path"], work_dir).replace(os.sep, "/")
    return record

# ------------------------- HTML 发射 -------------------------
def emit_host(pack: dict, mounts: list[str], audios: list[str], total: float,
              w: int, h: int) -> str:
    """填 host.html 的占位符; 占位符少了或多写都算包与脚本不一致 → 停机。"""
    host = pack["host"]
    for token in HOST_PLACEHOLDERS:
        if token not in host:
            raise EmitterError(f"host.html 缺少占位符 {token}")
    filled = (
        host.replace("{{COMPOSITION_ID}}", HOST_COMPOSITION_ID)
        .replace("{{W}}", str(w))
        .replace("{{H}}", str(h))
        .replace("{{TOTAL}}", fmt_secs(total))
        .replace("{{SCENES}}", "\n".join(mounts))
        .replace("{{AUDIOS}}", "\n".join(audios))
    )
    leftover = re.findall(r"\{\{[A-Z_]+\}\}", filled)
    if leftover:
        raise EmitterError(f"host.html 里有未填充的占位符: {leftover}")
    # 占位符被 replace 全局替换, 注释里写一遍就会把挂载复制进样式表 (实测踩过):
    # 数一遍成品里的标记数量, 不等于挂载条数就停机, 别把重复片段留给渲染。
    for marker, count, what in (
        ('data-composition-src="compositions/', len(mounts), "画面挂载"),
        ('<audio id="voice-', len(audios), "配音挂载"),
    ):
        found = filled.count(marker)
        if found != count:
            raise EmitterError(
                f"生成的 index.html 里{what}标记 {marker!r} 出现 {found} 次, "
                f"应为 {count} 次 —— 多半是 host.html 的注释里写了占位符原文, "
                "把占位符名改成不带双花括号的写法"
            )
    return filled


def emit_mount(mount_index: int, layout: dict, values: dict, start: float,
               dur: float, w: int, h: int) -> str:
    """一镜一个 clip: 时序 = 配音时长, 内容 = 按契约填好的变量。"""
    payload = dict(values)
    payload["slotSeconds"] = round(dur, 3)
    encoded = html.escape(json.dumps(payload, ensure_ascii=False), quote=True)
    return MOUNT_TPL.format(
        mount_id=f"shot-{mount_index}",
        composition_id=layout["composition_id"],
        file_name=layout["file_name"],
        values=encoded,
        start=fmt_secs(start),
        dur=fmt_secs(dur),
        w=w,
        h=h,
    )


def audio_slot_duration(dur: float) -> float:
    """配音挂载的时长 = 画面时长 − ``AUDIO_MOUNT_HEADROOM_SECONDS``。

    三位小数与 ``fmt_secs`` 的写入口径一致, 免得余量本身又被四舍五入抖回来。
    """
    return round(dur - AUDIO_MOUNT_HEADROOM_SECONDS, 3)


def emit_audio_mount(mount_index: int, audio_path: str, work_dir: str,
                     start: float, dur: float) -> str:
    """一镜一条配音挂进宿主: 单独打开 index.html 就应该是有声的。

    这也是 ``hyperframes check`` 的 audio_file_without_element 判据要求的形态:
    工程目录里躺着 mp3 而合成里一个 ``<audio>`` 都没有, 说明声音是链路外补的,
    工程与产物不一致 —— 该修的是工程, 不是把 lint 关掉。
    最终成片的声音始终由 narration.mp3 提供 (mux_and_burn 用 -map 明说只要它),
    所以这里多挂一层不会造成双声道重叠。
    终点比画面窗早 AUDIO_MOUNT_HEADROOM_SECONDS 收(起点不变), 原因见那个常量的注释。
    """
    src = os.path.relpath(audio_path, work_dir).replace(os.sep, "/")
    return AUDIO_TPL.format(
        audio_id=f"voice-{mount_index}",
        src=html.escape(src, quote=True),
        start=fmt_secs(start),
        dur=fmt_secs(audio_slot_duration(dur)),
        track=AUDIO_TRACK_INDEX,
    )


def _subtitle_pieces(cue, display: str):
    """把上屏串按词切片：每个词连同**紧跟其后**的标点切成一片（服务不念标点，观众要看见）。

    逐字走 `display`（`caption_display_text` 的结果，已去 `｜`、留正常标点）：非标点字符
    必须落进当前词，词消费完（`words[ti]["w"]` 长度到）才翻页；标点一律接到**前一个词**的尾巴上。
    这样切片拼回去与 `display` 一字不差（裁决：强调/切片都不改上屏文本）。
    """
    words = cue.get("words") or []
    if not words:
        return []
    pieces, cur, ti, tc = [], "", 0, 0
    for ch in display:
        if CAPTION_PUNCT_RE.fullmatch(ch):
            cur += ch                          # 标点接在当前词后（此时 ti 仍是未完成的那个）
            continue
        if ti >= len(words):                    # 词已用尽却还有字 = 切片与稿子分家
            raise EmitterError(
                f"字幕切片多出字符 {ch!r}（cue {cue.get('text')!r}）—— "
                "词序列比上屏文本短，宁可停机也不把多出来的字并进上一个词")
        if tc == len(words[ti]["w"]):           # 上一个词吃满，结算后再开新词
            pieces.append((words[ti], cur))
            ti += 1
            tc, cur = 0, ""
        cur += ch
        tc += 1
    if ti < len(words):
        pieces.append((words[ti], cur))
    return pieces


def subtitle_scene_cues(scene_cue: list, scene: dict, slot: float,
                        line_chars: int) -> list[dict]:
    """一镜的字幕上屏数据：逐 cue 的行/词 + 整条退场时刻（裁决 17 的每 cue 退场）。

    强调在切片**之后**才着色（`accent` 标记打在词片上，文本一个字没动）：
    取数面交出的 `words` 与整词匹配出的强调词按 `id` 对应，改颜色不改"亮哪个字"。
    退场口径：非末条 cue 从 `cue.end` 起淡出，时长夹到与下一条开头的间隙（不许盖住下一条）；
    末条贴着本镜尾收 `max(cue.end, slot - SUBTITLE_EXIT_SECONDS)`，读得完又不在下一镜残留。
    """
    accent_by_id = set()
    cues = []
    for cue in scene_cue:
        for w in cue_accent_words(cue, scene):
            accent_by_id.add(id(w))
        lines = []
        for piece_word, piece_text in _subtitle_pieces(cue, caption_display_text(cue["text"])):
            seg = piece_text.strip()
            if not seg:
                continue
            lines.append((piece_word, seg))
        wrapped = _subtitle_lines_wrap(lines, line_chars, accent_by_id)
        if not wrapped:
            continue
        cues.append({"start": cue["start"], "end": cue["end"], "lines": wrapped})
    for j, item in enumerate(cues):
        nxt = cues[j + 1]["start"] if j + 1 < len(cues) else None
        if nxt is not None:
            item["exit_at"] = round(item["end"], 3)
            item["exit_dur"] = round(
                min(SUBTITLE_EXIT_SECONDS, max(0.05, nxt - item["end"])), 3)
        else:
            item["exit_dur"] = SUBTITLE_EXIT_SECONDS
            item["exit_at"] = round(max(item["end"], slot - SUBTITLE_EXIT_SECONDS), 3)
    return cues


def _subtitle_lines_wrap(segs, line_chars, accent_by_id) -> list[list[dict]]:
    """把 (词, 文本) 序列按行宽折行，同时把强调标记打在词片上。只换行不丢字。"""
    lines: list[list[dict]] = [[]]
    width = 0
    for word, seg in segs:
        seg_len = len(caption_norm(seg))
        if width and width + seg_len > line_chars:
            lines.append([])
            width = 0
        lines[-1].append({"t": seg, "s": word["s"], "e": word["e"],
                          "accent": id(word) in accent_by_id})
        width += seg_len
    return [ln for ln in lines if ln]


def emit_subtitle_composition(composition_id: str, cues: list[dict],
                              slot: float, w: int, h: int) -> str:
    """把一镜的字幕编译成一份**子合成 HTML**（引擎克隆 `<template>`、按 `data-composition-id` 挂载）。

    发射器在这里**把绝对时间烤进** timeline（每个词的 `at=` 用 `word.s`、每条 cue 的退场用
    `exit_at`），运行时不读 `Date.now()`/随机 ⇒ 判据 4a 逐字节可复现。入场逐词 `fromTo`
    （累积、不逐词消失），退场按整条 cue 容器 `to opacity 0`（裁决 17）。
    文字色统一白、黑描边；强调词换成固定高亮色**同样描边**（只换字色，不动几何）。
    """
    # 每条 cue 一个容器，每个词一个 span：入场打 span、退场打容器（一次淡出整条）。
    body_lines, tween_lines = [], []
    for ci, cue in enumerate(cues):
        box_id = f"sc-c{ci}"
        rows = []
        for li, line in enumerate(cue["lines"]):
            cells = []
            for wi, span in enumerate(line):
                sid = f"sc-c{ci}-l{li}-w{wi}"
                cells.append(f'<span id="{sid}"'
                             f' class="sc-w{" sc-acc" if span["accent"] else ""}">'
                             f'{html.escape(span["t"])}</span>')
                # 逐词入场：opacity 0→1 + 轻微上浮，词与词错开（at=各自 start）
                dur = round(max(SUBTITLE_ENTRANCE_MIN,
                                min(0.32, span["e"] - span["s"])), 3)
                tween_lines.append(
                    f'        tl.fromTo("#{sid}", {{opacity: 0, y: 10}},'
                    f' {{opacity: 1, y: 0, duration: {dur}, ease: "power2.out"}},'
                    f' {round(span["s"], 3)});')
            rows.append(f'<div class="sc-row">{"".join(cells)}</div>')
        body_lines.append(f'<div id="{box_id}" class="sc-cue">{"".join(rows)}</div>')
        # 整条 cue 退场（per-cue，非逐词）：容器淡出，盖住里面所有词。
        tween_lines.append(
            f'        tl.to("#{box_id}", {{opacity: 0, duration: {cue["exit_dur"]},'
            f' ease: "power2.in"}}, {cue["exit_at"]});')
    if not body_lines:
        body_lines = ['<div id="sc-c0" class="sc-cue"></div>']
        tween_lines = [f'        tl.set("#sc-c0", {{opacity: 0}}, 0);']
    # 版式自检要求每个 `#id` 补间都能在本文件解析到元素 —— 空 cue 兜底也要有那个 div。
    return SUBTITLE_COMP_TPL.format(
        comp_id=composition_id,
        slot=round(slot, 3),
        w=w,
        h=h,
        bottom=SUBTITLE_BOTTOM_CQH,
        font=SUBTITLE_FONT_CQH,
        side=SUBTITLE_SIDE_CQW,
        maxw=SUBTITLE_MAX_WIDTH_CQW,
        outline=SUBTITLE_OUTLINE_EM,
        body="".join(body_lines),
        tweens="\n".join(tween_lines),
    )


def emit_subtitle_mount(mount_index: int, start: float, dur: float,
                        w: int, h: int) -> str:
    """字幕子合成挂在 2 轨：永远压在版式（1 轨）之上，配音（0 轨）与之无关。"""
    return SUBTITLE_MOUNT_TPL.format(
        mount_id=f"subtitle-{mount_index}",
        composition_id=f"{SUBTITLE_FILE_PREFIX}-{mount_index}",
        file_name=f"{SUBTITLE_FILE_PREFIX}-{mount_index}.html",
        start=fmt_secs(start),
        dur=fmt_secs(dur),
        w=w,
        h=h,
        track=SUBTITLE_TRACK_INDEX,
    )


def emit_composition(pack: dict, scenes: list, durations: list, work_dir: str,
                     ctx_base: dict, w: int, h: int,
                     audio_files: list, image_records: list,
                     scene_cues: list | None = None) -> list[dict]:
    """逐镜选版式 + 填变量 + 生成宿主与挂载, 并把用过的版式文件复制进工作目录。

    `scene_cues` 提供且 pack 是**编译包**（path_c，`pack["compiled"]`）时，额外把每镜字幕
    编译成 2 轨子合成（`subtitle_<i>.html`）挂上去，并把该镜的字幕子合成文本收集到
    `subtitle_files` 交给调用方落盘 —— 这是裁决 2「字幕收进 HyperFrames」的唯一接入点。
    存量手发包（path_b）`scene_cues` 传 None，一行字幕子合成都不生成，片子字节形状不变。
    """
    mounts, audios, shots = [], [], []
    subtitle_files: list[tuple[str, str]] = []
    native_sub = bool(pack.get("compiled")) and scene_cues is not None
    start = 0.0
    prev_ground_tone = None
    for i, (scene, dur, image_record) in enumerate(zip(scenes, durations, image_records), 1):
        ctx = dict(ctx_base)
        ctx.update({
            "shot_no": i,
            "shot_ordinal": f"{i:02d}",
            "slot_seconds": round(dur, 3),
            "is_first": i == 1,
            "is_last": i == len(scenes),
            "prev_ground_tone": prev_ground_tone,
            "image_record": image_record,
        })
        layout_name = choose_layout(pack, scene, ctx)
        layout = pack["layouts"][layout_name]
        values = fill_variables(layout, scene, ctx)
        mounts.append(emit_mount(i, layout, values, start, dur, w, h))
        if native_sub:
            cues = subtitle_scene_cues(scene_cues[i - 1], scene, dur,
                                       caption_line_chars(w, h))
            comp_id = f"{SUBTITLE_FILE_PREFIX}-{i}"
            subtitle_files.append((
                f"{comp_id}.html",
                emit_subtitle_composition(comp_id, cues, dur, w, h)))
            mounts.append(emit_subtitle_mount(i, start, dur, w, h))
        if i <= len(audio_files):
            audios.append(emit_audio_mount(i, audio_files[i - 1], work_dir, start, dur))
        # 本镜实际呈现的地面: 固定地面的版式用装包时算好的, 可换面的版式(story)
        # 用它自己填出来的 tone —— 下一镜的"翻不翻面"必须看真实地面, 不能看默认值。
        declared = values.get(TONE_VAR_ID)
        prev_ground_tone = declared if declared in GROUND_TONES else layout["ground_tone"]
        shots.append({"no": i, "layout": layout_name, "start": start, "dur": dur,
                      "composition_id": layout["composition_id"],
                      "ground": prev_ground_tone, "values": values})
        log(f"  分镜{i} → {layout_name}  时长 {dur:.1f}s  start {start:.1f}s  地面 {prev_ground_tone}")
        capacity = row_capacity(layout)
        surplus = len(scene_items(scene)) - capacity if capacity else 0
        if surplus > 0:
            log(f"  ⚠ 分镜{i} 有 {capacity + surplus} 条条目, 但 {layout_name} 固定 {capacity} 行: "
                f"末尾 {surplus} 条不会上屏。请拆镜或换版式, 别让数据悄悄丢掉")
        if title_needs_slot(scene, layout):
            log(f"  ⚠ 分镜{i} 的标题行没有落点: {layout_name} 没有标题位, 而标题行不进配音 ⇒ "
                f"这句作者的话既不上屏也不出声。并进正文, 或点名带 title 的版式(rail/catalog/story/hook)")
        start += dur
    write_text(os.path.join(work_dir, "index.html"),
               emit_host(pack, mounts, audios, start, w, h))
    dest_dir = os.path.join(work_dir, "compositions")
    os.makedirs(dest_dir, exist_ok=True)
    for layout in pack["layouts"].values():
        shutil.copyfile(layout["path"], os.path.join(dest_dir, layout["file_name"]))
    for file_name, text in subtitle_files:
        write_text(os.path.join(dest_dir, file_name), text)
    return shots


# ------------------------- 渲染前门禁 -------------------------
def gate_layout_selfcheck(work_dir: str) -> None:
    """跑结构不变量(见 layout_selfcheck): 空目标补间、面上淡入等在这里就停机。"""
    violations = [
        violation
        for layout_path in layout_selfcheck.discover_layouts(Path(work_dir))
        for violation in layout_selfcheck.check_layout(layout_path)
    ]
    if not violations:
        log("✅ 版式自检通过 (0 违规)")
        return
    for violation in violations:
        log(f"  ✗ {violation}")
    raise EmitterError(f"版式自检不过: {len(violations)} 条违规")


def gate_hyperframes_check(work_dir: str) -> None:
    """check --strict 是渲染前的硬门禁: 有 error/warning 就不许烧 GPU 时间。

    **失败时必须报出真实原因**（2026-10-08 实跑 t002 修）:
    旧实现只打「check 输出尾部: 报告无法解析: check.json」+ 一个 stderr **路径**。
    实跑那次的真实原因是 `No index.html file found`（工作目录被系统 temp 清理掉了），
    而 check.json / check.err.txt 两个文件当时**都是空的** —— 用户看着"无法解析"只能猜。
    「假绿比红危险」在红这一侧同样成立: **报不出原因的拒绝等于没有拒绝**。
    所以这里把 stderr 原文（非空行）直接打进异常消息。
    """
    json_path = os.path.join(work_dir, "check.json")
    err_path = os.path.join(work_dir, "check.err.txt")
    with open(json_path, "wb") as out, open(err_path, "wb") as err:
        r = run(hf_argv("check", ".", "--strict", "--json",
                        f"--caption-zone={CAPTION_ZONE}"), cwd=work_dir, stdout=out, stderr=err)
    if r.returncode != 0:
        tail = summarize_check_json(json_path)
        log(f"  check 输出尾部: {tail}")
        # stderr 原文（跳过空行）—— 这是"为什么失败"的唯一凭据
        detail = read_text(err_path).strip() if os.path.exists(err_path) else ""
        detail_lines = [ln for ln in detail.splitlines() if ln.strip()]
        if detail_lines:
            for line in detail_lines[-8:]:
                log(f"  ! {line}")
        else:
            log("  ! hyperframes 的 stderr 是空的 —— 多半是工作目录被清了或 npx 拉包失败")
            log(f"    (工作目录: {work_dir} | 存在 index.html: "
                f"{os.path.isfile(os.path.join(work_dir, 'index.html'))})")
        log(f"  详细 stderr: {err_path}")
        raise EmitterError(
            f"hyperframes check --strict 未通过, 已拒绝渲染。"
            f"原因: {tail}"
            + (f" | stderr: {' / '.join(detail_lines[-3:])}" if detail_lines else ""))
    log(f"✅ check --strict 通过 ({summarize_check_json(json_path)})")


def summarize_check_json(json_path: str) -> str:
    """把 check 的 JSON 摘成一行; 读不动就退回文件大小, 不吞异常。"""
    try:
        report = json.loads(read_text(json_path))
    except (OSError, json.JSONDecodeError):
        return f"报告无法解析: {json_path}"
    sections = report.get("sections") or report.get("results") or {}
    if isinstance(sections, dict):
        parts = [
            f"{name} err={item.get('errors', '?')}/{item.get('warnings', item.get('errorCount', '?'))}"
            for name, item in sections.items()
            if isinstance(item, dict)
        ]
        if parts:
            return ", ".join(parts)
    return f"ok={report.get('ok')}"


# ------------------------- 渲染后动量审计 -------------------------
def measure_tail_motion(video: str, shots: list, work_dir: str) -> list[float]:
    """用 scdet 量每镜后 1/4 的平均帧间变化量, 证明"画面一直在动"(判据 3)。"""
    meta_path = os.path.join(work_dir, "scdet.txt")
    if os.path.exists(meta_path):
        os.remove(meta_path)
    vf = f"scdet=threshold=0,metadata=mode=print:file={ffmpeg_sub_path(meta_path)}"
    with open(os.devnull, "wb") as devnull:
        run(["ffmpeg", "-y", "-i", video, "-vf", vf, "-f", "null", "-"],
            stdout=devnull, stderr=devnull)
    if not os.path.isfile(meta_path):
        raise EmitterError(f"scdet 没写出元数据文件, 无法审计动量: {meta_path}")
    frames = parse_scdet(read_text(meta_path, errors="replace"))
    if not frames:
        raise EmitterError("scdet 元数据里没有可解析的帧分数")
    scores = []
    for shot in shots:
        window_start = shot["start"] + shot["dur"] * (1.0 - TAIL_FRACTION)
        window_end = shot["start"] + shot["dur"]
        tail = [score for ts, score in frames if window_start <= ts < window_end]
        scores.append(sum(tail) / len(tail) if tail else 0.0)
    return scores


def parse_scdet(text: str) -> list[tuple[float, float]]:
    """scdet 每个时间点可能打多条平面分数, 取该帧最大值。"""
    frames: list[tuple[float, float]] = []
    current = None
    best = 0.0
    for line in text.splitlines():
        pts = MOTION_PTS_RE.search(line)
        if pts:
            if current is not None:
                frames.append((current, best))
            current, best = float(pts.group(1)), 0.0
            continue
        score = MOTION_SCORE_RE.search(line)
        if score and current is not None:
            best = max(best, float(score.group(1)))
    if current is not None:
        frames.append((current, best))
    return frames


def audit_motion(video: str, shots: list, work_dir: str) -> None:
    scores = measure_tail_motion(video, shots, work_dir)
    frozen = []
    for shot, score in zip(shots, scores):
        mark = "✓" if score >= MIN_TAIL_MOTION else "✗ 冻住"
        log(f"  镜{shot['no']}({shot['layout']}) 尾段动量 {score:.4f} ≥ {MIN_TAIL_MOTION} {mark}")
        if score < MIN_TAIL_MOTION:
            frozen.append(shot["no"])
    if frozen:
        raise EmitterError(
            f"这些镜头尾段画面没有持续变化: {frozen} —— 判据 3 不成立, 成片不合格"
        )


# ------------------------- 联络表 -------------------------
def build_contact_sheet(video: str, shots: list, out_dir: str, work_dir: str) -> str:
    """每镜取尾段一帧拼成 jpg, 人工一眼比对整片节奏(判据 6 的验收对象)。"""
    frames_dir = os.path.join(work_dir, "sheet")
    os.makedirs(frames_dir, exist_ok=True)
    for shot in shots:
        grab_at = shot["start"] + shot["dur"] * (1.0 - TAIL_FRACTION / 2)
        cell = os.path.join(frames_dir, f"cell_{shot['no']:02d}.png")
        with open(os.devnull, "wb") as devnull:
            run(["ffmpeg", "-y", "-ss", fmt_secs(grab_at), "-i", video,
                 "-frames:v", "1", "-vf", f"scale={CONTACT_SHEET_CELL_W}:-1", cell],
                stdout=devnull, stderr=devnull)
        if not os.path.isfile(cell):
            raise EmitterError(f"联络表取帧失败: 镜{shot['no']} @ {grab_at:.2f}s")
    # 拼贴用 image2 序列: 按镜号补零连续命名, tile 自左而右逐行铺
    seq_dir = os.path.join(work_dir, "sheet_seq")
    os.makedirs(seq_dir, exist_ok=True)
    for i, shot in enumerate(shots, 1):
        shutil.copyfile(os.path.join(frames_dir, f"cell_{shot['no']:02d}.png"),
                        os.path.join(seq_dir, f"seq_{i:02d}.png"))
    sheet = os.path.join(out_dir, "contact-sheet.jpg")
    rows = -(-len(shots) // CONTACT_SHEET_COLS)  # 向上取整
    with open(os.devnull, "wb") as devnull:
        run(["ffmpeg", "-y", "-start_number", "1", "-i", os.path.join(seq_dir, "seq_%02d.png"),
             "-vf", f"tile={CONTACT_SHEET_COLS}x{rows}", "-frames:v", "1", sheet],
            stdout=devnull, stderr=devnull)
    if not os.path.isfile(sheet):
        raise EmitterError(f"联络表拼接失败: {sheet}")
    log(f"联络表: {os.path.abspath(sheet)}")
    return sheet


# ------------------------- 环境自检 -------------------------
def doctor():
    ok = True
    log("=== 环境自检 (doctor) ===")

    node = which("node")
    if node:
        ver = subprocess.check_output([node, "--version"]).decode().strip()
        maj = int(ver.lstrip("v").split(".")[0])
        if maj >= 22:
            log(f"✅ Node.js {ver} (>=22 满足)")
        else:
            log(f"❌ Node.js {ver} 过低, 需要 >=22")
            ok = False
    else:
        log("❌ 未找到 node, 请安装 https://nodejs.org (>=22)")
        ok = False

    hf = which("hyperframes") or (which("npx") is not None)
    if hf:
        log("✅ hyperframes 可经 npx 调用 (npm install -g hyperframes 后更佳)")
    else:
        log("❌ 未找到 npx/hyperframes, 请安装 Node.js + npm")
        ok = False

    ff = which("ffmpeg")
    if ff:
        log("✅ ffmpeg 已安装")
    else:
        log("❌ 未找到 ffmpeg, 请安装 https://ffmpeg.org")
        ok = False

    try:
        pack = load_style_pack(DEFAULT_STYLE)
        log(f"✅ 设计系统包 {DEFAULT_STYLE}: {len(pack['layouts'])} 个版式 "
            f"({', '.join(sorted(pack['layouts']))})")
    except EmitterError as exc:
        log(f"❌ 设计系统包不可用: {exc}")
        ok = False

    try:
        import edge_tts  # noqa: F401
        log("✅ edge-tts 已安装")
    except ImportError:
        log("❌ 未安装 edge-tts, 请运行: pip install edge-tts")
        ok = False

    if which("npx"):
        log("→ 运行 'npx hyperframes doctor' 检查 Chrome 是否就绪:")
        run(hf_argv("doctor"))
    log("=== 自检结束: " + ("全部就绪 ✅" if ok else "有缺失项, 见上方 ❌") + " ===")
    return ok


# ------------------------- 配音 -------------------------
def tts_word_events(text: str, voice: str, mp3_path: str):
    """edge-tts 的 Python API：一次 stream 同时落盘 mp3 并交出词级时序原值。

    返回 `(WordBoundary 事件列表, 音频字节数)`；事件里的 `offset`/`duration` 是**服务
    原单位（100ns tick）**，换算成秒只许在 `words_from_events` 那一处做。

    为什么非走 Python API 不可：命令行那一支只写句子级字幕 —— 7.2.8 的 `SubMaker`
    只有 `get_srt`，压根没有词级出口；词边界只有 `Communicate(..., boundary="WordBoundary")`
    这条路，而 `boundary` 这个参数只在 `Communicate` 的签名上（`TTSConfig` 属于
    `data_classes`，不是公开入口）。P2-0 实测：同一次 stream 里 audio 与 WordBoundary
    两类块交替出现，17 个词全部拿到（证据 §K1）。
    """
    import asyncio
    import edge_tts

    async def _collect():
        events, written = [], 0
        sink = open(mp3_path, "wb")
        try:
            com = edge_tts.Communicate(text, voice, boundary="WordBoundary")
            async for chunk in com.stream():
                kind = chunk.get("type")
                if kind == "audio":
                    data = chunk.get("data") or b""
                    sink.write(data)
                    written += len(data)
                elif kind == "WordBoundary":
                    events.append(chunk)
        finally:
            sink.close()
        return events, written

    return asyncio.run(_collect())


def scene_cues_from_words(text: str, words, seconds: float, index: int) -> list:
    """词表 → 逐镜 cue；归组对不上时**退到字符支**，不退到"猜"。

    `cues_from_words` 用精确消费字符数归组，对不上就抛。抛在这里不往上冒是因为产线上
    还有第二条正确出路：词形本来就取自稿子（`words_from_text`），换过去只降级时序精度，
    画面上亮起来的字仍然由同一个 `match_accent` 决定。反过来若让它整片失败，一份稿子
    因为服务多给了一个词就发不出去，而画面文本其实完全正确 —— 那是把取数面的抖动
    放成产线的停机。退化必须**出声**（⚠️ 那行日志），否则没人知道这一片走的是兜底支。
    """
    try:
        return cues_from_words(text, words, seconds)
    except EmitterError as exc:
        log(f"  ⚠️ 分镜{index} 词表与稿子对不上（{exc}）—— 本镜时序退到字符支")
        return cues_from_words(text, words_from_text(text, seconds), seconds)


def synthesize_audio(scenes, voice_default, work_dir):
    """逐镜配音并交出词级 cues；命中 `cues.json` 的那一镜**不碰服务**。

    返回 `(mp3 列表, 逐镜 cue 列表, 时长列表)`。第二项从前的"逐镜 .vtt 路径"换成了
    取数面交出的结构 —— 旧文件名一直在骗人（那是 SRT 体），而且解析它等于让一份
    已经算好的时序再过一次正则。

    `cues.json` 落盘的两个真理由（§6.4 订正后，原来写的"两条路径时序不同"已被 P2-0
    实测推翻 —— 同稿同音色两次请求逐词差 ≤0.000s）：
      · 这一片走的是词级支还是字符支只有落下来才证明得了，判据 4a 要对着它核；
      · 配音段实测 12.1–12.9s 全是网络往返，重跑门禁不该再花一次，更不该在微软服务
        抖动时把一份已经合格的稿子变成失败。
    缓存键是 (归一化正文, 音色) 的哈希：改一个字、换一个音色都必须重配 —— 拿旧 cues
    配新稿会让字幕和配音对不上，而 mp3 和 cues.json **两边都还是绿的**。
    """
    doc = read_json(os.path.join(work_dir, CUES_NAME))
    cached = doc["scenes"] if isinstance(doc, dict) and doc.get("schema") == CUES_SCHEMA \
        and isinstance(doc.get("scenes"), list) else []
    audio_files, scene_cues, durations, entries = [], [], [], []
    for i, sc in enumerate(scenes, 1):
        voice = sc.get("voice") or voice_default
        mp3_name = f"scene_{i}.mp3"
        mp3 = os.path.join(work_dir, mp3_name)
        # 朗读语义不受影响，压平空白：换行会让服务的韵律分段和稿子的句子切分不一致
        speak_text = " ".join(sc["body"].split())
        if not speak_text:
            raise EmitterError(f"分镜{i} 正文为空, 无话可配 —— 删掉这条或补正文")
        key = cue_cache_key(speak_text, voice)
        hit = next((e for e in cached
                    if e.get("index") == i and e.get("key") == key
                    and e.get("mp3") == mp3_name and isinstance(e.get("words"), list)
                    and e["words"] and e.get("seconds")
                    and os.path.isfile(mp3)), None)
        if hit is not None:
            mode, seconds = str(hit.get("mode", "word")), float(hit["seconds"])
            words = [{"w": w["w"], "s": w["s"], "e": w["e"]} for w in hit["words"]]
            log(f"→ 配音 分镜{i} 复用 cues.json (voice={voice}, {mode} 支 {len(words)} 词)")
        else:
            log(f"→ 配音 分镜{i} (voice={voice})")
            try:
                events, written = tts_word_events(speak_text, voice, mp3)
            except Exception as exc:
                raise EmitterError(
                    f"分镜{i} 配音失败: {exc} (检查网络是否能连微软语音服务 / "
                    "pip install edge-tts)") from exc
            if written <= 0:
                raise EmitterError(f"分镜{i} 配音返回 0 字节音频 —— 服务没给声音")
            measured = ffprobe_duration(mp3)
            seconds = measured if measured is not None else estimate_duration(speak_text)
            # 估算值**不参与词表裁剪**：拿 estimate_duration 去当上界会成批丢词，
            # 然后 cues_from_words 因为"词表多出没归属的字"而拒编 —— 那是估算的锅。
            words = words_from_events(events, measured)
            mode = "word"
            if not words:
                mode = "char"
                words = words_from_text(speak_text, seconds)
                log(f"  ⚠️ 分镜{i} 服务没给词级时序 —— 本镜时序退到字符支")
            else:
                log(f"  词级 {len(words)} 个")
        if seconds < MIN_SLOT_SECONDS:
            raise EmitterError(
                f"分镜{i} 配音只有 {seconds:.2f}s, 低于版式契约下限 {MIN_SLOT_SECONDS}s —— "
                "这一镜太短, 请与相邻分镜合并"
            )
        cues = scene_cues_from_words(speak_text, words, seconds, i)
        log(f"  时长 {seconds:.3f}s · {len(cues)} 条 cue")
        audio_files.append(mp3)
        scene_cues.append(cues)
        durations.append(seconds)
        entries.append({"index": i, "voice": voice, "key": key, "text": speak_text,
                        "seconds": seconds, "mode": mode, "mp3": mp3_name, "words": words})
    write_json(os.path.join(work_dir, CUES_NAME),
               {"schema": CUES_SCHEMA, "scenes": entries})
    return audio_files, scene_cues, durations


def fallback_scene_cues(text: str, seconds: float, index: int) -> list:
    """不配音（`--skip-render`）时的逐镜 cue：走的是同一字符支，词形仍来自稿子。

    发射链路要能脱离网络和 ffprobe 单验，但字幕结构必须是**真的那一种** —— 这里交出
    的和降级支逐字同形，P2-3 的字幕合成拿它当真输入跑，不会出现"跳过渲染就绕过字幕"
    的第二条代码路径。
    """
    speak_text = " ".join((text or "").split())
    if not speak_text:
        raise EmitterError(f"分镜{index} 正文为空, 无话可配 —— 删掉这条或补正文")
    return cues_from_words(speak_text, words_from_text(speak_text, seconds), seconds)



# ------------------------- 音频 + 字幕合成 -------------------------
#: ffmpeg 失败时回显的日志尾部行数 (拼接与最终合成两处共用, 不各写一个 -6)
FFMPEG_LOG_TAIL_LINES = 6


def _ffmpeg_failure(log_path: str, message: str) -> None:
    """停机前把 ffmpeg 日志尾部打进控制台: 失败原因必须当场可见, 不许静默往下走。"""
    tail = (read_text(log_path, errors="replace").splitlines()[-FFMPEG_LOG_TAIL_LINES:]
            if os.path.isfile(log_path) else ["(空)"])
    log("  ffmpeg 输出尾部:\n  " + "\n  ".join(tail))
    raise EmitterError(message)


def aigc_metadata_json(producer: str, silent_path: str) -> str:
    """按 GB 45438-2025 附录 E 拼隐式标识 JSON(单行, 纯 ASCII)。

    结构是标准钉死的: 外层字段名必须**含 "AIGC"**, 值是一个 JSON 文本, 里面
    `Label` / `ContentProducer` / `ProduceID` / `ReservedCode1` /
    `ContentPropagator` / `PropagateID` / `ReservedCode2` 七项。

    各字段取法与理由:
    - `Label="1"` —— "1" = 属于 AI 生成合成内容(由本流水线自己合成, 不是"可能"/"疑似",
      那两个是平台侧判定用语, 创作者不该自降等级)。
    - `ContentProducer` —— 标准允许写**名称**或 27 位编码(网安秘字〔2025〕29 号)。
      27 位编码要把主体类型/绑定方式与 18 位统一社会信用代码或身份号码绑定, 本机既没有
      企业资质也没有把身份证号写进公开产物 metadata 的授权, 所以走"名称"这一支。
    - `ProduceID` —— 取渲染产物 silent.mp4 的 sha256 前 32 位十六进制(标准上限 32 字节)。
      为什么拿画面文件而不是稿件文本: 稿件改了没渲出新片时不该发同一个编号, 而 silent.mp4
      是"这一版画面"的唯一指纹, 编号与内容严格绑定。
    - `ReservedCode1` —— 完整性校验码, 取 sha256(producer + ProduceID) 前 40 位(上限 40 字节)。
    - 传播三项留空 —— 谁把片子发出去是平台/发布方(抖音)的事, 由它们在传播时改写;
      本流水线是**生成**方, 冒充传播方填自己的编号反而违反"单文件仅一份隐式标识"。

    `ensure_ascii=True`(默认)是有意的: 值里只留 ASCII, 命令行与 mp4 metadata
    两处都不依赖进程代码页, 任何 JSON 解析器读回来都能还原中文。实测中文直写
    (`ensure_ascii=False`)在本机 shell=False 链路上也能以 UTF-8 原样落进 mdta
    并读回, 但那要求**每一环**都在 UTF-8 上: 一旦有人把这条命令搬进 cmd.exe 的
    936 代码页或非 UTF-8 的封装脚本, 中文就成乱码字节 —— 而乱码的标识等于没有标识。
    """
    produce_id = _sha256_prefix(silent_path, AIGC_PRODUCE_ID_BYTES)
    inner = {
        "Label": AIGC_LABEL_VALUE,
        "ContentProducer": producer,
        "ProduceID": produce_id,
        "ReservedCode1": _sha256_prefix(
            f"{producer}{produce_id}".encode("utf-8"), AIGC_INTEGRITY_CODE_BYTES),
        "ContentPropagator": "",
        "PropagateID": "",
        "ReservedCode2": "",
    }
    return json.dumps({"AIGC": inner}, ensure_ascii=True,
                      separators=(",", ":"))


def _sha256_prefix(data, nbytes: int) -> str:
    """对文件路径或 bytes 取 sha256 十六进制前缀(长度按**字节**算, hex 一字节一字符)。"""
    h = hashlib.sha256()
    if isinstance(data, (bytes, bytearray)):
        h.update(bytes(data))
    else:
        with open(data, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    return h.hexdigest()[:nbytes]


def mux_and_burn(silent, audio_files, cues, work_dir, final, w, h,
                 aigc_badge_seconds: float = 0.0,
                 aigc_producer: str = DEFAULT_AIGC_PRODUCER,
                 aigc_label: str = AIGC_LABEL_TEXT,
                 render: str = "full",
                 render_cause: str = "full(代码默认全开)"):
    """拼配音 → 烧 ASS 字幕(交付轨含 AIGC 显式角标) → 写 AIGC 隐式元数据 → 读回核验。

    `aigc_badge_seconds` 是角标持续时长, 主流程传 `aigc_badge_seconds(全片时长)`
    (= 开场 4 秒, 片长不足则等于片长); 低于 `AIGC_LABEL_MIN_SECONDS` 直接停机 ——
    国标量化了"文字高度 ≥ 最短边 5%、持续 ≥ 2 秒"两条线, 而《标识办法》§ 4-四 的
    "应当"落在**起始画面**与**播放周边**: 前者由这条 4 秒角标满足, 后者由下面那份
    隐式元数据 + 发布端自主声明满足(取舍记在 routes/news/ARCHITECTURE.md D8)。
    隐式标识按 GB 45438-2025 附录 E 写进容器元数据, 写完 ffprobe 读回核验,
    不一致就抛 EmitterError。字幕轨为空时降级为只合成音频(不许让成片不可用)。
    返回真正落到文件里的那份标识 JSON, 供调用方落 sidecar 备查。

    `render` 是**三档**而不是布尔(2026-09-29 用户点头放宽判据, 见 ARCHITECTURE D14):

        full      烧 ① + 写 ②          —— 原交付轨
        no-badge  不烧 ①、**照写 ②**   —— 交付轨: 产物可发布, 代价是发布必须带 ③
        draft     ①② 都不做, 返回 None —— 草稿轨: 侧车只落 draft 一段,
                                        check_publishable.py 读到即拒绝发布

    ② 是"能不能交付"的分界: draft 之外都必须留下读得回的元数据, 所以 `aigc_producer`
    为空只在要写 ② 时停机 —— 可交付的成片不提供"关掉标识"这条路(《标识办法》§ 2 的
    "应当"不容许拿空参数当开关), 要改的是标识内容而不是有无。
    ≥2 秒那条线是**① 的**判据, 只在真烧角标时卡: no-badge 没有画面标识, 拿 ① 的
    时长线去挡 ② 交付件是判据错位。
    `render_cause` 只影响日志与台账里"这一档是谁定的"那句话(旗标 `--deliver` /
    `--no-badge` / `--draft`, 还是姿态文件 `routes/news/aigc-mode.json`),
    不参与任何判据 —— 出处必须如实, 否则事后查不到是谁关的标。
    """
    burn_badge = render == "full"
    write_meta = render != "draft"
    if write_meta and not burn_badge and render != "no-badge":
        raise EmitterError(f"未知的渲染档 {render!r} —— 只能是 {aigc_mode.RENDER_MODES}")
    if write_meta:
        if not aigc_producer:
            # 可交付的成片不提供"关掉标识"这条路: 《标识办法》§ 2 要求"应当"添加,
            # 拿空参数当开关等于给用户一个违法的便利。要改的是标识内容
            # (--aigc-producer 填主体名), 不是有无。两件都能关的只有草稿轨,
            # 那条轨的产物直接不可发布, 而不是"无标的成品"。
            raise EmitterError(
                "AIGC 标识不可关闭 (aigc_producer 为空) —— 无标识成片不得交付, "
                "请填生成者名称: --aigc-producer <你的频道/主体名>")
    if burn_badge and aigc_badge_seconds < AIGC_LABEL_MIN_SECONDS:
        raise EmitterError(
            f"全片时长只有 {aigc_badge_seconds:.2f}s, 开场角标达不到国标 "
            f"{AIGC_LABEL_MIN_SECONDS}s 的显式标识持续下限 —— 补足内容, "
            "或在剪辑端另加一条 ≥2s 的显著标识后再交付")
    narr = os.path.join(work_dir, "narration.mp3")
    # concat 解封装器把 list.txt 里的相对路径按 **list.txt 自己的目录** 解析。
    # 实测传 "--work-dir .harness-news-runtime/tmp/x" 这种相对目录时, 条目写成
    # ".harness-news-runtime/tmp/x/scene_1.mp3" 会让它去找 …/x/.harness-news-runtime/…
    # 一个文件也读不到, 而老代码把 stderr 全丢进 devnull 又不查返回码 —— 错误
    # 憋到下一步 mux 才爆, 报的是"narration.mp3 不存在"这种误导性话。
    # 配音本来就与 list.txt 同目录 (synthesize_audio 写在这), 所以只写文件名:
    # 既与 CWD 无关, 又避开 concat 的单引号转义坑。
    write_text(
        os.path.join(work_dir, "list.txt"),
        "".join(f"file '{os.path.basename(a)}'\n" for a in audio_files),
    )
    concat_log = os.path.join(work_dir, "ffmpeg_concat.log")
    with open(concat_log, "wb") as celf:
        r = run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                 "-i", os.path.join(work_dir, "list.txt"), "-c", "copy", narr],
                stdout=celf, stderr=celf)
    if r.returncode != 0 or not os.path.isfile(narr):
        _ffmpeg_failure(concat_log, f"配音拼接失败, 详见 {concat_log}")

    ass_path = os.path.join(work_dir, "subs.ass")
    write_text(ass_path, build_ass(cues, w, h,
                                   aigc_text=aigc_label if burn_badge else None,
                                   aigc_seconds=aigc_badge_seconds if burn_badge else 0.0))
    err_log = os.path.join(work_dir, "ffmpeg_final.log")
    # 明确取流: 视频只从渲染产物拿, 声音只从拼接好的 narration 拿。
    # 合成里现在挂了 <audio>, 渲染出的 silent.mp4 也可能带一层声音;
    # 不写 -map 的话 ffmpeg 会各挑一条, 轻则双配音, 重则选了没字幕的那条。
    stream_maps = ["-map", "0:v:0", "-map", "1:a:0"]
    # AIGC 隐式标识 (§5 要求"在生成合成内容文件组件中加元数据"):
    # 实测 `-movflags +faststart` 会把不认识的键**静默丢掉**(ffprobe 读不到、
    # 字节里也搜不到), 必须加 use_metadata_tags 才落到 mdta atom。
    movflags = ["-movflags", "+faststart+use_metadata_tags"]
    aigc_meta = aigc_metadata_json(aigc_producer, silent) if write_meta else None
    meta_args = [] if aigc_meta is None else ["-metadata", f"{AIGC_METADATA_KEY}={aigc_meta}"]
    ff = which("ffmpeg") or "ffmpeg"
    # 字幕轨为空**且**这一档不烧角标 ⇒ 没东西可烧，直接 copy 视频流。
    # 编译包（path_c）把字幕收进 HyperFrames 后传 `cues=[]`，但 AIGC 角标仍走 ASS 烧：
    # `burn_badge` 为真时必须进滤镜支，否则合规的开场显式标识会被静默丢掉。
    if not cues and not burn_badge:
        log("⚠️ 字幕轨为空, 跳过烧录字幕(仅合成配音)")
        cmd = [ff, "-y", "-i", silent, "-i", narr] + stream_maps + [
            "-c:v", "copy", "-c:a", "aac", "-shortest"] + movflags + meta_args + [final]
    else:
        # cmd.exe 把 '&' 当命令分隔符（ASS 颜色码里全是 &），而 list2cmdline
        # 不会给无空格参数加引号，所以滤镜图必须落到文件里用 -filter_script:v
        # 传，不能直接拼进命令行。
        vf_file = os.path.join(work_dir, "vf.txt")
        write_text(vf_file, f"subtitles={ffmpeg_sub_path(ass_path)}\n")
        cmd = [ff, "-y", "-i", silent, "-i", narr] + stream_maps + [
            "-filter_script:v", vf_file,
            "-c:a", "aac", "-shortest"] + movflags + meta_args + [final]
    with open(err_log, "wb") as elf:
        # 带 JSON 的这条必须过 shell=False: cmd.exe 会吃掉成对双引号, 到 ffmpeg
        # 手里 JSON 就碎了(见 run_exe)。滤镜图已在文件里, 不再依赖 cmd 语法。
        r = run_exe(cmd, stdout=subprocess.DEVNULL, stderr=elf)
    if r.returncode != 0 or not os.path.exists(final):
        _ffmpeg_failure(err_log, f"ffmpeg 合成失败, 详见 {err_log}")
    if not write_meta:
        log(f"⚠️ 草稿模式[{render_cause}]: 角标没烧、元数据没写 —— 台账会标成草稿, "
            "发布那一步(check_publishable.py)读到即拒绝")
        return None
    if not burn_badge:
        # 这一档是 D14 放宽判据买到的东西: 产物可发布, 但代价在闸门那侧结算 ——
        # ① 没烧 ⇒ ③ 必带, 姿态文件与 --allow-undeclared 都关不掉它。
        log(f"⚠️ 未烧 ① 角标[{render_cause}]: ② 元数据照写并读回 —— 这份**可发布**, "
            "代价是发布必须带 ③ 自主声明(check_publishable.py 会拒绝 undeclared)")
    # 写完立刻读回来验一次: 标识"写了"不等于"在文件里", 而缺标识的成片是违法
    # 品而不是瑕疵品 —— 这里必须停机, 不能只在日志里抱怨一句。
    # 比对按语义而不是按字节: ffprobe 的输出层可能给特殊字符换层壳, 而真正要
    # 保证的是"能解析成同一份标识内容、关键字段一致"。
    tag = ffprobe_format_tag(final, AIGC_METADATA_KEY)
    want = json.loads(aigc_meta)["AIGC"]
    got = None
    if tag:
        try:
            got = json.loads(tag).get("AIGC")
        except ValueError:
            got = None
    if not got or not all(got.get(k) == v for k, v in want.items()):
        raise EmitterError(
            f"成片 {final} 的 {AIGC_METADATA_KEY} 元数据未生效或不一致 "
            f"(读回={tag!r}) —— 无标识成片不得发布; "
            "若本机 ffmpeg 太旧, 请升级到支持 movflags use_metadata_tags 的版本")
    log(f"  AIGC 隐式标识已核验: ProduceID={want['ProduceID']} "
        f"Label={want['Label']} ContentProducer={want['ContentProducer']}")
    return aigc_meta


# ------------------------- 主流程 -------------------------
def parse_resolution(text: str) -> tuple[int, int]:
    try:
        w, h = (int(x) for x in text.lower().split("x"))
    except ValueError as exc:
        raise EmitterError(f"分辨率格式错误: {text} (应为 宽x高, 如 1080x1920)") from exc
    return w, h


#: 渲染工作目录的默认根（2026-10-08 起，理由见 default_work_dir 的 docstring）
DEFAULT_WORK_ROOT = Path(__file__).resolve().parents[3] / ".harness-news-runtime" / "work"


def default_work_dir() -> str:
    """本次渲染的工作目录，**默认落在项目内而不是系统 temp**。

    为什么改（2026-10-08 实跑 t002 踩到）:
      旧实现是 `tempfile.mkdtemp(prefix="pathb_")` → `%TEMP%\\pathb_xxxx`。
      实跑一次完整渲染要 **15 分钟**，其中大半耗在首次 `npx -y hyperframes`
      联网拉包上。等包拉好时，**Windows 临时目录已被系统自动清理** ——
      实测 `index.html` 连同前 4 段的 mp3/vtt 一起消失，只剩最后一段音频，
      hyperframes 于是报 `No index.html file found`，而发射器只说
      「报告无法解析: check.json」—— 用户拿不到真实原因。

    落在 `.harness-news-runtime/work/` 的理由:
      - 与新闻域其他产物同域（ARCHITECTURE §6 的运行时目录约定）
      - 已被 .gitignore 忽略，不会污染仓库
      - **不被系统清理** —— 15 分钟的渲染跨得过去
      - 出问题时目录还在，可以直接进去看 index.html / 逐镜 compositions

    `--work-dir` 仍然可以显式覆盖（smoke 探针就是这么用的）。
    """
    return str(DEFAULT_WORK_ROOT / f"pathb_{os.getpid()}")


def main():
    ap = argparse.ArgumentParser(description="Path B 免费端到端成片脚本 (设计系统驱动)")
    ap.add_argument("--input", help="脚本文件 (.txt/.md 或 .json 场景列表)")
    ap.add_argument("--output", default="output.mp4", help="最终 MP4 路径 (默认 output.mp4)")
    ap.add_argument("--template", "--style", dest="style", default=DEFAULT_STYLE,
                     help="节目包 (设计系统) 名 (兼容旧名 --style); 默认 " + DEFAULT_STYLE
                     + "; 两个 pack 根（存量 path_b + 编译产物 path_c）下现存的包都可选，"
                       "名单由 `available_templates()` 现算 (见 --list-templates)"
                     + ". 见 templates/hyperframes_path_b/ 与 news-workflow/SKILL.md 模板决策树")
    ap.add_argument("--list-templates", action="store_true",
                    help="打印当前可点名的 pack 名单（含编译包）后退出")
    ap.add_argument("--voice", default="zh-CN-XiaoxiaoNeural", help="edge-tts 音色")
    ap.add_argument("--resolution", default="1080x1920", help="分辨率, 如 1080x1920(竖) 或 1920x1080(横)")
    ap.add_argument("--doctor", action="store_true", help="只做环境自检")
    ap.add_argument("--kicker", help="全片眉标(如栏目名), 不传则用版式自带标签")
    ap.add_argument("--layout", help="全片强制点名同一版式(默认按分镜形态自动选); "
                                     "只对当前 pack 已有的真版式有效")
    ap.add_argument("--source", help="来源/频道署名, 引文与收口版式必需")
    ap.add_argument("--aigc-producer", default=DEFAULT_AIGC_PRODUCER,
                    help="AIGC 标识里的生成者(ContentProducer): 名称或 27 位编码, 默认 "
                         + DEFAULT_AIGC_PRODUCER + "。正式发布建议填账号主体名称 "
                         "(GB 45438-2025 允许写名称; 不要填身份证号等个人敏感信息)")
    ap.add_argument("--aigc-label", default=AIGC_LABEL_TEXT,
                    help=f"显式角标文字(默认 %(default)s), 开场 "
                         f"{AIGC_LABEL_ON_SECONDS:g} 秒常驻左下角")
    ap.add_argument("--draft", action="store_true",
                    help="草稿轨: 不烧 AIGC 角标、不写隐式元数据, 侧车只落 "
                         "draft 一段(不含 explicit/metadata_key/implicit) —— "
                         "check_publishable.py 读到即拒绝发布。调版式/看效果用它, 交付不用。"
                         "覆盖姿态文件里的 render=full/no-badge")
    ap.add_argument("--no-badge", action="store_true",
                    help="交付轨但不烧 ① 画面角标(ARCHITECTURE D14): ② 隐式元数据照写并读回, "
                         "产物**可发布**, 代价是发布必须带 ③ 自主声明"
                         "(check_publishable.py 对这份台账拒绝 undeclared)。"
                         "与 --draft / --deliver 同时给 = 报错")
    ap.add_argument("--deliver", action="store_true",
                    help="反向旗标: 本次强制走完整交付轨(烧 ① + 写 ②), 用来盖掉 "
                         "routes/news/aigc-mode.json 里的 render=no-badge/draft; "
                         "与 --draft / --no-badge 同时给 = 报错")
    ap.add_argument("--fps", type=int, default=DEFAULT_FPS, help=f"渲染帧率 (默认 {DEFAULT_FPS})")
    ap.add_argument("--quality", default=DEFAULT_QUALITY, choices=QUALITY_CHOICES,
                    help=f"渲染质量 (默认 {DEFAULT_QUALITY})")
    ap.add_argument("--gpu", action="store_true",
                    help="改用 GPU 光栅化 (--browser-gpu)。默认软件光栅：硬件路径实测不产出"
                         "逐字节可复现的码流（判据 4a），只在排查渲染本身时开")
    ap.add_argument("--work-dir", help="指定中间文件目录(存在则复用, 且不清理)")
    ap.add_argument("--hyperframes-bin",
                    help="显式指定 hyperframes 可执行(跳过自动探测); 排查与新机器用")
    ap.add_argument("--check-only", action="store_true", help="只发射+版式自检+check 门禁, 不渲染")
    ap.add_argument("--skip-gate", action="store_true",
                    help="跳过 check 门禁(仅限排查门禁本身, 成片不认)")
    ap.add_argument("--skip-render", action="store_true", help="只生成音频+HTML, 不渲染(调试用)")
    ap.add_argument("--keep", action="store_true", help="保留中间文件")
    ap.add_argument("--timing-out", help="分段计时 JSON 落点(默认 <成片目录>/timing.json)")
    args = ap.parse_args()

    if args.list_templates:
        for name in available_templates():
            print(name)
        sys.exit(0)

    if args.hyperframes_bin:
        hf_init(args.hyperframes_bin)

    if args.check_only or args.skip_render:
        # 这两条路存在的意义就是留给人复看中间产物, 收尾删目录等于白跑
        args.keep = True

    if args.doctor:
        sys.exit(0 if doctor() else 1)

    if not args.input:
        ap.error("必须提供 --input 脚本文件 (或用 --doctor 自检)")

    # 包名校验从 argparse 的 `choices` 挪到这里：可寻址范围取决于**磁盘上现在有哪些包**
    # （编译一套就多一套），建 parser 时算一次就冻住了，P5 每套都要回来改这个文件 = 双轨失效。
    known_templates = available_templates()
    if args.style not in known_templates:
        ap.error(f"--template {args.style!r} 不是可点名的 pack"
                 f"（两个根下现有 {len(known_templates)} 个）: "
                 + ", ".join(known_templates))

    if not os.path.isfile(args.input):
        log(f"❌ 找不到输入文件: {args.input}")
        sys.exit(1)

    try:
        w, h = parse_resolution(args.resolution)
    except EmitterError as exc:
        log(f"❌ {exc}")
        sys.exit(1)

    # 标识开关: 旗标 > 姿态文件 > 代码默认(全开)。姿态文件是"临时把标关掉"的
    # 唯一落点 —— 代码默认值不跟着一次会话的偏好改(ARCHITECTURE D11)。
    # 渲染层从两档变三档(D14): full / no-badge / draft, 三个旗标只能挑一个。
    try:
        aigc_posture = aigc_mode.load_mode()
        render_mode, render_cause = aigc_mode.resolve_render(
            aigc_posture, draft=args.draft, deliver=args.deliver,
            no_badge=args.no_badge)
    except aigc_mode.ModeError as exc:
        log(f"❌ {exc}")
        sys.exit(1)
    is_draft = render_mode == "draft"
    log(f"[aigc] {aigc_mode.describe(aigc_posture)}")
    log(f"[aigc] 渲染层开关 → {render_cause} → {aigc_mode.RENDER_WHAT[render_mode]}")

    work = args.work_dir or default_work_dir()
    os.makedirs(work, exist_ok=True)

    try:
        with timed("parse"):
            scenes = parse_input(read_text(args.input))
            if not scenes:
                log("❌ 输入未解析出任何分镜")
                sys.exit(1)
            log(f"解析到 {len(scenes)} 个分镜 | 设计系统 {args.style} | {w}x{h}")

            pack = load_style_pack(args.style)
            register_indexed_derivers(
                set().union(*(contract_ids(l) for l in pack["layouts"].values()))
            )

        with timed("dub"):
            if args.skip_render:
                # 没有配音就没有真实时长, 用文本估算保证发射链路照样能验
                audio_files = []
                durations = [estimate_duration(sc["body"]) for sc in scenes]
                scene_cues = [fallback_scene_cues(sc["body"], dur, i)
                              for i, (sc, dur) in enumerate(zip(scenes, durations), 1)]
            else:
                audio_files, scene_cues, durations = synthesize_audio(
                    scenes, args.voice, work)

        ctx_base = {
            "kicker": args.kicker,
            "source": args.source,
            "layout": args.layout,
            "overrides": {},
        }

        with timed("images"):
            # 逐镜取图 (best-effort: 网络/授权/尺寸/相关性任何失败都降级为该镜无图)
            # --skip-render 与 --check-only 不打网络, 全部降级为无图。
            if args.skip_render or args.check_only:
                image_records = [None] * len(scenes)
                log("图: 跳过 (--skip-render / --check-only 不取图)")
            else:
                image_records = []
                for i, sc in enumerate(scenes, 1):
                    rec = _resolve_shot_image(work, i, sc, ctx_base, log=log)
                    image_records.append(rec)
                    if rec is not None:
                        log(f"  镜{i} 图: {rec['title']} ({rec['width']}x{rec['height']}, {rec['license']})")
                    else:
                        log(f"  镜{i} 图: 降级为无图")
        with timed("emit"):
            # 编译包（path_c）把字幕收进 HyperFrames 2 轨（传 scene_cues）；存量手发包不传，
            # 字幕仍走烧录 ASS。这条开关的唯一判据是 pack 有没有 spec.toml，不在这里猜。
            shots = emit_composition(pack, scenes, durations, work, ctx_base, w, h,
                                     audio_files, image_records,
                                     scene_cues=scene_cues if pack.get("compiled") else None)
            log(f"→ 合成 HTML 已生成: {os.path.join(work, 'index.html')}")

        with timed("gate"):
            gate_layout_selfcheck(work)
            if args.check_only:
                gate_hyperframes_check(work)
                log(f"✅ 发射与门禁通过 (未渲染)。工程目录: {os.path.abspath(work)}")
                sys.exit(0)
            if args.skip_render:
                log("⏭  --skip-render 已设, 跳过门禁与渲染。中间文件在: " + work)
                sys.exit(0)
            if args.skip_gate:
                log("⚠️  --skip-gate 已设, 跳过 check 门禁 (成片不视为合格)")
            else:
                gate_hyperframes_check(work)

        with timed("render"):
            # ⑥ HyperFrames 渲染静帧视频
            silent = os.path.join(work, "silent.mp4")
            log("→ HyperFrames 渲染画面 (首次会下载 Chrome, 请耐心等待)")
            # `-q` 是短选项, 引擎不替短选项剥 `=`: 实测 `-q=delivery` 把字面量 "=delivery"
            # 当值送进校验, 直接 "Invalid quality" 退出。带 `=` 必须写长选项 `--quality=`。
            render_cmd = hf_argv("render", "-c", "index.html",
                                 "-o", "silent.mp4", "-f", str(args.fps),
                                 f"--quality={args.quality}")
            # 默认走**软件光栅**（判据 4a 的决定性证据）：同一次发射渲染两遍，
            # 硬件路径（ANGLE / 本机 Intel Arc）的 H.264 码流两次不同 —— 最终几何实测
            # 1290 帧里编译包 464 帧、存量包 710 帧像素不同（两次流哈希也不同）；
            # `--no-browser-gpu` 两遍逐帧 md5 全同、流哈希逐字节一致。存量包同样复现，
            # 所以这不是编译包引入的，但产线的"同稿同片"口径必须由发射器钉住，不能靠机器。
            # 代价：软件光栅更慢（渲染段 编译包 61.4/59.9s vs 硬件 57.2/48.9s；
            # 存量包 66.0/63.2s vs 硬件 40.9/36.2s），但硬件那两条时间自身就有 17% 抖动，
            # 而确定性是门禁、时长只是预算。`--gpu` 保留给"我就是想看硬件那条路"。
            render_cmd.append("--browser-gpu" if args.gpu else "--no-browser-gpu")
            # HyperFrames 要求入口文件必须留在项目目录内("Invalid composition path")，
            # 因此以 work 为 cwd、传相对路径，而不是传 Temp 下的绝对路径。
            r = run(render_cmd, cwd=work)
            if r.returncode != 0 or not os.path.exists(silent):
                raise EmitterError(
                    "HyperFrames 渲染失败。常见原因: 未装 Chrome(运行 npx hyperframes browser ensure) "
                    "/ 未装 ffmpeg / 网络受限")

        with timed("motion"):
            # ⑦ 动量审计 (判据 3): 每镜尾段仍在变化才算过
            audit_motion(silent, shots, work)

        with timed("mux"):
            # ⑧ 拼音频 + 烧字幕
            cues = collect_cues(scene_cues, durations, caption_line_chars(w, h))
            log(f"字幕轨: {len(cues)} 条")
            merged = ["WEBVTT", ""]
            for s, e, text in cues:
                merged += [f"{vtt_time(s)} --> {vtt_time(e)}", text.replace("\\N", "\n"), ""]
            write_text(os.path.join(work, "subs.vtt"), "\n".join(merged))  # 备查/可上传平台
            final = args.output
            os.makedirs(os.path.dirname(os.path.abspath(final)) or ".", exist_ok=True)
            log(f"→ ffmpeg 合成最终视频: {final}")
            # 编译包（path_c）字幕已收进 HyperFrames 2 轨渲染进画面，烧录 ASS 只留角标：
            # 这里传空 cue，mux_and_burn 靠 burn_badge 仍走滤镜烧开场 AIGC 标识。
            # subs.vtt 照旧落盘（上传平台用的外挂字幕，与成片烧录无关）。
            ass_cues = [] if pack.get("compiled") else cues
            if pack.get("compiled"):
                log("字幕: 编译包 → 字幕在 HyperFrames 内，ASS 只烧 AIGC 角标")
            # 显式标识时长 = 开场 AIGC_LABEL_ON_SECONDS 秒(不足则等于全片时长),
            # 由 mux_and_burn 卡 ≥ AIGC_LABEL_MIN_SECONDS: 单镜短片的真实时长可以低到
            # MIN_SLOT_SECONDS(1s), 达不到国标 2 秒线, 必须挡。
            # (这条线只在真烧角标那一档生效 —— no-badge 没有画面标识, 见 D14)
            badge_seconds = aigc_badge_seconds(sum(durations))
            aigc_meta = mux_and_burn(silent, audio_files, ass_cues, work, final, w, h,
                                     aigc_badge_seconds=badge_seconds,
                                     aigc_producer=args.aigc_producer,
                                     aigc_label=args.aigc_label,
                                     render=render_mode, render_cause=render_cause)
            # 标识台账: 发布环节(douyin-upload)要照着它做平台侧自主声明,
            # 监管要举证时也拿这份对着成片核。只随成片走, 不进工作目录。
            # glyph_height_px 是**合规线上真正被量的那个数**(字芯高, 不是 em 高),
            # 落进台账就不用举证时再让人重算一遍字面率。
            # 草稿的台账**故意不含 metadata_key / implicit / explicit 三段** ——
            # 缺什么就记什么缺, 而不是写一堆 false 装作"标识在只是没开";
            # check_publishable.py 认这三段的存在性, 草稿因此过不了发布闸门。
            # no-badge(D14)反过来: ② 在、① 被点名关掉, 所以 explicit 段**必须存在**并写明
            # burned_in=false + 谁关的(disabled_by) + 怎么开回来(to_enable)。
            # 「关了什么记什么关」与「缺什么记什么缺」是两件事 —— 台账留空等于让下一个人
            # 猜这版是没烧还是烧丢了。
            badge_fs = aigc_badge_font_size(w, h)
            if is_draft:
                to_publish = ("去掉 --draft 重渲一次, 让 ①② 落进成片" if args.draft else
                              "把 routes/news/aigc-mode.json 的 render 改回 full"
                              "(或渲染时加 --deliver)再重渲一次, 让 ①② 落进成片")
                sidecar = {
                    "file": os.path.basename(final),
                    "switch": render_cause,
                    "draft": {
                        "reason": f"草稿渲染[{render_cause}]: ① 画面角标与 ② 隐式元数据都没有",
                        "burned_in": False,
                        "to_publish": to_publish,
                    },
                    "resolution": f"{w}x{h}",
                }
            else:
                if render_mode == "full":
                    explicit = {
                        "text": args.aigc_label,
                        "position": "bottom-left",
                        "font_size_px": badge_fs,
                        "glyph_height_px": round(badge_fs * AIGC_LABEL_GLYPH_RATIO, 1),
                        "short_side_px": min(w, h),
                        "margin_v_px": aigc_badge_margin_v(w, h),
                        "shown_seconds": round(badge_seconds, 3),
                        "burned_in": True,
                    }
                else:
                    explicit = {
                        "burned_in": False,
                        "disabled_by": render_cause,
                        "to_enable": ("去掉 --no-badge 重渲一次(或加 --deliver), 让 ① 落进成片"
                                      if args.no_badge else
                                      "把 routes/news/aigc-mode.json 的 render 改回 full"
                                      "(或渲染时加 --deliver)再重渲一次, 让 ① 落进成片"),
                    }
                sidecar = {
                    "file": os.path.basename(final),
                    "switch": render_cause,
                    "metadata_key": AIGC_METADATA_KEY,
                    "implicit": json.loads(aigc_meta),
                    "explicit": explicit,
                    "resolution": f"{w}x{h}",
                }
            write_text(os.path.join(os.path.dirname(os.path.abspath(final)), "aigc.json"),
                       json.dumps(sidecar, ensure_ascii=False, indent=2))

        with timed("finalize"):
            # 图片授权台账: media-manifest.json 只活在临时工作目录, 渲染完就被清 ——
            # CC BY 的署名义务与授权追溯靠它, 必须拷到成片旁跟随成片归档。
            media_manifest = os.path.join(work, "media", "media-manifest.json")
            if os.path.isfile(media_manifest):
                shutil.copyfile(media_manifest,
                                os.path.join(os.path.dirname(os.path.abspath(final)), "media-credits.json"))
                log("→ 图片授权台账已归档: media-credits.json")

            # ⑨ 联络表: 逐镜一帧, 人工验收比对
            build_contact_sheet(silent, shots, os.path.dirname(os.path.abspath(final)), work)

            # 发射事实落盘, 复盘时能对着成片看每镜填了什么
            write_text(os.path.join(work, "shots.json"),
                       json.dumps(shots, ensure_ascii=False, indent=2))
            if args.work_dir:
                shutil.copyfile(os.path.join(work, "shots.json"),
                                os.path.join(os.path.dirname(os.path.abspath(final)), "shots.json"))
        log(f"✅ 完成! 最终视频: {os.path.abspath(final)}")
    except (EmitterError, FileNotFoundError, OSError) as exc:
        log(f"❌ {exc}")
        sys.exit(1)
    finally:
        write_timings(args.timing_out
                      or os.path.join(os.path.dirname(os.path.abspath(args.output)), "timing.json"))
        if not args.keep and not args.work_dir:
            shutil.rmtree(work, ignore_errors=True)
        else:
            log(f"中间文件保留在: {work}")


if __name__ == "__main__":
    main()
