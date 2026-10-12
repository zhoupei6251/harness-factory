#!/usr/bin/env node
/**
 * Print live counts for the ARCHITECTURE.md / README.md "Current state" tables.
 * Run via `npm run stats` or `tsx scripts/stats.ts`.
 *
 * Why: README/ARCHITECTURE used to hardcode "270" / "441" — both stale.
 * The script makes the table reproducible: if the count drifts, the table drifts too.
 */
import { readdir, readFile } from "node:fs/promises";
import { resolve, dirname, extname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");

const SKIP_DIRS = new Set([
  ".git",
  "node_modules",
  ".harness-news-runtime",
  ".harness-novel-runtime",
  ".ai-runtime-artifacts",
  ".workbuddy",
]);

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

async function listJsonFiles(rel: string): Promise<string[]> {
  try {
    const entries = await readdir(resolve(ROOT, rel), { withFileTypes: true });
    return entries.filter((e) => e.isFile() && e.name.endsWith(".json")).map((e) => e.name);
  } catch {
    return [];
  }
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

const skillsActive = (await listDirs("skills")).filter((n) => n !== "archive").length;
const skillsArchive = (await listDirs("skills/archive")).length;

const capabilityVerticals = (await listDirs("capabilities/rules")).length;
const schemaFiles = (await listJsonFiles("schemas")).length;

const pkg = JSON.parse(await readFile(resolve(ROOT, "package.json"), "utf-8"));
const npmScripts = Object.keys(pkg.scripts ?? {}).length;

const rows: Array<[string, string | number]> = [
  ["Source files (excl .git + node_modules + runtime dirs)", totalSource],
  ["  .ts", ts],
  ["  .md", md],
  ["  .json", json],
  ["  .py", py],
  ["  .html", html],
  ["  other", other],
  ["Core governance docs", governance],
  ["Platform adapters", platforms],
  ["Routes", routes],
  ["Skills (active / archive)", `${skillsActive} / ${skillsArchive}`],
  ["Capability verticals", capabilityVerticals],
  ["Schemas", schemaFiles],
  ["npm scripts", npmScripts],
];

console.log("# harness-factory stats (live — re-run `npm run stats`)");
console.log("");
console.log("| Metric | Count |");
console.log("|---|---|");
for (const [k, v] of rows) {
  console.log(`| ${k} | ${v} |`);
}
