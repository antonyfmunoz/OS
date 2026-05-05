// lib/orchestrator/phase-runner.ts
// Generic per-page phase runner. Knows nothing about what each phase actually
// DOES — it accepts a `PhaseImplementation` and handles the bookkeeping:
//
//   1. Ensure pipeline_pages rows exist for every page in the work list
//   2. Iterate pages in order, skipping any already marked complete (D-09)
//   3. Mark each page in_progress, run the implementation, persist output
//   4. On success → status=complete, output=<json>
//   5. On failure → status=failed, error=<message>; surface to caller (D-10)
//
// The orchestrator's index.ts wires concrete implementations into a registry
// keyed by phase name.

import {
  createPage,
  getPagesForPhase,
  updatePage,
  type Phase,
  type PipelinePageRow,
} from "./db.js";
import type { ProjectConfig } from "../../shared/design-schema.js";

export interface PageWorkUnit {
  pageName: string;
  pageIndex: number;
  /** Free-form payload passed straight through to PhaseImplementation.runPage. */
  input: unknown;
}

export type PageDecision =
  | { action: "continue" }
  | { action: "continue-with-feedback"; feedback: string }
  | { action: "retry"; feedback: string }
  | { action: "skip" };

export interface PageCompleteContext {
  pageName: string;
  pageIndex: number;
  output: unknown;
}

export interface PhaseImplementation {
  /** Compute the work units for this phase from the project state.
   *  `runId` is passed so implementations can query pipeline_pages to skip
   *  already-complete pages when batching expensive work (e.g. parallel
   *  React generation in react-gen, parallel sub-agents in integration). */
  prepare(
    config: ProjectConfig,
    runId?: number,
  ): Promise<PageWorkUnit[]>;

  /** Execute one page worth of work. Return value is JSON-serialized into the
   *  pipeline_pages.output column. Throw on failure — phase-runner will mark
   *  the page failed and surface the error. */
  runPage(input: unknown, config: ProjectConfig): Promise<unknown>;

  /**
   * Optional. Called by the orchestrator BEFORE the destructive-phase
   * approval gate so the user can see exactly what the phase intends to do.
   * Should be cheap (no LLM, no network) and side-effect free aside from
   * writing planning artifacts the user can re-read. Return a human-readable
   * string that gets appended to the approval message.
   */
  previewForApproval?(config: ProjectConfig): Promise<string>;

  /**
   * Optional. Called after each page completes successfully. Returns a
   * PageDecision controlling what happens next:
   * - "continue": proceed to next page (default if hook absent)
   * - "retry": re-run this page (implementation should inject user feedback)
   * - "skip": mark page as skipped and move on
   *
   * The hook receives the page context and output so it can display review
   * information to the user (e.g. screenshots, scores, preview links).
   */
  onPageComplete?(
    context: PageCompleteContext,
    config: ProjectConfig,
  ): Promise<PageDecision>;
}

export interface PhaseRunResult {
  phase: Phase;
  totalPages: number;
  completedPages: number;
  failedPages: { pageName: string; error: string }[];
}

export async function runPhase(
  runId: number,
  phase: Phase,
  impl: PhaseImplementation,
  config: ProjectConfig,
): Promise<PhaseRunResult> {
  // 1. Compute work units for this phase (passing runId so implementations
  //    can skip already-complete pages when batching expensive work).
  const workUnits = await impl.prepare(config, runId);

  // 2. Reconcile work units against existing pipeline_pages rows. Pages that
  //    already exist are reused (preserving status); missing pages are inserted
  //    as pending. This makes the runner idempotent across resumes.
  const existing = await getPagesForPhase(runId, phase);
  const existingByIndex = new Map(existing.map((r) => [r.pageIndex, r]));

  const pageRows: PipelinePageRow[] = [];
  for (const unit of workUnits) {
    const found = existingByIndex.get(unit.pageIndex);
    if (found) {
      pageRows.push(found);
    } else {
      const created = await createPage({
        runId,
        projectId: config.projectId,
        pageName: unit.pageName,
        pageIndex: unit.pageIndex,
        phase,
      });
      pageRows.push(created);
    }
  }

  // 3. Iterate. Skip pages already marked complete (D-09).
  const failed: { pageName: string; error: string }[] = [];
  let completed = 0;

  // Accumulated user feedback from 'continue-with-feedback' decisions.
  // Persists across pages so corrections carry forward to all remaining pages.
  const runningFeedback: string[] = [];

  for (let i = 0; i < pageRows.length; i++) {
    const row = pageRows[i];
    const unit = workUnits[i];

    if (row.status === "complete") {
      completed++;
      continue;
    }

    // Inject accumulated feedback into the work unit input so downstream
    // phase implementations can read it without knowing about the runner.
    if (runningFeedback.length > 0) {
      (unit.input as Record<string, unknown>).accumulatedFeedback =
        runningFeedback.join("\n");
    }

    await updatePage(row.id, {
      status: "in_progress",
      startedAt: new Date(),
      error: null,
    });

    try {
      let output = await impl.runPage(unit.input, config);
      let decision: PageDecision = { action: "continue" };

      if (impl.onPageComplete) {
        decision = await impl.onPageComplete(
          { pageName: unit.pageName, pageIndex: unit.pageIndex, output },
          config,
        );

        if (decision.action === "retry") {
          // Re-run the page once with user feedback injected.
          (unit.input as Record<string, unknown>).accumulatedFeedback =
            [...runningFeedback, decision.feedback].join("\n");
          output = await impl.runPage(unit.input, config);
          // After retry, always continue — no infinite loops.
        }

        if (decision.action === "continue-with-feedback") {
          runningFeedback.push(decision.feedback);
        }

        if (decision.action === "skip") {
          await updatePage(row.id, {
            status: "complete",
            output: JSON.stringify({ skipped: true }),
            completedAt: new Date(),
          });
          completed++;
          continue;
        }
      }

      await updatePage(row.id, {
        status: "complete",
        output: JSON.stringify(output ?? null),
        completedAt: new Date(),
      });
      completed++;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      await updatePage(row.id, {
        status: "failed",
        error: message,
        completedAt: new Date(),
      });
      failed.push({ pageName: unit.pageName, error: message });
    }
  }

  return {
    phase,
    totalPages: pageRows.length,
    completedPages: completed,
    failedPages: failed,
  };
}
