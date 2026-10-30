#!/usr/bin/env node
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { cp, mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const fixture = await mkdtemp(join(tmpdir(), "hf-stats-"));

try {
  for (const directory of ["scripts", "core", "platforms", "routes/code", "skills/archive", "capabilities/rules", "schemas"]) {
    await mkdir(join(fixture, directory), { recursive: true });
  }
  await cp(join(ROOT, "scripts/stats.ts"), join(fixture, "scripts/stats.ts"));
  await writeFile(join(fixture, "package.json"), '{"type":"module","scripts":{}}');
  await writeFile(join(fixture, ".gitignore"), "output/\n");
  await writeFile(join(fixture, "模块 example.ts"), "export const value = 1;\n");
  execFileSync("git", ["init", "--quiet"], { cwd: fixture });
  execFileSync("git", ["add", "--all"], { cwd: fixture });

  const run = (): string => execFileSync(process.execPath, [join(ROOT, "node_modules/tsx/dist/cli.mjs"), join(fixture, "scripts/stats.ts")], {
    cwd: fixture, encoding: "utf-8",
  });
  const expectedCount = execFileSync("git", ["ls-files", "-z"], { cwd: fixture, encoding: "utf-8" }).split("\0").filter(Boolean).length;
  const before = run();
  await mkdir(join(fixture, "output/nested"), { recursive: true });
  await writeFile(join(fixture, "output/nested/generated.ts"), "export const generated = true;\n");
  await writeFile(join(fixture, "scratch.ts"), "export const untracked = true;\n");
  const after = run();

  assert.ok(before.includes(`| Source files (Git tracked only) | ${expectedCount} |`));
  assert.ok(after.includes(`| Source files (Git tracked only) | ${expectedCount} |`));
  assert.ok(after.includes("|  · .ts | 2 |"), "Unicode and space-containing paths retain their extension");
  assert.equal((await readFile(join(fixture, "output/nested/generated.ts"), "utf-8")), "export const generated = true;\n");
  console.log("[ok] stats counts tracked sources, handles Unicode/space paths and ignores generated/untracked files");
} finally {
  assert.ok(fixture.startsWith(resolve(tmpdir(), "hf-stats-")), "cleanup stays within the generated temp fixture");
  await rm(fixture, { recursive: true, force: true });
}
