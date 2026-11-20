import assert from "node:assert/strict";
import { mkdtemp, mkdir, readdir, readFile, rm, symlink, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";
import { tmpdir, platform } from "node:os";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../../", import.meta.url));
const sandbox = await mkdtemp(join(tmpdir(), "harness-declaration-"));
const project = join(sandbox, "project");
const tsx = join(root, "node_modules/tsx/dist/cli.mjs");

function run(script: string, args: string[]) {
  return spawnSync(process.execPath, [tsx, join(root, "tools/scripts", script), ...args], { encoding: "utf8", timeout: 60000 });
}

async function writeDeclaration(decl: unknown): Promise<void> {
  await writeFile(join(project, "harness.json"), JSON.stringify(decl), "utf-8");
}

try {
  await mkdir(project, { recursive: true });

  // 1. No declaration: legacy behaviour installs the whole active catalogue.
  const legacy = run("install-skills.ts", ["--platform", "claude", "--profile", "all", "--target", project]);
  assert.equal(legacy.status, 0, legacy.stderr);
  const allLinked = await readdir(join(project, ".claude", "skills"));
  assert.ok(allLinked.length > 5, `legacy install linked ${allLinked.length} skills`);
  assert.doesNotMatch(legacy.stdout, /pruned:/, "legacy install never prunes");

  // A user's own skill (real dir) and a link pointing outside the factory must both survive pruning.
  await mkdir(join(project, ".claude", "skills", "my-own-skill"), { recursive: true });
  const outside = join(sandbox, "outside-skill");
  await mkdir(outside, { recursive: true });
  await symlink(outside, join(project, ".claude", "skills", "foreign-skill"), platform() === "win32" ? "junction" : "dir");

  // 2. A declaration narrows the set to exactly what it names.
  await writeDeclaration({ platforms: ["claude"], skills: ["ponytail", "code-review"], agents: [] });
  const narrowed = run("install-skills.ts", ["--target", project]);
  assert.equal(narrowed.status, 0, narrowed.stderr);
  assert.match(narrowed.stdout, /pruned:/, "declaration mode reports pruning");

  const after = (await readdir(join(project, ".claude", "skills"))).sort();
  assert.deepEqual(after, ["code-review", "foreign-skill", "my-own-skill", "ponytail"].sort(),
    "only declared links remain; foreign link and real dir survive");

  // 3. A typo fails loudly instead of silently installing nothing.
  await writeDeclaration({ platforms: ["claude"], skills: ["ponytail", "does-not-exist"], agents: [] });
  const typo = run("install-skills.ts", ["--target", project]);
  assert.equal(typo.status, 1, "unknown skill must fail");
  assert.match(typo.stderr, /unknown skill\(s\): does-not-exist/);
  assert.match(typo.stderr, /available: /, "the message lists valid names");

  // 4. Platform validation comes from platforms/, not a script-local list.
  await writeDeclaration({ platforms: ["nope"], skills: [], agents: [] });
  const badPlatform = run("install-skills.ts", ["--target", project]);
  assert.equal(badPlatform.status, 1);
  assert.match(badPlatform.stderr, /unknown platform\(s\): nope/);

  // 5. Agents: declaration filters wrappers and prunes generated ones it drops.
  await writeDeclaration({ platforms: ["claude"], skills: [], agents: ["reviewer", "coder"] });
  const agentsRun = run("install-agents.ts", ["--target", project]);
  assert.equal(agentsRun.status, 0, agentsRun.stderr);
  const wrappers = (await readdir(join(project, ".claude", "agents"))).sort();
  assert.deepEqual(wrappers, ["harness-coder.md", "reviewer.md"], "only declared wrappers remain");

  const coder = await readFile(join(project, ".claude", "agents", "harness-coder.md"), "utf-8");
  assert.match(coder, /core: harness-factory\/agents\/coder\.md/);

  // 6. A host without per-agent files is skipped, not failed, when a declaration includes it.
  await writeDeclaration({ platforms: ["claude", "codex"], skills: [], agents: ["coder"] });
  const mixed = run("install-agents.ts", ["--target", project]);
  assert.equal(mixed.status, 0, mixed.stderr);
  assert.match(mixed.stdout, /\[skip\] no per-agent files on: codex/);

  console.log("harness declaration: all assertions passed");
} finally {
  await rm(sandbox, { recursive: true, force: true });
}
