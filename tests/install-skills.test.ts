import assert from "node:assert/strict";
import { mkdtemp, mkdir, readdir, readFile, realpath, rm, symlink, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";
import { tmpdir, platform } from "node:os";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../", import.meta.url));
const sandbox = await mkdtemp(join(tmpdir(), "harness-skills-"));
const home = join(sandbox, "home");
const target = join(sandbox, "project");
const env = { ...process.env, USERPROFILE: home, HOME: home };
const core = ["codebase-memory", "hf-debug", "hf-design", "hf-security", "hf-tdd", "hf-ui", "hf-verify", "hf-web-test", "playwright", "ponytail"].sort();
const hosts = [".claude", ".agents", ".trae", ".codebuddy", ".qoder"];

function run(args: string[]) {
  return spawnSync(process.execPath, [join(root, "node_modules/tsx/dist/cli.mjs"), join(root, "scripts/install-skills.ts"), ...args], {
    encoding: "utf8", env, timeout: 30000,
  });
}

try {
  const actualHome = spawnSync(process.execPath, ["-p", "require('os').homedir()"], { env, encoding: "utf8" });
  assert.equal(resolve(actualHome.stdout.trim()), resolve(home), "test child must use the isolated home");

  const preview = run(["--target", target, "--dry-run"]);
  assert.equal(preview.status, 0, preview.stderr);
  assert.match(preview.stdout, /10.*core/);
  assert.deepEqual(await readdir(sandbox), [], "preview creates neither home nor project");

  const installed = run(["--target", target]);
  assert.equal(installed.status, 0, installed.stderr);
  for (const host of hosts) {
    const dir = join(target, host, "skills");
    assert.deepEqual((await readdir(dir)).sort(), core, `${host} gets only the curated core`);
    assert.equal(await realpath(join(dir, "ponytail")), await realpath(join(root, "skills/ponytail")));
  }
  assert.equal(run(["--target", target]).status, 0, "reinstall is idempotent");

  const extra = run(["--platform", "codex", "--target", target, "--profile", "all"]);
  assert.equal(extra.status, 0, extra.stderr);
  assert.ok((await readdir(join(target, ".agents/skills"))).includes("analyze-impact"), "all retains legacy skills");
  assert.ok(!(await readdir(join(target, ".claude/skills"))).includes("analyze-impact"), "selected host only");
  assert.ok(!(await readdir(join(target, ".agents/skills"))).includes("archive"));

  const foreign = join(sandbox, "foreign");
  await mkdir(foreign);
  await writeFile(join(foreign, "keep.txt"), "user content");
  const conflicting = join(target, ".agents/skills/ponytail");
  await rm(conflicting);
  await symlink(foreign, conflicting, platform() === "win32" ? "junction" : "dir");
  const conflict = run(["--platform", "codex", "--target", target]);
  assert.equal(conflict.status, 1, "a foreign symlink is an explicit conflict");
  assert.equal(await realpath(conflicting), await realpath(foreign), "foreign symlink preserved");
  await rm(conflicting);
  await mkdir(conflicting);
  await writeFile(join(conflicting, "keep.txt"), "user content");
  assert.equal(run(["--platform", "codex", "--target", target]).status, 1);
  assert.equal(await readFile(join(conflicting, "keep.txt"), "utf8"), "user content", "user directory preserved");

  for (const args of [["--wat"], ["--platform"], ["--platform", "bad"], ["--profile", "bad"], ["--target"], ["--target", "--dry-run"]]) {
    assert.equal(run(args).status, 1, `reject ${args.join(" ")}`);
  }
  console.log("Skill installer passed: five hosts, profiles, preview, idempotence, conflicts and invalid input.");
} finally {
  // sandbox is the exact mkdtemp-created test root; never traverse a caller-supplied path.
  await rm(sandbox, { recursive: true, force: true });
}
