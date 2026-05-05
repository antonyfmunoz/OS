#!/usr/bin/env npx tsx
// scripts/saas-dev-build.ts
// Single entry point for the SaaS dev pipeline (v3 multi-agent architecture).
// Usage:
//   npx tsx scripts/saas-dev-build.ts           # New build
//   npx tsx scripts/saas-dev-build.ts --resume   # Resume from checkpoint
//   npx tsx scripts/saas-dev-build.ts --edit     # Edit mode

import "dotenv/config";
import { createInterface } from "node:readline/promises";
import { stdin, stdout } from "node:process";
import { PMOrchestrator } from "../lib/agents/pm-orchestrator.js";
import { ensureLivePreviewServer, type LivePreviewServer } from "../lib/react-gen/live-preview-server.js";
import type { BuildResult, EditResult } from "../lib/agents/types.js";

const BAR = "\u2501".repeat(35);

let previewServer: LivePreviewServer | null = null;

function printBanner(): void {
  console.log("");
  console.log(`${BAR}`);
  console.log("  saas-dev \u2014 v3 Multi-Agent Pipeline");
  console.log(`${BAR}`);
  console.log("");
}

function printBuildSummary(result: BuildResult): void {
  console.log("");
  console.log(`${BAR}`);
  console.log("  Build Complete");
  console.log(`${BAR}`);
  console.log("");
  console.log(`  Pages built:      ${result.pagesBuilt}`);
  console.log(`  Backend routes:   ${result.backendRoutes}`);
  console.log(`  QA passed:        ${result.qaReport?.allPassed ? "yes" : "no"}`);
  if (result.qaReport && !result.qaReport.allPassed) {
    console.log(`  Issues remaining: ${result.qaReport.remainingIssues.length}`);
  }
  if (result.errors.length > 0) {
    console.log("");
    console.log("  Errors:");
    for (const err of result.errors) {
      console.log(`    - ${err}`);
    }
  }
  console.log("");
  if (previewServer) {
    console.log(`  Preview: ${previewServer.url}`);
  }
  console.log(`${BAR}`);
  console.log("");
}

function printEditSummary(result: EditResult): void {
  console.log("");
  console.log(`${BAR}`);
  if (result.success) {
    console.log(`  Edit applied`);
    if (result.pagesEdited.length > 0) {
      console.log(`  Pages edited: ${result.pagesEdited.join(", ")}`);
    }
    if (result.qaReport) {
      console.log(`  QA passed: ${result.qaReport.allPassed ? "yes" : "no"}`);
    }
  } else {
    console.log("  Edit failed");
    for (const err of result.errors) {
      console.log(`    - ${err}`);
    }
  }
  console.log(`${BAR}`);
  console.log("");
}

async function ask(rl: ReturnType<typeof createInterface>, prompt: string): Promise<string> {
  const answer = await rl.question(prompt);
  return answer.trim();
}

async function runNewBuild(orchestrator: PMOrchestrator, autoApprove = false): Promise<void> {
  // ── Intake ────────────────────────────────────────────────────────────────
  console.log("[intake] Running intake phase...");
  const brief = await orchestrator.runIntake();

  console.log("");
  console.log(`  Product:    ${brief.productName}`);
  console.log(`  Pages:      ${brief.spec.pages.length}`);
  console.log(`  Endpoints:  ${brief.spec.endpoints?.length ?? 0}`);
  console.log("");

  // ── Approval gate ─────────────────────────────────────────────────────────
  if (!autoApprove) {
    const rl = createInterface({ input: stdin, output: stdout });
    try {
      const approval = await ask(rl, "Proceed with build? [Y/n] ");
      if (approval.toLowerCase() === "n" || approval.toLowerCase() === "no") {
        console.log("");
        console.log("Build cancelled. Run again when ready.");
        console.log("");
        return;
      }
    } finally {
      rl.close();
    }
  } else {
    console.log("[auto] --yes flag set, skipping approval gate");
  }

  // ── Build ─────────────────────────────────────────────────────────────────
  console.log("");
  console.log("[build] Starting multi-agent build...");
  const result: BuildResult = await orchestrator.runBuild(brief);
  printBuildSummary(result);
}

async function runResume(orchestrator: PMOrchestrator): Promise<void> {
  console.log("[resume] Loading existing build state...");
  const state = orchestrator.getStatus();

  if (!state || !state.brief) {
    console.error("");
    console.error("No existing build state found. Run a new build first:");
    console.error("  npx tsx scripts/saas-dev-build.ts");
    console.error("");
    process.exit(1);
  }

  console.log("");
  console.log(`  Product:           ${state.brief.productName}`);
  console.log(`  Current phase:     ${state.status.phase}`);
  console.log(`  Completed agents:  ${state.status.completedAgents.length}/${state.status.totalAgents}`);
  if (state.status.failedAgents.length > 0) {
    console.log(`  Failed agents:     ${state.status.failedAgents.join(", ")}`);
  }
  console.log(`  Checkpoints:       ${state.checkpoints.length}`);
  console.log("");

  console.log("[resume] Continuing build from last checkpoint...");
  const result: BuildResult = await orchestrator.runBuild(state.brief);
  printBuildSummary(result);
}

async function runEditMode(orchestrator: PMOrchestrator): Promise<void> {
  const state = orchestrator.getStatus();

  if (!state || !state.brief) {
    console.error("");
    console.error("No existing build state found. Run a build first before editing:");
    console.error("  npx tsx scripts/saas-dev-build.ts");
    console.error("");
    process.exit(1);
  }

  console.log(`[edit] Loaded build: ${state.brief.productName}`);
  console.log("[edit] Enter edit instructions below. Type 'exit' or 'quit' to stop.");
  console.log("");

  const rl = createInterface({ input: stdin, output: stdout });

  try {
    while (true) {
      const instruction = await ask(rl, "edit> ");

      if (!instruction) continue;
      if (instruction === "exit" || instruction === "quit") {
        console.log("");
        console.log("Edit session ended.");
        console.log("");
        break;
      }

      console.log("");
      console.log(`[edit] Applying: ${instruction}`);
      const result: EditResult = await orchestrator.runEdit(instruction);
      printEditSummary(result);
    }
  } finally {
    rl.close();
  }
}

async function shutdown(): Promise<void> {
  if (previewServer?.isNew) {
    console.log("");
    console.log("[shutdown] Stopping live preview server...");
    await previewServer.shutdown();
  }
}

async function main(): Promise<void> {
  printBanner();

  const args = process.argv.slice(2);
  const isResume = args.includes("--resume");
  const isEdit = args.includes("--edit");
  const autoApprove = args.includes("--yes") || args.includes("-y");

  const projectRoot = process.cwd();

  // ── Live preview ──────────────────────────────────────────────────────────
  console.log("[preview] Starting Vite dev server...");
  previewServer = await ensureLivePreviewServer(projectRoot);
  console.log(`Open ${previewServer.url} to watch the build live`);
  console.log("");

  // ── Handle graceful shutdown ──────────────────────────────────────────────
  process.on("SIGINT", async () => {
    console.log("");
    console.log("[signal] Caught SIGINT, shutting down...");
    await shutdown();
    process.exit(0);
  });

  // ── Orchestrator ──────────────────────────────────────────────────────────
  const orchestrator = new PMOrchestrator(projectRoot);

  if (isEdit) {
    await runEditMode(orchestrator);
  } else if (isResume) {
    await runResume(orchestrator);
  } else {
    await runNewBuild(orchestrator, autoApprove);
  }

  await shutdown();
}

main().catch(async (err: unknown) => {
  console.error("");
  console.error(`${BAR}`);
  console.error("  Pipeline failed");
  console.error(`${BAR}`);
  console.error("");
  if (err instanceof Error) {
    console.error(err.message);
    if (err.stack) {
      console.error("");
      console.error(err.stack);
    }
  } else {
    console.error(err);
  }
  await shutdown();
  process.exit(1);
});
