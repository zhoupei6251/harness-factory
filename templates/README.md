# harness-factory templates

把 harness-factory 引入新项目的模板集合。

## 用法

1. 把 `harness-factory/` 克隆或软链到目标项目根（保持目录名 `harness-factory/`）
2. 在目标项目根跑：
   ```bash
   npx tsx harness-factory/scripts/install-into-project.ts --target .
   ```
3. 按提示确认（如有 `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` 已存在，会自动备份）
4. 验证：
   - `git status` 无 harness 相关 dirty
   - 启动 Claude Code / Codex / Gemini 会话，应能看到 harness 规则

## 模板清单

| 模板 | 目标文件 | 用途 |
|---|---|---|
| `target-CLAUDE.md` | `CLAUDE.md` | Claude Code 项目根加载 |
| `target-AGENTS.md` | `AGENTS.md` | Codex / Qoder 项目根加载 |
| `target-GEMINI.md` | `GEMINI.md` | Gemini 项目根加载 |
| `project-birds-eye.template.md` | （占位文本） | 填入目标项目的项目鸟瞰 |

## 占位符

模板中含两个占位符，`install-into-project.ts` 会自动替换：

| 占位符 | 替换为 |
|---|---|
| `${PROJECT_BIRDS_EYE}` | 用户通过 `--birds-eye-file <path>` 提供，或 `project-birds-eye.template.md` 的内容 |
| `${HARNESS_FACTORY_IMPORT}` | self 模式：`@ENTRY.md`（同目录）；other 模式：`@harness-factory/CLAUDE.harness.md` |

## self 模式

`install-into-project.ts --target .` 若在 harness-factory 仓库自身运行（路径等于 `__dirname/..`），自动进入 self 模式：

- import 路径走 `@ENTRY.md`（同目录、已存在）
- 前置检查：ENTRY.md 存在、core/ 存在、AGENTS.md 存在
- 任一不满足：退出码 3，不写任何文件

## 重要：不要改 harness-factory/ 目录名

`install-into-project.ts` 硬编码相对路径 `harness-factory/...`。改名会导致所有 @import 失效。
