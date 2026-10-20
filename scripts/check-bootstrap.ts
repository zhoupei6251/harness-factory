#!/usr/bin/env node
/**
 * Detect drift between the bootstrap-owned files in the working tree and what
 * `scripts/bootstrap.ts` produces from the current sources.
 *
 * Method: copy the contract's inputs into a throwaway repo root, run the REAL
 * generator there (bootstrap.ts derives its ROOT from its own file location, so
 * the copy projects into the copy and never writes to this repository), then
 * compare each artifact's bytes against the working tree. The generator is the
 * oracle — this script re-implements no projection rule, so it cannot rot into
 * the hand-maintained artifact->source table this file used to be.
 *
 * Exit 0 = match. Exit 1 = drift or generator failure.
 * Artifacts that are absent from the working tree report `[skip]` by default:
 * that is the healthy state on a machine that has not run `npm run bootstrap`
 * yet (README, "Migrating to a new machine"). Pass --require-generated to make
 * absence a failure instead; the pre-commit hook uses that mode so a checkout
 * with no generated artifacts cannot pass the gate vacuously.
 */
import { createHash } from "node:crypto";
import { existsSync } from "node:fs";
import { cp, mkdtemp, readFile, readdir, rm, stat } from "node:fs/promises";
import { join, resolve, dirname, relative } from "node:path";
import { tmpdir } from "node:os";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { BOOTSTRAP_INPUTS, GENERATED_FILES, ROUTE_MEMORY } from "./bootstrap-contract.ts";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const NODE = process.execPath;
const TSX = resolve(ROOT, "node_modules", "tsx", "dist", "cli.mjs");

let fail = 0;
const REQUIRE_GENERATED = process.argv.includes("--require-generated");

function ok(msg: string): void {
  console.log(`[ok]   ${msg}`);
}

function skip(msg: string): void {
  console.log(`[skip] ${msg}`);
}

function bad(msg: string): void {
  console.log(`[FAIL] ${msg}`);
  fail++;
}

async function sha256(path: string): Promise<string> {
  return createHash("sha256").update(await readFile(path)).digest("hex");
}

/**
 * Line endings are not part of the contract. core.autocrlf=true rewrites them on
 * checkout, so a committed artifact legitimately differs from a freshly generated
 * one by nothing but CRLF. Content-equal after stripping CR is a pass.
 */
function contentHash(text: string): string {
  return createHash("sha256").update(text.replaceAll("\r\n", "\n")).digest("hex");
}

async function exists(path: string): Promise<boolean> {
  try {
    await stat(path);
    return true;
  } catch {
    return false;
  }
}

/** Every file under `root`, repo-relative with forward slashes. */
async function manifest(root: string): Promise<Set<string>> {
  const files = new Set<string>();
  async function walk(dir: string): Promise<void> {
    for (const entry of await readdir(dir, { withFileTypes: true })) {
      const abs = join(dir, entry.name);
      if (entry.isDirectory()) await walk(abs);
      else if (entry.isFile()) files.add(relative(root, abs).replaceAll("\\", "/"));
    }
  }
  await walk(root);
  return files;
}

if (!existsSync(TSX)) {
  bad(`tsx not found at node_modules/tsx/dist/cli.mjs — run \`npm install\` first`);
  console.log("");
  console.log("check-bootstrap FAILED.");
  process.exit(1);
}

const tempRoot = await mkdtemp(join(tmpdir(), "hf-drift-check-"));

try {
  for (const input of BOOTSTRAP_INPUTS) {
    const src = resolve(ROOT, input);
    if (!(await exists(src))) {
      bad(`contract input missing from the repository: ${input}`);
      continue;
    }
    await cp(src, resolve(tempRoot, input), { recursive: true });
  }

  // Snapshot before generating: every new file afterwards is an output. Comparing
  // against the contract catches the other direction too — an output added to
  // bootstrap.ts but not to GENERATED_FILES would otherwise never be verified.
  const before = await manifest(tempRoot);

  const run = spawnSync(NODE, [TSX, resolve(tempRoot, "scripts", "bootstrap.ts"), "--platform", "all", "--route", "code"], {
    cwd: tempRoot,
    encoding: "utf-8",
  });
  if (run.status !== 0) {
    bad(`generator failed (exit ${run.status}): ${(run.stderr || run.stdout).trim().slice(0, 400)}`);
  } else {
    ok(`generator ran clean in ${tempRoot}`);

    const after = await manifest(tempRoot);
    const created = [...after].filter((p) => !before.has(p)).sort();
    const expected = new Set([...GENERATED_FILES, ROUTE_MEMORY]);
    const unlisted = created.filter((p) => !expected.has(p));
    const notWritten = GENERATED_FILES.filter((p) => !after.has(p));
    for (const p of notWritten) {
      bad(`bootstrap-contract.ts lists ${p} but scripts/bootstrap.ts did not write it`);
    }
    for (const p of unlisted) {
      bad(`scripts/bootstrap.ts wrote ${p} but bootstrap-contract.ts GENERATED_FILES does not list it`);
    }
    if (notWritten.length === 0 && unlisted.length === 0) {
      ok(`generator output set matches the contract (${created.length} files)`);
    }
  }

  if (fail === 0) {
    for (const rel of GENERATED_FILES) {
      const inTree = resolve(ROOT, rel);
      const fresh = resolve(tempRoot, rel);
      if (!(await exists(inTree))) {
        if (REQUIRE_GENERATED) bad(`${rel} (absent) — run \`npm run bootstrap\` before committing`);
        else skip(`${rel} (absent) — run \`npm run bootstrap\` to generate`);
        continue;
      }
      if (!(await exists(fresh))) {
        bad(`${rel} exists in the working tree but scripts/bootstrap.ts no longer writes it`);
        continue;
      }
      if (contentHash(await readFile(inTree, "utf-8")) === contentHash(await readFile(fresh, "utf-8"))) {
        ok(`${rel} == freshly generated`);
      } else {
        bad(`${rel} DRIFTS from a fresh bootstrap run — re-run \`npm run bootstrap\`, or revert the direct edit`);
      }
    }

    // Root MEMORY.md: must equal some route template, whichever route was bootstrapped.
    if (await exists(resolve(ROOT, ROUTE_MEMORY))) {
      const routes = (await readdir(resolve(ROOT, "routes"))).sort();
      const treeHash = await sha256(resolve(ROOT, ROUTE_MEMORY));
      const matched: string[] = [];
      for (const route of routes) {
        const template = resolve(ROOT, "routes", route, "MEMORY.md");
        if ((await exists(template)) && (await sha256(template)) === treeHash) {
          matched.push(`routes/${route}/MEMORY.md`);
        }
      }
      if (matched.length > 0) {
        ok(`${ROUTE_MEMORY} == ${matched.join(" | ")}`);
      } else {
        bad(`${ROUTE_MEMORY} matches no routes/<route>/MEMORY.md — it was edited directly, or its source changed without \`npm run bootstrap\``);
      }
    } else {
      if (REQUIRE_GENERATED) bad(`${ROUTE_MEMORY} (absent) — run \`npm run bootstrap\` before committing`);
      else skip(`${ROUTE_MEMORY} (absent) — run \`npm run bootstrap\` to generate`);
    }
  }
} finally {
  await rm(tempRoot, { recursive: true, force: true });
}

console.log("");
if (fail === 0) {
  console.log("No bootstrap drift detected.");
} else {
  console.log(`Bootstrap drift found in ${fail} file(s) — re-run \`npm run bootstrap\` or revert the artifact.`);
  process.exit(1);
}
