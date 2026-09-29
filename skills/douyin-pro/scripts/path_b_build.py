#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Path B 全链路串联脚本 · 抖音短视频生产专家团
============================================================
把"优化好的脚本文字"变成带 AI 配音 + 字幕的竖屏 MP4，全程零云费:

    脚本文本 ──▶ ① 分段            (按空行 / JSON 场景)
              ──▶ ② edge-tts 配音   (免费, 微软接口) → 每段 .mp3 + .vtt
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
    - edge-tts          (pip install edge-tts)
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
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

import layout_selfcheck


# ------------------------- 常量 (禁止魔法值) -------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_ROOT = os.path.join(os.path.dirname(SCRIPT_DIR), "templates", "hyperframes_path_b")
DEFAULT_STYLE = "news-coral"

#: 12 个节目包 (设计系统 = 模板 = style; 三者同义, --template 与 --style 都接这同一组值)。
#: 顺序按"用途+情绪"二维分组, 默认 DEFAULT_STYLE 仍为 news-coral (人物故事型, 兼容存量稿件)。
#: 增加新模板只动这里 + templates/hyperframes_path_b/<name>/ 落地, 不动发射器主逻辑。
ALL_TEMPLATES = (
    "news-coral",      # T1  人物故事 / 反转 / 单条深挖 (已有完整 7 个版式)
    "news-ink",        # T2  调查 / 深度揭露 / 长文
    "news-policy",     # T3  政策 / 法规 / 通知
    "news-stat",       # T4  数据 / 排行 / 数字冲击
    "news-onsite",     # T5  现场 / 突发 / 抢险
    "news-bulletin",   # T6  多事件速报 / 整点新闻
    "news-explainer",  # T7  科普 / 原理 / 图解
    "news-alert",      # T8  应急 / 防诈 / 健康警示
    "news-thread",     # T9  节日 / 纪念 / 专题
    "news-takes",      # T10 观点 / 评论 / 专栏
    "news-blast",      # T11 体育 / 比分 / 实时赛事
    "news-world",      # T12 国际 / 战况 / 地理
)
#: --style / --template 选择映射; 选模板看 news-workflow/SKILL.md 的"模板决策树"或
#: routes/news/MEMORY.md videos[].template 字段 (12 个 pack 任何一个都合法)。

#: 占位 composition 的文件名(=版式名)。每个新 pack 先放它凑齐三层目录, 但它
#: **不是版式**: `load_style_pack` 直接跳过它, 于是"只有占位"的 pack 会在加载阶段
#: 就报"没有可用版式", 而不是渲染到第 1 镜才抛"填不满任何版式"(决策 D7)。
PLACEHOLDER_LAYOUT = "placeholder"

# ------------------------- AIGC 标识 (合规硬要求) -------------------------
#: 依据: 《人工智能生成合成内容标识办法》(2025-09-01 施行) § 4/§ 5 +
#: 强制性国标 GB 45438-2025《网络安全技术 人工智能生成合成内容标识方法》。
#: 显式标识 (§ 4-四): 视频起始画面与播放周边要有显著提示标识; 国标另要求
#: **文字高度 ≥ 画面最短边的 5%**、**持续时长 ≥ 2 秒**。本实现取"全程左上角角标",
#: 一次满足起始/周边/中间/末尾四个位置, 字号按最短边 7.9% (字面率实测值换算来的,
#: 见 AIGC_LABEL_GLYPH_RATIO 与 aigc_badge_font_size)。
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
#: 所以"字号按 5% 取"当场不合规。字号 = 线 / ratio, 再乘余量 AIGC_LABEL_HEADROOM
#: (换字体的字面率只会更低不会更高, 1.15 是把这一档余量写实, 不是审美)。
AIGC_LABEL_GLYPH_RATIO = 0.729
AIGC_LABEL_FLOOR_FRAC = 0.05
AIGC_LABEL_HEADROOM = 1.15
AIGC_LABEL_SHORT_SIDE_FRAC = round(AIGC_LABEL_FLOOR_FRAC / AIGC_LABEL_GLYPH_RATIO
                                  * AIGC_LABEL_HEADROOM, 4)
AIGC_LABEL_MARGIN_W_FRAC = 0.045     # 距左边 = 宽 * 0.045
AIGC_LABEL_MARGIN_H_FRAC = 0.022     # 距顶边 = 高 * 0.022 (避开状态栏/刘海区)
AIGC_PRODUCE_ID_BYTES = 32           # 内容编号取渲染产物哈希的前 N 位十六进制
AIGC_INTEGRITY_CODE_BYTES = 40       # ReservedCode1 取哈希的前 N 位十六进制
#: 显式标识最短持续时长(秒)。国标对视频显式标识的量化线: 文字高度 ≥ 最短边 5%、
#: 持续 ≥ 2 秒。本实现让角标贯穿全片, 但**仍要挡**住"片长不足 2 秒"的极端输入 ——
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
    "#f5f0e8": TONE_LIGHT,   # cream 主地面
    "#e8e0d4": TONE_LIGHT,   # cream-dark 引用块地面
    "#1a1a1a": TONE_DARK,    # ink 地面
    # news-policy (frame.md §2): 米白公文纸两档都归明, 暗地面走公文蓝而不是黑 ——
    # 公文系统里没有"黑底"这一层, 翻面靠 cobalt #1F3A68(纸字在其上 9.84, 见 frame.md §2.1)。
    "#f5efe3": TONE_LIGHT,   # paper 主地面
    "#e8dfcb": TONE_LIGHT,   # paper-dark 卡衬地面(条目卡底)
    "#1f3a68": TONE_DARK,    # cobalt 地面(暗面翻面 + closer 书挡)
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

# 整条字幕事件: 时间轴行 + 其后直到空行/文件尾的文本
CUE_RE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*"
    r"(\d{2}):(\d{2}):(\d{2})[.,](\d{3})[^\n]*\n(.*?)(?=\n[ \t]*\n|\Z)",
    re.S,
)

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
Style: AIGC,{font},{aigc_fs},&H00FFFFFF,&H000000FF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,{aigc_ol},1,7,{aml},{amr},{amv},134

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


def which(tool: str) -> str | None:
    return shutil.which(tool) or shutil.which(tool + ".exe")


def read_text(path: str, errors: str = "strict") -> str:
    with open(path, encoding="utf-8", errors=errors) as f:
        return f.read()


def write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


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


def collect_cues(sub_files, durations, line_chars, max_lines=CAPTION_MAX_LINES):
    """把 edge-tts 的分段 .vtt 按分镜起始时间平移, 汇总成 (start, end, text) 列表。

    行宽与行数上限见 caption_line_chars / split_cue。
    """
    cues = []
    start = 0.0
    for path, dur in zip(sub_files, durations):
        raw = read_text(path).replace("\r\n", "\n").replace("\r", "\n")
        for m in CUE_RE.finditer(raw):
            g = m.groups()
            t1 = int(g[0]) * 3600 + int(g[1]) * 60 + int(g[2]) + int(g[3]) / 1000.0
            t2 = int(g[4]) * 3600 + int(g[5]) * 60 + int(g[6]) + int(g[7]) / 1000.0
            text = " ".join(line.strip() for line in g[8].split("\n") if line.strip())
            if not text:
                continue
            # 平移后夹到本分镜区间内, 防止跨场景字幕重叠
            s = min(start + t1, start + max(0.0, dur - 0.2))
            e = min(start + t2, start + dur)
            if e - s < 0.15:
                e = min(s + 0.8, start + dur)
            cues.extend(split_cue(s, e, text, line_chars, max_lines))
        start += dur
    return cues


def aigc_badge_font_size(w: int, h: int) -> int:
    """AIGC 角标字号 = 画面**最短边** × AIGC_LABEL_SHORT_SIDE_FRAC。

    两条容易踩空的量纲, 都在这里处理:

    1. **按最短边, 不按高度**。国标写的是"画面最短边的 5%": 竖屏 1080×1920 最短边是
       宽 1080(线 = 54px), 横屏 1920×1080 最短边反过来是**高** 1080 —— 拿高度当基准
       写死会在横屏上算错。
    2. **字号 ≠ 字高**。ASS 的 FontSize 是 em 高度, 国标量的是字形实际高度。
       0.065 这一档是**推**出来的、错的: 端到端成片实测(Microsoft YaHei,
       1080×1920, FontSize 70)白色字芯只有 51px, 字面率 0.729, 低于 54px 的线 ——
       也就是说上一版按 6.5% 出的片**并不合规**, 而它自己不会报错。
       现在把实测字面率写成 AIGC_LABEL_GLYPH_RATIO, 字号 = 5% / 0.729 × 1.15
       ≈ 最短边 7.89% → 竖屏 FontSize 85 → 字芯约 62px(线的 115%)。

    残余风险(如实写): 0.729 是**这一台机器、这一个字体、这一个分辨率**上量来的,
    不是通用常数。换 pack / 换字体 / 改输出分辨率后必须重量一次(成片取一帧, 量左上角
    白色字芯的纵向像素数 ÷ FontSize), 别默认推导值够用; `aigc.json` 里落了
    font_size_px 与 short_side_px, 对着 contact-sheet.jpg 就能核。
    """
    return max(1, int(round(min(w, h) * AIGC_LABEL_SHORT_SIDE_FRAC)))


def build_ass(cues, w: int, h: int, font: str = "Microsoft YaHei",
              aigc_text: str | None = AIGC_LABEL_TEXT,
              aigc_seconds: float = 0.0) -> str:
    """显式写 PlayRes, 字号按输出高度推导。

    ⚠️ 不要用 subtitles 的 force_style 调字号: libass 读 VTT 时脚本坐标默认
    只有 288 高, FontSize=36 会被放大到画面 12% 高, 竖屏上直接溢出屏幕。

    AIGC 显式标识: `aigc_text` 非空且 `aigc_seconds` > 0 时, 额外挂一条**贯穿全片**
    的 `AIGC` 样式事件(Alignment 7 = 左上角, Layer 1 压在字幕之上), 一次满足
    《标识办法》§ 4-四 的"起始画面 + 播放周边 + 中间 + 末尾"与国标"持续 ≥ 2 秒"。
    为什么落左上角(实测 news-coral 各版式): 右上角被 36cqw 的壁纸序号占了
    (top:3cqh / right:4cqw, 横向约 62→96cqw), 下方 y≥0.80 是字幕带; 左上角这条
    (竖屏 1080×1920 实测量: MarginL 48px≈4.4cqw, FontSize 85 → 字芯 62px,
    "AI 生成合成内容" 九字符占 522px≈48.3cqw, 纵向 57→118px≈6.1cqh)是全片唯一
    无人认领的区域 —— 离 62cqw 的序号还剩约 14cqw 间隙, 眉标从 17cqh 才起。
    换 pack / 换字号后这个间隙要重算, 别默认它永远不撞。
    """
    aigc_fs = aigc_badge_font_size(w, h)
    header = ASS_HEADER.format(
        w=w, h=h, font=font,
        fs=caption_font_size(h),
        ol=max(2, int(round(h / ASS_OUTLINE_H_FRAC))),
        ml=int(w * ASS_MARGIN_W_FRAC), mr=int(w * ASS_MARGIN_W_FRAC),
        mv=int(h * ASS_MARGIN_BOTTOM_H_FRAC),
        aigc_fs=aigc_fs,
        aigc_ol=max(1, int(round(aigc_fs / 16))),
        aml=int(w * AIGC_LABEL_MARGIN_W_FRAC), amr=int(w * AIGC_LABEL_MARGIN_W_FRAC),
        amv=int(h * AIGC_LABEL_MARGIN_H_FRAC),
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
    comp_dir = os.path.join(TEMPLATE_ROOT, style, "compositions")
    if not os.path.isdir(comp_dir):
        return False
    return any(f.endswith(".html") and f != f"{PLACEHOLDER_LAYOUT}.html"
               for f in os.listdir(comp_dir))


def ready_packs() -> list[str]:
    """当前可选出真版式的 pack 名单(顺序跟 ALL_TEMPLATES)。"""
    return [s for s in ALL_TEMPLATES if pack_has_real_layout(s)]


def load_style_pack(style: str) -> dict:
    """读 ``templates/hyperframes_path_b/<style>/``: 宿主骨架 + 各版式契约。

    ``placeholder.html`` 不进 ``layouts`` (D7): 它只是把三层目录凑齐的壳, 不是版式。
    跳掉之后若一个版式都不剩, 就在这里停 —— 报"这个 pack 还没有真版式 + 现在哪些有",
    而不是等配完音、发射到第 1 镜才抛"填不满任何版式"(那要白跑一趟网络与渲染)。
    """
    pack_dir = os.path.join(TEMPLATE_ROOT, style)
    host_path = os.path.join(pack_dir, "host.html")
    comp_dir = os.path.join(pack_dir, "compositions")
    if not os.path.isdir(pack_dir):
        raise EmitterError(f"设计系统包不存在: {pack_dir}")
    if not os.path.isfile(host_path) or not os.path.isdir(comp_dir):
        raise EmitterError(f"{pack_dir} 缺少 host.html 或 compositions/")
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
    return {"name": style, "dir": pack_dir, "host": read_text(host_path),
            "compositions_dir": comp_dir, "layouts": layouts}


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

#: 条目类变量名的形态: item1Label / step2Body / …
INDEXED_VAR_RE = re.compile(r"^(item|step)([1-9])(Label|Value|Body)$")


def register_indexed_derivers(variable_ids) -> None:
    """按需把 itemN*/stepN* 的推导器挂上表(新增版式不必改这张表)。"""
    for var_id in variable_ids:
        match = INDEXED_VAR_RE.match(var_id)
        if not match:
            continue
        DERIVERS.setdefault(var_id, _indexed_item(var_id, int(match.group(2)) - 1))


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
    if ctx["is_first"]:
        candidates.append("hook")
    if ctx["is_last"]:
        candidates.append("closer")
    if scene.get("onscreen"):
        candidates.append("story")
    if len(facts) >= MIN_STAT_FACTS:
        candidates.append("stat")
    if scene.get("quote"):
        candidates.append("quote")
    if len(items) >= MIN_RAIL_ITEMS:
        candidates.append("catalog")
    if rail_ready(items):
        candidates.append("rail")
    # 兜底顺序: 整句版式优先(story), 条目/数据版式次之, 首尾专用版式最后
    candidates += ["story", "stat", "quote", "catalog", "rail", "closer", "hook"]
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


def emit_composition(pack: dict, scenes: list, durations: list, work_dir: str,
                     ctx_base: dict, w: int, h: int,
                     audio_files: list) -> list[dict]:
    """逐镜选版式 + 填变量 + 生成宿主与挂载, 并把用过的版式文件复制进工作目录。"""
    mounts, audios, shots = [], [], []
    start = 0.0
    prev_ground_tone = None
    for i, (scene, dur) in enumerate(zip(scenes, durations), 1):
        ctx = dict(ctx_base)
        ctx.update({
            "shot_no": i,
            "shot_ordinal": f"{i:02d}",
            "slot_seconds": round(dur, 3),
            "is_first": i == 1,
            "is_last": i == len(scenes),
            "prev_ground_tone": prev_ground_tone,
        })
        layout_name = choose_layout(pack, scene, ctx)
        layout = pack["layouts"][layout_name]
        values = fill_variables(layout, scene, ctx)
        mounts.append(emit_mount(i, layout, values, start, dur, w, h))
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
    """check --strict 是渲染前的硬门禁: 有 error/warning 就不许烧 GPU 时间。"""
    json_path = os.path.join(work_dir, "check.json")
    err_path = os.path.join(work_dir, "check.err.txt")
    with open(json_path, "wb") as out, open(err_path, "wb") as err:
        r = run(["npx", "-y", "hyperframes", "check", ".", "--strict", "--json",
                 f"--caption-zone={CAPTION_ZONE}"], cwd=work_dir, stdout=out, stderr=err)
    if r.returncode != 0:
        tail = summarize_check_json(json_path)
        log(f"  check 输出尾部: {tail}")
        log(f"  详细 stderr: {err_path}")
        raise EmitterError("hyperframes check --strict 未通过, 已拒绝渲染")
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
        run(["npx", "-y", "hyperframes", "doctor"])
    log("=== 自检结束: " + ("全部就绪 ✅" if ok else "有缺失项, 见上方 ❌") + " ===")
    return ok


# ------------------------- 配音 -------------------------
def synthesize_audio(scenes, voice_default, work_dir):
    """逐段 edge-tts 配音, 返回 (mp3 列表, vtt 列表, 时长列表)。"""
    edge_tts_bin = which("edge-tts")
    if not edge_tts_bin:
        raise EmitterError(
            "找不到 edge-tts 命令。请先: pip install edge-tts (并确认其 Scripts 目录在 PATH)")
    audio_files, sub_files, durations = [], [], []
    for i, sc in enumerate(scenes, 1):
        voice = sc.get("voice") or voice_default
        mp3 = os.path.join(work_dir, f"scene_{i}.mp3")
        vtt = os.path.join(work_dir, f"scene_{i}.vtt")
        log(f"→ 配音 分镜{i} (voice={voice})")
        # Windows 下 run() 走 shell=True(cmd.exe)，参数里的换行会截断命令，
        # 导致 --write-media 丢失、音频被吐到 stdout。朗读语义不受影响，压平空白。
        speak_text = " ".join(sc["body"].split())
        if not speak_text:
            raise EmitterError(f"分镜{i} 正文为空, 无话可配 —— 删掉这条或补正文")
        r = run([edge_tts_bin, "--voice", voice, "--text", speak_text,
                 "--write-media", mp3, "--write-subtitles", vtt])
        if r.returncode != 0 or not os.path.exists(mp3):
            raise EmitterError(
                f"分镜{i} 配音失败 (检查网络是否能连微软语音服务 / edge-tts 是否安装)")
        dur = ffprobe_duration(mp3)
        if dur is None:
            dur = estimate_duration(sc["body"])
            log(f"  (ffprobe 不可用, 估算时长 {dur:.1f}s)")
        else:
            log(f"  时长 {dur:.1f}s")
        if dur < MIN_SLOT_SECONDS:
            raise EmitterError(
                f"分镜{i} 配音只有 {dur:.2f}s, 低于版式契约下限 {MIN_SLOT_SECONDS}s —— "
                "这一镜太短, 请与相邻分镜合并"
            )
        audio_files.append(mp3)
        sub_files.append(vtt)
        durations.append(dur)
    return audio_files, sub_files, durations


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
                 aigc_label: str = AIGC_LABEL_TEXT):
    """拼配音 → 烧 ASS 字幕(含 AIGC 显式角标) → 写 AIGC 隐式元数据 → 读回核验。

    `aigc_badge_seconds` 是角标持续时长, 主流程传全片时长(贯穿); 低于
    `AIGC_LABEL_MIN_SECONDS` 直接停机 —— 《标识办法》§ 4-四 要视频起始画面与播放
    周边有显著标识, 国标另量化了"文字高度 ≥ 最短边 5%、持续 ≥ 2 秒"两条线。
    隐式标识按 GB 45438-2025 附录 E 写进容器元数据, 写完 ffprobe 读回核验,
    不一致就抛 EmitterError。字幕轨为空时降级为只合成音频(不许让成片不可用)。
    返回真正落到文件里的那份标识 JSON, 供调用方落 sidecar 备查。
    """
    if not aigc_producer:
        # 不提供"关掉标识"这条路: 《标识办法》§ 2 要求"应当"添加, 拿空参数当开关
        # 等于给用户一个违法的便利。要改的是标识内容(--aigc-producer 填主体名), 不是有无。
        raise EmitterError(
            "AIGC 标识不可关闭 (aigc_producer 为空) —— 无标识成片不得交付, "
            "请填生成者名称: --aigc-producer <你的频道/主体名>")
    if aigc_badge_seconds < AIGC_LABEL_MIN_SECONDS:
        raise EmitterError(
            f"全片时长只有 {aigc_badge_seconds:.2f}s, 贯穿式角标达不到国标 "
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
    write_text(ass_path, build_ass(cues, w, h, aigc_text=aigc_label,
                                   aigc_seconds=aigc_badge_seconds))
    err_log = os.path.join(work_dir, "ffmpeg_final.log")
    # 明确取流: 视频只从渲染产物拿, 声音只从拼接好的 narration 拿。
    # 合成里现在挂了 <audio>, 渲染出的 silent.mp4 也可能带一层声音;
    # 不写 -map 的话 ffmpeg 会各挑一条, 轻则双配音, 重则选了没字幕的那条。
    stream_maps = ["-map", "0:v:0", "-map", "1:a:0"]
    # AIGC 隐式标识 (§5 要求"在生成合成内容文件组件中加元数据"):
    # 实测 `-movflags +faststart` 会把不认识的键**静默丢掉**(ffprobe 读不到、
    # 字节里也搜不到), 必须加 use_metadata_tags 才落到 mdta atom。
    movflags = ["-movflags", "+faststart+use_metadata_tags"]
    aigc_meta = aigc_metadata_json(aigc_producer, silent)
    meta_args = ["-metadata", f"{AIGC_METADATA_KEY}={aigc_meta}"]
    ff = which("ffmpeg") or "ffmpeg"
    if not cues:
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


def main():
    ap = argparse.ArgumentParser(description="Path B 免费端到端成片脚本 (设计系统驱动)")
    ap.add_argument("--input", help="脚本文件 (.txt/.md 或 .json 场景列表)")
    ap.add_argument("--output", default="output.mp4", help="最终 MP4 路径 (默认 output.mp4)")
    ap.add_argument("--template", "--style", dest="style", default=DEFAULT_STYLE,
                    choices=ALL_TEMPLATES,
                     help="节目包 (设计系统) 名 (兼容旧名 --style); 默认 " + DEFAULT_STYLE + "; 12 个可选项: " + ", ".join(ALL_TEMPLATES) + ". 见 templates/hyperframes_path_b/ 与 news-workflow/SKILL.md 模板决策树")
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
                    help="显式角标文字(默认 %(default)s), 贯穿全片显示在左上角")
    ap.add_argument("--fps", type=int, default=DEFAULT_FPS, help=f"渲染帧率 (默认 {DEFAULT_FPS})")
    ap.add_argument("--quality", default=DEFAULT_QUALITY, choices=QUALITY_CHOICES,
                    help=f"渲染质量 (默认 {DEFAULT_QUALITY})")
    ap.add_argument("--gpu", action="store_true", help="用 GPU 光栅化 (--browser-gpu, 本机 Intel Arc 实测可用)")
    ap.add_argument("--work-dir", help="指定中间文件目录(存在则复用, 且不清理)")
    ap.add_argument("--check-only", action="store_true", help="只发射+版式自检+check 门禁, 不渲染")
    ap.add_argument("--skip-gate", action="store_true",
                    help="跳过 check 门禁(仅限排查门禁本身, 成片不认)")
    ap.add_argument("--skip-render", action="store_true", help="只生成音频+HTML, 不渲染(调试用)")
    ap.add_argument("--keep", action="store_true", help="保留中间文件")
    args = ap.parse_args()

    if args.check_only or args.skip_render:
        # 这两条路存在的意义就是留给人复看中间产物, 收尾删目录等于白跑
        args.keep = True

    if args.doctor:
        sys.exit(0 if doctor() else 1)

    if not args.input:
        ap.error("必须提供 --input 脚本文件 (或用 --doctor 自检)")

    if not os.path.isfile(args.input):
        log(f"❌ 找不到输入文件: {args.input}")
        sys.exit(1)

    try:
        w, h = parse_resolution(args.resolution)
    except EmitterError as exc:
        log(f"❌ {exc}")
        sys.exit(1)

    work = args.work_dir or tempfile.mkdtemp(prefix="pathb_")
    os.makedirs(work, exist_ok=True)

    try:
        scenes = parse_input(read_text(args.input))
        if not scenes:
            log("❌ 输入未解析出任何分镜")
            sys.exit(1)
        log(f"解析到 {len(scenes)} 个分镜 | 设计系统 {args.style} | {w}x{h}")

        pack = load_style_pack(args.style)
        register_indexed_derivers(
            set().union(*(contract_ids(l) for l in pack["layouts"].values()))
        )

        if args.skip_render:
            # 没有配音就没有真实时长, 用文本估算保证发射链路照样能验
            audio_files, sub_files = [], []
            durations = [estimate_duration(sc["body"]) for sc in scenes]
        else:
            audio_files, sub_files, durations = synthesize_audio(scenes, args.voice, work)

        ctx_base = {
            "kicker": args.kicker,
            "source": args.source,
            "layout": args.layout,
            "overrides": {},
        }
        shots = emit_composition(pack, scenes, durations, work, ctx_base, w, h,
                                 audio_files)
        log(f"→ 合成 HTML 已生成: {os.path.join(work, 'index.html')}")

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

        # ⑥ HyperFrames 渲染静帧视频
        silent = os.path.join(work, "silent.mp4")
        log("→ HyperFrames 渲染画面 (首次会下载 Chrome, 请耐心等待)")
        # `-q` 是短选项, 引擎不替短选项剥 `=`: 实测 `-q=delivery` 把字面量 "=delivery"
        # 当值送进校验, 直接 "Invalid quality" 退出。带 `=` 必须写长选项 `--quality=`。
        render_cmd = ["npx", "-y", "hyperframes", "render", "-c", "index.html",
                      "-o", "silent.mp4", "-f", str(args.fps), f"--quality={args.quality}"]
        if args.gpu:
            render_cmd.append("--browser-gpu")
        # HyperFrames 要求入口文件必须留在项目目录内("Invalid composition path")，
        # 因此以 work 为 cwd、传相对路径，而不是传 Temp 下的绝对路径。
        r = run(render_cmd, cwd=work)
        if r.returncode != 0 or not os.path.exists(silent):
            raise EmitterError(
                "HyperFrames 渲染失败。常见原因: 未装 Chrome(运行 npx hyperframes browser ensure) "
                "/ 未装 ffmpeg / 网络受限")

        # ⑦ 动量审计 (判据 3): 每镜尾段仍在变化才算过
        audit_motion(silent, shots, work)

        # ⑧ 拼音频 + 烧字幕
        cues = collect_cues(sub_files, durations, caption_line_chars(w, h))
        log(f"字幕轨: {len(cues)} 条")
        merged = ["WEBVTT", ""]
        for s, e, text in cues:
            merged += [f"{vtt_time(s)} --> {vtt_time(e)}", text.replace("\\N", "\n"), ""]
        write_text(os.path.join(work, "subs.vtt"), "\n".join(merged))  # 备查/可上传平台
        final = args.output
        os.makedirs(os.path.dirname(os.path.abspath(final)) or ".", exist_ok=True)
        log(f"→ ffmpeg 合成最终视频: {final}")
        # 显式标识时长 = 全片时长(贯穿), 由 mux_and_burn 卡 ≥ AIGC_LABEL_MIN_SECONDS:
        # 单镜短片的真实时长可以低到 MIN_SLOT_SECONDS(1s), 达不到国标 2 秒线, 必须挡。
        badge_seconds = sum(durations)
        aigc_meta = mux_and_burn(silent, audio_files, cues, work, final, w, h,
                                 aigc_badge_seconds=badge_seconds,
                                 aigc_producer=args.aigc_producer,
                                 aigc_label=args.aigc_label)
        # 标识台账: 发布环节(douyin-upload)要照着它做平台侧自主声明,
        # 监管要举证时也拿这份对着成片核。只随成片走, 不进工作目录。
        write_text(os.path.join(os.path.dirname(os.path.abspath(final)), "aigc.json"),
                   json.dumps({
                       "file": os.path.basename(final),
                       "metadata_key": AIGC_METADATA_KEY,
                       "implicit": json.loads(aigc_meta),
                       "explicit": {
                           "text": args.aigc_label,
                           "position": "top-left",
                           "font_size_px": aigc_badge_font_size(w, h),
                           "short_side_px": min(w, h),
                           "shown_seconds": round(badge_seconds, 3),
                           "burned_in": True,
                       },
                       "resolution": f"{w}x{h}",
                   }, ensure_ascii=False, indent=2))

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
        if not args.keep and not args.work_dir:
            shutil.rmtree(work, ignore_errors=True)
        else:
            log(f"中间文件保留在: {work}")


if __name__ == "__main__":
    main()
