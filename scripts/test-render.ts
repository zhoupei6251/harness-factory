#!/usr/bin/env node
/**
 * Run the Python render-engine self-test as part of `npm test`.
 *
 * path_b_selftest.py is stdlib-only and offline, but its assertions cover
 * render-path invariants that no TypeScript test reaches (on-screen sentence
 * rules, subtitle geometry, image gates, pack contrast). The assertion count is
 * printed by the script itself — never copy it here (news ARCHITECTURE D26).
 * Keeping it behind a Node launcher means one test entry point without adding a
 * Python framework.
 */
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SELFTEST = resolve(ROOT, "skills", "douyin-pro", "scripts", "path_b_selftest.py");
const candidates = process.platform === "win32" ? ["python", "py"] : ["python3", "python"];

for (const exe of candidates) {
  const probe = spawnSync(exe, ["--version"], { encoding: "utf-8" });
  if (probe.error || probe.status !== 0) continue;

  console.log(`[test:render] ${exe} ${(probe.stdout || probe.stderr).trim()}`);
  const run = spawnSync(exe, [SELFTEST], { cwd: ROOT, stdio: "inherit" });
  if (run.error) {
    console.error(`[test:render] failed to spawn ${exe}: ${run.error.message}`);
    process.exit(1);
  }
  process.exit(run.status ?? 1);
}

console.error(
  `[test:render] no Python interpreter found (tried: ${candidates.join(", ")}). ` +
    "Install Python 3.11+ — the self-test imports tomllib.",
);
process.exit(1);
