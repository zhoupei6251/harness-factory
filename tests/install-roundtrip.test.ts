#!/usr/bin/env node
/**
 * install-roundtrip.test.ts — byte-equality roundtrip for install-into-project.ts.
 *
 * Why: install-into-project is the only entry point that writes the
 * three downstream files (CLAUDE.md / AGENTS.md / GEMINI.md) into a
 * target project. It is also the rollback path called out in
 * `ENTRY.md` § "Workflow (this repository only)". If its render logic
 * ever drifts from what `templates/target-*.md` + a birds-eye file
 * would produce on their own, a downstream that re-installs the same
 * fixture will get different bytes — and the only way anyone notices is
 * by reading the file.
 *
 * This test makes the roundtrip a checked invariant:
 *
 *   1. Spin up an empty `git init`'d target dir.
 *   2. Run install-into-project with a fixture birds-eye.
 *   3. Independently render each template by replacing ${PROJECT_BIRDS_EYE}
 *      and ${HARNESS_FACTORY_IMPORT} the way install-into-project would.
 *   4. Assert the two renderings are byte-equal (line endings excluded —
 *      Windows CRLF is a checkout artefact, not a contract).
 *   5. Re-run install-into-project on the same target with the same
 *      fixture: outputs must be byte-equal to the first run (idempotence).
 *   6. Run with a different fixture: outputs MUST differ (the script
 *      isn't accidentally ignoring the birds-eye file).
 *   7. Run with --dry-run after the real install: the target files
 *      must be unchanged (dry-run promise).
 *
 * Stays in a fresh temp dir for the whole run. Cleans up on the way out,
 * and the cleanup path refuses to rm anything outside the temp root.
 */
import { createHash } from "node:crypto";
import { mkdtemp, readFile, realpath, rm, writeFile, stat } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { resolve, dirname, join, sep } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..");
const NODE = process.execPath;
const TSX = resolve(ROOT, "node_modules/tsx/dist/cli.mjs");
const INSTALL_SCRIPT = resolve(ROOT, "scripts/install-into-project.ts");
const TEMPLATE_DIR = resolve(ROOT, "templates");

let fail = 0;
function assert(cond: boolean, msg: string): void {
  if (cond) console.log(`[ok]   ${msg}`);
  else { console.log(`[FAIL] ${msg}`); fail++; }
}

async function exists(p: string): Promise<boolean> {
  try { await stat(p); return true; } catch { return false; }
}

/** Same normalisation check-bootstrap uses for content equality. */
function contentHash(text: string): string {
  return createHash("sha256").update(text.replaceAll("\r\n", "\n")).digest("hex");
}

/** Mirror of install-into-project's templateImport() for "other" mode. */
function templateImport(file: "CLAUDE.md" | "AGENTS.md" | "GEMINI.md"): string {
  if (file === "CLAUDE.md") return "@harness-factory/CLAUDE.harness.md";
  if (file === "AGENTS.md") return "harness-factory/AGENTS.harness.md";
  return "harness-factory/GEMINI.harness.md";
}

/** Mirror of install-into-project's render() (same regexes, same trim). */
function render(template: string, birdsEye: string, importLine: string): string {
  return template
    .replace(/\$\{PROJECT_BIRDS_EYE\}/g, birdsEye.trim())
    .replace(/\$\{HARNESS_FACTORY_IMPORT\}/g, importLine);
}

function runInstall(target: string, birdsEyePath: string, extra: string[] = []): { status: number; stdout: string; stderr: string } {
  const r = spawnSync(NODE, [TSX, INSTALL_SCRIPT, "--target", target, "--birds-eye-file", birdsEyePath, ...extra], { encoding: "utf-8" });
  return { status: r.status ?? 1, stdout: r.stdout ?? "", stderr: r.stderr ?? "" };
}

async function safeRemoveTemp(p: string, root: string): Promise<void> {
  const target = await realpath(p).catch(() => resolve(p));
  if (target !== root && !target.startsWith(root + sep) && !target.startsWith(root + "/") && !target.startsWith(root + "\\")) {
    throw new Error(`refusing to remove path outside temp root: ${target}`);
  }
  await rm(p, { recursive: true, force: true });
}

const fixtureDir = await mkdtemp(join(tmpdir(), "hf-roundtrip-fixture-"));
const fixtureA = join(fixtureDir, "birds-eye-A.md");
const fixtureB = join(fixtureDir, "birds-eye-B.md");
const fixtureBodyA = "# 真实 fixture A\n\n- name: harness-roundtrip-A\n- description: 第一次安装用于确认安装逻辑严格按模板渲染\n";
const fixtureBodyB = "# 真实 fixture B\n\n- name: harness-roundtrip-B\n- description: 第二次安装用不同 fixture，确认不是缓存命中\n";
await writeFile(fixtureA, fixtureBodyA, "utf-8");
await writeFile(fixtureB, fixtureBodyB, "utf-8");

const tempRootRaw = await mkdtemp(join(tmpdir(), "hf-install-roundtrip-"));
const tempRoot = await realpath(tempRootRaw);

try {
  spawnSync("git", ["init", "--quiet"], { cwd: tempRoot, encoding: "utf-8" });
  spawnSync("git", ["config", "user.email", "roundtrip@test"], { cwd: tempRoot, encoding: "utf-8" });
  spawnSync("git", ["config", "user.name", "roundtrip"], { cwd: tempRoot, encoding: "utf-8" });

  // Step 1 + 2 + 3 + 4: render-equality against a freshly installed target.
  console.log("# Step 1-4: install + byte-equality against templates/target-*.md");
  const firstRun = runInstall(tempRoot, fixtureA);
  assert(firstRun.status === 0, `install-into-project exited 0 (got ${firstRun.status})`);
  if (firstRun.status !== 0) {
    console.log(firstRun.stdout);
    console.log(firstRun.stderr);
  }

  const expectedTemplateFiles = ["CLAUDE.md", "AGENTS.md", "GEMINI.md"] as const;
  for (const file of expectedTemplateFiles) {
    const expectedRaw = await readFile(join(TEMPLATE_DIR, `target-${file}`), "utf-8");
    const expectedContent = render(expectedRaw, fixtureBodyA, templateImport(file));
    const actualPath = join(tempRoot, file);
    assert(await exists(actualPath), `${file} was written into target`);
    const actualContent = await readFile(actualPath, "utf-8");
    assert(
      contentHash(actualContent) === contentHash(expectedContent),
      `${file} bytes match an independent rendering of templates/target-${file} + fixture A (CRLF-normalised)`,
    );
  }

  // Step 5: idempotence — re-run with the same fixture, no edits expected.
  console.log("");
  console.log("# Step 5: idempotence");
  const beforeReHashes = await Promise.all(
    expectedTemplateFiles.map(async (file) => contentHash(await readFile(join(tempRoot, file), "utf-8"))),
  );
  const secondRun = runInstall(tempRoot, fixtureA);
  assert(secondRun.status === 0, `second install-into-project exited 0 (got ${secondRun.status})`);
  const afterReHashes = await Promise.all(
    expectedTemplateFiles.map(async (file) => contentHash(await readFile(join(tempRoot, file), "utf-8"))),
  );
  for (let i = 0; i < expectedTemplateFiles.length; i++) {
    assert(beforeReHashes[i] === afterReHashes[i], `${expectedTemplateFiles[i]} unchanged on second install with the same fixture`);
  }

  // Step 6: a different birds-eye MUST change the output. This catches a
  // script that ignores the --birds-eye-file argument and reads a default
  // template silently (would have failed the byte-equality check above
  // but for the wrong reason: "fixture file was never used").
  console.log("");
  console.log("# Step 6: different fixture produces different output");
  const beforeDifferentHash = contentHash(await readFile(join(tempRoot, "CLAUDE.md"), "utf-8"));
  const thirdRun = runInstall(tempRoot, fixtureB);
  assert(thirdRun.status === 0, `install with fixture B exited 0 (got ${thirdRun.status})`);
  const afterDifferentHash = contentHash(await readFile(join(tempRoot, "CLAUDE.md"), "utf-8"));
  assert(
    afterDifferentHash !== beforeDifferentHash,
    "CLAUDE.md changes when the birds-eye fixture changes (script is not silently ignoring --birds-eye-file)",
  );

  // Step 7: dry-run promise.
  console.log("");
  console.log("# Step 7: --dry-run does not write");
  const snapshot = await Promise.all(
    expectedTemplateFiles.map(async (file) => ({
      file,
      hash: contentHash(await readFile(join(tempRoot, file), "utf-8")),
      mtime: (await stat(join(tempRoot, file))).mtimeMs,
    })),
  );
  const dryRun = runInstall(tempRoot, fixtureA, ["--dry-run"]);
  assert(dryRun.status === 0, `--dry-run exit 0 (got ${dryRun.status})`);
  for (const entry of snapshot) {
    const after = await stat(join(tempRoot, entry.file));
    const afterHash = contentHash(await readFile(join(tempRoot, entry.file), "utf-8"));
    assert(
      afterHash === entry.hash && after.mtimeMs === entry.mtime,
      `--dry-run did not touch ${entry.file} (bytes + mtime unchanged)`,
    );
  }
} finally {
  await safeRemoveTemp(tempRootRaw, tempRoot);
  await safeRemoveTemp(fixtureDir, await realpath(fixtureDir));
}

console.log("");
if (fail === 0) {
  console.log("install-roundtrip smoke test passed.");
} else {
  console.log(`install-roundtrip smoke test FAILED (${fail} issue(s)).`);
  process.exit(1);
}