#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { readFile, stat } from "node:fs/promises";
import { join } from "node:path";
import { homedir, platform as osPlatform } from "node:os";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const HOME = homedir();

let fail = 0;

function ok(message: string): void {
  console.log(`[ok]   ${message}`);
}

function missing(tool: string, fix: string): void {
  console.error(`[MISS] ${tool}`);
  console.error(`       fix: ${fix}`);
  fail = 1;
}

async function exists(path: string): Promise<boolean> {
  try {
    await stat(path);
    return true;
  } catch {
    return false;
  }
}

const [major, minor] = process.versions.node.split(".").map(Number);
if (major > 20 || (major === 20 && minor >= 9)) {
  ok(`node ${process.versions.node} (requires >=20.9)`);
} else {
  missing(`node ${process.versions.node}`, "upgrade to Node.js >= 20.9");
}

// codebase-memory-mcp: the bin supports --version and exits cleanly, so this
// both installs it into the npx cache (first run) and verifies it.
const npx = osPlatform() === "win32" ? "npx.cmd" : "npx";
// Windows: .cmd shims require shell:true (Node >=20.12 rejects them otherwise).
// Args are fixed literals, so no shell-injection risk.
const probe = spawnSync(npx, ["-y", "codebase-memory-mcp", "--version"], {
  encoding: "utf-8",
  timeout: 120_000,
  shell: osPlatform() === "win32",
});
if (probe.status === 0 && /codebase-memory-mcp/.test(probe.stdout ?? "")) {
  ok(`codebase-memory-mcp ${probe.stdout?.trim().split(/\s+/).pop()}`);
} else {
  missing(
    "codebase-memory-mcp",
    "run `npx -y codebase-memory-mcp --version` manually (network or npm registry issue)",
  );
}

// MCP wiring is OR-ed across platforms: a Qoder-only or Claude-only machine has
// no reason to fail bootstrap. The project `.mcp.json` counts on its own, but is
// labelled separately — it ships with the repo, so it proves the snippet is
// present, not that any client on this machine was actually wired.
const claudeMcp = join(ROOT, ".mcp.json");
const codexWired = await exists(join(HOME, ".codex", "config.toml"))
  && /mcp_servers\.codebase_memory/.test(await readFile(join(HOME, ".codex", "config.toml"), "utf-8"));
const qoderWired = await exists(join(HOME, ".qoder-cn", "settings.json"))
  && /codebase_memory/.test(await readFile(join(HOME, ".qoder-cn", "settings.json"), "utf-8"));
const claudeWired = await exists(claudeMcp)
  && /codebase_memory/.test(await readFile(claudeMcp, "utf-8"));
const clients = [codexWired && "codex", qoderWired && "qoder"].filter(Boolean).join(" + ");
if (clients || claudeWired) {
  ok(`codebase-memory-mcp wired (client config: ${clients || "none"}; project .mcp.json: ${claudeWired ? "present" : "absent"})`);
} else {
  missing(
    "codebase-memory-mcp config (no platform wiring found)",
    "codex: append mcp-config/codebase-memory.codex.toml to ~/.codex/config.toml · qoder: top-level mcpServers in ~/.qoder-cn/settings.json (Windows command=npx.cmd) · claude: keep .mcp.json at repo root",
  );
}

const ponytailPaths = [
  join(HOME, ".codex", "skills", "ponytail", "SKILL.md"),
  join(HOME, ".claude", "skills", "ponytail", "SKILL.md"),
  join(HOME, ".qoder", "skills", "ponytail", "SKILL.md"),
];
if (await ponytailPaths.reduce(async (acc, path) => (await acc) || exists(path), Promise.resolve(false))) {
  ok("ponytail skills installed");
} else {
  missing(
    "ponytail",
    "git clone https://github.com/DietrichGebert/ponytail and copy its skills/* into ~/.codex/skills/, ~/.claude/skills/ or ~/.qoder/skills/ (in Claude Code: /plugin marketplace add DietrichGebert/ponytail)",
  );
}

if (fail) {
  console.error("\nRequired external tooling missing — bootstrap blocked.");
  process.exit(1);
}
console.log("\nAll required external tools present.");
