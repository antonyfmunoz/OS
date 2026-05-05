#!/usr/bin/env tsx
/**
 * saas-dev first-run setup.
 * Run from a target project root:
 *   tsx .claude/skills/saas-dev/scripts/setup.ts
 *
 * Idempotent. Never overwrites existing files.
 * Copies starter templates into the project and prints next steps.
 */
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const SKILL_ROOT = resolve(dirname(__filename), "..");
const PROJECT_ROOT = process.cwd();

type Copy = { from: string; to: string; label: string };
const copies: Copy[] = [
  {
    from: join(SKILL_ROOT, "templates", ".env.example"),
    to: join(PROJECT_ROOT, ".env.example"),
    label: ".env.example",
  },
  {
    from: join(SKILL_ROOT, "templates", "design-system.template.md"),
    to: join(PROJECT_ROOT, ".planning", "design-system.md"),
    label: ".planning/design-system.md",
  },
];

let created = 0;
let skipped = 0;

for (const c of copies) {
  if (existsSync(c.to)) {
    console.log(`skip   ${c.label} (exists)`);
    skipped++;
    continue;
  }
  mkdirSync(dirname(c.to), { recursive: true });
  copyFileSync(c.from, c.to);
  console.log(`create ${c.label}`);
  created++;
}

mkdirSync(join(PROJECT_ROOT, ".planning", "specs"), { recursive: true });

console.log(`\n${created} created, ${skipped} skipped.`);
console.log("\nNext steps:");
console.log("  1. cp .env.example .env  (if you don't already have one) and fill in keys");
console.log("  2. Edit .planning/design-system.md — replace {{...}} placeholders with your brand tokens");
console.log("  3. Add page specs to .planning/specs/ using templates/page-spec.template.md");
console.log("  4. tsx .claude/skills/saas-dev/scripts/verify.ts");
console.log("  5. In Claude Code, invoke the orchestrator skill to run the pipeline");
