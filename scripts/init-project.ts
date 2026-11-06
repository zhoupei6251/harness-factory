#!/usr/bin/env node
// init-project.ts — 一条命令把 harness-factory 投影到目标项目：
// 入口文件 + skills + agents。步骤可重复执行，已存在的相同产物保持不动。
import { spawnSync } from "node:child_process";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const TSX = join(ROOT, "node_modules/tsx/dist/cli.mjs");
const HOSTS = ["claude", "codex", "trae", "workbuddy", "qoder"];

function parseArgs(argv: string[]) {
  let target = "";
  let platform = "claude";
  let profile = "all";
  let dryRun = false;
  let force = false;
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--help" || arg === "-h") {
      console.log(
        "Usage: init-project.ts --target <path> [--platform all|<host>] [--profile core|all] [--force] [--dry-run]\n" +
          "Installs entry files, skills and agents into a project. Default host: claude; default profile: all.",
      );
      process.exit(0);
    }
    if (arg === "--dry-run") { dryRun = true; continue; }
    if (arg === "--force") { force = true; continue; }
    if (!["--target", "--platform", "--profile"].includes(arg)) throw new Error(`Unknown argument: ${arg}`);
    const value = argv[++i];
    if (!value || value.startsWith("--")) throw new Error(`Missing value for ${arg}`);
    if (arg === "--target") target = resolve(value);
    else if (arg === "--platform") platform = value;
    else profile = value;
  }
  if (!target) throw new Error("--target is required");
  if (platform !== "all" && !HOSTS.includes(platform)) throw new Error(`Unknown platform: ${platform}`);
  return { target, platform, profile, dryRun, force };
}

function step(name: string, script: string, args: string[]): void {
  console.log(`\n── ${name}`);
  const result = spawnSync(process.execPath, [TSX, join(ROOT, "scripts", script), ...args], { stdio: "inherit", timeout: 120000 });
  if (result.status !== 0) {
    throw new Error(`${name} failed (exit ${result.status ?? "signal " + result.signal})`);
  }
}

try {
  const { target, platform, profile: prof, dryRun, force } = parseArgs(process.argv.slice(2));
  const flags = [dryRun ? "--dry-run" : "", force ? "--force" : ""].filter(Boolean);
  const hosts = platform === "all" ? HOSTS : [platform];
  console.log(`init-project: ${target} (hosts: ${hosts.join(", ")}, profile: ${prof})${dryRun ? " [preview]" : ""}`);

  step("entry files", "install-into-project.ts", ["--target", target, ...flags]);
  step("skills", "install-skills.ts", ["--platform", platform, "--profile", prof, "--target", target, ...flags]);

  // Agents only project to hosts that have a per-agent file concept; a codex-only target skips this step.
  if (hosts.includes("claude")) {
    step("agents", "install-agents.ts", ["--platform", "claude", "--target", target, ...flags]);
  } else {
    console.log("\n── agents\n[skip] no selected host has a per-agent file concept");
  }

  console.log(`\n${dryRun ? "Preview complete" : "Project initialized"}.`);
} catch (error) {
  console.error(`[FAIL] ${error instanceof Error ? error.message : String(error)}`);
  process.exitCode = 1;
}
