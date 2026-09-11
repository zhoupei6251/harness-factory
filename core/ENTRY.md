# core/ENTRY.md - governance doc index

| Doc | Read when |
|-----|-----------|
| `intent-routing.md` | Task start: decide what to load |
| `karpathy-guidelines.md` | Coding: thinking rules |
| `NEVER.md` | **Mandatory**: forbidden list |
| `principles.md` | Design: design principles |
| `routing.md` | **Single source of truth**: 业务路线表 + 任务路由表 + 阶段门禁 + Git 协作 |
| `runbooks.md` | Trigger words map to actions（新功能/缺陷/决策/news 写作/Git/尾盘） |
| `tags-index.md` | Tag system |
| `artifacts.md` | spec / plan / decision 产物契约 |
| `verification.md` | 验证流程基线 |
| `harness.md` | 架构总览（可选） |
| `orchestration/dispatcher-workflow.md` | 多 task 编排：WU 拆分、DISPATCH-TRACK、尾盘 |

## Project-level instance files

| File | Read when |
|------|-----------|
| `../project/profile.md` | 改代码前：项目身份、技术栈、模块边界 |
| `../project/git.md` | Git 任务：本项目相对组织规范的差异 |
| `../project/verification.md` | 验证阶段：本项目的验证命令清单 |

## Loading strategy

Do not read all docs every session. Read by intent:
- Coding task: `NEVER.md` + `karpathy-guidelines.md` + `routing.md`
- Design task: `principles.md` + `routing.md`
- Plan task: `artifacts.md` + `routing.md` § 阶段门禁
- Bug fix: `NEVER.md` + `runbooks.md`
- Verification: `verification.md` + `../project/verification.md`
- News / writing: `../routes/news/MEMORY.md` + `runbooks.md` § news 路线
- New project: skim all once
