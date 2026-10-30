# intent-routing.md - task-specific loading

The only route is `code`. After `core/NEVER.md`, choose the smallest relevant context.

| Intent | Additional context |
|--------|--------------------|
| Implement / refactor | `karpathy-guidelines.md` + common/current-language patterns |
| Bug fix | Relevant code and callers; `runbooks.md#bug-fix` if needed |
| Design / architecture | `principles.md`; write a plan only if the task needs it |
| Plan only | Inspect relevant code and return the requested plan; stop before implementation |
| Review / audit | `principles.md` + the changed contracts and tests |
| Frontend UI / layout / styling | `references/frontend-design.md`; select only the relevant upstream reference |
| Bootstrap / tool setup | The relevant section of `runbooks.md` and `references/tooling.md` |

Root `MEMORY.md` holds current project state; route MEMORY is a blank template. Read security/testing rules when the change touches those concerns. Read hook rules only when configuring hooks. A document already present in context does not need another tool read.

User requests to implement/fix/optimize proceed directly through relevant verification. Extra spec/plan approval, broad graph audits and full-suite reruns are not default steps.
