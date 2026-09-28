---
name: code-insight-stack
description: "编排 codebase-memory + ripgrep + LSP 三层查询栈，按场景选择最便宜的工具组合。触发：探索陌生代码库、定位修改点、调查 bug、准备 refactor、计划实现、跨文件影响分析。"
version: 1.0.0
when_to_use: 在 code 域做结构化查询前，先决定用哪个/哪些工具组合
status: stable
tags:
- code
- orchestration
- intelligence
domain: code
category: code.intelligence
---
# /code-insight-stack

code 域的"洞察栈"编排：把 **codebase-memory**（知识图谱）、**ripgrep**（文本搜索）、**LSP**（语言服务）三个工具分层组合，按场景选最便宜、最权威的路径。

## 三层定位

| 层 | 工具 | 强项 | 弱项 |
|----|------|------|------|
| 知识图谱 | `codebase-memory` (`search_graph` / `trace_path` / `detect_changes` / `get_architecture`) | 跨文件、跨服务、跨仓库的结构关系 | 不感知编译时类型、字符串、注释 |
| 文本搜索 | `ripgrep-search` (`rg`) | 任意字符串/正则/glob，速度极快 | 无语义，不知道别名/重命名/继承 |
| 语言服务 | 宿主 IDE（IntelliJ IDEA / VS Code LSP），`lsp-query` 协议 | 编译器级定义/引用/类型/诊断、语义重命名 | 需要 IDE 配合；AI 侧不直接调用 |

## 选栈原则

1. **结构关系**优先 `codebase-memory`（图查询一次给出整片调用图）。
2. **字符串 / 注释 / 路径 / 配置**直接用 `ripgrep-search`。
3. **类型与符号语义**（定义/重命名/类型签名/编译错误）交给宿主 IDE（IntelliJ IDEA / VS Code），AI 侧用 `codebase-memory` + `ripgrep` 定位。
4. 三个不确定时，从最便宜往最权威靠：先 `ripgrep` 缩小范围 → 用 `codebase-memory` 看结构 → 宿主 IDE 拿权威定义与重命名。
5. 每次写代码前，先用其中至少 1 个工具**确认修改点的真实存在**，不要凭记忆改。

## 场景决策表

| 场景 | 首选 | 配合 |
|------|------|------|
| 陌生项目，先摸全局 | `codebase-memory` 的 `get_architecture` | `ripgrep-search` 看目录结构 |
| 找某个类的定义 | `codebase-memory` 的 `search_graph` | `ripgrep-search` 确认路径 |
| 谁调用了这个函数 | `codebase-memory` 的 `trace_path(direction="inbound")` | 宿主 IDE（IntelliJ）Find Usages 交叉验证 |
| 这个方法内部调了什么 | `codebase-memory` 的 `trace_path(direction="outbound")` | `ripgrep-search` 找调用点 |
| 跨文件重命名符号 | 宿主 IDE（IntelliJ）Refactor → Rename | `codebase-memory` 的 `detect_changes` 评估影响 |
| 符号级编辑（改方法体/插入） | 宿主 IDE 编辑 | `ripgrep-search` 定位上下文 |
| 找字符串/配置项/日志/注释 | `ripgrep-search` | — |
| 检查编译错误 | 宿主 IDE / `mvn compile` | `simplify` / `tdd` |
| 改动前的全部影响 | `codebase-memory` 的 `detect_changes` | `trace_path(direction="inbound")` 交叉验证 |
| 跨服务的接口契约 | `codebase-memory` 的 `query_graph` (Cypher) | `ripgrep-search` 找路由文件 |
| 找某个 TODO / FIXME | `ripgrep-search` | — |

## 标准工作流

```text
1. 拿到任务
   ↓
2. (新项目) get_architecture / list_projects
   ↓
3. 定位修改点
   ├─ 知道符号名 → search_graph → ripgrep 确认路径
   └─ 不知道符号名 → ripgrep-search 找关键字 → search_graph
   ↓
4. 读上下文
   ├─ get_code_snippet 读精确源码
   └─ ripgrep-search 看相关调用
   ↓
5. 评估影响
   ├─ trace_path(direction="inbound")
   ├─ trace_path(direction="outbound")
   └─ detect_changes
   ↓
6. 修改 + 重命名
   └─ 精确语义操作交宿主 IDE（IntelliJ），机械替换用 Edit
   ↓
7. 验证
   └─ mvn compile / 宿主 IDE 诊断
```

## 失败与降级

- `codebase-memory` 索引未建立 → 退到 `ripgrep-search` 串行探查；任务结束前补 `index_repository`
- `ripgrep` 不可用 → 用文件系统的 `find`/`grep`，但结果要标注 `low_confidence`
- 宿主 IDE 不可用 → 语义操作退化为 `codebase-memory` + `ripgrep`，重命名类改动需人工确认

## 协同 Agent

- `coder` / `debugger`：实现 / 修复前必跑 1 步 3 → 4 → 5
- `explorer`：第 2 → 3 步是默认动作
- `reviewer` / `code-reviewer`：第 5 步 + 第 7 步是默认动作