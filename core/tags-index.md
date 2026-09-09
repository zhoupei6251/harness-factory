# tags-index.md - tag system

## Tag categories

| Tag | Read when | Examples |
|-----|-----------|----------|
| `Rules` | Session start, behavior guide | ENTRY.md, NEVER.md, principles.md |
| `Runbook` | Trigger matches, procedure | runbooks.md, routing.md |
| `Memory` | On demand, accumulated state | MEMORY.md, route state |
| `Standard` | By role, spec | language-style.md, framework-conventions.md |
| `Never` | All tasks, forbidden | NEVER.md |

## Loading policy

- `Rules` + `Never` = always read
- `Runbook` = read when trigger matches
- `Memory` = read on demand
- `Standard` = read by current role/task
