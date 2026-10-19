#!/usr/bin/env node
/**
 * install-hooks.ts — copy git-hooks/<name> → .git/hooks/<name> and chmod +x.
 *
 * Why: bootstrap outputs are gitignored. There is no `git pull` event that
 * refreshes `.git/hooks/` — git only seeds that directory on `git init`,
 * and never overwrites a custom one. Without an installer, a fresh clone
 * has no pre-commit gate even though `git-hooks/pre-commit` is in the
 * working tree. Run `npm run hooks:install` once per clone (and again
 * after any change to git-hooks/).
 *
 * Idempotent: re-running on a fresh source overwrites the installed hook,
 * preserving git's own existing samples if they happen to share a name.
 *
 * Windows note: git for Windows does not require +x on hook scripts; the
 * bash shebang line is enough. We still call chmod — POSIXNode ignores
 * the failure on Windows where the binary may not exist.
 */
import { copyFile, mkdir, readFile, stat, chmod } from "node:fs/promises";
import { existsSync } from "node:fs";
import { resolve, dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..");
const SRC_DIR = resolve(ROOT, "git-hooks");
const DST_DIR = resolve(ROOT, ".git", "hooks");

let fail = 0;

function ok(msg: string): void {
  console.log(`[ok]   ${msg}`);
}

function bad(msg: string): void {
  console.log(`[FAIL] ${msg}`);
  fail++;
}

async function exists(p: string): Promise<boolean> {
  try {
    await stat(p);
    return true;
  } catch {
    return false;
  }
}

const gitDir = resolve(ROOT, ".git");
if (!(await exists(gitDir))) {
  console.log("[FAIL] not a git repository (no .git/ at repo root) — install-hooks only operates inside a checkout");
  process.exit(1);
}

await mkdir(DST_DIR, { recursive: true });

// Enumerate every file in git-hooks/ and mirror it into .git/hooks/. We do
// not hard-code `pre-commit` — future gates (commit-msg, pre-push, …)
// drop into git-hooks/ and get installed by the same script.
const entries = (await import("node:fs/promises")).readdir(SRC_DIR);
const names = (await entries).filter((n) => !n.startsWith("."));

if (names.length === 0) {
  console.log(`[FAIL] no hook sources in ${SRC_DIR}`);
  process.exit(1);
}

for (const name of names) {
  const src = join(SRC_DIR, name);
  const dst = join(DST_DIR, name);
  const srcStat = await stat(src);
  if (!srcStat.isFile()) continue;

  // Refuse to clobber a hook git itself seeded (the .sample variants), or a
  // hook the user installed themselves. They can opt in by re-running with
  // --force; the script intentionally does not silently overwrite.
  const dstExists = await exists(dst);
  if (dstExists) {
    const head = (await readFile(dst, "utf-8")).slice(0, 256);
    const isOurCopy = head.includes("harness-factory pre-commit gate") || head.includes("harness-factory-managed");
    if (!isOurCopy && !process.argv.includes("--force")) {
      bad(`${name} exists at ${dst} and does not look like a harness-factory hook — refusing to overwrite (re-run with --force)`);
      continue;
    }
  }

  await copyFile(src, dst);
  // POSIX only; on Windows the chmod call is a no-op and the shebang is
  // sufficient for git's bash runner.
  try {
    await chmod(dst, 0o755);
  } catch {
    // ignore
  }
  ok(`installed ${name} (from git-hooks/${name})`);
}

console.log("");
if (fail === 0) {
  console.log("Hooks installed. Pre-commit gate: `npm run check-bootstrap`.");
  console.log("Re-run after editing anything under git-hooks/.");
} else {
  console.log(`install-hooks FAILED (${fail} issue(s)).`);
  process.exit(1);
}