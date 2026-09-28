---
name: novel-mechanical-scorer
description: 无LLM的确定性章节质量评分器 — 借鉴 autonovel (NousResearch) 机械评分器，在LLM审稿前做纯规则检查
version: 1.0.0
when_to_use: 写章节后、提交LLM审稿前、作为质量门禁的第一道检查
status: peripheral
tags:
- novel
- scoring
- mechanical
- quality
domain: novel
category: novel.quality
---

# Novel Mechanical Scorer — 机械评分器

> 借鉴 [autonovel](https://github.com/NousResearch/autonovel) (NousResearch) 的"双重免疫系统"：
> **先用纯规则/正则扫描过滤低级问题，再用 LLM 审稿判断文学质量。**

## 为什么需要机械评分器

```
autonovel 的核心发现：

1. OVER-EXPLAIN 占 AI 写作问题的 ~32% — 旁白解释场景已展示的内容
2. REDUNDANT 占 ~26% — 同一观点被重复多次
3. 句长均匀度是 AI 写作的强信号
4. 用不同模型做评估 vs 写作，避免"自我恭维"偏差
```

**机械评分器的价值：**
- **零 API 成本** — 纯正则/统计算法，不调用 LLM
- **确定性结果** — 同样的输入永远产生同样的输出
- **快速** — ~0.1 秒完成全部检查
- **在 LLM 审稿前过滤低级问题** — 减少 LLM 审稿负担

---

## 使用方式

### 命令行

```bash
# 快速摘要
python scripts/novel/mechanical_scorer.py 章节正文/第1章_xxx.md

# 详细检查清单
python scripts/novel/mechanical_scorer.py 章节正文/第1章_xxx.md --checklist

# JSON 输出（供程序使用）
python scripts/novel/mechanical_scorer.py 章节正文/第1章_xxx.md --json
```

### 在写作流程中集成

```markdown
1. Writer 完成章节
       ↓
2. 运行 Mechanical Scorer（本章步骤）
       ↓
3. IF BLOCK → 修复后重新运行
       ↓
4. IF PASS → 提交给 novel-evaluator（LLM 7维审稿）
```

---

## 检查维度（9 大类）

借鉴 autonovel evaluate.py + 融合 traps-archive 63 条陷阱：

| 检查 | 借鉴来源 | 说明 |
|------|---------|------|
| **字数检查** | autonovel word count baseline | ≥2000 字，<5000 字为佳 |
| **AI 高频词汇** | traps-archive §1-15 | 15 条正则扫描 |
| **标点规范** | 原创 | 半角标点检测 |
| **句长均匀度** | autonovel sentence-length uniformity | 标准差 <5.0 疑似 AI |
| **Show-Don't-Tell** | autonovel show-don't-tell violations | 5 条正则扫描 |
| **对话占比** | 原创 | 10%-60% 为合理范围 |
| **段落长度** | 原创 | 不超过 500 字 |
| **钩子检查** | traps-archive §34-40 | 结尾是否平淡 |
| **OVER-EXPLAIN** | autonovel #1 finding | 旁白解释场景已展示的内容 |

---

## 评分规则

```
满分 100 分：
- 每个 BLOCK 扣 20 分（如字数 <500）
- 每个 WARN 扣 5 分
- 每个 INFO 扣 1 分

分数仅供参考，不代表文学质量
```

---

## 处理决策

参考 autonovel 的 modify-evaluate-keep/discard 循环：

| 决策 | 条件 | 动作 |
|------|------|------|
| **BLOCK** | 存在 BLOCK 级别发现 | 拒绝交付，必须修复后重新运行 |
| **WARN** | WARN > 10 个 | 可以提交 LLM 审稿，但建议先修复 |
| **PASS** | WARN ≤ 10，无 BLOCK | 机械评分通过，提交 LLM 审稿 |

---

## 与 autonovel 的对应关系

| autonovel 概念 | 本系统对应 |
|---------------|----------|
| `evaluate.py` (mechanical) | `mechanical_scorer.py` (本工具) |
| BANNED_PATTERNS | AI_PATTERNS (15 条正则) |
| show-don't-tell violations | TELL_PATTERNS (5 条正则) |
| sentence-length uniformity | `check_sentence_variety()` |
| `evaluate.py` (LLM judge) | `novel-evaluator` skill (7维评分) |
| `reader_panel.py` | 暂未实现 |
| `adversarial_edit.py` | 暂未实现 |
| `gen_revision.py` | 审稿返修流程 |

---

## JSON 输出格式

```json
{
  "meta": {
    "tool": "novel-mechanical-scorer",
    "version": "1.0.0",
    "inspiration": "autonovel evaluate.py (NousResearch)"
  },
  "score": 85,
  "max_score": 100,
  "findings_count": {
    "total": 4,
    "block": 0,
    "warn": 2,
    "info": 2
  },
  "categories": { ... },
  "findings": [ ... ],
  "stats": {
    "char_count": 3200,
    "avg_sentence_length": 12.3,
    "sentence_std_dev": 7.2,
    "dialogue_ratio": 35.0,
    "over_explain_count": 2
  },
  "processing": {
    "decision": "PASS",
    "action": "机械评分通过，可以提交 LLM 审稿",
    "next": "提交给 novel-evaluator 进行 7 维 LLM 审稿"
  }
}
```

---

## 扩展到更多检查

### 从 autonovel 可以继续借鉴的

```python
# TODO: autonovel 的其他机械检查

# 1. 陈词滥调检测 (参考 autonovel BANNED_PATTERNS)
CLICHE_PATTERNS = [
    r"命运的齿轮",
    r"冥冥之中",
    r"天意如此",
    r"命中注定",
]

# 2. em-dash 过度使用 (参考 autonovel)
# 中文对应：破折号密度检查

# 3. 章节开头重复 (参考 autonovel freshness decay)
# 检查连续章节开头是否过于相似
```

---

## 禁止事项

- ❌ 机械评分通过 = 文学质量好（需要 LLM 审稿补充判断）
- ❌ 跳过机械评分直接提交 LLM 审稿
- ❌ BLOCK 级别的发现不修复就交付

---

## 依赖

- `traps-archive/novel/00-all.md` — 63 条陷阱
- `skills/novel-evaluator/` — LLM 7 维审稿
- `scripts/novel/mechanical_scorer.py` — 本工具
