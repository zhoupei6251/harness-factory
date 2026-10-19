# core/ENTRY.md - governance doc index

> This file is itself the 8th governance doc. The table below names the other
> seven. `scripts/structure-audit.ts` asserts that all eight exist; updating the
> list and the file together is the only safe way to change either.

| Doc | Read when |
|-----|-----------|
| `intent-routing.md` | Task start: decide what to load |
| `karpathy-guidelines.md` | Coding: thinking rules |
| `NEVER.md` | **Mandatory**: forbidden list |
| `principles.md` | Design: design principles |
| `routing.md` | Route table details |
| `runbooks.md` | Trigger words map to actions |
| `tags-index.md` | Tag system |

## Loading strategy

Do not read all 8 every session. Read by intent:
- Coding task: `NEVER.md` + `karpathy-guidelines.md` + `routing.md`
- Design task: `principles.md` + `routing.md`
- Bug fix: `NEVER.md` + `runbooks.md`
- New project: all 8 once