# Code-only Harness maintenance plan

**Goal:** Distribute only software-engineering rules, minimize coding overhead and keep correctness verifiable.

**Authorization:** The user requested implementation, repository cleanup, commit to main and push.

## Implementation

1. Keep `code` as the sole route in directories, schema, bootstrap and documentation.
2. Remove obsolete material and local outputs; retain frontend guidance as on-demand upstream links.
3. Enumerate tracked source paths through Git instead of walking output directories. Reuse current tooling and add no dependency.
4. Check route-schema consistency and active skill metadata in the existing structural audit.
5. Preserve targeted evidence, boundary validation, meaningful tests, project memory and independent review for material risks.
6. Run the repository checks, inspect the diff, commit on main and push normally.

## Evidence

Project: `D-work-xinyue-aigc_platfrom_back-harness-factory`; graph generation `2026-10-30T02:26:04Z`.
Graph searches locate stats/bootstrap/validation functions. `trace_path(stats.walk, both)` identifies the stats module as its caller; `get_code_snippet` confirms recursive directory traversal. Cited-path coverage records match current metadata. Exact source and repository-wide searches supplement the graph for documents and local artifacts.

## Pass criteria

- Only code and shared engineering support remain in the current repository files.
- Source statistics ignore untracked and ignored outputs and handle non-ASCII/space-containing paths.
- Invalid routes fail before writes; generated entries match canonical sources and preserve project state.
- Full checks pass, independent review has no unresolved material findings, and remote main matches the commit.
