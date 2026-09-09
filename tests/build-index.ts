#!/usr/bin/env node
/**
 * Regenerate skills/INDEX.md from current skills/<name>/SKILL.md frontmatter.
 *
 * Usage: tsx tests/build-index.ts  (or  npm run index)
 */
import { readdir, readFile, writeFile } from "node:fs/promises";
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

async function main(): Promise<number> {
  let entries: string[] = [];
  try {
    entries = await readdir(SKILLS_DIR);
  } catch {
    console.log(`no skills/ dir at ${SKILLS_DIR}`);
    return 1;
  }
  const skillDirs = entries
    .filter((e) => e !== "INDEX.md")
    .sort();
  const rows: Array<[string, string]> = [];
  for (const s of skillDirs) {
    const sm = join(SKILLS_DIR, s, "SKILL.md");
    const desc = (await getDescription(sm).catch(() => "(missing SKILL.md)")) || "(missing SKILL.md)";
    rows.push([s, desc]);
  }
  let out = `# Skill Index\n\nAuto-generated. Re-run with: npm run index\nTotal: ${rows.length} skills\n\n| Skill | Description |\n|-------|-------------|\n`;
  for (const [s, d] of rows) {
    const dSafe = d.replace(/\|/g, "\\|").slice(0, 100);
    out += `| ${s} | ${dSafe} |\n`;
  }
  await writeFile(INDEX, out, "utf-8");
  console.log(`wrote ${INDEX} (${rows.length} skills)`);
  return 0;
}

process.exit(await main());
