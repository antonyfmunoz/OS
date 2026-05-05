// lib/orchestrator/context-detector.ts
// Determines where in the pipeline a project currently sits, so the
// orchestrator can skip phases that have already been completed.
//
// Detection draws from BOTH the database (pipeline_pages, dm_pages) AND the
// filesystem (presence of .planning/specs/, generated client/src/pages files,
// PostHog setup). DB is the source of truth where it has rows; filesystem is
// the fallback for projects that ran the skill before orchestrator state was
// recorded.

import fs from "node:fs";
import path from "node:path";
import { eq, and } from "drizzle-orm";
import { dmPages, pipelinePages } from "../../shared/design-schema.js";
import type { ProjectConfig } from "../../shared/design-schema.js";
import { getOrchestratorDb } from "./db.js";
import type { Phase } from "./db.js";

export interface PipelineContext {
  hasSpec: boolean;
  hasApprovedUI: boolean;
  hasIntegratedCode: boolean;
  hasBackend: boolean;
  hasAnalytics: boolean;
  /** The phase the orchestrator should start (or resume) at. */
  suggestedPhase: Phase;
}

export async function detectContext(
  config: ProjectConfig,
): Promise<PipelineContext> {
  const projectRoot = path.resolve(config.repoPath);
  const db = getOrchestratorDb();

  // ─── Spec ────────────────────────────────────────────────────────────────
  const specsDir = path.join(projectRoot, ".planning", "specs");
  const hasSpec =
    fs.existsSync(specsDir) &&
    fs.readdirSync(specsDir).some((f) => f.endsWith(".json"));

  // ─── Approved UI ────────────────────────────────────────────────────────
  // Source of truth: dm_pages with approvedAt set for this project
  const approvedRows = await db
    .select()
    .from(dmPages)
    .where(eq(dmPages.projectId, config.projectId));
  const hasApprovedUI = approvedRows.some((r) => r.approvedAt !== null);

  // ─── Integrated code ────────────────────────────────────────────────────
  // Source of truth: pipeline_pages rows with phase=integration AND status=complete
  const integrationRows = await db
    .select()
    .from(pipelinePages)
    .where(
      and(
        eq(pipelinePages.projectId, config.projectId),
        eq(pipelinePages.phase, "integration"),
      ),
    );
  const hasIntegratedCode = integrationRows.some((r) => r.status === "complete");

  // ─── Backend ────────────────────────────────────────────────────────────
  const backendRows = await db
    .select()
    .from(pipelinePages)
    .where(
      and(
        eq(pipelinePages.projectId, config.projectId),
        eq(pipelinePages.phase, "backend"),
      ),
    );
  const hasBackend = backendRows.some((r) => r.status === "complete");

  // ─── Analytics ──────────────────────────────────────────────────────────
  // Filesystem detection — PostHog provider wired into client entry point
  const clientEntries = [
    path.join(projectRoot, config.clientSrcPath, "main.tsx"),
    path.join(projectRoot, config.clientSrcPath, "App.tsx"),
  ];
  const hasAnalytics = clientEntries.some((p) => {
    if (!fs.existsSync(p)) return false;
    try {
      const text = fs.readFileSync(p, "utf-8");
      return /posthog-js|PostHogProvider/i.test(text);
    } catch {
      return false;
    }
  });

  // ─── Suggested phase ────────────────────────────────────────────────────
  let suggestedPhase: Phase = "spec";
  if (hasSpec) suggestedPhase = "react-gen";
  if (hasApprovedUI) suggestedPhase = "integration";
  if (hasIntegratedCode) suggestedPhase = "backend";
  if (hasBackend) suggestedPhase = "deploy";
  if (hasAnalytics && hasBackend) suggestedPhase = "deploy"; // already at last phase

  return {
    hasSpec,
    hasApprovedUI,
    hasIntegratedCode,
    hasBackend,
    hasAnalytics,
    suggestedPhase,
  };
}
