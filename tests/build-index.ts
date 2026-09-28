#!/usr/bin/env node
/**
 * Regenerate skills/INDEX.md from current skills/<name>/SKILL.md frontmatter.
 *
 * Usage: tsx tests/build-index.ts  (or  npm run index)
 */
import { readdir, readFile, writeFile, stat } from "node:fs/promises";
import { resolve, dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..");
const SKILLS_DIR = resolve(ROOT, "skills");
const INDEX = join(SKILLS_DIR, "INDEX.md");

async function getDescription(skillMd: string): Promise<string> {
  const content = await readFile(skillMd, "utf-8");
  const head = content.slice(0, 2000);
  if (head.startsWith("---")) {
    const end = head.indexOf("---", 3);
    if (end > 0) {
      for (const line of head.slice(3, end).split("\n")) {
        if (line.startsWith("description:")) {
          return line.split(":", 2)[1].trim().replace(/^["']|["']$/g, "");
        }
      }
    }
  }
  for (const line of head.split("\n")) {
    const t = line.trim();
    if (t && !t.startsWith("#") && !t.startsWith("---")) return t.slice(0, 80);
  }
  return "";
}

async function collectRows(dir: string, prefix: string): Promise<Array<[string, string]>> {
  let entries: string[] = [];
  try {
    entries = await readdir(dir);
  } catch {
    return [];
  }
  const rows: Array<[string, string]> = [];
  for (const s of entries.sort()) {
    // skip the archive subdir (collected separately) and non-dir entries like INDEX.md
    if (s === "archive") continue;
    if (!(await stat(join(dir, s)).then((st) => st.isDirectory()).catch(() => false))) continue;
    const sm = join(dir, s, "SKILL.md");
    const desc = (await getDescription(sm).catch(() => "(missing SKILL.md)")) || "(missing SKILL.md)";
    rows.push([prefix + s, desc]);
  }
  return rows;
}

async function main(): Promise<number> {
  const active = await collectRows(SKILLS_DIR, "");
  const archived = await collectRows(join(SKILLS_DIR, "archive"), "archive/");
  const rows = [...active, ...archived];
  let out = `# Skill Index\n\nAuto-generated. Re-run with: npm run index\nTotal: ${active.length} active + ${archived.length} archived = ${rows.length} skills\n\n`;
  out += `## Active (${active.length})\n\n| Skill | Description |\n|-------|-------------|\n`;
  for (const [s, d] of active) {
    const dSafe = d.replace(/\|/g, "\\|").slice(0, 100);
    out += `| ${s} | ${dSafe} |\n`;
  }
  out += `\n## Archived (${archived.length})\n\n> Not in active use. Restore via: \`git mv skills/archive/<name> skills/<name>\`\n\n| Skill | Description |\n|-------|-------------|\n`;
  for (const [s, d] of archived) {
    const dSafe = d.replace(/\|/g, "\\|").slice(0, 100);
    out += `| ${s} | ${dSafe} |\n`;
  }
  await writeFile(INDEX, out, "utf-8");
  console.log(`wrote ${INDEX} (${active.length} active, ${archived.length} archived)`);
  return 0;
}

process.exit(await main());
