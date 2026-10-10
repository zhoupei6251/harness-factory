#!/usr/bin/env node
// install-template.test.ts — 三个用例验证 install-into-project.ts

import { cp, mkdtemp, readFile, readdir, rm, stat, mkdir, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { join, resolve, dirname, basename } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..");
const INSTALL_SCRIPT = resolve(ROOT, "scripts/install-into-project.ts");
const TEMPLATES_BIRDS_EYE = resolve(ROOT, "templates/project-birds-eye.template.md");

// Resolve tsx from this repo's node_modules (same pattern as bootstrap.test.ts).
// `npx tsx` is unreliable from spawnSync; using node + direct tsx path avoids that.
const NODE = process.execPath;
const TSX = resolve(ROOT, "node_modules", "tsx", "dist", "cli.mjs");

let fail = 0;

function assert(cond: boolean, msg: string): void {
  if (cond) console.log(`[ok]   ${msg}`);
  else { console.log(`[FAIL] ${msg}`); fail++; }
}

function run(target: string, extra: string[] = []): { stdout: string; stderr: string; status: number } {
  const r = spawnSync(NODE, [TSX, INSTALL_SCRIPT, "--target", target, ...extra], { encoding: "utf-8" });
  return { stdout: r.stdout || "", stderr: r.stderr || "", status: r.status ?? 1 };
}

async function exists(path: string): Promise<boolean> {
  try { await stat(path); return true; } catch { return false; }
}

async function setupTarget(): Promise<string> {
  const base = await mkdtemp(join(tmpdir(), "harness-install-"));
  spawnSync("git", ["init", "--quiet"], { cwd: base, encoding: "utf-8" });
  spawnSync("git", ["config", "user.email", "test@test"], { cwd: base, encoding: "utf-8" });
  spawnSync("git", ["config", "user.name", "test"], { cwd: base, encoding: "utf-8" });
  return base;
}

/** 用真实内容（用户提供的 birds-eye 文件）来测，避免依赖 default 模板文字。 */
async function setupBirdsEye(): Promise<string> {
  const dir = await mkdtemp(join(tmpdir(), "harness-birdseye-"));
  const file = join(dir, "birds-eye.md");
  await writeFile(file, "# 测试项目\n\n- 名称: test\n- 定位: 测试 install-into-project 用的临时项目\n", "utf-8");
  return file;
}

async function testCleanTarget(): Promise<void> {
  console.log("--- test: clean target (other mode) ---");
  const target = await setupTarget();
  const birdsEye = await setupBirdsEye();
  const r = run(target, ["--birds-eye-file", birdsEye]);
  assert(r.status === 0, `exit code 0 (got ${r.status})`);

  for (const f of ["CLAUDE.md", "AGENTS.md", "GEMINI.md"]) {
    const ok = await exists(join(target, f));
    assert(ok, `${f} created`);
  }

  const claude = await readFile(join(target, "CLAUDE.md"), "utf-8");
  assert(!claude.includes("${PROJECT_BIRDS_EYE}"), "${PROJECT_BIRDS_EYE} replaced");
  assert(!claude.includes("${HARNESS_FACTORY_IMPORT}"), "${HARNESS_FACTORY_IMPORT} replaced");
  assert(claude.includes("# 测试项目"), "BIRDS_EYE content rendered into CLAUDE.md");
  assert(claude.includes("@harness-factory/CLAUDE.harness.md"), "CLAUDE.md has other-mode @import line");

  const agents = await readFile(join(target, "AGENTS.md"), "utf-8");
  assert(agents.includes("harness-factory/AGENTS.harness.md"), "AGENTS.md references harness-factory/AGENTS.harness.md in text instruction");

  const excludeFile = join(target, ".git/info/exclude");
  const exclude = existsSync(excludeFile) ? await readFile(excludeFile, "utf-8") : "";
  assert(exclude.includes("harness-factory"), "harness-factory added to .git/info/exclude");

  await rm(target, { recursive: true });
  await rm(birdsEye.replace(/birds-eye\.md$/, ""), { recursive: true });
}

async function testReinstallBackup(): Promise<void> {
  console.log("--- test: re-install with existing files (auto-backup) ---");
  const target = await setupTarget();
  const birdsEye = await setupBirdsEye();
  const r1 = run(target, ["--birds-eye-file", birdsEye]);
  assert(r1.status === 0, "first install: exit 0");
  const r2 = run(target, ["--birds-eye-file", birdsEye]);
  assert(r2.status === 0, "second install: exit 0");

  const files = await readdir(target);
  const bakFiles = files.filter((f) => f.includes(".bak-") && f.endsWith(".md"));
  assert(bakFiles.length === 3, `exactly 3 backup files created (got ${bakFiles.length})`);

  await rm(target, { recursive: true });
  await rm(birdsEye.replace(/birds-eye\.md$/, ""), { recursive: true });
}

async function testColleagueScenario(): Promise<void> {
  console.log("--- test: colleague scenario (no harness-factory/ dir, syntactically valid imports) ---");
  const target = await setupTarget();
  const birdsEye = await setupBirdsEye();
  const r = run(target, ["--birds-eye-file", birdsEye]);
  assert(r.status === 0, "install: exit 0");

  const claude = await readFile(join(target, "CLAUDE.md"), "utf-8");
  // @import line: starts with @, has a path, end of line
  const importLine = claude.split(/\r?\n/).find((l) => /^@/.test(l));
  assert(importLine !== undefined && /^@\S+$/.test(importLine.trim()), `valid @import line in CLAUDE.md (got: ${importLine})`);

  // AGENTS.md and GEMINI.md have text-instruction form
  const agents = await readFile(join(target, "AGENTS.md"), "utf-8");
  assert(/harness-factory\/AGENTS\.harness\.md/.test(agents), "AGENTS.md references harness-factory/AGENTS.harness.md");
  const gemini = await readFile(join(target, "GEMINI.md"), "utf-8");
  assert(/harness-factory\/GEMINI\.harness\.md/.test(gemini), "GEMINI.md references harness-factory/GEMINI.harness.md");

  await rm(target, { recursive: true });
  await rm(birdsEye.replace(/birds-eye\.md$/, ""), { recursive: true });
}

await testCleanTarget();
await testReinstallBackup();
await testColleagueScenario();

if (fail === 0) {
  console.log("");
  console.log("All install-template tests passed.");
} else {
  console.log("");
  console.log("install-template tests FAILED.");
  process.exit(1);
}
