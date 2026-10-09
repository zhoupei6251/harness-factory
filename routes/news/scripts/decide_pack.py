"""
decide_pack.py - 新闻域 pack 决策工具

输入: 热点主题 (text) + 可选 metadata (类型/紧急度/长度/调性)
输出: 推荐 pack + 备选 + 理由 (3 选 1)

用法:
  python routes/news/scripts/decide_pack.py "老人捡垃圾 21年账户 42 万"
  python routes/news/scripts/decide_pack.py "国务院新规" --type policy --length 60
  python routes/news/scripts/decide_pack.py "地震现场救援" --type breaking --length 30
  python routes/news/scripts/decide_pack.py --list   # 列出全部 pack 分类
  python routes/news/scripts/decide_pack.py --explain news-coral-mono     # 解释某个 pack

设计: 关键词权重 + 类别 bucket + 调性匹配 + 长度适配

**pack 数量不写死在本文件**（D20, 2026-10-08）: 曾经这里与 pack-decision.md 都手写了
一个 pack 数，而 path_b_build.ALL_TEMPLATES 的真实数量与之不符 ——
实测 PACK_BUCKETS 的集合**正好覆盖全部真实模板**，错的只是那句字面文案。
本项目已吃过两次"手抄数字悄悄过期"的亏（ARCHITECTURE D15 记的「可渲染数」是同一个病），
所以这里一律现算，集合对不上由 curate_selftest.py 的
`t_decide_pack_covers_every_real_template` 拦。
"""
import re
import sys
import json
from pathlib import Path
from collections import defaultdict

_REPO_ROOT = Path(__file__).resolve().parents[3]

# pack 主气质 + 关键词 bucket（**数量不写死, 见 docstring 的 D20 说明**）
# 权重: 高 = 3 (决定性) / 中 = 2 (强) / 低 = 1 (辅助)
PACK_BUCKETS = {
    "person_story": {  # 人物/故事
        "label": "人物/故事",
        "primary": ["news-coral", "news-coral-mono"],
        "secondary": ["news-mosaic", "news-dusk"],
        "keywords": {
            "故事": 3, "人物": 3, "老人": 2, "孩子": 2, "他": 1, "她": 1,
            "家人": 2, "回忆": 2, "采访": 2, "经历": 2, "感人": 3,
            "心酸": 3, "温暖": 2, "情感": 2, "故事": 3, "人物": 3,
            "坚持": 2, "梦想": 2, "传承": 2, "童年": 2, "乡愁": 2,
        },
    },
    "investigation": {  # 调查/揭露
        "label": "调查/揭露",
        "primary": ["news-ink", "news-ink-graphite"],
        "secondary": ["news-noir"],
        "keywords": {
            "调查": 3, "揭露": 3, "卧底": 3, "追踪": 3, "暗访": 3,
            "曝光": 3, "深度": 2, "长文": 2, "独家": 2, "真相": 2,
            "内幕": 3, "黑幕": 3, "灰色": 2, "腐败": 2, "调查": 3,
        },
    },
    "policy": {  # 政策/法规
        "label": "政策/法规",
        "primary": ["news-policy", "news-policy-bold"],
        "secondary": ["news-paper"],
        "keywords": {
            "新规": 3, "政策": 3, "办法": 3, "通知": 3, "施行": 3,
            "印发": 3, "调整": 2, "发布": 2, "规定": 3, "条例": 3,
            "法规": 3, "公文": 3, "法律": 2, "国务院": 3, "财政部": 2,
            "民政部": 2, "修订": 2, "草案": 2, "意见": 2, "标准": 1,
        },
    },
    "data": {  # 数据/排行
        "label": "数据/排行",
        "primary": ["news-stat", "news-stat-grid"],
        "secondary": [],
        "keywords": {
            "排行": 3, "TOP": 3, "数据": 2, "第一": 2, "同比": 3,
            "增长": 2, "指数": 3, "统计": 2, "报告": 1, "榜单": 3,
            "总额": 2, "占比": 2, "排名": 2, "达到": 1, "涨幅": 2,
            "下降": 1, "最高": 1, "平均": 2,
        },
    },
    "onsite": {  # 现场/突发
        "label": "现场/突发",
        "primary": ["news-onsite", "news-onsite-urgent"],
        "secondary": [],
        "keywords": {
            "突发": 3, "现场": 3, "直击": 3, "抢险": 3, "灾害": 3,
            "地震": 3, "火灾": 3, "洪水": 3, "事故": 2, "救援": 2,
            "塌方": 3, "台风": 3, "暴雨": 2, "遇难": 3, "抢救": 2,
        },
    },
    "bulletin": {  # 速报
        "label": "速报/合辑",
        "primary": ["news-bulletin", "news-bulletin-strip"],
        "secondary": [],
        "keywords": {
            "速报": 3, "整点": 3, "合辑": 3, "盘点": 3, "要闻": 2,
            "一句话": 3, "简报": 2, "今日": 1, "多条": 1, "多条新闻": 3,
        },
    },
    "explainer": {  # 科普
        "label": "科普/图解",
        "primary": ["news-explainer", "news-explainer-blueprint"],
        "secondary": [],
        "keywords": {
            "为什么": 3, "原理": 3, "科普": 3, "图解": 3, "解读": 2,
            "怎么": 2, "什么是": 3, "揭秘": 2, "知识": 2, "冷知识": 3,
            "小知识": 3, "百科": 2, "机制": 2, "机制": 2, "工作原理": 2,
        },
    },
    "alert": {  # 警示
        "label": "警示/应急",
        "primary": ["news-alert", "news-alert-warning"],
        "secondary": [],
        "keywords": {
            "紧急": 3, "务必": 3, "不要": 2, "立即": 2, "预警": 3,
            "提醒": 2, "安全": 1, "防": 1, "险": 2, "危险": 2,
            "小心": 3, "当心": 2, "避免": 1, "不要点": 2, "骗局": 3,
            "诈骗": 3, "假": 2, "冒充": 2, "紧急通知": 3, "立即": 2,
        },
    },
    "thread": {  # 节日/纪念
        "label": "节日/纪念",
        "primary": ["news-thread", "news-thread-tribute"],
        "secondary": [],
        "keywords": {
            "纪念": 3, "致敬": 3, "清明": 3, "国庆": 3, "周年": 2,
            "节日": 2, "诞辰": 2, "追忆": 3, "致敬": 3, "纪念": 3,
            "缅怀": 3, "悼念": 3, "回忆": 2, "致敬": 3, "永远": 1,
        },
    },
    "takes": {  # 观点
        "label": "观点/评论",
        "primary": ["news-takes", "news-takes-column"],
        "secondary": ["news-podcast"],
        "keywords": {
            "观点": 3, "评论": 2, "专栏": 3, "我观察": 3, "思考": 2,
            "分析": 1, "认为": 2, "我觉": 2, "看法": 2, "想说": 2,
            "想说": 2, "说点": 2, "聊聊": 1, "感悟": 2,
        },
    },
    "blast": {  # 体育
        "label": "体育/比分",
        "primary": ["news-blast", "news-blast-score"],
        "secondary": [],
        "keywords": {
            "比赛": 3, "比分": 3, "进球": 3, "加时": 3, "绝杀": 3,
            "奥运": 2, "世界杯": 3, "联赛": 2, "CBA": 3, "NBA": 3,
            "中超": 3, "冠军": 1, "决赛": 2, "半决赛": 2, "晋级": 2,
            "夺冠": 2, "金牌": 1, "奖牌": 1, "球员": 1, "教练": 1,
        },
    },
    "world": {  # 国际
        "label": "国际/战况",
        "primary": ["news-world", "news-world-globe"],
        "secondary": [],
        "keywords": {
            "国际": 2, "战况": 3, "边境": 2, "外交": 3, "联合国": 2,
            "海外": 1, "美国": 1, "欧洲": 1, "日本": 1, "韩国": 1,
            "俄罗斯": 1, "乌克兰": 2, "加沙": 2, "以色列": 1, "战争": 2,
            "冲突": 1, "地缘": 2, "大使馆": 2, "联合国": 2,
        },
    },
    "polarity": {  # 高反差
        "label": "高反差黑白",
        "primary": ["news-polarity"],
        "secondary": [],
        "keywords": {
            "反差": 3, "极简": 3, "对比": 2, "强烈": 2, "黑白": 3,
            "强烈对比": 3, "视觉冲击": 2, "反差感": 3,
        },
    },
    "dawn": {  # 拂晓
        "label": "拂晓/晨光",
        "primary": ["news-dawn"],
        "secondary": [],
        "keywords": {
            "温暖": 2, "希望": 2, "新生": 2, "清晨": 2, "拂晓": 3,
            "晨光": 3, "破晓": 2, "新生": 2, "希望": 2, "温暖": 2,
            "希望工程": 2, "希望": 2,
        },
    },
}

# 长度 → 镜数
LENGTH_TO_SHOTS = {15: 3, 30: 3, 45: 4, 60: 5, 90: 7, 120: 8}

# 类型 → 主类别映射 (type 简写)
TYPE_TO_CATEGORY = {
    "story": "person_story",
    "person": "person_story",
    "investigation": "investigation",
    "investigate": "investigation",
    "policy": "policy",
    "data": "data",
    "stat": "data",
    "breaking": "onsite",
    "onsite": "onsite",
    "live": "onsite",
    "bulletin": "bulletin",
    "roundup": "bulletin",
    "explainer": "explainer",
    "science": "explainer",
    "alert": "alert",
    "warning": "alert",
    "thread": "thread",
    "tribute": "thread",
    "takes": "takes",
    "opinion": "takes",
    "blast": "blast",
    "sport": "blast",
    "world": "world",
    "international": "world",
}


def score_buckets(text: str, type_hint: str = None) -> dict:
    """对输入 text 计算每个 bucket 的加权得分"""
    scores = defaultdict(int)
    text_lower = text.lower()
    for bucket, info in PACK_BUCKETS.items():
        for kw, weight in info["keywords"].items():
            if kw in text or kw.lower() in text_lower:
                scores[bucket] += weight
    if type_hint and type_hint in TYPE_TO_CATEGORY:
        scores[TYPE_TO_CATEGORY[type_hint]] += 5  # type 提示加权
    return dict(scores)


def decide(text: str, type_hint: str = None, length: int = 60) -> dict:
    """决策主函数: 输入热点 text + type/length, 输出推荐 pack"""
    scores = score_buckets(text, type_hint)
    if not scores:
        return {
            "primary": "news-coral",
            "alternatives": ["news-dusk", "news-explainer"],
            "reason": "未匹配关键词, 默认主版(人物故事型) -- 适合 80% 内容",
            "scores": {},
            "shots": LENGTH_TO_SHOTS.get(length, 5),
        }
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    top_bucket, top_score = ranked[0]
    info = PACK_BUCKETS[top_bucket]
    primary = info["primary"][0]
    alternatives = info["primary"][1:] + info["secondary"]
    second_bucket = ranked[1][0] if len(ranked) > 1 else None
    reason = f"匹配 {info['label']} (得分 {top_score}"
    if second_bucket:
        reason += f", 次匹配 {PACK_BUCKETS[second_bucket]['label']} {ranked[1][1]}"
    reason += f"). 长度 {length}s -> {LENGTH_TO_SHOTS.get(length, 5)} 镜"
    return {
        "primary": primary,
        "alternatives": alternatives[:3],
        "reason": reason,
        "scores": dict(ranked[:3]),
        "shots": LENGTH_TO_SHOTS.get(length, 5),
    }


def all_pack_names() -> set[str]:
    """本决策表覆盖的全部 pack 名（primary + secondary 去重）。"""
    names: set[str] = set()
    for info in PACK_BUCKETS.values():
        names.update(info.get("primary", []))
        names.update(info.get("secondary", []))
    return names


def all_template_names() -> set[str]:
    """渲染器真正认的模板集合（path_b_build.ALL_TEMPLATES），**现算不手抄**。

    两者对不上时说明决策表与真实模板脱节了 —— 选出来的包可能渲不出来
    （表里有、磁盘上没有），或磁盘上有、表里选不到（永远选不到）。
    脱节检查见 skills/news-curate/scripts/curate_selftest.py 的
    `t_decide_pack_covers_every_real_template`。
    """
    scripts = _REPO_ROOT / "skills" / "douyin-pro" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    try:
        import path_b_build as pb
        return set(pb.ALL_TEMPLATES)
    except Exception:  # noqa: BLE001  拿不到就返回空集, 由测试报出来
        return set()


def list_all():
    n = len(all_pack_names())
    print("=" * 60)
    print(f"{n} pack 分类表 (按主气质)")   # 数量现算, 不写死 (D20)
    print("=" * 60)
    # 脱节当场说清, 不让"选了渲不出来的包"等到渲染期才崩（D7 的同一条原则）
    real = all_template_names()
    if real:
        drift = (all_pack_names() ^ real)
        if drift:
            print(f"  ⚠ 决策表与真实模板不一致: {sorted(drift)}"
                  f"（前者独有=渲不出来, 后者独有=选不到）")
    for cat, info in PACK_BUCKETS.items():
        print(f"\n[{info['label']}] ({cat})")
        print(f"  Primary: {', '.join(info['primary'])}")
        if info['secondary']:
            # 标明 Secondary 同样是合法可选项, 不是"别的类" —— 2026-10-08 实测
            # 有 5 个包只出现在 secondary, 曾被决策表忽略（D20）
            print(f"  Secondary（也是合法可选项）: {', '.join(info['secondary'])}")
        kws = sorted(info['keywords'].items(), key=lambda x: -x[1])[:5]
        print(f"  关键词 top5: {', '.join(f'{k}({w})' for k, w in kws)}")


def explain_pack(pack_name: str):
    for cat, info in PACK_BUCKETS.items():
        if pack_name in info['primary']:
            print(f"{pack_name} = [{info['label']}] 主类别")
            print(f"  关键词: {sorted(info['keywords'].items(), key=lambda x: -x[1])}")
            return
        if pack_name in info.get('secondary', []):
            print(f"{pack_name} = [{info['label']}] 备选")
            return
    print(f"{pack_name} 未在决策树中 -- 可能是派生变体, 见 pack-decision.md")


def main():
    if len(sys.argv) < 2:
        print("用法: python decide_pack.py \"<热点>\" [--type story] [--length 60]")
        print("      python decide_pack.py --list")
        print("      python decide_pack.py --explain <pack>")
        sys.exit(0)
    arg = sys.argv[1]
    if arg == "--list":
        list_all()
        return
    if arg == "--explain":
        if len(sys.argv) < 3:
            print("用法: --explain <pack>")
            sys.exit(1)
        explain_pack(sys.argv[2])
        return
    text = arg
    type_hint = None
    length = 60
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--type" and i + 1 < len(sys.argv):
            type_hint = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--length" and i + 1 < len(sys.argv):
            length = int(sys.argv[i + 1])
            i += 2
        else:
            i += 1
    result = decide(text, type_hint, length)
    print(f"输入: {text}")
    if type_hint:
        print(f"Type 提示: {type_hint}")
    print(f"长度: {length}s -> {result['shots']} 镜")
    print(f"推荐 pack: {result['primary']}")
    print(f"备选 pack: {', '.join(result['alternatives'])}")
    print(f"理由: {result['reason']}")
    if result.get('scores'):
        print(f"得分详情: {result['scores']}")


if __name__ == "__main__":
    main()

