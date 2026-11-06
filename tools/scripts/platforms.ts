#!/usr/bin/env node
// platforms.ts — the one reader of platforms/<p>/platform.json.
// Every script that projects something per host goes through here, so the
// platform matrix exists exactly once on disk.
import { readdir, readFile } from "node:fs/promises";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

export const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
export const PLATFORMS_DIR = join(ROOT, "platforms");

export interface PlatformConfig {
  id: string;
  label: string;
  configDir: string;
  nativeEntry: string;
  renderDir: string;
  skillsDir: string;
  agentsDir: string | null;
  agentFrontmatter: string[] | null;
}

const REQUIRED = ["id", "configDir", "nativeEntry", "renderDir", "skillsDir"] as const;

export async function loadPlatforms(): Promise<Map<string, PlatformConfig>> {
  const out = new Map<string, PlatformConfig>();
  for (const entry of await readdir(PLATFORMS_DIR, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const file = join(PLATFORMS_DIR, entry.name, "platform.json");
    const config = JSON.parse(await readFile(file, "utf-8")) as PlatformConfig;
    for (const key of REQUIRED) {
      if (!config[key]) throw new Error(`platforms/${entry.name}/platform.json is missing ${key}`);
    }
    if (config.id !== entry.name) {
      throw new Error(`platforms/${entry.name}/platform.json declares id=${config.id}`);
    }
    if (!("agentsDir" in config)) {
      throw new Error(`platforms/${entry.name}/platform.json must declare agentsDir (null when the host has no per-agent files)`);
    }
    out.set(entry.name, config);
  }
  if (out.size === 0) throw new Error(`no platform.json found under ${PLATFORMS_DIR}`);
  return out;
}

/** Hosts that can carry per-agent files, in stable order. */
export async function agentHosts(): Promise<string[]> {
  const matrix = await loadPlatforms();
  return [...matrix.values()].filter((c) => c.agentsDir !== null).map((c) => c.id).sort();
}
