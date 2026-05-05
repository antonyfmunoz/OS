#!/usr/bin/env npx tsx
// scripts/saas-dev-fix.ts
// Targeted fix script — re-runs only failed or low-quality phases.
// Skips: Product Intel, Architecture, Copy (artifacts exist and are usable)
// Re-runs: Design System, Component Library, failing pages, QA
//
// Usage:
//   npx tsx scripts/saas-dev-fix.ts           # Interactive (prompts before running)
//   npx tsx scripts/saas-dev-fix.ts --yes     # Auto-approve

import "dotenv/config";
import { execSync } from "node:child_process";
import { createInterface } from "node:readline/promises";
import { stdin, stdout } from "node:process";
import pLimit from "p-limit";
import { ArtifactStore } from "../lib/agents/artifact-store.js";
import { AgentRunner } from "../lib/agents/agent-runner.js";
import { runDesignSystemAgent } from "../lib/agents/design-system-agent.js";
import { runComponentLibraryAgent } from "../lib/agents/component-library-agent.js";
import { runPageAgent } from "../lib/agents/page-agent.js";
import { runQAAgent } from "../lib/agents/qa-agent.js";
import type { PageOutput, QAReport } from "../lib/agents/types.js";
import type { PageSpecFull } from "@shared/spec-schema.js";

const BAR = "\u2501".repeat(50);
const PAGE_CONCURRENCY = 3;

// Pages that need re-generation (compiled=false or score < 0.5)
const PAGES_TO_FIX = [
  "CommandCenter",
  "PortfolioList",
  "PortfolioDetail",
  "AgentChat",
  "Workflows",
  "TaskBoard",
];

function printBanner(): void {
  console.log("");
  console.log(BAR);
  console.log("  saas-dev fix \u2014 Targeted Re-run");
  console.log(BAR);
  console.log("");
}

function printCostEstimate(): void {
  console.log("Estimated Claude API calls:");
  console.log("  Design System Agent:    2-3 calls");
  console.log("  Component Library:      7-10 calls (one per component)");
  console.log(`  ${PAGES_TO_FIX.length} Page Agents:         ${PAGES_TO_FIX.length * 2}-${PAGES_TO_FIX.length * 3} calls (2-3 per page with fixes)`);
  console.log("  QA Agent:              3-5 calls");
  console.log("  \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500");
  const low = 2 + 7 + PAGES_TO_FIX.length * 2 + 3;
  const high = 3 + 10 + PAGES_TO_FIX.length * 3 + 5;
  console.log(`  Total estimate:        ${low}-${high} calls (~$0.50-$1.50 at Sonnet pricing)`);
  console.log("");
}

function countTscErrors(projectRoot: string): number {
  try {
    execSync("npx tsc --noEmit", { cwd: projectRoot, stdio: "pipe", timeout: 120_000 });
    return 0;
  } catch (err) {
    const stderr = err instanceof Error && "stderr" in err
      ? String((err as { stderr: unknown }).stderr)
      : "";
    return (stderr.match(/error TS/g) ?? []).length;
  }
}

async function main(): Promise<void> {
  printBanner();

  const args = process.argv.slice(2);
  const autoApprove = args.includes("--yes") || args.includes("-y");
  const projectRoot = process.cwd();
  const store = new ArtifactStore(projectRoot);
  const runner = new AgentRunner(projectRoot);

  // ── 1. Verify existing artifacts ──────────────────────────────────────────

  console.log("[check] Verifying existing artifacts...");
  const brief = store.getBrief();
  const architecture = store.getArchitecture();
  const projectCopy = store.getProjectCopy();
  const productInsights = store.getProductInsights();

  const missing: string[] = [];
  if (!brief) missing.push("brief (run full build first)");
  if (!architecture) missing.push("architecture");
  if (!projectCopy) missing.push("project-copy");

  if (missing.length > 0) {
    console.error("");
    console.error("Missing required artifacts — cannot fix without a prior build:");
    for (const m of missing) console.error(`  - ${m}`);
    console.error("");
    console.error("Run a full build first:");
    console.error("  npx tsx scripts/saas-dev-build.ts");
    console.error("");
    process.exit(1);
  }

  console.log("  \u2713 brief");
  console.log("  \u2713 architecture");
  console.log("  \u2713 project-copy");
  console.log(`  ${productInsights ? "\u2713" : "\u2717"} product-insights (${productInsights ? "found" : "will use defaults"})`);
  console.log("");

  // Identify pages to fix
  const existingPages = store.getPageOutputs() ?? [];
  const failingPages = existingPages.filter(
    (p) => !p.compiledClean || p.reviewScore < 0.5,
  );
  const pagesToFix = PAGES_TO_FIX.length > 0
    ? PAGES_TO_FIX
    : failingPages.map((p) => p.pageName);

  console.log(`[check] Pages to fix: ${pagesToFix.length}`);
  for (const name of pagesToFix) {
    const existing = existingPages.find((p) => p.pageName === name);
    const status = existing
      ? `compiled=${existing.compiledClean} score=${existing.reviewScore}`
      : "not built";
    console.log(`  - ${name} (${status})`);
  }
  console.log("");

  // ── 2. Cost estimate and approval ─────────────────────────────────────────

  printCostEstimate();

  if (!autoApprove) {
    const rl = createInterface({ input: stdin, output: stdout });
    try {
      const answer = await rl.question("Continue? [Y/n] ");
      if (answer.trim().toLowerCase() === "n" || answer.trim().toLowerCase() === "no") {
        console.log("Aborted.");
        return;
      }
    } finally {
      rl.close();
    }
  } else {
    console.log("[auto] --yes flag set, skipping approval");
  }

  // ── 3. Pre-fix tsc error count ────────────────────────────────────────────

  console.log("");
  console.log("[tsc] Counting TypeScript errors before fix...");
  const errorsBefore = countTscErrors(projectRoot);
  console.log(`  Errors before: ${errorsBefore}`);
  console.log("");

  const errors: string[] = [];

  // ── 4. Re-run Design System Agent ─────────────────────────────────────────

  console.log(BAR);
  console.log("  Phase 1: Design System");
  console.log(BAR);
  console.log("");

  const insights = productInsights ?? {
    productCategory: "saas",
    targetUserProfile: brief!.targetUsers.join(", ") || "general users",
    competitiveIntel: null,
    designRecommendations: [],
    copyRecommendations: [],
    architectureRecommendations: [],
    marketPositioning: brief!.productDescription,
  };

  const dsResult = await runner.run(
    () => runDesignSystemAgent(brief!, insights, store),
    { name: "design-system", onProgress: (msg) => console.log(`  [ds] ${msg}`) },
  );

  if (dsResult.status === "failed") {
    errors.push(`Design System Agent failed: ${dsResult.error}`);
    console.error(`  \u2717 Design System failed: ${dsResult.error}`);
  } else {
    const ds = store.getDesignSystem();
    console.log(`  \u2713 Design System: ${ds?.aesthetic ?? "generated"}`);

    // Verify primary color
    if (ds) {
      const primary = ds.tokens.colors.primary;
      console.log(`  Primary color: ${primary}`);
    }
  }
  console.log("");

  // ── 5. Re-run Component Library Agent ─────────────────────────────────────

  console.log(BAR);
  console.log("  Phase 2: Component Library");
  console.log(BAR);
  console.log("");

  const compResult = await runner.run(
    () => runComponentLibraryAgent(brief!, store),
    { name: "component-library", onProgress: (msg) => console.log(`  [comp] ${msg}`) },
  );

  if (compResult.status === "failed") {
    errors.push(`Component Library Agent failed: ${compResult.error}`);
    console.error(`  \u2717 Component Library failed: ${compResult.error}`);
  } else {
    const paths = store.getComponentPaths() ?? {};
    console.log(`  \u2713 Built ${Object.keys(paths).length} components`);
  }
  console.log("");

  // ── 6. Re-run failing pages ───────────────────────────────────────────────

  console.log(BAR);
  console.log(`  Phase 3: Fix ${pagesToFix.length} Pages`);
  console.log(BAR);
  console.log("");

  const allPageSpecs = brief!.spec.pages as PageSpecFull[];
  const pageSpecsToFix = pagesToFix
    .map((name) => allPageSpecs.find((p) => p.name === name))
    .filter((p): p is PageSpecFull => p !== undefined);

  if (pageSpecsToFix.length === 0) {
    console.log("  No matching page specs found in brief. Skipping page re-generation.");
  } else {
    const limit = pLimit(PAGE_CONCURRENCY);
    let pagesFixed = 0;

    const pagePromises = pageSpecsToFix.map((pageSpec) =>
      limit(async () => {
        console.log(`  [page] Starting ${pageSpec.name}...`);
        try {
          const output = await runPageAgent(pageSpec, brief!, store);
          const status = output.compiledClean ? "\u2713" : "\u2717";
          console.log(`  ${status} ${output.pageName}: compiled=${output.compiledClean} score=${output.reviewScore}`);
          if (output.compiledClean) pagesFixed++;
          return output;
        } catch (err) {
          const msg = err instanceof Error ? err.message : String(err);
          console.error(`  \u2717 ${pageSpec.name}: ${msg}`);
          errors.push(`Page ${pageSpec.name} failed: ${msg}`);
          return null;
        }
      }),
    );

    await Promise.all(pagePromises);
    console.log(`  Fixed: ${pagesFixed}/${pageSpecsToFix.length}`);
  }
  console.log("");

  // ── 7. Run QA Agent ───────────────────────────────────────────────────────

  console.log(BAR);
  console.log("  Phase 4: QA");
  console.log(BAR);
  console.log("");

  const qaResult = await runner.run(
    () => runQAAgent(store),
    { name: "qa", onProgress: (msg) => console.log(`  [qa] ${msg}`) },
  );

  const qaReport = qaResult.data as QAReport | null;
  if (qaReport) {
    console.log(`  QA passed: ${qaReport.allPassed}`);
    console.log(`  Total issues: ${qaReport.totalIssues}`);
    console.log(`  Issues fixed: ${qaReport.issuesFixed}`);
    console.log(`  Remaining: ${qaReport.remainingIssues.length}`);
    if (!qaReport.allPassed) {
      for (const issue of qaReport.remainingIssues.slice(0, 5)) {
        console.log(`    - [${issue.severity}] ${issue.category}: ${issue.message.slice(0, 100)}`);
      }
    }
  }
  console.log("");

  // ── 8. Post-fix tsc error count ───────────────────────────────────────────

  console.log("[tsc] Counting TypeScript errors after fix...");
  const errorsAfter = countTscErrors(projectRoot);
  console.log(`  Errors before: ${errorsBefore}`);
  console.log(`  Errors after:  ${errorsAfter}`);
  console.log(`  Delta:         ${errorsAfter - errorsBefore > 0 ? "+" : ""}${errorsAfter - errorsBefore}`);
  console.log("");

  // ── 9. Final summary ──────────────────────────────────────────────────────

  console.log(BAR);
  if (errors.length === 0 && (qaReport?.allPassed ?? false)) {
    console.log("  Fix complete \u2014 all phases passed");
  } else {
    console.log("  Fix complete \u2014 with issues");
    if (errors.length > 0) {
      console.log("");
      console.log("  Errors:");
      for (const err of errors) {
        console.log(`    - ${err}`);
      }
    }
  }
  console.log(BAR);
  console.log("");
}

main().catch((err: unknown) => {
  console.error("");
  console.error(BAR);
  console.error("  Fix script failed");
  console.error(BAR);
  console.error("");
  if (err instanceof Error) {
    console.error(err.message);
    if (err.stack) console.error(err.stack);
  } else {
    console.error(err);
  }
  process.exit(1);
});
