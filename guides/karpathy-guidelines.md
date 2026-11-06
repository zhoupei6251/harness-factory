# karpathy-guidelines.md - thinking rules for coding

1. Understand the task and observable pass criteria before editing.
2. Read current code, relevant callers and one nearby example when the pattern is unfamiliar.
3. Take the first complete option: do nothing unnecessary, reuse existing code, use standard/platform features, reuse installed dependencies, then write the minimum.
4. Keep changes within the authorized scope. Do not add future options, wrappers or abstractions for a single use.
5. Batch related edits; run the checks that can detect the affected failure modes.
6. New non-trivial behavior needs a meaningful test or a small executable self-check. Pure wording and trivial reversible edits do not need invented tests.
7. Review the diff before committing. State what changed, what was verified and what remains uncertain.

A plan/document is a tool for complexity, not a prerequisite for every change. Reuse fresh evidence and successful checks unless changed code makes them stale.
