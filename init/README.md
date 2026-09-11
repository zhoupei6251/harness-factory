# init/ — 项目初始化工具集

**目的**：当一个新的项目想用 harness-factory 时，在项目根跑一次 `init.sh`（或 `init.ps1`），建立 `.harness/` 骨架。

**vs `scripts/` 的边界**：
- `init/` = 给人用，新建项目跑一次
- `scripts/` = 给引擎用，升级/重渲染时跑

## 5 分钟上手

```bash
# 在新项目的根目录（跟 harness-factory/ 平级）：
cd /path/to/your-project
/path/to/harness-factory/init/init.sh

# Windows PowerShell：
\path\to\harness-factory\init\init.ps1
```

脚本会：
1. 在项目根建 `.harness/` 目录骨架（与 harness-factory/ 平级）
2. 从 `init/templates/` 复制 `.harness/{state,code,novel,news,rendered}/` 全骨架
3. 把 `engine/contracts/` 的 L 档模板（spec/plan/verification/closeout）副本放进 `.harness/rendered/`
4. 在项目根 `.git/info/exclude` 添加 `.harness/` 与平台 shim 路径

## init.sh 的三个 mode

| mode | 行为 |
|---|---|
| `./init.sh`（默认） | 创建 `.harness/` 骨架（已存在则跳过） |
| `./init.sh --reset` | nuke `.harness/` 重建（**警告**：丢失 AI 状态） |
| `./init.sh --verify` | 不改任何东西，只检查 `.harness/` 完整性 |

## 文件说明

| 文件 | 干什么 |
|---|---|
| `init.sh` / `init.ps1` | 跨平台 bootstrap 入口 |
| `verify.sh` | init 后体检（`--verify` 模式调用） |
| `templates/state/` | 人类 seed 文件（config.md profile.md）+ AI 初始（MEMORY.md state.json） |
| `templates/code/` | code 线工作区骨架（specs plans verifications retros tracking） |
| `templates/novel/` | novel 线工作区骨架（drafts archive） |
| `templates/news/` | news 线工作区骨架（drafts archive） |
| `templates/rendered/` | 引擎渲染产物骨架（AGENTS.md 等 7 文件） |
