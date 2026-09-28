---
name: lsp-query
description: "通过 Language Server Protocol（typescript-language-server / pyright / gopls 等）做结构化代码查询：定义、引用、悬停信息、符号、代码诊断。触发：找定义、找引用、找类型、看类型签名、go to definition、find references、hover、diagnostics、rename、检查类型错误。"
version: 1.0.0
when_to_use: 需要语言服务器提供的精确类型/定义/引用/诊断信息时
status: stable
tags:
- code
- lsp
- tool
- tactical
domain: code
category: code.lsp
---
# /lsp-query

通过 Language Server Protocol（LSP）获得编译器级别的结构化查询能力。是 code 域的"权威查询"：当 ripgrep 只能给文本、codebase-memory 给图时，LSP 给带类型的真实定义/引用/诊断。

## 何时用

- 找符号的精确"定义"和"声明"
- 找符号的"所有引用"（按语义，跨别名/重命名/继承）
- 看类型签名、参数、返回类型
- 检查当前文件的语法/类型错误
- 跨语言（TS / JS / Python / Go / Rust / Java / C#）的语义查询
- 改动前确认一处符号的真正来源

## 何时不要用

- 找文件内未识别的关键字/字符串 → `ripgrep-search`
- 找跨服务的接口契约 → `codebase-memory` 的 `HTTP_CALLS` 边
- 想做大范围影响评估 → `analyze-impact`

## 工具能力

- 服务：使用宿主 IDE 已有的 language server（typescript-language-server、pyright、gopls、rust-analyzer、clangd、jdtls、omnisharp-roslyn 等）
- 通信：LSP over stdin/stdout 或 socket；通过 `lsp-cli` / `lsp_command_*` 调用
- 覆盖：定义、引用、悬停、符号、诊断、重命名、格式化、范围、类型定义
- 由 IDE 或 MCP LSP bridge 暴露给 AI；本 skill 只规定协议和调用约定
- **当前项目未启用 LSP 后端**：语义检索类能力由 `codebase-memory`（结构关系）+ `ripgrep-search`（文本/注释）承担；需要精确语义操作时用宿主 IDE（IntelliJ IDEA）完成

## 调用方式

```markdown
# 1. textDocument/definition — 找定义
LSP: textDocument/definition
{
  "textDocument": {"uri": "file://<project>/src/auth/login.ts"},
  "position": {"line": 42, "character": 18}
}

# 2. textDocument/references — 找全部引用
LSP: textDocument/references
{
  "textDocument": {"uri": "file://<project>/src/auth/login.ts"},
  "position": {"line": 42, "character": 18},
  "context": {"includeDeclaration": false}
}

# 3. textDocument/hover — 取类型签名
LSP: textDocument/hover
{
  "textDocument": {"uri": "file://<project>/src/auth/login.ts"},
  "position": {"line": 42, "character": 18}
}

# 4. textDocument/documentSymbol — 列出当前文件符号
LSP: textDocument/documentSymbol
{"textDocument": {"uri": "file://<project>/src/auth/login.ts"}}

# 5. workspace/executeCommand — 重命名（带预览）
LSP: workspace/executeCommand
{
  "command": "typescript.applyCodeAction",
  "arguments": [{"file": "<path>", "startLine": 42, "endLine": 42, "newName": "authenticate"}]
}
```

## 返回格式

```json
{
  "language": "typescript",
  "server": "typescript-language-server",
  "method": "textDocument/definition",
  "result": [
    {
      "uri": "file://<project>/src/auth/auth.service.ts",
      "range": {"start": {"line": 17, "character": 4}, "end": {"line": 17, "character": 24}},
      "preview": "  public async login(req: LoginRequest): Promise<AuthResult> {"
    }
  ]
}
```

## 跟 codebase-memory / ripgrep 的关系

| 需求 | 优先 | 备用 |
|------|------|------|
| 谁调用了 X（语义、含继承/重写） | `codebase-memory` 的 `trace_path(direction="inbound")` | 宿主 IDE（IntelliJ）Find Usages |
| 找文本/字符串 | `ripgrep-search` | — |
| 找 X 的类型/签名 | `codebase-memory` 的 `get_code_snippet` | 宿主 IDE 跳转 |
| 编译期错误 | 宿主 IDE / `mvn compile` | `simplify` / `tdd` |
| 跨文件图关系 | `codebase-memory` | `ripgrep-search` |

> 协同原则：`codebase-memory` 跨服务、跨仓库；宿主 IDE（IntelliJ IDEA）提供权威语义与重命名；`ripgrep-search` 兜底非语义搜索（注释、字符串、配置）。

## 失败与边界

- LSP 后端不可用（未启用 / 启动失败）→ 报告 `tool_unavailable: lsp`，降级到 `codebase-memory` + `ripgrep-search`，**不阻塞任务**
- 中文注释/字符串语义检索不可用（LSP 不索引注释与字符串）→ 用 `ripgrep-search` 兜底
- 需要精确语义操作（重命名/Find Usages）→ 交给宿主 IDE（IntelliJ IDEA），AI 不做跨文件手工替换
- 想跨 IDE 改代码 → 改用 IDE 的 rename/refactor，不要靠 LSP executeCommand