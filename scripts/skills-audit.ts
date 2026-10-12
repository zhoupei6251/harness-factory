#!/usr/bin/env node
/**
 * Audit the skills/ tree: list active + archived skills, report size and
 * last-modified dates, and surface archive bit-rot risk.
 *
 * Why: 51 archived skills is a lot. Some may be stale (no _meta.json, broken
 *      links, or referencing APIs that have since changed). This script doesn't
 *      decide what to delete — it just reports so the user can.
 */
import { readdir, stat, readFile } from "node:fs/promises";
import type { Dirent } from "node:fs";
import { resolve, dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SKILLS = resolve(ROOT, "skills");
const ARCHIVE = join(SKILLS, "archive");

interface Row {
  name: string;
  location: string; // "active" | "archive"
  hasSkill: boolean;
  hasMeta: boolean;
  sizeKiB: number;
  mtimeIso: string;
}

async function dirKiB(p: string): Promise<number> {
  try {
    const out = (await readFile(p, "utf-8")).length;
    return Math.round(out / 1024);
  } catch {
    return 0;
  }
}

async function auditDir(dir: string, location: "active" | "archive"): Promise<Row[]> {
  let entries: Dirent[] = [];
  try {
    entries = await readdir(dir, { withFileTypes: true });
  } catch {
    return [];
  }
  const rows: Row[] = [];
  for (const e of entries) {
    if (!e.isDirectory()) continue;
    if (e.name === "archive") continue; // sibling dir, not a skill; handled by the archive pass
    const full = join(dir, e.name);
    const s = await stat(full).catch(() => null);
    if (!s) continue;
    const hasSkill = await readFile(join(full, "SKILL.md"), "utf-8")
      .then(() => true)
      .catch(() => false);
    const hasMeta = await readFile(join(full, "_meta.json"), "utf-8")
      .then(() => true)
      .catch(() => false);
    const sizeKiB = await dirKiB(join(full, "SKILL.md"));
    rows.push({
      name: e.name,
      location,
      hasSkill,
      hasMeta,
      sizeKiB,
      mtimeIso: s.mtime.toISOString().slice(0, 10),
    });
  }
  return rows.sort((a, b) => a.name.localeCompare(b.name));
}

const active = await auditDir(SKILLS, "active");
const archive = await auditDir(ARCHIVE, "archive");

function table(location: string, rows: Row[]): void {
  console.log(`\n## ${location} (${rows.length})\n`);
  console.log("| Skill | SKILL.md | _meta.json | Size (KiB) | mtime |");
  console.log("|---|---|---|---|---|");
  for (const r of rows) {
    const skill = r.hasSkill ? "✓" : "✗";
    const meta = r.hasMeta ? "✓" : "✗";
    console.log(`| ${r.name} | ${skill} | ${meta} | ${r.sizeKiB} | ${r.mtimeIso} |`);
  }
}

console.log("# skills/ audit (live — re-run `npm run skills:audit`)");
table("active", active);
table("archive", archive);

const missingSkill = [...active, ...archive].filter((r) => !r.hasSkill);
const missingMeta = [...active, ...archive].filter((r) => !r.hasMeta);

console.log("\n## Risks\n");
if (missingSkill.length) {
  console.log(`- ${missingSkill.length} skill(s) missing SKILL.md: ${missingSkill.map((r) => r.location + "/" + r.name).join(", ")}`);
}
if (missingMeta.length) {
  console.log(`- ${missingMeta.length} skill(s) missing _meta.json: ${missingMeta.map((r) => r.location + "/" + r.name).join(", ")}`);
}
if (missingSkill.length === 0 && missingMeta.length === 0) {
  console.log("- (none)");
}
