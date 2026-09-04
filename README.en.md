# Harness Foundry

> A standalone multi-agent AI workflow framework that you drop into **any project** to help it use AI better — unified driver for **Claude Code / Trae / Codex / WorkBuddy**, one truth source, rebuilt anytime.

**Independent of any host project**: harness-foundry is not part of a business repository — it is a portable toolkit. Clone it (or add it as a submodule) into the root of any project to give that project AI workflow capabilities: intent routing, stage gates, expert agents, review chains, and intelligent code understanding.

[中文](README.md)

---

## What It Does

Harness Foundry provides a structured orchestration layer on top of any AI coding IDE. Instead of a free-form chat loop, it enforces discipline:

```
User Intent → Intent Routing → Domain Leader → Stage Gates → Parallel Workers → Verification
```

Three operational domains share the same orchestration primitives:

| Domain | Stage Gates | Workers |
|--------|-----------|---------|
| **code** | spec → plan → implement → verify | coder, debugger, reviewer, test-engineer, explorer |
| **novel** | outline → chapter → revision → publish | novel-writer, novel-planner, novel-reviewer, humanizer |
| **news** | angle → draft → fact-check → polish → publish | news-writer, fact-checker, news-editor |

Every session starts by reading `core/intent-routing.md` and declaring:

```
Route: <code|novel|news>
```

---

## Intelligence Layer (Smart Code Understanding)

Harness Foundry integrates **codebase-memory-mcp** (knowledge graph) and **ripgrep / LSP** for intelligent code comprehension:

| Layer | Tool | Capability |
|-------|------|------------|
| **Strategic** | codebase-memory-mcp (`index_repository` / `get_architecture`) | Project understanding, architecture analysis, natural language Q&A |
| **Tactical · Graph** | codebase-memory (`search_graph` / `trace_path` / `detect_changes`) | Cross-file structure, call graphs, impact |
| **Tactical · Text** | ripgrep (`rg`) | Strings / comments / paths / TODOs |
| **Tactical · LSP** | LSP (`textDocument/definition` / `references` / `hover` / `diagnostic`) | Compiler-level definitions, refs, types, diagnostics |
| **Tactical · Orchestration** | `code-insight-stack` | Unified entrypoint for the three-layer stack |

**Benefits**:
- Understand unfamiliar projects in 5 minutes
- 57% reduction in Token consumption
- 71% reduction in tool calls

### One-Command Install

```bash
# Linux/macOS
bash scripts/install-intelligence-deps.sh

# Windows PowerShell
.\scripts\install-intelligence-deps.ps1

# Optional: Initialize project index after installation
index_repository(project_path="<project>")
```

See: [v2.1 Architecture](docs/specs/harness-foundry-v2.1-architecture.md) | [User Guide](docs/intelligence-layer-user-guide.md) | [Troubleshooting](docs/intelligence-layer-troubleshooting.md)

---

## Quick Start

```bash
# 1. Project adapters to your IDE
bash scripts/bootstrap.sh --target all       # All platforms
bash scripts/bootstrap.sh --target trae      # Trae only
bash scripts/bootstrap.sh --target claude    # Claude Code only
bash scripts/bootstrap.sh --target codex     # Codex only
bash scripts/bootstrap.sh --target workbuddy # WorkBuddy only

# 2. Sync skills
bash scripts/sync-skills.sh --target all

# 3. Install dependency plugins (one-time; see "Three-Layer Architecture" below)
claude plugin marketplace add ecc https://github.com/affaan-m/ECC
claude plugin install ecc@ecc
claude plugin marketplace add claude-plugins-official https://github.com/anthropics/claude-plugins-official
claude plugin install superpowers@claude-plugins-official
claude plugin marketplace add ponytail https://github.com/DietrichGebert/ponytail
claude plugin install ponytail@ponytail

# 4. Preview first (safe — no writes)
bash scripts/bootstrap.sh --target all --dry-run
bash scripts/sync-skills.sh --target all --dry-run

# 5. Verify
bash scripts/verify.sh
```

**Windows:** Use `bash` from Git Bash or WSL. PowerShell equivalents exist:
```powershell
.\scripts\bootstrap.ps1 -Target all
.\scripts\sync-skills.ps1 -Target all -DryRun
```

---

## Three-Layer Architecture: superpowers + ecc + harness

Harness Foundry is the orchestration layer; it depends on three plugin ecosystems (**not vendored in this repo**, loaded at runtime from plugins):

| Layer | Ecosystem | Version | Role | Install |
|-------|-----------|---------|------|---------|
| **Methodology** | [obra/superpowers](https://github.com/obra/superpowers) | 6.2.0 | Process skills: brainstorming / systematic-debugging / TDD / parallel dispatch | `claude plugin install superpowers@claude-plugins-official` |
| **Expert agent pool** | [affaan-m/ECC](https://github.com/affaan-m/ECC) | 2.0.0 | 80+ review/build/design agents: `java-reviewer`, `security-reviewer`, `code-architect` | `claude plugin install ecc@ecc` |
| **Minimal-code baseline** | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) | 4.9.0 | Lazy-ladder ruleset: YAGNI / stdlib-first / one-line-first, resident during implementation | `claude plugin install ponytail@ponytail` |
| **Orchestration** | harness-foundry (this repo) | — | Routing table + stage gates + review chain + 3 domains | `git clone` this repo |

### Plugin Dependencies: What Breaks If Missing

- **Without superpowers**: `Skill(superpowers:brainstorming)`, `systematic-debugging`, etc. fail silently — design/debug flows degrade
- **Without ecc (optional)**: code review chain falls back to local `agents/ecc-*.md` (java/security/database reviewer); functionality preserved. Optional install `claude plugin install ecc@ecc` for richer specialists (type-design / silent-failure / pr-test-analyzer etc.)
- **Without ponytail**: the lazy ladder (YAGNI / stdlib-first / one-line-first) is not injected during implementation; the code domain falls back to the karpathy-guidelines baseline
- **No error when missing**: Claude ignores unknown skill/agent references silently — always install plugins on a new machine

### Division of Labor

- **superpowers owns process**: design (brainstorming) → plan (writing-plans) → debug (systematic-debugging) → test (test-driven-development) → finish (finishing-a-development-branch), triggered by [core/intent-routing.md](core/intent-routing.md)
- **ecc owns experts**: post-code mandatory `ecc:java-reviewer`, conditional security / database / type-design / silent-failure reviews, build failures → `ecc:java-build-resolver` (see [skill-preferences.md](core/orchestration/skill-preferences.md))
- **ponytail owns minimalism**: injects the lazy ladder (YAGNI → reuse → stdlib → native platform → installed deps → one line → minimal implementation) during implementation; `/ponytail-review` emits a deletion list for a diff (see [skill-preferences.md](core/orchestration/skill-preferences.md))
- **harness owns orchestration**: Route declaration → routing table → stage gates → review chain, shared across 3 domains (code/novel/news)

> The 84 skills in `skills/` are harness-specific; 57 skills that duplicated plugin skills (brainstorming, etc.) were deduplicated on 2026-08-05 and are no longer vendored.

---

## Architecture

```
harness-foundry/
├── AGENTS.md                     # Unified entry: code of conduct R1-R8 + prohibitions + runbook
├── RULES.md                      # Top-level rules digest
├── CLAUDE.md                     # Claude Code context file
│
├── core/                         # Platform-agnostic truth source
│   ├── ENTRY.md                  # Core entry
│   ├── intent-routing.md         # Intent routing table (read first)
│   ├── routing.md                # Compat alias → intent-routing.md
│   ├── NEVER.md                  # Hard prohibitions (417 trap rules)
│   ├── principles.md             # 10 core principles
│   ├── capabilities/             # Capability ID registry
│   ├── intelligence/             # Intelligence Layer config
│   ├── memory/                   # Memory management protocol
│   ├── orchestration/            # Dispatcher, roles, skill routing
│   │   ├── domain-config.yaml    # Domain → agent/skill mapping
│   │   ├── dispatcher-workflow.md # Parallel dispatch workflow (≤5 workers)
│   │   └── skill-preferences.md  # WU-level skill routing
│   ├── review/                   # Two-stage review protocol
│   ├── rules/                    # Design gate rules
│   ├── optimization/             # Token optimization strategy
│   ├── observability/            # Health protocol / metrics
│   ├── eval/                     # Eval framework
│   ├── security/                 # Canary token protocol
│   └── karpathy-guidelines.md    # Code of conduct original text
│
├── adapters/                     # Platform physical bindings (thin shells; status: adapters/README.md)
│   ├── README.md                 # Adapter status overview (all four usable)
│   ├── TEMPLATE/                 # New adapter template
│   ├── agents/                   # AGENTS.md unified code of conduct
│   ├── claude/                   # Claude Code adapter (incl. desktop support)
│   ├── trae/                     # Trae IDE adapter (incl. Trae Work / CLI notes)
│   ├── codex/                    # Codex adapter (ChatGPT desktop / CLI shared)
│   └── workbuddy/                # WorkBuddy adapter (Tencent, = CodeBuddy dual brand)
│
├── skills/                       # ★ 84 Skills (flat structure, deduplicated)
│   ├── INDEX.md                  # Complete skill index (auto-generated)
│   ├── categories.yaml           # 57 category definitions
│   ├── _layer.yaml               # Skill layer classification
│   └── <slug>/SKILL.md           # Each skill in its own directory
│
├── agents/                       # ★ 34 Agents (flat structure)
│   ├── leader-*.md               # Domain leaders (code / novel / news / product)
│   ├── coder.md / debugger.md    # Coding / debugging
│   ├── reviewer.md / code-reviewer.md / spec-compliance-reviewer.md  # Review
│   ├── test-engineer.md / explorer.md / architect.md / planner.md    # Other roles
│   ├── novel-*.md / news-*.md    # Novel / news domain agents
│   ├── product-*.md              # Product domain agents
│   ├── ecc-*.md (+ .meta.json)   # ECC review agents (review phase)
│   └── *.md                      # Other specialized agents
│
├── hooks/                        # Guardrail static config (hooks not mounted)
│   ├── README.md                 # Guardrail architecture
│   ├── guardrails/               # Double-layer protection (parallel input + sequential output)
│   │   ├── guardrail-config.json # Rules config center
│   │   └── rules/                # Rule docs (prompt-injection / sensitive-data etc.)
│   └── continuous-learning/      # Experience protocol (user-triggered, not automatic)
│
├── scripts/                      # Utility scripts (30+)
│   ├── bootstrap.sh / bootstrap.ps1         # Project adapters to your IDE
│   ├── bootstrap-self.sh                    # Self-bootstrap (developing harness itself)
│   ├── init-project.sh                      # Template-based project init
│   ├── sync-skills.sh / sync-skills.ps1     # Sync skills to IDE
│   ├── verify.sh                            # CI verification entry
│   ├── gen-skill-index.sh / gen-skill-index.ps1
│   ├── gen-skill-graph.py / auto-fill-frontmatter.py / classify-skills.py
│   ├── skill-quality-check.sh / harness-check.sh / harness-health.js
│   ├── novel/                   # Novel tools (novel_graph.py plot graph + causality breaker)
│   ├── dashboard/               # Dashboard GUI
│   ├── eval/                    # Eval testing
│   ├── security/                # Security scanning
│   └── visual-companion/        # Visual companion tool
│
├── tests/                        # L1 static / L2 integration / L3 intelligence tests
│   ├── L1-static/               # Agent format, skill meta, NEVER validation
│   ├── L2-integration/          # Routing / domain config / sync tests
│   └── L3-eval/ L3-intelligence/ # Eval & Intelligence Layer tests
│
├── commands/                     # Quick commands
├── contexts/                     # Domain-specific contexts (code / novel / news / review)
├── rules/                        # Tech-stack-specific coding rules
├── references/                   # Context maps, instincts, traps
├── traps-archive/                # Historical trap archive (417 rules)
│   ├── code/00-all.md            # 251 code traps
│   ├── novel/00-all.md           # 82 novel traps
│   └── news/00-all.md            # 69 news traps
│
├── handoff/                      # Agent handoff protocol
├── memory/                       # Memory storage
├── schemas/                      # JSON schemas
├── examples/                     # Examples (novel-graph/ plot-graph sample)
├── artifact-templates/           # Artifact templates
├── docs/                         # Documentation
│   ├── QUICKSTART.md / USER-GUIDE.md / CLI-REFERENCE.md / CLAUDE-TEMPLATE.md
│   ├── skill-frontmatter-schema.md / skill-dependency-graph.md
│   ├── intelligence-layer-*.md   # Intelligence Layer docs
│   └── specs/                    # Architecture design docs
│
├── CHANGELOG.md / CONTRIBUTING.md
└── LICENSE
```

---

## Intent Routing

`core/intent-routing.md` is the **single mandatory entry point** for every session. It maps natural language triggers to domains and capability IDs:

| Trigger Phrases | Domain | Capability |
|----------------|--------|-----------|
| 写代码 / 实现 / 修 bug / 重构 | code | `roles.coder` |
| 设计 / 架构 / 方案 | code | `roles.architect` |
| 调试 / 排查 | code | `roles.debugger` |
| 审查 / review | code | `roles.reviewer` |
| 写小说 / 章节 / 续写 | novel | `roles.novel-writer` |
| 写新闻 / 报道 / 快讯 | news | `roles.news-writer` |
| 小改动 / quick fix | code | Direct (no dispatch) |

---

## Skill System

**84 Skills** in a flat `skills/<slug>/SKILL.md` structure (deduplicated against ecc/superpowers plugins on 2026-08-05).

### Category System (57 Categories)

| Category | Count | Description |
|----------|-------|-------------|
| code | 18 | Full code development lifecycle |
| novel | 26 | Novel writing and editing |
| news | 3 | News writing and fact-checking |
| shared | 6 | Cross-domain skills |
| biz | 2 | Business analysis |
| crypto | 1 | Cryptography related |
| science | 1 | Scientific research |

### Skill Layer Classification

```yaml
_layer.yaml:
  core:        # Core skills (84) — synced to IDE projections by default
  peripheral:  # Peripheral skills (0) — all merged into core after dedup
  archived:    # Archived skills — not synced
```

### Skill Metadata

Each Skill may contain optional `_meta.json`:
```json
{
  "slug": "skill-name",
  "domain": "code|novel|news|shared",
  "category": "category-id",
  "tags": ["tag1", "tag2"],
  "purpose": "Brief description",
  "requires": ["other-skill"],
  "complements": ["related-skill"],
  "conflicts": ["incompatible-skill"]
}
```

### Loading Path (Cursor example)

1. `.cursor/skills/<slug>/SKILL.md` — projection (generated by `sync-skills.sh`)
2. `skills/<slug>/SKILL.md` — truth source
3. `~/.cursor/skills/<slug>/SKILL.md` — user global

---

## Agent Pool

**34 Agents** across 3 domains. Each agent is a markdown file with YAML frontmatter.

| Domain | Leader | Primary Workers |
|--------|--------|---------------|
| **code** | leader-code | coder, debugger, reviewer, test-engineer, explorer |
| **novel** | leader-novel | novel-writer, novel-planner, novel-reviewer, humanizer, memory-keeper |
| **news** | leader-news | news-writer, fact-checker, news-editor |

### Specialized Reviewers (ecc plugin agents · optional)

Provided by the ecc plugin (`spawn ecc:*`), invoked only during the review phase; **falls back to local `agents/ecc-*.md`** when missing:

- `ecc:java-reviewer` — Java specialized review (recommended after writing code; falls back to `agents/ecc-java-reviewer.md`)
- `ecc:security-reviewer` — Security review (new APIs / permissions / user input; falls back to `agents/ecc-security-reviewer.md`)
- `ecc:database-reviewer` — Database review (SQL / DDL / schema changes; falls back to `agents/ecc-database-reviewer.md`)

### Handoff Protocol

All agent files include built-in Handoff protocol entries to ensure context transfer during multi-agent collaboration.

---

## Guardrails (Static Reference)

**Double-Layer Protection (P0-2)** is provided as static config — **hooks are not mounted** (discipline is enforced at session level by AGENTS.md + ecc gateguard; see Known Limitations):

| Layer | Type | Rules |
|-------|------|-------|
| **Input** (parallel, any-fail-block) | prompt injection | SQL injection | command injection | prompt override | path traversal |
| **Output** (sequential, any-block) | secret leak | canary token leak | NEVER violation | AI writing markers | syntax check |

**Config**: `hooks/guardrails/guardrail-config.json`
**Audit log**: `.ai-runtime-artifacts/guardrail-audit.jsonl` (produced after manual enablement)

### Canary Token

`scripts/canary-rotate.sh` generates Canary Tokens to detect prompt leakage. Token file (`core/security/canary-tokens.yaml`) is gitignored — never committed.

---

## Memory Management

| Layer | Path | Description |
|-------|------|-------------|
| **Global** | `~/.claude/GLOBAL-MEMORY.md` | Cross-project shared |
| **Project** | `MEMORY.md` (root) | Project-specific |
| **Session** | `memory/` | Runtime temporary |

See: [hooks/guardrails/guardrail-config.json](hooks/guardrails/guardrail-config.json)

---

## Testing & Verification

```bash
# Full CI verification
bash scripts/verify.sh

# L1 static checks
bash tests/L1-static/validate-agent-format.sh
bash tests/L1-static/validate-skill-meta.sh
bash tests/L1-static/validate-never.sh

# L2 integration checks
bash tests/L2-integration/validate-routing.sh
bash tests/L2-integration/validate-domain-config.sh

# Skill quality check
bash scripts/skill-quality-check.sh

# Shell script syntax
shellcheck scripts/*.sh
```

---

## Key Files Reference

| What you need | File |
|---------------|------|
| How this project works | [`CLAUDE.md`](CLAUDE.md) |
| Intent routing rules | [`core/intent-routing.md`](core/intent-routing.md) |
| Stage gates | [`core/intent-routing.md` § 阶段门禁](core/intent-routing.md) |
| Skill routing table | [`core/orchestration/skill-preferences.md`](core/orchestration/skill-preferences.md) |
| Dispatcher workflow | [`core/orchestration/dispatcher-workflow.md`](core/orchestration/dispatcher-workflow.md) |
| Domain config | [`core/orchestration/domain-config.yaml`](core/orchestration/domain-config.yaml) |
| All skills | [`skills/INDEX.md`](skills/INDEX.md) |
| Skill categories | [`skills/categories.yaml`](skills/categories.yaml) |
| Skill metadata spec | [`docs/skill-frontmatter-schema.md`](docs/skill-frontmatter-schema.md) |
| Skill dependency graph | [`docs/skill-dependency-graph.md`](docs/skill-dependency-graph.md) |
| All agents | [`agents/README.md`](agents/README.md) |
| Guardrails static config | [`hooks/README.md`](hooks/README.md) |
| **Intelligence Layer** | [`docs/intelligence-layer-user-guide.md`](docs/intelligence-layer-user-guide.md) |
| Trae quick ref | [`adapters/trae/trae-quick-ref.md`](adapters/trae/trae-quick-ref.md) |

---

## Changelog

| Date | Change |
|------|--------|
| **2026-08-05** | Intelligence Layer fully embraces codebase-memory-mcp: removed Understand-Anything (MCP config, install scripts, knowledge-graph references); strategic skills rewritten to `index_repository` / `get_architecture` |
| **2026-08-05** | Deduplicated against ecc/superpowers plugins: skills 141→84, removed 57 verbatim copies (now loaded from plugins at runtime); routing references prefixed with `superpowers:`/`ecc:`; `_layer.yaml` ghost references cleaned (196→84) |
| **2026-08-06** | Asset-usage audit: removed 4 foreign-ecosystem skills (Clawdbot/OpenClaw), 84→80; wired 4 valuable orphans (`novel-guardian` / `novel-foreshadowing-dag` / `novel-writer-cn` / `document-review`) into routing |
| **2026-08-06** | Novel-domain chain: novel-protocol entry (progressive disclosure + causality consistency) + novel-graph lite (`kb/graph.yaml` plot graph + causality circuit-breaker script) |

---

## Known Limitations

- Canary tokens are generated at runtime — not available for offline use
- Execution context providers (worktree/local) are defined but not yet fully wired
- Three planned domains (essay/math/academic) are stubbed out in `domain-config.yaml`
- CI only runs on Linux (shell scripts); Windows uses PowerShell equivalents

---

## License

MIT — see [`LICENSE`](LICENSE).

## Credits

Inspired by and cherry-picks from:

- [obra/superpowers](https://github.com/obra/superpowers) — skill-triggered workflow methodology
- [affaan-m/ECC](https://github.com/affaan-m/ECC) — 60+ agents, 230+ skills, multi-harness ecosystem
- **codebase-memory-mcp** — knowledge-graph-driven code understanding (strategic + tactical)
