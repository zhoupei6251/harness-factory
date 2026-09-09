# routing.md - route table

| Route | When | MEMORY template | Runtime dir |
|-------|------|----------------|-------------|
| `code` | Software engineering task | `routes/code/MEMORY.md` | `.ai-runtime-artifacts/` |
| `novel` | Fiction writing task | `routes/novel/MEMORY.md` | `.harness-novel-runtime/` |
| `news` | News/article task | `routes/news/MEMORY.md` | `.harness-news-runtime/` |
| small change | < 50 lines, no spec needed | none | none |

## Default

`code` is the default route. Override with explicit intent at session start.
