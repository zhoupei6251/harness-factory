# routing.md - route table

| Route | When | MEMORY template | Runtime dir |
|-------|------|----------------|-------------|
| `code` | Software engineering task | `routes/code/MEMORY.md` | `.ai-runtime-artifacts/` |
| `novel` | **archived 2026-10-22** → 实现迁往 heron | `routes/novel/MEMORY.md`（归档件） | `.harness-novel-runtime/` |
| `news` | **archived 2026-10-22** → 实现迁往 heron | `routes/news/MEMORY.md`（归档件） | `.harness-news-runtime/` |
| small change | < 50 lines, no spec needed | none | none |

## Default

`code` is the default route. Override with explicit intent at session start.

`news` / `novel` 两行仍在表里，是因为**目录与脚本此刻仍可运行**（退役分两步：先摘路由，
再摘目录）。"表里有这行"不等于"意图会走到这行"——见 `intent-routing.md#归档中的路由`。
