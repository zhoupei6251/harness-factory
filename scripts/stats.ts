#!/usr/bin/env node
/**
 * Print live counts + health for the ARCHITECTURE.md table and CI gates.
 * Re-run via `npm run stats`.
 *
 * Why: README/ARCHITECTURE used to hardcode "270" / "441" — both stale.
 *      This script makes the table reproducible and adds repo health signals
 *      (git cleanliness, runtime dir size, archive bit-rot risk) that were
 *      previously invisible.
 */
import { readdir, readFile, stat } from "node:fs/promises";
import { resolve, dirname, extname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");

const SKIP_DIRS = new Set([
  ".git",
  "node_modules",
  ".harness-news-runtime",
  ".harness-novel-runtime",
  ".ai-runtime-artifacts",
  ".workbuddy",
]);

const RUNTIME_DIRS = [
  ".harness-news-runtime",
  ".harness-novel-runtime",
  ".ai-runtime-artifacts",
  ".workbuddy",
];

const RUNTIME_SIZE_WARN_MB = 1024; // 1 GiB

async function* walk(dir: string): AsyncGenerator<string> {
  const entries = await readdir(dir, { withFileTypes: true });
  for (const e of entries) {
    if (SKIP_DIRS.has(e.name)) continue;
    const p = join(dir, e.name);
    if (e.isDirectory()) {
      yield* walk(p);
    } else {
      yield p;
    }
  }
}

async function listDirs(rel: string): Promise<string[]> {
  try {
    const entries = await readdir(resolve(ROOT, rel), { withFileTypes: true });
    return entries.filter((e) => e.isDirectory()).map((e) => e.name);
  } catch {
    return [];
  }
}

async function listMdFiles(rel: string): Promise<string[]> {
  try {
    const entries = await readdir(resolve(ROOT, rel), { withFileTypes: true });
    return entries.filter((e) => e.isFile() && e.name.endsWith(".md")).map((e) => e.name);
  } catch {
    return [];
  }
}

async function dirSizeMiB(rel: string): Promise<number> {
  try {
    const out = execFileSync("du", ["-sm", rel], { cwd: ROOT, encoding: "utf-8" });
    return Number(out.split(/\s+/)[0] ?? 0);
  } catch {
    return 0;
  }
}

function gitLines(args: string[]): string {
  return execFileSync("git", args, { cwd: ROOT, encoding: "utf-8" }).trim();
}

let totalSource = 0;
let ts = 0,
  md = 0,
  json = 0,
  py = 0,
  html = 0,
  other = 0;

for await (const p of walk(ROOT)) {
  totalSource++;
  switch (extname(p)) {
    case ".ts":
      ts++;
      break;
    case ".md":
      md++;
      break;
    case ".json":
      json++;
      break;
    case ".py":
      py++;
      break;
    case ".html":
      html++;
      break;
    default:
      other++;
      break;
  }
}

const governance = (await listMdFiles("core")).length;
const platforms = (await listDirs("platforms")).length;
const routes = (await listDirs("routes")).length;

const skillsAll = await listDirs("skills");
const skillsActive = skillsAll.filter((n) => n !== "archive").length;
const skillsArchive = (await listDirs("skills/archive")).length;
const skillsAllEntries = (await readdir(resolve(ROOT, "skills"), { withFileTypes: true })).length;

const capabilityVerticals = (await listDirs("capabilities/rules")).length;
const schemaFiles = (await readdir(resolve(ROOT, "schemas"), { withFileTypes: true })
  .catch(() => [])
  .then((es) => es.filter((e) => e.isFile() && e.name.endsWith(".json")).length));

const pkg = JSON.parse(await readFile(resolve(ROOT, "package.json"), "utf-8"));
const npmScripts = Object.keys(pkg.scripts ?? {}).length;

const trackedCount = Number(gitLines(["ls-files"]).split("\n").filter(Boolean).length);

let gitClean = "n/a";
let ahead = 0;
let behind = 0;
try {
  const status = gitLines(["status", "--porcelain"]);
  gitClean = status === "" ? "clean" : `${status.split("\n").length} modified`;
  const ab = gitLines(["rev-list", "--left-right", "--count", "HEAD...@{u}"]).split(/\s+/);
  ahead = Number(ab[0] ?? 0);
  behind = Number(ab[1] ?? 0);
} catch {
  // No upstream configured; leave as n/a
}

const runtimeRows: Array<[string, string]> = [];
for (const d of RUNTIME_DIRS) {
  const mib = await dirSizeMiB(d);
  const flag = mib > RUNTIME_SIZE_WARN_MB ? " ⚠" : "";
  runtimeRows.push([d, `${mib} MiB${flag}`]);
}

console.log("# harness-factory stats (live — re-run `npm run stats`)");
console.log("");
console.log("| Metric | Count |");
console.log("|---|---|");
console.log(`| Source files (excl .git + node_modules + runtime dirs) | ${totalSource} |`);
console.log(`|  · .ts | ${ts} |`);
console.log(`|  · .md | ${md} |`);
console.log(`|  · .json | ${json} |`);
console.log(`|  · .py | ${py} |`);
console.log(`|  · .html | ${html} |`);
console.log(`|  · other | ${other} |`);
console.log(`| Tracked files (git ls-files) | ${trackedCount} |`);
console.log(`| Core governance docs | ${governance} |`);
console.log(`| Platform adapters | ${platforms} |`);
console.log(`| Routes | ${routes} |`);
console.log(`| Skills (active / archive) | ${skillsActive} / ${skillsArchive} |`);
console.log(`| Skills/ total entries (incl. INDEX.md + archive/) | ${skillsAllEntries} |`);
console.log(`| Capability verticals | ${capabilityVerticals} |`);
console.log(`| Schemas | ${schemaFiles} |`);
console.log(`| npm scripts | ${npmScripts} |`);
console.log(`| Git working tree | ${gitClean} |`);
console.log(`| Git ahead/behind upstream | ${ahead} / ${behind} |`);
console.log("");
console.log("## Runtime dir sizes (gitignored; >1 GiB flagged)");
console.log("");
for (const [d, s] of runtimeRows) console.log(`- \`${d}\`: ${s}`);
