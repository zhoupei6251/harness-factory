#!/usr/bin/env node
import { readFile, readdir } from "node:fs/promises";
import { resolve, dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..");
const SCHEMAS_DIR = resolve(ROOT, "schemas");
const SKILLS_DIR = resolve(ROOT, "skills");

let fail = 0;

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

async function validateSkills(): Promise<void> {
  let entries: string[] = [];
  try {
    entries = await readdir(SKILLS_DIR);
  } catch {
    return;
  }
  for (const name of entries) {
    const skillMd = join(SKILLS_DIR, name, "SKILL.md");
    try {
      await readFile(skillMd);
      console.log(`[ok]   skills/${name}/SKILL.md`);
    } catch {
      console.log(`[FAIL] skills/${name}/: missing SKILL.md`);
      fail = 1;
    }
  }
}

await validateSchemas();
await validateSkills();

if (fail === 0) {
  console.log("");
  console.log("All validations passed.");
} else {
  console.log("");
  console.log("Validation FAILED.");
  process.exit(1);
}
