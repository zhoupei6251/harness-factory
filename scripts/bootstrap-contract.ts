#!/usr/bin/env node
/**
 * The bootstrap contract in one place: what `scripts/bootstrap.ts` reads, and
 * every path it owns in the working tree.
 *
 * Why this module exists: check-bootstrap.ts and the two integration tests each
 * kept their own copy of that list. The copy in check-bootstrap.ts drifted to
 * paths bootstrap never writes (`.claude/CLAUDE.md`, `.codex/AGENTS.md`,
 * `.qoder/AGENTS.md`, `.codebuddy/AGENTS.md`, `GEMINI.md`), so 5 of its 12 checks
 * `[skip]`-ed permanently while the script still printed "No bootstrap drift
 * detected." One list, three consumers.
 */

/** Paths `scripts/bootstrap.ts` reads.
 *
 * A new input has to be added here. If it is not, the throwaway bootstrap run in
 * check-bootstrap.ts cannot reproduce the artifact and reports drift — that
 * failure is the reminder, not a false alarm to work around.
 */
export const BOOTSTRAP_INPUTS = ["ENTRY.md", "package.json", "core", "platforms", "routes", "scripts", "templates"];

/** Files whose bytes must equal what a fresh bootstrap run produces. */
export const GENERATED_FILES = [
  "AGENTS.md",
  "CLAUDE.md",
  ".trae/rules/project_rules.md",
  ".codebuddy/rules/project_rules.md",
  ".claude/rules/ENTRY.md",
  ".claude/rules/ROOT.md",
  ".codex/rules/ENTRY.md",
  ".codex/rules/ROOT.md",
  ".qoder/rules/ENTRY.md",
  ".qoder/rules/ROOT.md",
  ".trae/rules/ENTRY.md",
  ".trae/rules/ROOT.md",
  ".codebuddy/rules/ENTRY.md",
  ".codebuddy/rules/ROOT.md",
  "CLAUDE.harness.md",
  "AGENTS.harness.md",
  "GEMINI.harness.md",
];

/**
 * Root `MEMORY.md` is deliberately NOT in GENERATED_FILES: `npm run bootstrap
 * -- --route news` projects whichever route was selected, so byte-equality with
 * one specific route template is not an invariant. check-bootstrap.ts instead
 * requires it to match SOME `routes/<route>/MEMORY.md` verbatim, which catches
 * both failure modes (root edited directly, source edited without re-run)
 * without hard-coding the selected route.
 */
export const ROUTE_MEMORY = "MEMORY.md";

const OWNED_TOP_DIRS = new Set([".claude", ".codex", ".qoder", ".trae", ".codebuddy", ".ai-runtime-artifacts", ".harness-novel-runtime", ".harness-news-runtime"]);

/**
 * Is this repo-root-relative path owned by bootstrap (generated output or the
 * runtime dirs it mkdirs)? Tests use this to copy the repo the way a fresh clone
 * looks — sources only — so an assertion about generation cannot be satisfied by
 * a copy of an already-generated file.
 */
export function isBootstrapOwned(rel: string): boolean {
  const normalised = rel.replaceAll("\\", "/");
  const top = normalised.split("/")[0];
  return OWNED_TOP_DIRS.has(top) || normalised === ROUTE_MEMORY || GENERATED_FILES.includes(normalised);
}
