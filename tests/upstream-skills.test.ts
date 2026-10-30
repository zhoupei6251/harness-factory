import assert from "node:assert/strict";
import { mkdtemp, mkdir, writeFile, readFile, rm, symlink } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir, platform } from "node:os";
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { verifyUpstreams } from "../scripts/check-upstreams.ts";

const root = fileURLToPath(new URL("../", import.meta.url));
assert.deepEqual(await verifyUpstreams(root), [], "all bundled source files match the pinned hashes");
const sandbox = await mkdtemp(join(tmpdir(), "harness-upstream-"));
try {
  await mkdir(join(sandbox, "references"));
  await mkdir(join(sandbox, "skills/demo/upstream"), { recursive: true });
  const content = "MIT\n";
  const file = { from: "LICENSE", to: "skills/demo/upstream/LICENSE", sha256: createHash("sha256").update(content).digest("hex") };
  const source = { id: "demo", repository: "https://github.com/owner/repo", revision: "a".repeat(40), files: [file] };
  const save = () => writeFile(join(sandbox, "references/upstreams.lock.json"), JSON.stringify({ formatVersion: 1, sources: [source] }));
  await writeFile(join(sandbox, file.to), content);
  await save();
  assert.deepEqual(await verifyUpstreams(sandbox), []);
  await writeFile(join(sandbox, file.to), "changed");
  assert.match((await verifyUpstreams(sandbox)).join("\n"), /hash mismatch/);
  await rm(join(sandbox, file.to));
  assert.match((await verifyUpstreams(sandbox)).join("\n"), /missing/);
  file.to = "../outside";
  await save();
  assert.match((await verifyUpstreams(sandbox)).join("\n"), /unsafe path/);
  source.revision = "main";
  await save();
  assert.match((await verifyUpstreams(sandbox)).join("\n"), /revision/);

  // On Windows this exercises a cross-drive junction when temp is on C: and the repo is on D:.
  const escape = join(sandbox, "skills/escape/upstream");
  await mkdir(join(sandbox, "skills/escape"));
  await symlink(join(root, "skills/ponytail"), escape, platform() === "win32" ? "junction" : "dir");
  source.revision = "a".repeat(40);
  file.to = "skills/escape/upstream/upstream-LICENSE";
  file.sha256 = createHash("sha256").update(await readFile(join(root, "skills/ponytail/upstream-LICENSE"))).digest("hex");
  await save();
  assert.match((await verifyUpstreams(sandbox)).join("\n"), /unsafe path outside repository/, "reject junction escape across volumes too");
} finally {
  await rm(sandbox, { recursive: true, force: true });
}

const python = ["python3", "python"].find((cmd) => {
  const probe = spawnSync(cmd, ["--version"], { encoding: "utf8" });
  return probe.status === 0 && /^Python 3\./.test(`${probe.stdout ?? ""}${probe.stderr ?? ""}`.trim());
});
if (python) {
  const cli = join(root, "skills/hf-ui/scripts/search.py");
  const run = (args: string[]) => spawnSync(python, ["-B", cli, ...args], { encoding: "utf8", timeout: 10000 });
  const ux = run(["keyboard focus", "--domain", "ux"]);
  assert.equal(ux.status, 0, ux.stderr);
  assert.ok(JSON.parse(ux.stdout).count > 0, "actual UX data matches keyboard focus");
  const vue = run(["forms accessibility", "--stack", "vue"]);
  assert.equal(vue.status, 0, vue.stderr);
  const result = JSON.parse(vue.stdout);
  assert.equal(result.stack, "vue");
  assert.ok(result.count > 0, "actual Vue guidance found");
  assert.equal(run([""]).status, 2, "empty query rejected");
  assert.equal(run(["focus", "--stack", "imaginary"]).status, 2, "unknown stack rejected");
  assert.equal(run(["focus", "--max-results", "0"]).status, 2);
  const absent = run(["zzzzzxxyyqq", "--domain", "ux"]);
  assert.equal(absent.status, 0, absent.stderr);
  assert.equal(JSON.parse(absent.stdout).count, 0, "no matches are reported honestly");
  console.log("UI search passed: UX/Vue retrieval, invalid arguments and no-match behavior.");
} else {
  console.log("[skip] UI search execution: Python 3 not installed; pinned files still verified.");
}
console.log("Pinned upstream integrity and failure cases passed.");
