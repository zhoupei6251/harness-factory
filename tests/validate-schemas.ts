#!/usr/bin/env node
import { readFile, readdir, stat } from "node:fs/promises";
import { resolve, dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..");
const SCHEMAS_DIR = resolve(ROOT, "schemas");
const SKILLS_DIR = resolve(ROOT, "skills");

// Runtime dirs are ignorable by contract (see core/routing.md). Anything tracked
// under one is an ad-hoc `git add -f` rescue that the next clone will lose.
const RUNTIME_DIRS = [".harness-news-runtime", ".harness-novel-runtime", ".ai-runtime-artifacts"];

function trackedFiles(): string[] {
  return execFileSync("git", ["ls-files"], { cwd: ROOT, encoding: "utf-8" })
    .split(/\r?\n/)
    .filter(Boolean);
}

async function validateRuntimeDirs(): Promise<void> {
  const offenders = trackedFiles().filter((p) => RUNTIME_DIRS.some((d) => p.startsWith(`${d}/`)));
  if (offenders.length === 0) {
    console.log(`[ok]   no tracked file under a runtime dir (${RUNTIME_DIRS.join(", ")})`);
  } else {
    for (const p of offenders) console.log(`[FAIL] runtime content must not be tracked: ${p}`);
    fail = 1;
  }
}

// Evidence pointers are live: a tracked doc naming an evidence file is a promise
// that file ships with the repo. Template paths (`<date>-…`) can't match this
// pattern at all, because `<` is outside the allowed charset — no special case.
const EVIDENCE_PTR = /routes\/[a-z0-9-]+\/evidence\/[A-Za-z0-9._\-/]+/g;
const OLD_EVIDENCE_HOME = ".harness-news-runtime/verifications/";

async function validateEvidence(): Promise<void> {
  const tracked = new Set(trackedFiles());
  // docs/superpowers/** is the historical record; its prose may name retired paths.
  const docs = [...tracked].filter((p) => /\.(md|jsonl)$/.test(p) && !p.startsWith("docs/superpowers/"));
  let bad = 0;
  for (const p of docs) {
    const text = await readFile(join(ROOT, p), "utf-8");
    for (const m of text.match(EVIDENCE_PTR) ?? []) {
      if (!tracked.has(m)) {
        console.log(`[FAIL] ${p}: evidence pointer is not tracked -> ${m}`);
        bad++;
      }
    }
    if (text.includes(OLD_EVIDENCE_HOME)) {
      console.log(`[FAIL] ${p}: evidence still referenced inside an ignorable runtime dir`);
      bad++;
    }
  }
  if (bad === 0) {
    console.log(`[ok]   evidence pointers resolve; no live pointer in a runtime dir (${docs.length} tracked docs scanned)`);
  } else {
    fail = 1;
  }
}

let fail = 0;

async function isDir(path: string): Promise<boolean> {
  try {
    const s = await stat(path);
    return s.isDirectory();
  } catch {
    return false;
  }
}

async function validateSchemas(): Promise<void> {
  let entries: string[] = [];
  try {
    entries = await readdir(SCHEMAS_DIR);
  } catch {
    return;
  }
  for (const entry of entries) {
    if (!entry.endsWith(".json")) continue;
    const path = join(SCHEMAS_DIR, entry);
    try {
      JSON.parse(await readFile(path, "utf-8"));
      console.log(`[ok]   ${relative(ROOT, path).replace(/\\/g, "/")}`);
    } catch {
      console.log(`[FAIL] ${entry}: not valid JSON`);
      fail = 1;
    }
  }
}

const ARCHIVE_DIR = join(SKILLS_DIR, "archive");

async function validateSkills(): Promise<void> {
  let entries: string[] = [];
  try {
    entries = await readdir(SKILLS_DIR);
  } catch {
    return;
  }
  for (const name of entries) {
    const fullPath = join(SKILLS_DIR, name);
    // Skip non-directory entries (e.g., README.md, _layer.yaml, categories.yaml)
    if (!(await isDir(fullPath))) continue;
    // skills/archive/ is validated separately below
    if (fullPath === ARCHIVE_DIR) continue;
    const skillMd = join(fullPath, "SKILL.md");
    try {
      await readFile(skillMd);
      console.log(`[ok]   skills/${name}/SKILL.md`);
    } catch {
      console.log(`[FAIL] skills/${name}/: missing SKILL.md`);
      fail = 1;
    }
  }
}

// Archived skills must stay valid too (restorable via: mv skills/archive/<name> skills/<name>)
async function validateArchiveSkills(): Promise<void> {
  let entries: string[] = [];
  try {
    entries = await readdir(ARCHIVE_DIR);
  } catch {
    return; // no archive dir yet
  }
  for (const name of entries) {
    const fullPath = join(ARCHIVE_DIR, name);
    if (!(await isDir(fullPath))) continue;
    const skillMd = join(fullPath, "SKILL.md");
    try {
      await readFile(skillMd);
      console.log(`[ok]   skills/archive/${name}/SKILL.md`);
    } catch {
      console.log(`[FAIL] skills/archive/${name}/: missing SKILL.md`);
      fail = 1;
    }
  }
}

await validateSchemas();
await validateSkills();
await validateArchiveSkills();
await validateRuntimeDirs();
await validateEvidence();

if (fail === 0) {
  console.log("");
  console.log("All validations passed.");
} else {
  console.log("");
  console.log("Validation FAILED.");
  process.exit(1);
}
