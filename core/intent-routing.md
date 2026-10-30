# intent-routing.md - task-specific loading

The only route is `code`. After `core/NEVER.md`, choose the smallest relevant context.

| Intent | Additional context |
|--------|--------------------|
| Implement / refactor | `karpathy-guidelines.md` + common/current-language patterns; `skills/hf-tdd/SKILL.md` for non-trivial testable behavior, `hf-design` when changing module contracts |
| Bug fix | Relevant code and callers + `skills/hf-debug/SKILL.md`; reuse an established root cause instead of restarting investigation |
| Design / architecture | `principles.md` + `skills/hf-design/SKILL.md`; write a plan only if the task needs it |
| Plan only | Inspect relevant code and return the requested plan; stop before implementation |
| Review / audit | `principles.md` + changed contracts/tests; `skills/hf-security/SKILL.md` for changed trust boundaries |
| Frontend UI / layout / styling | `skills/hf-ui/SKILL.md`; select one local upstream source; `playwright` / `hf-web-test` for actual browser verification |
| Bootstrap / tool setup | The relevant section of `runbooks.md` and `references/tooling.md` |
| Auth / inputs / uploads / sensitive data | `skills/hf-security/SKILL.md` and relevant existing language/security rules |
| Finish a code change | `skills/hf-verify/SKILL.md`; reuse fresh checks, report actual results and limits |

Root `MEMORY.md` holds current project state; route MEMORY is a blank template. Read security/testing rules when the change touches those concerns. Read hook rules only when configuring hooks. A document already present in context does not need another tool read.

User requests to implement/fix/optimize proceed directly through relevant verification. Extra spec/plan approval, broad graph audits and full-suite reruns are not default steps.

Names above refer to bundled `skills/<name>/SKILL.md`, relative to the harness directory (downstream: `harness-factory/skills/...`). Read them directly if native discovery is unavailable. Basic `ponytail` and `codebase-memory` remain required. Do not preload all skills or chain multiple providers' planning/TDD/review workflows. Local adapters govern conflicts; upstream examples do not override project restrictions. Details and exact imported subsets: `references/coding-capabilities.md`.
