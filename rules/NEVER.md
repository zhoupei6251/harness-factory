# NEVER.md - coding boundaries

| Forbidden | Alternative |
|-----------|-------------|
| edit unread file | Read current source and the relevant callers |
| change code without evidence | Query the graph first; verify stale/gapped source; if unavailable, explain degradation |
| skip the lazy ladder | Apply ponytail before generation |
| empty catch or silent data loss | Handle errors with context or re-raise |
| controller writes business | Keep business logic in its existing service layer |
| loop SQL (N+1) | Join or batch |
| cache update before commit | Update after commit |
| secrets in source/logs | Use configured secrets and redact output |
| over-abstract on first use | Reuse existing code; add abstraction when repetition warrants it |
| multi-line if without braces | Always brace |
| auto git push | Require explicit user authorization |
| retry an approval or sandbox denial through another tool/path | Treat the denial as final; report the blocked action and remaining work |
| treat your own question as host approval | Only the host's approval outcome authorizes a gated action |
| fix without a regression check | Add or update a test that fails on the old bug and passes now |
| claiming independent review of your own work | Use a separate reviewer when independent review is required |
| claiming checks passed without running them | Report the actual command, result and any limits |

Use structured edit tools for source changes. Never trade input validation, data integrity or accessibility for speed.
