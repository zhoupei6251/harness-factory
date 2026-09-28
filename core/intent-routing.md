# intent-routing.md - how to decide what to load

Every task starts with: classify the intent, then load the minimum doc set.

## Intent classification

| Trigger | Intent | Load |
|---------|--------|------|
| design / spec / architecture | design | `principles.md` + `routing.md` |
| plan / wbs / breakdown | plan | `routing.md` + `runbooks.md` |
| implement / code / build | implement | `NEVER.md` + `karpathy-guidelines.md` |
| bug / fix / broken | bug | `NEVER.md` + `runbooks.md#bug` |
| review / audit | review | `NEVER.md` + `principles.md` |
| config / setup | config | `runbooks.md#bootstrap` |

## Anti-pattern: pre-loading everything

Do not read all 7 governance docs at session start. Read by intent.
Token cost of pre-loading all 7: ~3000 tokens. Per-intent load: ~500 tokens.
