#!/usr/bin/env tsx
/**
 * saas-dev health check.
 * Run: tsx .claude/skills/saas-dev/scripts/verify.ts
 *
 * Reports on:
 *   1. Required environment variables
 *   2. Template files present
 *   3. Skill files present
 *   4. Framework detection (React + Vite + Tailwind + shadcn monorepo)
 *   5. MCP availability is NOT checked here — MCPs are discovered inside
 *      interactive Claude Code sessions, not headless tsx runs.
 */
import { existsSync, readFileSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const SKILL_ROOT = resolve(dirname(__filename), "..");
const PROJECT_ROOT = process.cwd();

type Check = { name: string; ok: boolean; detail?: string };
const checks: Check[] = [];

function check(name: string, ok: boolean, detail?: string) {
  checks.push({ name, ok, detail });
}

// 1. Env vars
const requiredEnv = ["ANTHROPIC_API_KEY", "STITCH_API_KEY", "DATABASE_URL"];
const optionalEnv = ["OPENAI_API_KEY", "GEMINI_API_KEY"];

// Load .env if present (no dotenv dependency — parse manually)
const envPath = join(PROJECT_ROOT, ".env");
if (existsSync(envPath)) {
  const lines = readFileSync(envPath, "utf8").split(/\r?\n/);
  for (const line of lines) {
    const m = line.match(/^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*?)\s*$/);
    if (m && !process.env[m[1]]) process.env[m[1]] = m[2].replace(/^["']|["']$/g, "");
  }
}

for (const key of requiredEnv) {
  check(`env:${key}`, Boolean(process.env[key]), process.env[key] ? "set" : "MISSING — required");
}
for (const key of optionalEnv) {
  check(`env:${key}`, true, process.env[key] ? "set" : "unset (optional)");
}

// 2. Templates
const templates = [
  "templates/.env.example",
  "templates/design-system.template.md",
  "templates/page-spec.template.md",
];
for (const t of templates) {
  check(`template:${t}`, existsSync(join(SKILL_ROOT, t)));
}

// 3. Skills
const skills = [
  "orchestrator",
  "spec-parser",
  "detect-framework",
  "ui-generator",
  "integrator",
  "backend-wirer",
  "analytics-delivery",
];
for (const s of skills) {
  const p = join(SKILL_ROOT, "skills", s, "SKILL.md");
  check(`skill:${s}`, existsSync(p));
}

// 4. Framework detection (best effort)
const pkgPath = join(PROJECT_ROOT, "package.json");
if (existsSync(pkgPath)) {
  const pkg = JSON.parse(readFileSync(pkgPath, "utf8"));
  const deps = { ...(pkg.dependencies ?? {}), ...(pkg.devDependencies ?? {}) };
  const need = ["react", "vite", "tailwindcss"];
  const missing = need.filter((d) => !deps[d]);
  check(
    "framework:react-vite-tailwind",
    missing.length === 0,
    missing.length ? `missing deps: ${missing.join(", ")}` : "detected",
  );
  check(
    "framework:monorepo-layout",
    existsSync(join(PROJECT_ROOT, "client")) &&
      existsSync(join(PROJECT_ROOT, "server")) &&
      existsSync(join(PROJECT_ROOT, "shared")),
    "expects client/ server/ shared/",
  );
} else {
  check("framework:react-vite-tailwind", false, "no package.json at cwd");
}

// 5. Design system present?
check(
  "design-system",
  existsSync(join(PROJECT_ROOT, ".planning", "design-system.md")),
  ".planning/design-system.md — copy templates/design-system.template.md to bootstrap",
);

// Report
const pad = (s: string, n: number) => s + " ".repeat(Math.max(0, n - s.length));
let fail = 0;
console.log("\nsaas-dev verify\n" + "-".repeat(60));
for (const c of checks) {
  const mark = c.ok ? "OK  " : "FAIL";
  if (!c.ok) fail++;
  console.log(`${mark}  ${pad(c.name, 40)}  ${c.detail ?? ""}`);
}
console.log("-".repeat(60));
console.log(fail === 0 ? "All checks passed." : `${fail} check(s) failed.`);
process.exit(fail === 0 ? 0 : 1);
