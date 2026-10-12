#!/usr/bin/env node
/**
 * Downstream integration test: install harness into a downstream project,
 * run `npm run bootstrap` in the installed copy, and assert the platform
 * artifacts match the canonical sources.
 *
 * Why this test exists:
 * - Pure meta tests (scripts/validate-schemas.ts, tests/bootstrap.test.ts)
 *   only verify harness-factory's own scripts work.
 * - They miss the case where a template regression (e.g., wrong @import path
 *   in templates/project-birds-eye.template.md) breaks every downstream user
 *   silently. install-template.test.ts catches the install side; this test
 *   adds the bootstrap side and ties them together against a real downstream.
 *
 * Strategy:
 * - If ../aigc_platfrom_back exists, copy it to a temp dir and use that
 *   (preferred: tests the real downstream contract).
 * - Otherwise build a minimal mock downstream in temp (still exercises the
 *   install + bootstrap + assertion flow).
 * - Always run install --force, then bootstrap, then assert the 5 platform
 *   dirs and 3 root wrappers. Cleanup the temp dir at the end.
 *
 * Exits 0 on full pass, 1 on any assertion failure.
 */
import { existsSync } from "node:fs";
import { cp, mkdtemp, readFile, rm, stat, writeFile, mkdir } from "node:fs/promises";
import { join, resolve, dirname } from "node:path";
import { tmpdir } from "node:os";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..");
const NODE = process.execPath;
const TSX = resolve(ROOT, "node_modules", "tsx", "dist", "cli.mjs");
const SIBLING = resolve(ROOT, "..", "aigc_platfrom_back");
const INSTALL = resolve(ROOT, "scripts", "install-into-project.ts");
const BOOTSTRAP = resolve(ROOT, "scripts", "bootstrap.ts");

let fail = 0;
const ok = (m: string): void => console.log(`[ok]   ${m}`);
const bad = (m: string): void => { console.log(`[FAIL] ${m}`); fail++; };
const info = (m: string): void => console.log(`[info] ${m}`);

async function isFile(p: string): Promise<boolean> {
  try { return (await stat(p)).isFile(); } catch { return false; }
}

async function setupMock(): Promise<string> {
  const work = await mkdtemp(join(tmpdir(), "hf-downstream-mock-"));
  await mkdir(join(work, ".git/info"), { recursive: true });
  // Realistic touches that exercise the install-into-project branches:
  // - .git/info/ present so appendExclude can write to .git/info/exclude
  // - existing CLAUDE.md so --force exercises the .bak-*.md backup branch
  // - .gitignore present so the script can append to it
  await writeFile(join(work, ".gitignore"), "# pre-existing downstream .gitignore\n");
  await writeFile(join(work, "CLAUDE.md"), "# pre-existing downstream CLAUDE.md (will be backed up)\n");
  return work;
}

async function main(): Promise<void> {
  const usedSibling = existsSync(SIBLING);
  const target = usedSibling
    ? await (async () => {
        info(`sibling aigc_platfrom_back found at ${SIBLING}; copying to temp`);
        const t = await mkdtemp(join(tmpdir(), "hf-downstream-sib-"));
        await cp(SIBLING, t, { recursive: true });
        return t;
      })()
    : await setupMock();
  info(usedSibling ? "using sibling copy" : "using minimal mock downstream");

  try {
    // 1. Install harness into the target
    const installResult = spawnSync(NODE, [TSX, INSTALL, "--target", target, "--force"], { encoding: "utf-8" });
    if (installResult.status !== 0) {
      bad(`install-into-project exited ${installResult.status}: ${(installResult.stderr || installResult.stdout).slice(0, 500)}`);
      return;
    }
    ok("install-into-project --force succeeded");

    // 2. Verify the 3 thin wrappers (other-mode). Import patterns differ:
    //    CLAUDE.md uses @harness-factory/CLAUDE.harness.md (@-syntax for Claude);
    //    AGENTS.md and GEMINI.md use the relative harness-factory/... path because
    //    Codex/Qoder don't honor the @-import form.
    const wrappers: Array<[string, RegExp]> = [
      ["CLAUDE.md", /@harness-factory\/CLAUDE\.harness\.md/],
      ["AGENTS.md", /harness-factory\/AGENTS\.harness\.md/],
      ["GEMINI.md", /harness-factory\/GEMINI\.harness\.md/],
    ];
    for (const [name, pattern] of wrappers) {
      const text = await readFile(join(target, name), "utf-8").catch(() => "");
      if (pattern.test(text)) {
        ok(`target ${name} has correct harness-factory import`);
      } else {
        bad(`target ${name} missing or wrong import (expected ${pattern}, got first 200 chars: ${text.slice(0, 200)})`);
      }
    }

    // 3. install-into-project does NOT create the harness-factory/ subdir — the
    //    user is expected to clone it alongside. Mimic that by copying our own
    //    root into target/harness-factory/ so bootstrap has sources to project.
    const installedHarness = join(target, "harness-factory");
    await cp(ROOT, installedHarness, {
      recursive: true,
      // Skip the .git dir of the harness itself (the target already has its own
      // .git; nesting .git dirs confuses git).
      filter: (src) => !src.includes(`${ROOT.replaceAll("\\", "/")}/.git`),
    });
    ok(`copied harness-factory source into ${installedHarness}`);

    // 4. Run bootstrap from the installed copy
    const bootResult = spawnSync(NODE, [TSX, BOOTSTRAP, "--platform", "all", "--route", "code"], {
      encoding: "utf-8",
      cwd: installedHarness,
    });
    if (bootResult.status !== 0) {
      bad(`bootstrap exited ${bootResult.status}: ${(bootResult.stderr || bootResult.stdout).slice(0, 500)}`);
      return;
    }
    ok("bootstrap --platform all --route code succeeded in installed copy");

    // 5. Assert the bootstrap output. Two distinct output classes:
    //    (a) platform projection under PLATFORM_DIR[plat]/rules/ → ENTRY.md + ROOT.md
    //    (b) native entry written to the path in PLATFORM_NATIVE_ENTRY[plat]
    //        (top-level CLAUDE.md/AGENTS.md for claude/codex+qoder; nested
    //        .trae/rules/project_rules.md and .codebuddy/rules/project_rules.md
    //        for trae/workbuddy, which don't have a top-level native entry file)
    const platformProjection: Array<[string, string]> = [
      [".claude", "rules/ENTRY.md"],
      [".codex", "rules/ENTRY.md"],
      [".qoder", "rules/ENTRY.md"],
      [".trae", "rules/ENTRY.md"],
      [".codebuddy", "rules/ENTRY.md"],
    ];
    for (const [dir, file] of platformProjection) {
      const p = join(installedHarness, dir, file);
      if (await isFile(p)) {
        ok(`bootstrap produced ${dir}/${file}`);
      } else {
        bad(`bootstrap missing ${dir}/${file}`);
      }
    }
    const nativeEntries: Array<[string, string]> = [
      ["CLAUDE.md", "claude native entry (top-level)"],
      ["AGENTS.md", "codex + qoder merged native entry (top-level)"],
      [".trae/rules/project_rules.md", "trae native entry (nested)"],
      [".codebuddy/rules/project_rules.md", "workbuddy native entry (nested)"],
    ];
    for (const [rel, label] of nativeEntries) {
      const p = join(installedHarness, rel);
      if (await isFile(p)) {
        ok(`bootstrap produced ${rel} (${label})`);
      } else {
        bad(`bootstrap missing ${rel} (${label})`);
      }
    }

    // 6. The bootstrap-generated CLAUDE.md must include the canonical harness
    //    entry content (not just be a placeholder). We don't byte-compare — the
    //    generator prepends a "Generated by `npm run bootstrap`" notice + merges
    //    multiple sources — but we assert the canonical ENTRY.md content shows
    //    up verbatim in the merged file.
    const generatedClaude = await readFile(join(installedHarness, "CLAUDE.md"), "utf-8").catch(() => "");
    const canonicalEntry = await readFile(resolve(ROOT, "ENTRY.md"), "utf-8");
    const strippedEntry = canonicalEntry.replace(/^---[\s\S]*?---\r?\n/, "");
    if (generatedClaude.length > 0 && generatedClaude.includes(strippedEntry.trim().slice(0, 200))) {
      ok("generated CLAUDE.md includes canonical ENTRY.md content");
    } else {
      bad(`generated CLAUDE.md missing canonical ENTRY content (gen ${generatedClaude.length}B, expected snippet not found)`);
    }
  } finally {
    await rm(target, { recursive: true, force: true });
    info(`removed temp target`);
  }
}

await main();

console.log("");
if (fail === 0) {
  console.log("All downstream tests passed.");
} else {
  console.log(`Downstream test FAILED (${fail} assertion(s)).`);
  process.exit(1);
}
