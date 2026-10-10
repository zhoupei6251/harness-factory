#!/usr/bin/env node
// install-into-project.ts — 把 harness-factory 的 harness 注入任意目标项目。
// 设计：docs/superpowers/specs/2026-10-10-harness-isolation-design.md
//
// 模式：
//   - self:  --target 等于本仓库根（harness-factory 自身），import 走 @ENTRY.md
//   - other: 其他任意路径，import 走 @harness-factory/CLAUDE.harness.md
//
// 退出码：0 成功 / 1 参数错 / 2 写入失败 / 3 self 模式前置检查失败

import {
  readFile, writeFile, copyFile, stat, appendFile,
} from "node:fs/promises";
import { existsSync } from "node:fs";
import { resolve, dirname, basename } from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..");
const TEMPLATES_DIR = resolve(ROOT, "templates");

type Mode = "self" | "other";
type TemplateFile = "CLAUDE.md" | "AGENTS.md" | "GEMINI.md";

interface Args {
  target: string;
  dryRun: boolean;
  force: boolean;
  birdsEyeFile: string | null;
}

function parseArgs(argv: string[]): Args {
  const args: Args = {
    target: "",
    dryRun: false,
    force: false,
    birdsEyeFile: null,
  };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--target" && argv[i + 1]) args.target = resolve(argv[++i]);
    else if (argv[i] === "--dry-run") args.dryRun = true;
    else if (argv[i] === "--force") args.force = true;
    else if (argv[i] === "--birds-eye-file" && argv[i + 1]) args.birdsEyeFile = resolve(argv[++i]);
    else if (argv[i] === "-h" || argv[i] === "--help") {
      console.log("Usage: install-into-project.ts --target <path> [--dry-run] [--force] [--birds-eye-file <path>]");
      process.exit(0);
    } else {
      console.error(`[FAIL] unknown arg: ${argv[i]}`);
      process.exit(1);
    }
  }
  if (!args.target) {
    console.error("[FAIL] --target is required");
    process.exit(1);
  }
  return args;
}

function determineMode(target: string): Mode {
  return resolve(target) === ROOT ? "self" : "other";
}

async function preCheckSelf(target: string): Promise<string | null> {
  const required = ["ENTRY.md", "core", "AGENTS.md"];
  const missing: string[] = [];
  for (const p of required) {
    try {
      await stat(resolve(target, p));
    } catch {
      missing.push(p);
    }
  }
  return missing.length > 0 ? `self 模式前置检查失败：缺失 ${missing.join(", ")}` : null;
}

function templateImport(file: TemplateFile, mode: Mode): string {
  if (file === "CLAUDE.md") {
    return mode === "self" ? "@ENTRY.md" : "@harness-factory/CLAUDE.harness.md";
  }
  if (file === "AGENTS.md") {
    return mode === "self" ? "./ENTRY.md" : "harness-factory/AGENTS.harness.md";
  }
  return mode === "self" ? "./ENTRY.md" : "harness-factory/GEMINI.harness.md";
}

async function loadBirdsEye(args: Args): Promise<string> {
  const src = args.birdsEyeFile ?? resolve(TEMPLATES_DIR, "project-birds-eye.template.md");
  return await readFile(src, "utf-8");
}

function render(template: string, birdsEye: string, importLine: string): string {
  return template
    .replace(/\$\{PROJECT_BIRDS_EYE\}/g, birdsEye.trim())
    .replace(/\$\{HARNESS_FACTORY_IMPORT\}/g, importLine);
}

async function backupIfExists(dst: string): Promise<string | null> {
  if (!existsSync(dst)) return null;
  const stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  const backup = `${dst}.bak-${stamp}.md`;
  await copyFile(dst, backup);
  return backup;
}

async function isGitRepo(target: string): Promise<boolean> {
  try {
    const s = await stat(resolve(target, ".git"));
    return s.isDirectory() || s.isFile();
  } catch {
    return false;
  }
}

function isTracked(target: string, file: string): boolean {
  try {
    execFileSync("git", ["ls-files", "--error-unmatch", "--", file], { cwd: target, encoding: "utf-8", stdio: "pipe" });
    return true;
  } catch {
    return false;
  }
}

function runGit(target: string, args: string[]): void {
  execFileSync("git", args, { cwd: target, encoding: "utf-8", stdio: "pipe" });
}

async function appendExclude(target: string, entries: string[]): Promise<string[]> {
  const excludeFile = resolve(target, ".git/info/exclude");
  let existing = "";
  try {
    existing = await readFile(excludeFile, "utf-8");
  } catch {
    // file doesn't exist yet
  }
  const lines = existing.split(/\r?\n/);
  const toAppend = entries.filter((e) => !lines.includes(e));
  if (toAppend.length > 0) {
    const sep = existing.endsWith("\n") || existing === "" ? "" : "\n";
    await appendFile(excludeFile, sep + toAppend.join("\n") + "\n", "utf-8");
  }
  return toAppend;
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));
  const target = args.target;
  const mode = determineMode(target);

  console.log(`[info] target: ${target}`);
  console.log(`[info] mode:   ${mode}`);

  // Validate target
  try {
    const s = await stat(target);
    if (!s.isDirectory()) {
      console.error(`[FAIL] target is not a directory: ${target}`);
      process.exit(1);
    }
  } catch {
    console.error(`[FAIL] target path does not exist: ${target}`);
    process.exit(1);
  }

  // Self pre-check
  if (mode === "self") {
    const err = await preCheckSelf(target);
    if (err) {
      console.error(`[FAIL] ${err}`);
      process.exit(3);
    }
    console.log("[ok]   self pre-check: ENTRY.md / core/ / AGENTS.md 全部存在");
  }

  // Load birds-eye
  const birdsEye = await loadBirdsEye(args);
  console.log(`[ok]   loaded birds-eye (${birdsEye.length} chars)${args.birdsEyeFile ? ` from ${args.birdsEyeFile}` : " from default template"}`);

  // Render + write
  const templateFiles: TemplateFile[] = ["CLAUDE.md", "AGENTS.md", "GEMINI.md"];
  for (const tf of templateFiles) {
    const template = await readFile(resolve(TEMPLATES_DIR, `target-${tf}`), "utf-8");
    const importLine = templateImport(tf, mode);
    const content = render(template, birdsEye, importLine);
    const dst = resolve(target, tf);
    const wasExisting = existsSync(dst);
    if (args.dryRun) {
      console.log(`[dry]  ${tf} (${content.length} chars, would write)`);
      continue;
    }
    const backup = wasExisting ? await backupIfExists(dst) : null;
    await writeFile(dst, content, "utf-8");
    console.log(`[ok]   ${tf} (${content.length} chars)${backup ? ` [backed up to ${basename(backup)}]` : ""}`);
  }

  // Git ops
  const inGitRepo = await isGitRepo(target);
  if (!inGitRepo) {
    console.log("[info] target is not a git repository, skipping local config");
  } else {
    console.log("[info] target is a git repository");

    // .git/info/exclude: add harness-factory path (other mode only)
    if (mode === "other") {
      if (args.dryRun) {
        console.log(`[dry]  would append 'harness-factory' to .git/info/exclude`);
      } else {
        const added = await appendExclude(target, ["harness-factory"]);
        if (added.length > 0) console.log(`[ok]   appended to .git/info/exclude: ${added.join(", ")}`);
        else console.log(`[ok]   .git/info/exclude already contains: harness-factory`);
      }
    }

    // skip-worktree on existing tracked files
    for (const tf of templateFiles) {
      if (!isTracked(target, tf)) continue;
      if (args.dryRun) {
        console.log(`[dry]  would git update-index --skip-worktree ${tf}`);
      } else {
        try {
          runGit(target, ["update-index", "--skip-worktree", tf]);
          console.log(`[ok]   skip-worktree set: ${tf}`);
        } catch (e) {
          console.error(`[FAIL] skip-worktree failed for ${tf}: ${(e as Error).message}`);
        }
      }
    }
  }

  console.log("");
  console.log(args.dryRun ? "Dry run complete. No files written." : `install-into-project complete (mode=${mode}).`);
  console.log("Next: verify `git status` has no harness-related dirty entries; restart sessions to load new rules.");
}

main().catch((e) => {
  console.error(`[FAIL] ${(e as Error).message}`);
  console.error((e as Error).stack);
  process.exit(1);
});
