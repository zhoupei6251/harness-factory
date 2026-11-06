# routing.md - code route

| Route | When | Initialization template | Runtime dir |
|-------|------|-------------------------|-------------|
| `code` | Software engineering | `templates/code-MEMORY.md` | `.ai-runtime-artifacts/` |

Only `--route code` is accepted. Bootstrap initializes a missing root `MEMORY.md`; existing project state is preserved.

Runtime scratch stays gitignored. Durable plans and verification records are optional for routine work; for complex work keep them under `records/plans/` and `records/verifications/` respectively.
