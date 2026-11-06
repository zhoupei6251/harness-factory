#!/usr/bin/env node
import { readdir, mkdir, stat, lstat, realpath, symlink } from "node:fs/promises";
import { join, resolve, dirname } from "node:path";
import { homedir, platform as osPlatform } from "node:os";
import { fileURLToPath } from "node:url";
import { loadPlatforms } from "./platforms.ts";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SKILLS_DIR = join(ROOT, "skills");

const CORE = ["ponytail", "codebase-memory", "hf-debug", "hf-verify", "hf-security", "hf-design", "hf-tdd", "hf-ui", "hf-web-test", "playwright"];

function parseArgs(argv: string[], known: string[]) {
  const platforms = new Set<string>();
  let profile = "core";
  let base = homedir();
  let dryRun = false;
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--help" || arg === "-h") {
      console.log("Usage: install-skills.ts [--platform all|claude|codex|trae|workbuddy|qoder] [--profile core|all] [--target <project>] [--dry-run]\nDefault: 10 core skills, all five hosts, user home. --target uses project-local native skill directories.");
      process.exit(0);
    }
    if (arg === "--dry-run") {
      dryRun = true;
      continue;
    }
    if (!["--platform", "--profile", "--target"].includes(arg)) {
      throw new Error(`Unknown argument: ${arg}`);
    }
    const value = argv[++i];
    if (!value || value.startsWith("--")) {
      throw new Error(`Missing value for ${arg}`);
    }
    if (arg === "--platform") {
      if (value === "all") {
        for (const key of known) platforms.add(key);
      } else if (known.includes(value)) {
        platforms.add(value);
      } else {
        throw new Error(`Unknown platform: ${value}`);
      }
    } else if (arg === "--profile") {
      if (value !== "core" && value !== "all") throw new Error(`Unknown profile: ${value}`);
      profile = value;
    } else {
      base = resolve(value);
    }
  }
  return { platforms: platforms.size ? [...platforms] : known, profile, base, dryRun };
}

async function skillNames(profile: string): Promise<string[]> {
  const names = profile === "core" ? CORE : (await readdir(SKILLS_DIR, { withFileTypes: true }))
    .filter((entry) => entry.isDirectory() && entry.name !== "archive").map((entry) => entry.name);
  for (const name of names) {
    if (!(await stat(join(SKILLS_DIR, name, "SKILL.md"))).isFile()) {
      throw new Error(`skills/${name}/SKILL.md is not a file`);
    }
  }
  return [...names].sort();
}

async function installSkill(name: string, destRoot: string, dryRun: boolean): Promise<"installed" | "kept" | "conflict"> {
  const src = join(SKILLS_DIR, name);
  const dst = join(destRoot, name);
  const existing = await lstat(dst).catch((error: NodeJS.ErrnoException) => {
    if (error.code !== "ENOENT") throw error;
    return null;
  });
  if (existing) {
    const linked = existing.isSymbolicLink() ? await realpath(dst).catch((error: NodeJS.ErrnoException) => {
      if (error.code !== "ENOENT") throw error;
      return null;
    }) : null;
    if (linked === await realpath(src)) {
      console.log(`[keep] ${dst}`);
      return "kept";
    }
    console.error(`[conflict] ${dst} already exists; preserved. Move it explicitly before installing this skill.`);
    return "conflict";
  }
  if (!dryRun) {
    await mkdir(destRoot, { recursive: true });
    await symlink(src, dst, osPlatform() === "win32" ? "junction" : "dir");
  }
  console.log(`[${dryRun ? "plan" : "ok"}] ${dst} -> ${src}`);
  return "installed";
}

try {
  const matrix = await loadPlatforms();
  const { platforms, profile, base, dryRun } = parseArgs(process.argv.slice(2), [...matrix.keys()].sort());
  const names = await skillNames(profile);
  console.log(`${names.length} skills (${profile}); hosts: ${platforms.join(", ")}; ${dryRun ? "preview" : "install"}`);
  const counts = { installed: 0, kept: 0, conflict: 0 };
  for (const target of platforms) {
    for (const name of names) {
      counts[await installSkill(name, join(base, matrix.get(target)!.skillsDir), dryRun)]++;
    }
  }
  console.log(`${dryRun ? "Planned" : "Installed"}: ${counts.installed}; already linked: ${counts.kept}; conflicts: ${counts.conflict}. No plugins, hooks or MCP settings changed.`);
  if (counts.conflict) process.exitCode = 1;
} catch (error) {
  console.error(`[FAIL] ${error instanceof Error ? error.message : String(error)}`);
  process.exitCode = 1;
}
