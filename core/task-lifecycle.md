# core/task-lifecycle.md — 任务从开始到结束的生命周期

> 本文件是**任务的阶段链**——从用户开口到收尾的标准流程。
> 档位决定每阶段的「文书重量」，本文件决定**阶段本身**。

## 阶段图（文字版状态机）

```
[REQUEST]
   │
   ▼
[ANALYZE]              弄清做什么
   │
   ▼
[EXPLORE]              看现状（代码/故事/事实）
   │
   ▼
[DESIGN]               想清楚怎么做
   │
   ▼
[IMPLEMENT]            实际改 / 写
   │
   ▼
[VERIFY]               跑证据
   │
   ▼
[REVIEW]               自审 + 他审
   │
   ▼
[CLOSE]                收尾（落合同/做总结）
   │
   ▼
[DONE]
```

**失败路径**：任何阶段失败 → 回到 [ANALYZE] 重来。**至少一次**回到 ANALYZE，而不是在失败点狂试。constitution R4：同一处连修两次失败即停手写诊断。

## 各阶段做什么

### ANALYZE — 弄清做什么

- 读 `.harness/state/profile.md`（项目事实）
- 读 `routes/<line>/workflow.md`（路线管线）
- 输出：**一段话确认**——「我理解这是做 X，方式是 Y，预期效果是 Z」
- 若 M/L 档：**方案落盘**（`engine/contracts/spec.md` 模板住；待写）

### EXPLORE — 看现状

- 读相关文件（**不读就改视为错误**，constitution R1）
- 跑 `git status` `git log` 之类观察性命令
- 收集**未冲突的事实**——不是读后表达观点，是列出现状

### DESIGN — 想清楚怎么做

- 改哪些文件？新增哪些？怎么验？风险在哪？
- 走 `routes/<line>/workflow.md` 的「路线管线」段
- 若 L 档：**plan 落盘**（`engine/contracts/plan.md`）

### IMPLEMENT — 实际改 / 写

- 最小改动（constitution R2）
- 不顺手重构
- 触发 hooks：覆盖前 backup 到 `.bak/`

### VERIFY — 跑证据

- constitution R3：**说「跑过了」必须同时贴命令与输出**
- 三件套：**动了什么 + 跑了什么 + 结果**
- 验证命令来自 `.harness/state/profile.md` 的 `verification_command`

### REVIEW — 自审 + 他审

- 自审：读一遍自己改的，**用别人眼光**
- 他审：spawn `agents/code-reviewer.md`（物理禁写）— 对 code 路线
- L 档批次必须过这一步

### CLOSE — 收尾

- S/M 档：写 `.harness/state/MEMORY.md` 一段日志
- L 档：写 `engine/contracts/closeout.md`（每条验收项打勾）

## 三类阶段的差异（code / novel / news）

### code

ANALYZE → EXPLORE → DESIGN → IMPLEMENT → VERIFY → REVIEW → CLOSE

特点：
- EXPLORE 阶段**必跑**（不读代码就改 = 撞错错）
- REVIEW 阶段**必跑**（`code-reviewer` agent）
- VERIFY 命令在 `state/profile.md` 预先声明

### novel

ANALYZE → (OUTLINE) → EXPLORE → DESIGN → (BASELINE) → IMPLEMENT → (CHECK) → VERIFY → REVIEW → CLOSE

特点：
- EXPLORE 阶段 = 读 `novel/book.md chapters.md characters.md foreshadowing.md voice.md`（状态文件）
- DESIGN 阶段 = **文风基线**（写前对齐）
- VERIFY 阶段 = **机械机检**（`novel/verify/comp`novel/`check-index check-continuity check-voice`）—— 写后跑连续性检查
- 没有 S 档——理由见 `core/quality-gates.md`

### news

ANALYZE → SEARCH → SOURCE-RANK → CROSS-CHECK → FACT-VERIFY → TIMELINE → WRITE → CITATION-AUDIT → CLOSE

特点：
- 多源核对是**路线管线**——S 档也照跑（不随档升降）
- 「要发出去 / 投出去」时强制升 L
- CITATION-AUDIT 是尾盘——所有引用必须可回溯

## 与 quality-gates.md 的关系

- 档位决定每阶段的「交付物」：口头三件套 / 一段方案 / 落盘合同
- 本文件决定「有哪些阶段」
- 一份文档回答一个明确问题：本文件回答阶段，quality-gates 回答档位