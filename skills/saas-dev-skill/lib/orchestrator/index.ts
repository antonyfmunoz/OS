// lib/orchestrator/index.ts
// Spine of the SaaS dev pipeline. Loads project config, detects pipeline
// state, runs phases in order with per-page checkpointing in Postgres
// (D-06, D-07, D-09, D-10), and surfaces approval gates as throwable errors.
//
// State model: ALL state lives in pipeline_runs + pipeline_pages tables. No
// JSON checkpoint files. Resume = re-call runPipeline/resumePipeline; the
// runner skips any page already marked complete and picks up where the last
// session left off.
//
// Approval gates: this orchestrator runs as a library inside Claude Code. It
// throws ApprovalRequiredError before destructive phases; the wrapping skill
// catches the error, shows the user the formatted prompt, and re-invokes
// resumePipeline() with `approved: <phase>` once the user agrees.

import { and, eq } from "drizzle-orm";
import {
  createRun,
  updateRun,
  getLastIncompleteRun,
  getOrchestratorDb,
  type Phase,
  type PipelineRunRow,
} from "./db.js";
import { pipelinePages } from "../../shared/design-schema.js";
import type { SpecOutput } from "@shared/spec-schema.js";
import { detectContext, type PipelineContext } from "./context-detector.js";
import {
  ApprovalRequiredError,
  formatApprovalRequest,
  formatApprovalSummary,
} from "./approval-gate.js";
import { runPhase, type PhaseImplementation, type PhaseRunResult } from "./phase-runner.js";
import type { ProjectConfig } from "../../shared/design-schema.js";
import { loadProjectConfig } from "../project-config.js";

const PHASE_ORDER: Phase[] = [
  "spec",
  "copy",
  "react-gen",
  "integration",
  "backend",
  "deploy",
];

const DESTRUCTIVE_PHASES = new Set<Phase>([
  "react-gen",   // writes React component files into client/src
  "integration", // writes files into client/src
  "backend",     // writes routes + DB migrations
  "deploy",      // pushes, instruments, deploys
]);

export interface RunPipelineOptions {
  /** Skip the orchestrator's auto-detection and force the start phase. */
  startPhase?: Phase;
  /** Phases the user has already approved this session. Bypasses the gate. */
  approvedPhases?: Phase[];
}

export interface OrchestratorStatus {
  runId: number | null;
  projectId: string;
  currentPhase: Phase | "complete";
  completedPhases: Phase[];
  pendingPhases: Phase[];
  context: PipelineContext;
  summary: string;
}

// ─── Phase implementation registry ───────────────────────────────────────────
//
// Each phase plugs in by registering a PhaseImplementation. Phases without a
// real implementation throw a typed error so the orchestrator can mark them
// failed-with-context instead of crashing the run.

class PhaseNotWiredError extends Error {
  constructor(phase: Phase) {
    super(
      `Phase "${phase}" is not yet wired into the orchestrator. ` +
        `Register a PhaseImplementation in lib/orchestrator/index.ts.`,
    );
    this.name = "PhaseNotWiredError";
  }
}

function notWiredImpl(phase: Phase): PhaseImplementation {
  return {
    async prepare() {
      throw new PhaseNotWiredError(phase);
    },
    async runPage() {
      throw new PhaseNotWiredError(phase);
    },
  };
}

/**
 * Phase implementation registry. Initially every entry is a "not wired" stub
 * — concrete implementations get plugged in here as each phase's library
 * surface stabilizes. The orchestrator scaffolding (state, checkpoints,
 * resume, approval gates) is fully functional regardless.
 */
export const PHASE_IMPLEMENTATIONS: Record<Phase, PhaseImplementation> = {
  spec: notWiredImpl("spec"),
  copy: notWiredImpl("copy"),
  "react-gen": notWiredImpl("react-gen"),
  integration: notWiredImpl("integration"),
  backend: notWiredImpl("backend"),
  deploy: notWiredImpl("deploy"),
};

/** Test/runtime hook for plugging real phase implementations into the registry. */
export function registerPhaseImplementation(
  phase: Phase,
  impl: PhaseImplementation,
): void {
  PHASE_IMPLEMENTATIONS[phase] = impl;
}

// ─── Public API ──────────────────────────────────────────────────────────────

/**
 * Start (or restart) a pipeline run. Detects current state, then runs each
 * pending phase in order. Throws `ApprovalRequiredError` before any
 * destructive phase unless that phase is in `options.approvedPhases`.
 */
export async function runPipeline(
  config: ProjectConfig,
  options: RunPipelineOptions = {},
): Promise<OrchestratorStatus> {
  const context = await detectContext(config);
  const startPhase = options.startPhase ?? context.suggestedPhase;
  const approved = new Set<Phase>(options.approvedPhases ?? []);

  const run = await createRun(config.projectId, startPhase, config);
  return executeFromPhase(run, startPhase, config, context, approved);
}

/**
 * Resume the most recent incomplete pipeline run for the given project.
 * Re-detects state, picks up at the run's recorded phase, and skips any
 * page already marked complete (D-09).
 */
export async function resumePipeline(
  config: ProjectConfig,
  options: { approvedPhases?: Phase[] } = {},
): Promise<OrchestratorStatus> {
  const existing = await getLastIncompleteRun(config.projectId);
  if (!existing) {
    // Nothing to resume — start fresh.
    return runPipeline(config, options);
  }
  const context = await detectContext(config);
  const approved = new Set<Phase>(options.approvedPhases ?? []);
  return executeFromPhase(
    existing,
    existing.phase as Phase,
    config,
    context,
    approved,
  );
}

/**
 * Read-only status report for a project. Does not start anything.
 */
export async function getStatus(
  config: ProjectConfig,
): Promise<OrchestratorStatus> {
  const context = await detectContext(config);
  const existing = await getLastIncompleteRun(config.projectId);
  const currentPhase: Phase | "complete" = existing
    ? (existing.phase as Phase)
    : context.suggestedPhase;
  const { completed, pending } = splitPhases(currentPhase);
  return {
    runId: existing?.id ?? null,
    projectId: config.projectId,
    currentPhase,
    completedPhases: completed,
    pendingPhases: pending,
    context,
    summary: formatApprovalSummary(completed, pending),
  };
}

// ─── Convenience: load config from a project root and run ────────────────────

export async function runPipelineFromRoot(
  projectRoot: string,
  options: RunPipelineOptions = {},
): Promise<OrchestratorStatus> {
  const config = loadProjectConfig(projectRoot);
  return runPipeline(config, options);
}

// ─── Internals ───────────────────────────────────────────────────────────────

async function executeFromPhase(
  run: PipelineRunRow,
  startPhase: Phase,
  config: ProjectConfig,
  context: PipelineContext,
  approved: Set<Phase>,
): Promise<OrchestratorStatus> {
  const startIdx = PHASE_ORDER.indexOf(startPhase);
  if (startIdx === -1) {
    throw new Error(`Unknown phase: ${startPhase}`);
  }

  for (let i = startIdx; i < PHASE_ORDER.length; i++) {
    const phase = PHASE_ORDER[i];

    // Approval gate before destructive phases (unless already approved)
    if (DESTRUCTIVE_PHASES.has(phase) && !approved.has(phase)) {
      const { completed, pending } = splitPhases(phase);
      const summary = formatApprovalSummary(completed, pending);

      // Phase C: let the phase preview itself so the user sees the plan
      // (e.g. integration's brownfield PLAN.md) inside the approval message.
      let preview = "";
      const impl = PHASE_IMPLEMENTATIONS[phase];
      if (impl.previewForApproval) {
        try {
          preview = await impl.previewForApproval(config);
        } catch (err) {
          preview = `(preview unavailable: ${(err as Error).message})`;
        }
      }

      const details = preview ? `${summary}\n\n${preview}` : summary;
      const message = formatApprovalRequest(
        phase,
        describeAction(phase),
        details,
      );
      await updateRun(run.id, { phase, status: "paused" });
      throw new ApprovalRequiredError(message, phase, describeAction(phase));
    }

    await updateRun(run.id, { phase, status: "running" });

    let result: PhaseRunResult;
    try {
      result = await runPhase(run.id, phase, PHASE_IMPLEMENTATIONS[phase], config);
    } catch (err) {
      // prepare() failed (e.g., phase not wired). Mark the run failed and
      // bubble up so the caller sees the real error.
      await updateRun(run.id, { status: "failed" });
      throw err;
    }

    if (result.failedPages.length > 0) {
      await updateRun(run.id, { status: "failed" });
      const detail = result.failedPages
        .map((f) => `  - ${f.pageName}: ${f.error}`)
        .join("\n");
      throw new Error(
        `Phase "${phase}" failed for ${result.failedPages.length} page(s):\n${detail}`,
      );
    }
  }

  await updateRun(run.id, {
    status: "complete",
    completedAt: new Date(),
  });

  // End-of-pipeline summary — pages, routes, functional vs scaffold, next steps.
  try {
    const summaryText = await buildEndOfRunSummary(config.projectId);
    // eslint-disable-next-line no-console
    console.log(summaryText);
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn(
      `[orchestrator] could not render end-of-run summary: ${(err as Error).message}`,
    );
  }

  const { completed, pending } = splitPhases("complete");
  return {
    runId: run.id,
    projectId: config.projectId,
    currentPhase: "complete",
    completedPhases: completed,
    pendingPhases: pending,
    context,
    summary: formatApprovalSummary(completed, pending),
  };
}

function splitPhases(current: Phase | "complete"): {
  completed: Phase[];
  pending: Phase[];
} {
  if (current === "complete") {
    return { completed: [...PHASE_ORDER], pending: [] };
  }
  const idx = PHASE_ORDER.indexOf(current);
  return {
    completed: PHASE_ORDER.slice(0, idx),
    pending: PHASE_ORDER.slice(idx),
  };
}

function describeAction(phase: Phase): string {
  switch (phase) {
    case "react-gen":
      return "Generate React page components and write them into client/src/pages";
    case "integration":
      return "Write generated pages into client/src and create per-page commits";
    case "backend":
      return "Generate API routes, schemas, and run database migrations";
    case "deploy":
      return "Instrument analytics and deploy the application";
    default:
      return phase;
  }
}

// ─── End-of-run summary ──────────────────────────────────────────────────────
//
// Pulls the completed spec out of pipeline_pages and renders a human-friendly
// summary: pages + routes, functional vs scaffold breakdown, dev command, and
// next steps. Called from executeFromPhase once every phase is complete.

export async function buildEndOfRunSummary(projectId: string): Promise<string> {
  const db = getOrchestratorDb();

  // Spec is the source of truth for declared pages + routes.
  const specRows = await db
    .select()
    .from(pipelinePages)
    .where(
      and(
        eq(pipelinePages.projectId, projectId),
        eq(pipelinePages.phase, "spec"),
        eq(pipelinePages.status, "complete"),
      ),
    )
    .limit(1);

  const spec: SpecOutput | null =
    specRows.length > 0 && specRows[0].output
      ? (JSON.parse(specRows[0].output) as SpecOutput)
      : null;

  // Which pages actually completed each downstream phase? A page is
  // "functional" when integration + deploy both succeeded for it.
  const integrationRows = await db
    .select()
    .from(pipelinePages)
    .where(
      and(
        eq(pipelinePages.projectId, projectId),
        eq(pipelinePages.phase, "integration"),
        eq(pipelinePages.status, "complete"),
      ),
    );
  const deployRows = await db
    .select()
    .from(pipelinePages)
    .where(
      and(
        eq(pipelinePages.projectId, projectId),
        eq(pipelinePages.phase, "deploy"),
        eq(pipelinePages.status, "complete"),
      ),
    );
  const integratedNames = new Set(integrationRows.map((r) => r.pageName));
  const deployedNames = new Set(deployRows.map((r) => r.pageName));

  const pages = spec?.pages ?? [];
  const endpoints = spec?.backendSpec?.endpoints ?? [];

  const functional: Array<{ name: string; route: string }> = [];
  const scaffold: Array<{ name: string; route: string; reason: string }> = [];

  for (const page of pages) {
    const entry = { name: page.name, route: page.route };
    if (integratedNames.has(page.name) && deployedNames.has(page.name)) {
      functional.push(entry);
    } else {
      const missing: string[] = [];
      if (!integratedNames.has(page.name)) missing.push("integration");
      if (!deployedNames.has(page.name)) missing.push("analytics");
      scaffold.push({
        ...entry,
        reason: missing.length > 0 ? `missing: ${missing.join(", ")}` : "scaffold only",
      });
    }
  }

  // Format.
  const lines: string[] = [];
  const bar = "━".repeat(64);
  lines.push("");
  lines.push(bar);
  lines.push("  ✓ PIPELINE COMPLETE");
  lines.push(bar);
  lines.push("");

  lines.push("APP PREVIEW");
  lines.push("  Run the dev server:");
  lines.push("    $ npm run dev");
  lines.push("  Then open:");
  lines.push("    http://localhost:5000");
  lines.push("");

  lines.push(`GENERATED PAGES (${pages.length})`);
  if (pages.length === 0) {
    lines.push("  (no pages in spec)");
  } else {
    const nameWidth = Math.max(
      ...pages.map((p) => p.name.length),
      10,
    );
    for (const p of pages) {
      const marker =
        integratedNames.has(p.name) && deployedNames.has(p.name) ? "✓" : "•";
      lines.push(`  ${marker} ${p.name.padEnd(nameWidth)}  ${p.route}`);
    }
  }
  lines.push("");

  lines.push("FUNCTIONAL vs SCAFFOLD");
  lines.push(`  ✓ Functional (routed + analytics wired): ${functional.length}`);
  for (const f of functional) {
    lines.push(`      ${f.route}  →  ${f.name}`);
  }
  lines.push(`  • Scaffold only:                         ${scaffold.length}`);
  for (const s of scaffold) {
    lines.push(`      ${s.route}  →  ${s.name}  (${s.reason})`);
  }
  lines.push("");

  if (endpoints.length > 0) {
    lines.push(`BACKEND ENDPOINTS (${endpoints.length})`);
    lines.push("  Generated under server/generated/ — any endpoint whose derived");
    lines.push("  storage method does not exist on the real IStorage interface is");
    lines.push("  stubbed with a 501 TODO until you implement it.");
    for (const ep of endpoints) {
      lines.push(`    ${ep.method.padEnd(6)} ${ep.path}`);
    }
    lines.push("");
  }

  lines.push("NEXT STEPS");
  lines.push("  1. Start the dev server (npm run dev) and click through the routes");
  lines.push("     listed above to visually review the generated pages.");
  lines.push("  2. Replace any 501 TODO storage stubs in server/generated/routes");
  lines.push("     with real implementations on DatabaseStorage.");
  lines.push("  3. Wire manualCaptures from .planning/output/analytics/*.injection.json");
  lines.push("     into their click/submit handlers by hand.");
  lines.push("  4. Run `npm test && npx tsc --noEmit` before committing.");
  lines.push("  5. Commit the run's artifacts and open a PR for review.");
  lines.push("");
  lines.push(bar);
  lines.push("");

  return lines.join("\n");
}

// ─── Re-exports ──────────────────────────────────────────────────────────────

export { ApprovalRequiredError } from "./approval-gate.js";
export type { PipelineContext } from "./context-detector.js";
export type { Phase, PipelineRunRow } from "./db.js";
export type { PhaseImplementation, PageWorkUnit, PhaseRunResult } from "./phase-runner.js";
