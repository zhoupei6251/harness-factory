#!/usr/bin/env node
import { readFile, realpath } from "node:fs/promises";
import { resolve, relative, sep, isAbsolute } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createHash } from "node:crypto";

interface SourceFile { from: string; to: string; sha256: string }
interface Source { id: string; repository: string; revision: string; files: SourceFile[] }

function safePath(value: unknown): value is string {
  return typeof value === "string" && value.length > 0 && !value.includes("\\") &&
    !value.includes(":") && value.split("/").every((part) => part !== "" && part !== "." && part !== "..");
}

/** Verify the reviewed, pinned local copies; never download or execute upstream code. */
export async function verifyUpstreams(root: string): Promise<string[]> {
  const errors: string[] = [];
  const seen = new Set<string>();
  const ids = new Set<string>();
  const canonicalRoot = await realpath(root);
  const lock = JSON.parse(await readFile(resolve(root, "references/upstreams.lock.json"), "utf8")) as { formatVersion: number; sources: Source[] };
  if (lock.formatVersion !== 1 || !Array.isArray(lock.sources) || !lock.sources.length) {
    return ["invalid upstream lock format"];
  }
  for (const source of lock.sources) {
    if (!source || typeof source.id !== "string" || ids.has(source.id)) {
      errors.push("missing or duplicate source id");
      continue;
    }
    ids.add(source.id);
    if (typeof source.repository !== "string" || !/^https:\/\/github\.com\/[\w.-]+\/[\w.-]+$/.test(source.repository) ||
        typeof source.revision !== "string" || !/^[a-f0-9]{40}$/.test(source.revision)) {
      errors.push(`${source.id}: invalid repository/revision; pin an exact Git commit`);
    }
    if (!Array.isArray(source.files) || !source.files.length) {
      errors.push(`${source.id}: no source files`);
      continue;
    }
    if (!source.files.some((file) => file && /(?:^|\/|-)LICENSE(?:\.txt)?$/i.test(file.to))) {
      errors.push(`${source.id}: license not recorded`);
    }
    for (const file of source.files) {
      if (!file || !safePath(file.from) || !safePath(file.to) || !file.to.startsWith("skills/")) {
        errors.push(`${source.id}: unsafe path`);
        continue;
      }
      if (seen.has(file.to) || typeof file.sha256 !== "string" || !/^[a-f0-9]{64}$/.test(file.sha256)) {
        errors.push(`${file.to}: duplicate path or invalid hash`);
        continue;
      }
      seen.add(file.to);
      try {
        const target = await realpath(resolve(root, file.to));
        const rel = relative(canonicalRoot, target);
        if (isAbsolute(rel) || rel === ".." || rel.startsWith(`..${sep}`)) {
          errors.push(`${file.to}: unsafe path outside repository`);
          continue;
        }
        const actual = createHash("sha256").update(await readFile(target)).digest("hex");
        if (actual !== file.sha256) errors.push(`${file.to}: hash mismatch`);
      } catch (error) {
        errors.push(`${file.to}: missing/unreadable (${(error as NodeJS.ErrnoException).code ?? String(error)})`);
      }
    }
  }
  return errors;
}

if (import.meta.url === pathToFileURL(resolve(process.argv[1] ?? "")).href) {
  try {
    const errors = await verifyUpstreams(fileURLToPath(new URL("../", import.meta.url)));
    for (const error of errors) console.error(`[FAIL] ${error}`);
    if (errors.length) process.exitCode = 1;
    else console.log("Pinned upstream files and licenses match their recorded hashes (offline).");
  } catch (error) {
    console.error(`[FAIL] ${error instanceof Error ? error.message : String(error)}`);
    process.exitCode = 1;
  }
}
