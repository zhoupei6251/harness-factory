#!/usr/bin/env node
import { readdir, mkdir, stat, lstat, symlink, rm } from "node:fs/promises";
import { join, resolve, dirname } from "node:path";
import { homedir, platform as osPlatform } from "node:os";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SKILLS_DIR = resolve(ROOT, "skills");

const TARGETS = {
  codex: join(homedir(), ".codex", "skills"),
  claude: join(homedir(), ".claude", "skills"),
} as const;

type TargetKey = keyof typeof TARGETS;

function parseArgs(argv: string[]): { platforms: TargetKey[] } {
  const valid: TargetKey[] = ["codex", "claude"];
  const platforms = new Set<TargetKey>();
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--platform" && valid.includes(argv[i + 1] as TargetKey)) {
      platforms.add(argv[++i] as TargetKey);
    } else if (argv[i] === "-h" || argv[i] === "--help") {
      console.log("Usage: install-skills.ts [--platform codex|claude] (default: all)");
      process.exit(0);
    } else if (argv[i] === "--platform") {
      console.error(`Unknown platform: ${argv[i + 1]}`);
      process.exit(1);
    }
  }
  return { platforms: platforms.size ? [...platforms] : valid };
}

async function activeSkillNames(): Promise<string[]> {
  const entries = await readdir(SKILLS_DIR, { withFileTypes: true });
  const names: string[] = [];
  for (const entry of entries) {
    if (!entry.isDirectory() || entry.name === "archive") continue;
    try {
      await stat(join(SKILLS_DIR, entry.name, "SKILL.md"));
      names.push(entry.name);
    } catch {
      console.log(`[skip] skills/${entry.name}: no SKILL.md`);
    }
  }
  return names;
}

async function installSkill(name: string, destRoot: string, target: TargetKey): Promise<void> {
  const src = join(SKILLS_DIR, name);
  const dst = join(destRoot, name);
  await mkdir(destRoot, { recursive: true });

  try {
    const existing = await lstat(dst);
    if (!existing.isSymbolicLink()) {
      console.log(`[skip] ${target}:${name}: ${dst} exists and is not managed by this script`);
      return;
    }
    await rm(dst);
  } catch {
    // Destination does not exist yet.
  }

  if (osPlatform() === "win32") {
    await symlink(src, dst, "junction");
  } else {
    await symlink(src, dst, "dir");
  }
  console.log(`[ok]   ${target}: ${name} -> ${dst}`);
}

const { platforms } = parseArgs(process.argv.slice(2));
const names = await activeSkillNames();

for (const target of platforms) {
  for (const name of names) {
    await installSkill(name, TARGETS[target], target);
  }
}

console.log(`\nInstalled ${names.length} active skills to: ${platforms.join(", ")}`);
console.log("Skills are symlinked, so edits under skills/ are live. Archived skills are not installed.");
