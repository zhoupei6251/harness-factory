#!/usr/bin/env node
/**
 * structure-audit.ts — make the prose in STRUCTURE.md / ARCHITECTURE.md /
 * README.md a machine-checked invariant instead of a hand-typed claim.
 *
 * What it asserts (each line is the inverse of a doc sentence that has already
 * drifted at least once; the claim and the evidence are right next to each
 * other so the next person who edits one knows to update the other):
 *
 *   1. core/ contains exactly the 8 governance docs listed by core/ENTRY.md
 *      (intent-routing / karpathy-guidelines / NEVER / principles / routing /
 *      runbooks / tags-index + ENTRY.md itself, which the index table leaves
 *      implicit).
 *   2. platforms/ has exactly 5 adapters, each with platforms/<p>/rules/ENTRY.md.
 *   3. routes/ has exactly 3 routes, each with routes/<r>/MEMORY.md.
 *   4. capabilities/rules/ has the 3 verticals java / typescript / common,
 *      each with hooks.md / patterns.md / security.md / testing.md.
 *   5. templates/ carries the 4 files install-into-project.ts + bootstrap.ts
 *      require: target-CLAUDE.md / target-AGENTS.md / target-GEMINI.md /
 *      harness.template.md. project-birds-eye.template.md and templates/README
 *      are reported but not asserted.
 *   6. skills/INDEX.md "Total:" line must equal the on-disk counts.
 *   7. Every active skill has SKILL.md + _meta.json (skills-audit.ts already
 *      reports this; we re-assert it here so the structure gate cannot be
 *      "green" while bit-rot quietly accumulates).
 *   8. Skillset frontmatter (`skills:` in a SKILL.md) names only active skills.
 *      An archived/removed skill left in a workflow's list is a route to a
 *      dead end — the workflow looks complete while the step cannot load.
 *   9. Forbidden homes per STRUCTURE.md §"Forbidden homes":
 *        - scripts/<name>.md     (scripts are .ts)
 *        - tests/<name>.md or tests/<name-without-.test>.ts
 *        - bootstrap-owned paths tracked under a runtime dir (already
 *          covered by validate-schemas.ts; we re-check it so structure-audit
 *          catches it when run before validate).
 *  10. Dependency direction at the skills/routes boundary: the render engine
 *      (skills/douyin-pro/scripts) must not import product code
 *      (routes/news/scripts). Product scripts may import the engine — that is
 *      the supported direction. path_b_selftest.py is exempt: it is the shared
 *      test harness and loads both sides on purpose.
 *
 * Exit 0 = clean. Exit 1 = at least one assertion failed. The script does not
 * repair anything — it reports, the human (or another script) decides.
 *
 * Re-run: `npm run structure:audit`. Wired into `npm test` after typecheck.
 */
import { readdir, readFile, stat } from "node:fs/promises";
import type { Dirent } from "node:fs";
import { existsSync } from "node:fs";
import { resolve, dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");

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

async function listDirs(rel: string): Promise<string[]> {
  try {
    const entries = await readdir(resolve(ROOT, rel), { withFileTypes: true });
    return entries.filter((e) => e.isDirectory()).map((e) => e.name).sort();
  } catch {
    return [];
  }
}

async function listFiles(rel: string, suffix?: string): Promise<string[]> {
  try {
    const entries = await readdir(resolve(ROOT, rel), { withFileTypes: true });
    const names = entries.filter((e) => e.isFile() && (!suffix || e.name.endsWith(suffix))).map((e) => e.name);
    return names.sort();
  } catch {
    return [];
  }
}

// ---------- 1. core/ governance docs ----------
{
  const expected = [
    "ENTRY.md", // the index file itself — the table in it is self-referential and leaves this row implicit, but the file must exist
    "intent-routing.md",
    "karpathy-guidelines.md",
    "NEVER.md",
    "principles.md",
    "routing.md",
    "runbooks.md",
    "tags-index.md",
  ];
  const actual = new Set(await listFiles("core", ".md"));
  const missing = expected.filter((f) => !actual.has(f));
  const extra = [...actual].filter((f) => !expected.includes(f));
  if (missing.length === 0 && extra.length === 0) {
    ok(`core/ has exactly the 8 governance docs`);
  } else {
    if (missing.length) bad(`core/ missing governance doc(s): ${missing.join(", ")}`);
    if (extra.length) bad(`core/ has extra .md file(s) not in core/ENTRY.md index: ${extra.join(", ")}`);
  }
}

// ---------- 2. platforms/ adapters ----------
{
  const expectedPlatforms = ["claude", "codex", "qoder", "trae", "workbuddy"];
  const actual = await listDirs("platforms");
  const missing = expectedPlatforms.filter((p) => !actual.includes(p));
  const extra = actual.filter((p) => !expectedPlatforms.includes(p));
  if (missing.length === 0 && extra.length === 0) {
    let allHaveEntry = true;
    for (const p of expectedPlatforms) {
      if (!(await exists(resolve(ROOT, "platforms", p, "rules", "ENTRY.md")))) {
        bad(`platforms/${p}/rules/ENTRY.md missing`);
        allHaveEntry = false;
      }
    }
    if (allHaveEntry) ok(`platforms/ has exactly 5 adapters, each with rules/ENTRY.md`);
  } else {
    if (missing.length) bad(`platforms/ missing adapter(s): ${missing.join(", ")}`);
    if (extra.length) bad(`platforms/ has extra adapter dir(s): ${extra.join(", ")}`);
  }
}

// ---------- 3. routes/ ----------
{
  const expectedRoutes = ["code", "news", "novel"];
  const actual = await listDirs("routes");
  const missing = expectedRoutes.filter((r) => !actual.includes(r));
  const extra = actual.filter((r) => !expectedRoutes.includes(r));
  if (missing.length === 0 && extra.length === 0) {
    let allHaveMemory = true;
    for (const r of expectedRoutes) {
      if (!(await exists(resolve(ROOT, "routes", r, "MEMORY.md")))) {
        bad(`routes/${r}/MEMORY.md missing`);
        allHaveMemory = false;
      }
    }
    if (allHaveMemory) ok(`routes/ has exactly 3 routes, each with MEMORY.md`);
  } else {
    if (missing.length) bad(`routes/ missing route(s): ${missing.join(", ")}`);
    if (extra.length) bad(`routes/ has extra route dir(s): ${extra.join(", ")}`);
  }
}

// ---------- 4. capabilities/rules verticals ----------
{
  const expectedVerticals = ["java", "typescript", "common"];
  const expectedFiles = ["hooks.md", "patterns.md", "security.md", "testing.md"];
  const actual = await listDirs("capabilities/rules");
  const missing = expectedVerticals.filter((v) => !actual.includes(v));
  const extra = actual.filter((v) => !expectedVerticals.includes(v));
  if (missing.length === 0 && extra.length === 0) {
    let allHaveFiles = true;
    for (const v of expectedVerticals) {
      const have = await listFiles(`capabilities/rules/${v}`, ".md");
      const miss = expectedFiles.filter((f) => !have.includes(f));
      if (miss.length) {
        bad(`capabilities/rules/${v}/ missing file(s): ${miss.join(", ")}`);
        allHaveFiles = false;
      }
    }
    if (allHaveFiles) ok(`capabilities/rules/ has the 3 verticals, each with 4 rule files`);
  } else {
    if (missing.length) bad(`capabilities/rules/ missing vertical(s): ${missing.join(", ")}`);
    if (extra.length) bad(`capabilities/rules/ has extra vertical(s): ${extra.join(", ")}`);
  }
}

// ---------- 5. templates/ required files ----------
{
  const required = ["target-CLAUDE.md", "target-AGENTS.md", "target-GEMINI.md", "harness.template.md"];
  const actual = new Set(await listFiles("templates", ".md"));
  const missing = required.filter((f) => !actual.has(f));
  if (missing.length === 0) {
    ok(`templates/ carries the 4 files bootstrap + install-into-project require`);
  } else {
    bad(`templates/ missing required file(s): ${missing.join(", ")}`);
  }
}

// ---------- 6. skills/INDEX.md counts vs filesystem ----------
{
  const indexPath = resolve(ROOT, "skills/INDEX.md");
  if (!(await exists(indexPath))) {
    bad(`skills/INDEX.md missing — run \`npm run index\``);
  } else {
    const indexBody = await readFile(indexPath, "utf-8");
    // "Total: 49 active + 51 archived = 100 skills" — match the numbers, not the prose around them.
    const totalMatch = /Total:\s+(\d+)\s+active\s+\+\s+(\d+)\s+archived\s+=\s+(\d+)\s+skills/.exec(indexBody);
    if (!totalMatch) {
      bad(`skills/INDEX.md "Total:" line not recognised — please update the regex here to match the new format`);
    } else {
      const claimedActive = Number(totalMatch[1]);
      const claimedArchive = Number(totalMatch[2]);
      const claimedTotal = Number(totalMatch[3]);
      const activeCount = (await listDirs("skills")).filter((n) => n !== "archive").length;
      const archiveCount = (await listDirs("skills/archive")).length;
      const totalCount = activeCount + archiveCount;
      const problems: string[] = [];
      if (claimedActive !== activeCount) problems.push(`active claimed=${claimedActive} on disk=${activeCount}`);
      if (claimedArchive !== archiveCount) problems.push(`archive claimed=${claimedArchive} on disk=${archiveCount}`);
      if (claimedTotal !== totalCount) problems.push(`total claimed=${claimedTotal} on disk=${totalCount}`);
      if (problems.length === 0) {
        ok(`skills/INDEX.md counts match fs (${activeCount} active + ${archiveCount} archived = ${totalCount})`);
      } else {
        for (const p of problems) bad(`skills/INDEX.md drift: ${p}`);
      }
    }
  }
}

// ---------- 7. every active skill has SKILL.md + _meta.json ----------
{
  const active = await listDirs("skills");
  let badCount = 0;
  for (const name of active) {
    if (name === "archive") continue;
    const full = resolve(ROOT, "skills", name);
    const s = await stat(full).catch(() => null);
    if (!s || !s.isDirectory()) continue;
    const hasSkill = existsSync(join(full, "SKILL.md"));
    const hasMeta = existsSync(join(full, "_meta.json"));
    if (!hasSkill || !hasMeta) {
      bad(`skills/${name} missing ${!hasSkill ? "SKILL.md" : ""}${!hasSkill && !hasMeta ? " + " : ""}${!hasMeta ? "_meta.json" : ""}`);
      badCount++;
    }
  }
  if (badCount === 0) ok(`every active skill has SKILL.md + _meta.json`);
}

// ---------- 8. skillset frontmatter points at active skills only ----------
{
  const active = new Set((await listDirs("skills")).filter((n) => n !== "archive"));
  const offenders: string[] = [];
  let entries = 0;
  for (const name of active) {
    const text = await readFile(resolve(ROOT, "skills", name, "SKILL.md"), "utf-8");
    const fm = /^---\r?\n([\s\S]*?)\r?\n---/.exec(text);
    if (!fm) continue;
    const lines = fm[1].split(/\r?\n/);
    const start = lines.findIndex((l) => /^skills:\s*$/.test(l));
    if (start < 0) continue;
    for (let i = start + 1; i < lines.length; i++) {
      const m = /^\s*-\s*["']?([^"'\s]+)["']?\s*$/.exec(lines[i]);
      if (!m) break;
      entries++;
      if (!active.has(m[1])) offenders.push(`skills/${name}/SKILL.md → ${m[1]}`);
    }
  }
  if (offenders.length === 0) {
    ok(`skillset frontmatter references only active skills (${entries} entries)`);
  } else {
    for (const o of offenders) bad(`${o} — skillset entry must name an active skill; archived/removed skills cannot be routed to`);
  }
}

// ---------- 9. forbidden homes ----------
{
  // scripts/<name>.md (scripts are .ts runnable)
  const scriptsEntries = await readdir(resolve(ROOT, "scripts"), { withFileTypes: true });
  const mdScripts = scriptsEntries.filter((e) => e.isFile() && e.name.endsWith(".md")).map((e) => e.name);
  if (mdScripts.length === 0) {
    ok(`scripts/ has no .md files (forbidden home)`);
  } else {
    for (const f of mdScripts) bad(`scripts/${f} — scripts are .ts runnable, not .md docs`);
  }

  // tests/<name>.md
  const testsRoot = resolve(ROOT, "tests");
  const topTests = await readdir(testsRoot, { withFileTypes: true });
  const mdTestsTop = topTests.filter((e) => e.isFile() && e.name.endsWith(".md")).map((e) => e.name);
  if (mdTestsTop.length === 0) {
    ok(`tests/ has no .md files at top level (forbidden home)`);
  } else {
    for (const f of mdTestsTop) bad(`tests/${f} — tests/ is for assertion-bearing test files only`);
  }
  // tests/<name>.ts that isn't a test file (must end with .test.ts by convention).
  const tsTestsTop = topTests.filter((e) => e.isFile() && e.name.endsWith(".ts")).map((e) => e.name);
  const nonTestTs = tsTestsTop.filter((n) => !n.endsWith(".test.ts"));
  if (nonTestTs.length === 0) {
    ok(`tests/ top-level .ts files all follow *.test.ts convention`);
  } else {
    for (const f of nonTestTs) bad(`tests/${f} — top-level test files must end with .test.ts; non-tests belong in scripts/`);
  }

  // skills/<name>/ without SKILL.md + _meta.json (the broken-pair case is its own
  // failure mode beyond §7, but only when the directory name doesn't even appear
  // in INDEX.md — i.e., bit-rot has drifted further).
  const indexBody = await exists(resolve(ROOT, "skills/INDEX.md")) ? await readFile(resolve(ROOT, "skills/INDEX.md"), "utf-8") : "";
  const active = await listDirs("skills");
  let ghostCount = 0;
  for (const name of active) {
    if (name === "archive") continue;
    const hasSkill = existsSync(resolve(ROOT, "skills", name, "SKILL.md"));
    if (!hasSkill && !indexBody.includes(`| ${name} |`)) {
      bad(`skills/${name} is a directory without SKILL.md and not listed in INDEX.md — likely an abandoned stub`);
      ghostCount++;
    }
  }
  if (ghostCount === 0) ok(`no abandoned skill stubs in skills/`);

  // runtime dir entries tracked (covered by validate-schemas.ts, but we re-check so
  // structure-audit is independent of validate's run order).
  const RUNTIME_DIRS = [".harness-news-runtime", ".harness-novel-runtime", ".ai-runtime-artifacts"];
  let tracked: string[] = [];
  try {
    tracked = execFileSync("git", ["ls-files"], { cwd: ROOT, encoding: "utf-8" })
      .split(/\r?\n/)
      .filter(Boolean);
  } catch {
    // not a git checkout; skip rather than fail
  }
  const runtimeOffenders = tracked.filter((p) => RUNTIME_DIRS.some((d) => p === d || p.startsWith(`${d}/`)));
  if (runtimeOffenders.length === 0) {
    ok(`no tracked files under runtime dirs (${RUNTIME_DIRS.join(", ")})`);
  } else {
    for (const p of runtimeOffenders) bad(`runtime content must not be tracked: ${p}`);
  }
}

// ---------- 10. skills/routes dependency direction ----------
{
  const engineFiles = await listFiles("skills/douyin-pro/scripts", ".py");
  const offenders: string[] = [];
  for (const name of engineFiles) {
    if (name === "path_b_selftest.py") continue;
    const text = await readFile(resolve(ROOT, "skills/douyin-pro/scripts", name), "utf-8");
    // Import plumbing only. Prose/error messages may legitimately name product files.
    const importsProduct = /(?:from|import)\s+[^\n]*routes[\\/]news[\\/]scripts/.test(text)
      || text.split(/\r?\n/).some((line) => /sys\.path/.test(line) && /routes[\\/]news[\\/]scripts/.test(line));
    if (importsProduct) offenders.push(name);
  }
  if (offenders.length === 0) {
    ok(`douyin-pro engine (${engineFiles.length - 1} non-selftest scripts) does not import routes/news code`);
  } else {
    for (const f of offenders) {
      bad(`skills/douyin-pro/scripts/${f} imports routes/news/scripts — dependency must point product → engine`);
    }
  }
}

console.log("");
if (fail === 0) {
  console.log("Structure audit passed.");
} else {
  console.log(`Structure audit FAILED (${fail} issue(s)). Fix the doc claim and/or the filesystem in lockstep.`);
  process.exit(1);
}