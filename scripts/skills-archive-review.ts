#!/usr/bin/env node
/**
 * skills-archive-review.ts — phase-6 cull candidate report.
 *
 * What it does: for every entry under skills/archive/, count how many
 * non-archive tracked files in the repository mention the skill's name
 * (word-boundary). Skills with zero non-self references are the cull
 * candidates — nothing in this repo points at them, and nothing outside
 * this repo can, because the archive is not exported.
 *
 * Skills with the same name as an active skill or a core doc are flagged
 * "name-collision" — the duplicate name is itself a hint that one of the
 * two is obsolete (the script does not decide which).
 *
 * The script reads `git ls-files` so the count is "what ships", not
 * "what happens to be on this machine". Local runtime dirs (skills/
 * <name>/scripts/dump.json etc.) are excluded automatically — they are
 * not tracked.
 *
 * Output: writes nothing into the working tree. Prints a Markdown table
 * to stdout, sorted by reference count ascending. The user pipes it
 * wherever it belongs (verifications/, or a tracking doc).
 *
 * Re-run: `npx tsx scripts/skills-archive-review.ts`. Not wired into
 * `npm test` on purpose: the count is an observation, not an invariant.
 * A skill with zero references today may gain one tomorrow; a hard gate
 * would silently break that.
 */
import { execFileSync } from "node:child_process";
import { readdir, readFile, stat } from "node:fs/promises";
import type { Dirent } from "node:fs";
import { resolve, dirname, join, sep } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");

// Track what we read so the count is "tracked files we walked", not just
// "files we found". Skills-audit covers existence/mtime; this script is
// strictly about reachability.
function trackedFiles(): string[] {
  return execFileSync("git", ["ls-files"], { cwd: ROOT, encoding: "utf-8" })
    .split(/\r?\n/)
    .filter(Boolean);
}

async function listDirs(rel: string): Promise<string[]> {
  try {
    const entries: Dirent[] = await readdir(resolve(ROOT, rel), { withFileTypes: true });
    return entries.filter((e) => e.isDirectory()).map((e) => e.name);
  } catch {
    return [];
  }
}

interface Collisions {
  sameNameActive: boolean;
  sameNameCore: boolean;
  sameNameRoutes: boolean;
  sameNamePlatforms: boolean;
}

interface ArchiveRow {
  name: string;
  references: number;
  hasSkill: boolean;
  hasMeta: boolean;
  sizeKiB: number;
  collisions: Collisions;
  sampleHits: string[]; // up to 3 paths
}

async function dirSizeKiB(p: string): Promise<number> {
  try {
    return Math.round((await readFile(p, "utf-8")).length / 1024);
  } catch {
    return 0;
  }
}

// Word-boundary match: \bSkill\b would over-match hyphenated names; the
// practical name shape here is [a-z0-9-]+ so we use a manual boundary on
// hyphen and word characters. Includes both forward-slash (md text) and
// back-slash (Windows-style paths in copy-pasted snippets).
function makeMatcher(name: string): RegExp {
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`(^|[^A-Za-z0-9_-])${escaped}([^A-Za-z0-9_-]|$)`, "g");
}

const archive = await listDirs("skills/archive");
const allActiveSkillNames = new Set((await listDirs("skills")).filter((n) => n !== "archive"));
const coreFiles = new Set((await readdir(resolve(ROOT, "core"), { withFileTypes: true }))
  .filter((e) => e.isFile() && e.name.endsWith(".md"))
  .map((e) => e.name.replace(/\.md$/, "")));
const routeDirs = await listDirs("routes");
const platformDirs = await listDirs("platforms");

// Files we will not count references from. Excluded:
//   - skills/archive/<n>/SKILL.md and _meta.json: self-reference (would
//     inflate the count for every skill trivially).
//   - The skills/INDEX.md generated file: lists every skill by design;
//     including it would make every skill read as "1 reference from
//     INDEX.md" and obscure real reachability.
//   - node_modules, dist, runtime dirs: not source-of-truth.
const skipRelDirs = ["skills/archive/", "node_modules/", "dist/", ".ai-runtime-artifacts/", ".workbuddy/"];

function isExcluded(rel: string): boolean {
  if (rel === "skills/INDEX.md") return true;
  for (const prefix of skipRelDirs) {
    if (rel === prefix.replace(/\/$/, "") || rel.startsWith(prefix)) return true;
  }
  return false;
}

const candidates: ArchiveRow[] = [];
const tracked = trackedFiles().filter((p) => !isExcluded(p));

for (const name of archive) {
  const re = makeMatcher(name);
  let count = 0;
  const sampleHits: string[] = [];
  for (const rel of tracked) {
    const full = resolve(ROOT, rel);
    let text: string;
    try {
      const st = await stat(full);
      // Skip binary by extension; ref counting is text-only.
      if (!/\.(md|ts|json|mjs|cjs|js|py|sh)$/.test(rel)) continue;
      text = await readFile(full, "utf-8");
    } catch {
      continue;
    }
    // Strip leading whitespace per line so word boundary at start-of-line still works.
    const hits = text.match(re);
    if (hits && hits.length > 0) {
      count += hits.length;
      if (sampleHits.length < 3) sampleHits.push(rel);
    }
  }
  const hasSkill = await stat(resolve(ROOT, "skills/archive", name, "SKILL.md")).then(() => true).catch(() => false);
  const hasMeta = await stat(resolve(ROOT, "skills/archive", name, "_meta.json")).then(() => true).catch(() => false);
  const sizeKiB = await dirSizeKiB(resolve(ROOT, "skills/archive", name, "SKILL.md"));
  const collisions: Collisions = {
    sameNameActive: allActiveSkillNames.has(name),
    sameNameCore: coreFiles.has(name),
    sameNameRoutes: routeDirs.includes(name),
    sameNamePlatforms: platformDirs.includes(name),
  };
  candidates.push({ name, references: count, hasSkill, hasMeta, sizeKiB, collisions, sampleHits });
}

candidates.sort((a, b) => {
  if (a.references !== b.references) return a.references - b.references;
  return a.name.localeCompare(b.name);
});

const total = candidates.length;
const zeroRef = candidates.filter((c) => c.references === 0);
const noSkillFile = candidates.filter((c) => !c.hasSkill);
const noMeta = candidates.filter((c) => !c.hasMeta);
const collisions = candidates.filter((c) => c.collisions.sameNameActive || c.collisions.sameNameCore || c.collisions.sameNameRoutes || c.collisions.sameNamePlatforms);

console.log(`# skills/archive phase-6 cull review (live — re-run \`npx tsx scripts/skills-archive-review.ts\`)`);
console.log("");
console.log(`Scanned ${total} archived skills across ${tracked.length} tracked non-archive text files.`);
console.log("");
console.log(`Reference count is the number of `);
console.log(`- word-boundary mentions of the skill name in source files;`);
console.log(`- excluding \`skills/archive/\` (self), \`skills/INDEX.md\` (every entry is listed there),`);
console.log(`- node_modules / dist / runtime dirs.`);
console.log("");

console.log(`## Summary`);
console.log("");
console.log(`| Bucket | Count |`);
console.log(`|---|---|`);
console.log(`| Total archived | ${total} |`);
console.log(`| 0 references (cull candidate) | ${zeroRef.length} |`);
console.log(`| missing SKILL.md | ${noSkillFile.length} |`);
console.log(`| missing _meta.json | ${noMeta.length} |`);
console.log(`| name-collision with active/core | ${collisions.length} |`);
console.log("");

console.log(`## Sorted by reachability (lowest first)`);
console.log("");
console.log(`| Skill | Refs | SKILL.md | _meta.json | Size KiB | Collision | Sample paths |`);
console.log(`|---|---:|---|---|---:|---|---|`);
for (const c of candidates) {
  const tags: string[] = [];
  if (c.collisions.sameNameActive) tags.push("active");
  if (c.collisions.sameNameCore) tags.push("core");
  if (c.collisions.sameNameRoutes) tags.push("route");
  if (c.collisions.sameNamePlatforms) tags.push("platform");
  const tagCell = tags.length === 0 ? "—" : tags.join(", ");
  const samples = c.sampleHits.length === 0 ? "—" : c.sampleHits.map((s) => `\`${s}\``).join("<br>");
  console.log(`| ${c.name} | ${c.references} | ${c.hasSkill ? "✓" : "✗"} | ${c.hasMeta ? "✓" : "✗"} | ${c.sizeKiB} | ${tagCell} | ${samples} |`);
}

console.log("");
console.log(`## Cull candidates (0 references, intact SKILL.md + _meta.json)`);
console.log("");
const cleanZero = zeroRef.filter((c) => c.hasSkill && c.hasMeta);
if (cleanZero.length === 0) {
  console.log(`- (none — every 0-ref archived skill is already missing a file; nothing clean to suggest removing)`);
} else {
  for (const c of cleanZero) {
    console.log(`- \`${c.name}\` — no in-repo references, complete skill files; safe to \`git rm\` if the user confirms the off-repo absence`);
  }
}
console.log("");
console.log(`## Collision candidates (decide which side survives)`);
console.log("");
if (collisions.length === 0) {
  console.log(`- (none)`);
} else {
  for (const c of collisions) {
    const tags: string[] = [];
    if (c.collisions.sameNameActive) tags.push(`active skill \`${c.name}\``);
    if (c.collisions.sameNameCore) tags.push(`core/${c.name}`);
    if (c.collisions.sameNameRoutes) tags.push(`routes/${c.name}`);
    if (c.collisions.sameNamePlatforms) tags.push(`platforms/${c.name}`);
    console.log(`- \`archive/${c.name}\` ↔ ${tags.join(" + ")} (refs=${c.references})`);
  }
}
