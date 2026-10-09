#!/usr/bin/env node
import { cp, mkdtemp, readFile, readdir, realpath, rm, stat } from "node:fs/promises";
import { existsSync } from "node:fs";
import { join, resolve, dirname } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..");

let fail = 0;

async function exists(path: string): Promise<boolean> {
  try {
    await stat(path);
    return true;
  } catch {
    return false;
  }
}

/**
 * Inputs scripts/bootstrap.ts reads, copied into the temporary repo root so the
 * smoke test can exercise bootstrap without writing to the real repository.
 */
const BOOTSTRAP_INPUTS = [
  "ENTRY.md",
  "package.json",
  "core",
  "platforms",
  "routes",
  "scripts",
];

/** Artifacts bootstrap must create — asserted inside the temporary root. */
const EXPECTED = [
  "AGENTS.md",
  "CLAUDE.md",
  ".claude/rules/ENTRY.md",
  ".claude/rules/ROOT.md",
  ".codex/rules/ENTRY.md",
  ".codex/rules/ROOT.md",
  ".trae/rules/project_rules.md",
  ".trae/rules/ENTRY.md",
  ".trae/rules/ROOT.md",
  ".codebuddy/rules/project_rules.md",
  ".codebuddy/rules/ENTRY.md",
  ".codebuddy/rules/ROOT.md",
  ".qoder/rules/ENTRY.md",
  ".qoder/rules/ROOT.md",
  ".ai-runtime-artifacts/specs",
  ".ai-runtime-artifacts/plans",
  ".ai-runtime-artifacts/decisions",
  ".ai-runtime-artifacts/verifications",
  "MEMORY.md",
];

/**
 * Repository-root paths an earlier version of this test deleted with `rm -rf`
 * (and thereby destroyed developer work: verified artifacts, drafts, renders).
 * The test must leave every one of them byte-for-byte untouched.
 */
const ROOT_MUST_SURVIVE = [
  "AGENTS.md",
  "CLAUDE.md",
  "MEMORY.md",
  ".claude",
  ".codex",
  ".trae",
  ".codebuddy",
  ".qoder",
  ".ai-runtime-artifacts",
  ".harness-novel-runtime",
  ".harness-news-runtime",
];

/**
 * Snapshot of the repository root: top-level entries (except node_modules, whose
 * mtime npm may legitimately touch) plus stat of the must-survive paths.
 */
async function snapshotRoot(): Promise<string[]> {
  const lines: string[] = [];
  const entries = (await readdir(ROOT)).filter((name) => name !== "node_modules").sort();
  for (const name of entries) {
    lines.push(`top ${name} ${await describe(await stat(resolve(ROOT, name)))}`);
  }
  for (const path of ROOT_MUST_SURVIVE) {
    lines.push(`guard ${path} ${await describeOrNull(resolve(ROOT, path))}`);
  }
  return lines;
}

async function describeOrNull(path: string): Promise<string> {
  try {
    return await describe(await stat(path));
  } catch {
    return "absent";
  }
}

async function describe(st: { isDirectory(): boolean; mtimeMs: number; size: number }): Promise<string> {
  return st.isDirectory() ? `dir mtime=${st.mtimeMs}` : `file size=${st.size} mtime=${st.mtimeMs}`;
}

/**
 * Delete a path only when it provably lives inside the system temp directory.
 * Guards against ever pointing recursive removal at the repository root again.
 */
async function safeRemoveTemp(path: string, tempRealPath: string): Promise<void> {
  const target = await realpath(path).catch(() => resolve(path));
  if (target !== tempRealPath && !target.startsWith(tempRealPath + "/") && !target.startsWith(tempRealPath + "\\")) {
    throw new Error(`refusing to remove path outside the temp root: ${target}`);
  }
  await rm(path, { recursive: true, force: true });
}

const before = await snapshotRoot();

// Resolve tsx from this repo's node_modules so the test never writes to the root.
const tsx = resolve(ROOT, "node_modules", "tsx", "dist", "cli.mjs");
if (!existsSync(tsx)) {
  console.log("[FAIL] tsx not found at node_modules/tsx/dist/cli.mjs — run `npm install` first");
  process.exit(1);
}

const tempRootRaw = await mkdtemp(join(tmpdir(), "hf-bootstrap-smoke-"));
const tempRoot = await realpath(tempRootRaw);
console.log(`[info] temporary repo root: ${tempRoot}`);

try {
  for (const input of BOOTSTRAP_INPUTS) {
    const src = resolve(ROOT, input);
    if (!(await exists(src))) {
      console.log(`[FAIL] missing bootstrap input in repo: ${input}`);
      fail = 1;
      continue;
    }
    await cp(src, resolve(tempRoot, input), { recursive: true });
  }

  // bootstrap.ts derives its ROOT from its own file location, so the copy inside
  // the temp root projects every artifact there and never touches the repository.
  const result = spawnSync(
    process.execPath,
    [tsx, resolve(tempRoot, "scripts", "bootstrap.ts"), "--platform", "all", "--route", "code"],
    { cwd: tempRoot, encoding: "utf-8" },
  );

  if (result.status !== 0) {
    console.log(`[FAIL] bootstrap exited with code ${result.status}`);
    if (result.stdout) console.log(result.stdout);
    if (result.stderr) console.log(result.stderr);
    fail = 1;
  } else {
    console.log("[ok] bootstrap exited 0");
    for (const line of (result.stdout || "").trim().split("\n")) {
      console.log(`     ${line}`);
    }
  }

  for (const e of EXPECTED) {
    const abs = resolve(tempRoot, e);
    if (await exists(abs)) {
      console.log(`[ok]   ${e} created in temp root`);
    } else {
      console.log(`[FAIL] ${e} missing in temp root`);
      fail = 1;
    }
  }

  // Required-tooling clause must survive into every native entry, and NEVER.md
  // must carry the two forbidden rows (spec: docs/superpowers/specs/
  // 2026-10-09-required-tooling-design.md §1).
  const NATIVE_ENTRIES = [
    "CLAUDE.md",
    "AGENTS.md",
    ".trae/rules/project_rules.md",
    ".codebuddy/rules/project_rules.md",
  ];
  const ENTRY_MARKERS = ["Tooling (required", "降级", "Tooling（本端接入）"];
  for (const entry of NATIVE_ENTRIES) {
    const body = await readFile(resolve(tempRoot, entry), "utf-8");
    const missing = ENTRY_MARKERS.filter((m) => !body.includes(m));
    if (missing.length === 0) {
      console.log(`[ok]   ${entry} carries required-tooling clause`);
    } else {
      console.log(`[FAIL] ${entry} missing markers: ${missing.join(", ")}`);
      fail = 1;
    }
  }

  // AGENTS.md is shared by codex and qoder: both deltas must survive the merge,
  // and the qoder delta must not be overwritten by a later single-platform run.
  const agents = await readFile(resolve(tempRoot, "AGENTS.md"), "utf-8");
  for (const delta of ["Codex platform rules", "Qoder platform rules"]) {
    if (agents.includes(delta)) {
      console.log(`[ok]   AGENTS.md merges the ${delta.toLowerCase()}`);
    } else {
      console.log(`[FAIL] AGENTS.md missing the ${delta} delta`);
      fail = 1;
    }
  }

  // core/NEVER.md is loaded by priority, not concatenated into native entries.
  const neverBody = await readFile(resolve(tempRoot, "core", "NEVER.md"), "utf-8");
  for (const marker of ["change code without evidence", "skip the lazy ladder"]) {
    if (neverBody.includes(marker)) {
      console.log(`[ok]   core/NEVER.md forbids "${marker}"`);
    } else {
      console.log(`[FAIL] core/NEVER.md missing forbidden row "${marker}"`);
      fail = 1;
    }
  }

  // The repository root must be byte-for-byte unchanged by the smoke test.
  const after = await snapshotRoot();
  if (after.join("\n") === before.join("\n")) {
    console.log("[ok]   repository root unchanged (no writes, no deletions)");
  } else {
    console.log("[FAIL] repository root was modified by the smoke test:");
    const beforeSet = new Set(before);
    const afterSet = new Set(after);
    for (const line of after) if (!beforeSet.has(line)) console.log(`       + ${line}`);
    for (const line of before) if (!afterSet.has(line)) console.log(`       - ${line}`);
    fail = 1;
  }
} finally {
  await safeRemoveTemp(tempRootRaw, tempRoot);
  if (await exists(tempRootRaw)) {
    console.log(`[FAIL] temp root not cleaned up: ${tempRootRaw}`);
    fail = 1;
  } else {
    console.log("[ok]   temp root removed");
  }
}

if (fail === 0) {
  console.log("");
  console.log("Bootstrap smoke test passed.");
} else {
  console.log("");
  console.log("Bootstrap smoke test FAILED.");
  process.exit(1);
}
