# agents/ — 角色行为契约

本目录存放 **agent 角色的完整行为契约**（canonical），平台侧只保留薄包装。

## 为什么单独一层

`skills/` 是可复用的**过程**，`agents/` 是**角色**：谁来做、能碰什么、返回什么。同一个角色在不同项目里行为应当一致，所以契约放这里，项目侧只留指针。

## 目标项目如何消费

在目标项目的 agent 目录里放一个薄包装，`core:` 指向本目录的契约：

```markdown
---
name: harness-web-investigator
platform: claude
type: general-purpose
model: inherit
readonly: true
core: harness-factory/agents/web-investigator.md
skills:
  - web-tools-guide
---
你是 <项目名> 的信息调研者。
**先 Read `harness-factory/agents/web-investigator.md`** — 完整行为契约。
```

`harness-factory/` 在各项目工作树里各有一份（均在 `.gitignore` 内），所以改这里的契约等于同时改所有项目；无需逐项目同步。

## 新增一个角色

1. 在本目录写 `<role>.md`，结构照 `web-investigator.md`：角色 → 何时派 → 纪律 → 输入 → 输出 → 禁止项
2. 在 `STRUCTURE.md` 的 canonical sources 表里加一行
3. 在目标项目建薄包装（见上）

不写平台专属内容（模型名、工具白名单）——那些留在包装的 frontmatter 里，本目录只写与平台无关的行为。
