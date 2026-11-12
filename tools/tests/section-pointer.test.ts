#!/usr/bin/env node
// A `<file>.md § <section>` pointer must name a heading that exists. Regression
// for 2026-11-12: the project CLAUDE.md ranked `guides/routing.md § 阶段门禁`
// above every other doc, but routing.md never had that section, so the rule that
// won every conflict resolved to nothing while a contradictory gate shipped next
// to it.
//
// Drives the pure module rather than structure-audit.ts: that script audits a
// whole repo at import time, and this repo carries no section pointer today, so
// an end-to-end test would prove nothing.
import assert from "node:assert/strict";
import { SECTION_PTR, findDanglingPointers, hasSection } from "../scripts/section-pointer.ts";

// Matching a heading must tolerate the hash level and the spacing the docs use.
assert.ok(hasSection("# routing\n\n## 阶段门禁（不可跳过）\n", "阶段门禁"), "CJK section matches");
assert.ok(hasSection("## Multi word section\n", "Multiword"), "whitespace is not part of the identity");
assert.ok(!hasSection("## About\n\nNo gate here.\n", "阶段门禁"), "an absent section does not match");
assert.ok(!hasSection("Body text mentions 阶段门禁 but no heading does.\n", "阶段门禁"), "body text is not a heading");

const docs = [
  { path: "ENTRY.md", text: "Read `guides/routing.md` § About first.\n" },
  { path: "guides/INDEX.md", text: "See `guides/routing.md` § 阶段门禁 and `guides/gone.md` § Anything.\n" },
];
const files: Record<string, string> = { "guides/routing.md": "# routing\n\n## About\n\nNo gate here.\n" };
const read = (p: string): string | null => files[p] ?? null;

const found = findDanglingPointers(docs, read);
assert.equal(found.length, 2, "one missing section and one missing file, neither dropped silently");
assert.deepEqual(found[0], {
  doc: "guides/INDEX.md",
  target: "guides/routing.md",
  section: "阶段门禁",
  reason: "missing-section",
});
assert.deepEqual(found[1], {
  doc: "guides/INDEX.md",
  target: "guides/gone.md",
  section: "Anything",
  reason: "missing-file",
});

// A healthy tree reports nothing, and the pointer count the audit prints is the
// same regex, so a doc that stops matching cannot look clean by being skipped.
assert.deepEqual(findDanglingPointers([docs[0]], read), []);
assert.equal([...docs[1].text.matchAll(SECTION_PTR)].length, 2);

console.log("section-pointer: all assertions passed");
