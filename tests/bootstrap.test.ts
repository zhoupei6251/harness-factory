#!/usr/bin/env node
import { stat, rm } from "node:fs/promises";
import { resolve, dirname } from "node:path";
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

const TEST_ARTIFACTS = [
  ".claude",
  ".codex",
  ".trae",
  ".codebuddy",
  ".ai-runtime-artifacts",
  "MEMORY.md",
];

async function cleanup(): Promise<void> {
  for (const a of TEST_ARTIFACTS) {
    await rm(resolve(ROOT, a), { recursive: true, force: true });
  }
}

await cleanup();

// Run bootstrap via npm (uses package.json scripts/bootstrap which invokes tsx)
const result = spawnSync("npm", ["run", "bootstrap", "--", "--platform", "all", "--route", "code"], {
  cwd: ROOT,
  encoding: "utf-8",
  shell: true,
});

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

// Check expected artifacts
const expected = [
  ".claude/rules/ENTRY.md",
  ".claude/rules/ROOT.md",
  ".codex/rules/ENTRY.md",
  ".codex/rules/ROOT.md",
  ".trae/rules/ENTRY.md",
  ".trae/rules/ROOT.md",
  ".codebuddy/rules/ENTRY.md",
  ".codebuddy/rules/ROOT.md",
  ".ai-runtime-artifacts/specs",
  ".ai-runtime-artifacts/plans",
  ".ai-runtime-artifacts/decisions",
  ".ai-runtime-artifacts/verifications",
  "MEMORY.md",
];

for (const e of expected) {
  if (await exists(resolve(ROOT, e))) {
    console.log(`[ok]   ${e} created`);
  } else {
    console.log(`[FAIL] ${e} missing`);
    fail = 1;
  }
}

// Clean up
await cleanup();

if (fail === 0) {
  console.log("");
  console.log("Bootstrap smoke test passed.");
} else {
  console.log("");
  console.log("Bootstrap smoke test FAILED.");
  process.exit(1);
}
