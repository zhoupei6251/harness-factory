---
name: ripgrep-search
description: "使用 ripgrep（rg）做高速文本搜索，定位引用、字符串、关键字。触发：grep、find、搜索文本、定位字符串、查找引用、查找 TODO/FIXME、查找实现、查找日志、搜索代码。"
version: 1.0.0
when_to_use: 需要按文本/正则定位代码中出现的字符串、标识符、引用或注解时
status: stable
tags:
- code
- search
- tool
- tactical
domain: code
category: code.search
---
# /ripgrep-search

用 ripgrep 在代码库里高速搜索文本或正则模式。Code 域的"第一站"：当 codebase-memory 的图结构无法覆盖（如字符串、注释、日志、文件路径、跨语言关键字）时，ripgrep 提供快速、可预测的文本定位能力。

## 何时用

- 找 `TODO / FIXME / XXX` 等注释标记
- 找特定字符串、URL、API key 引用
- 找跨文件的所有 import / require / include
- 找某段错误消息的源头
- 找某个 API 调用站点（参数匹配 / 日志关键字 / 调试打印）
- 找引用某个 schema、字段、配置项的位置

## 何时不要用

- 想知道"谁调用了这个函数" → `trace_path(direction="inbound")`
- 想知道"这个函数内部调了什么" → `trace_path(direction="outbound")`
- 想做完整的影响面评估 → `analyze-impact` / `detect_changes`
- 不知道符号的精确名 → 先 `search_graph(name_pattern=...)` 再 `ripgrep-search`

## 工具能力

- 命令：`rg`
- 依赖：宿主环境安装 ripgrep（`rg --version` ≥ 13）
- 默认在仓库根目录执行；通过 `--path` 限定子目录
- 自动忽略 `.git/`、`dist/`、`node_modules/`、`.codebase-memory/`

## 调用方式

```bash
# 1. 基础文本搜索（区分大小写）
rg --no-heading --line-number --color never 'PATTERN' --path src

# 2. 智能大小写（首字母大写时忽略大小写）
rg --no-heading --line-number --color never -i 'AuthError'

# 3. 限定文件类型 / glob
rg --no-heading --line-number --color never -g '*.ts' 'useEffect\('

# 4. 跨多行（必须开启 -U）
rg --no-heading --line-number --color never -U 'export const \w+ =' --multiline-dotall

# 5. 统计出现次数而非列出
rg --count-matches 'TODO' --type-add 'web:*.{ts,tsx,vue,js,jsx}'

# 6. JSON 输出（结构化）
rg --json 'useReducer' --type rust
```

## 推荐参数

| 参数 | 用途 |
|------|------|
| `--no-heading` | 单行结果，便于结构化输出 |
| `--line-number` / `-n` | 输出行号 |
| `--color never` | 避免在 JSON / 文本中夹带 ANSI |
| `--field-context-separator ' '` | 上下文用单空格分隔，配合 JSON |
| `--threads 4` | 大仓库限制并发 |
| `--max-columns 200` | 长行截断 |
| `--max-columns-preview` | 预览长行 |
| `-uu` | 同时搜隐藏文件、忽略文件（谨慎） |

## 返回格式

```json
{
  "pattern": "useReducer",
  "root": "<project>",
  "matches": [
    {"path": "src/hooks/use-todo.ts", "line": 42, "text": "const [state, dispatch] = useReducer(reducer, initial);"}
  ],
  "stats": {"files": 1, "hits": 1}
}
```

## 跟 codebase-memory 的关系

| 能力 | 优先使用 | 备用 |
|------|----------|------|
| 找函数/类的结构关系 | `search_graph` / `trace_path` | `ripgrep-search` |
| 找字符串、注释、配置 | `ripgrep-search` | 全库 grep |
| 影响面评估 | `analyze-impact` / `detect_changes` | `ripgrep-search --count` |

> 工作流：先用 `codebase-memory` 拿到精确符号名 → 再用 `ripgrep-search` 找该名字的字符串引用 → 用 `get_code_snippet` 读上下文。

## 失败与边界

- `rg` 不可用 → 报告 `tool_unavailable: ripgrep`，不要退化为 IDE 自带 search panel
- 结果超过 200 条 → 收紧 pattern、加 `-g` 限定目录或 `-l` 只列文件
- 想找"谁调用了函数 X" → 不要用 ripgrep，应去 `trace_path(direction="inbound")`

## 命令前缀

| 平台 | 形式 |
|------|------|
| Claude Code / Codex | `rg --no-heading -n --color never '<pattern>' --path <dir>` |
| 引用 | `rg --json '<pattern>' --type <type>` |