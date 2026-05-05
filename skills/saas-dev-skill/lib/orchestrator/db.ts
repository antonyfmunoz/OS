// lib/orchestrator/db.ts
// Postgres-backed state for orchestrator pipeline runs (D-06).
// Wraps the pipeline_runs and pipeline_pages tables defined in
// shared/design-schema.ts. State is NEVER written to JSON files.

import { drizzle as drizzlePostgres, type PostgresJsDatabase } from "drizzle-orm/postgres-js";
import { drizzle as drizzleNeon } from "drizzle-orm/neon-http";
import { neon } from "@neondatabase/serverless";
import postgres from "postgres";
import { and, eq, desc, ne } from "drizzle-orm";
import {
  pipelineRuns,
  pipelinePages,
  type ProjectConfig,
} from "../../shared/design-schema.js";
import { getDatabaseUrl } from "../env.js";

export type Phase = "spec" | "copy" | "react-gen" | "integration" | "backend" | "deploy";
export type RunStatus = "running" | "paused" | "complete" | "failed";
export type PageStatus = "pending" | "in_progress" | "complete" | "failed";

export interface PipelineRunRow {
  id: number;
  projectId: string;
  phase: string;
  status: string;
  config: string;
  startedAt: Date | null;
  updatedAt: Date | null;
  completedAt: Date | null;
}

export interface PipelinePageRow {
  id: number;
  runId: number;
  projectId: string;
  pageName: string;
  pageIndex: number;
  phase: string;
  status: string;
  error: string | null;
  output: string | null;
  startedAt: Date | null;
  completedAt: Date | null;
}

type OrchestratorDb = PostgresJsDatabase | ReturnType<typeof drizzleNeon>;

let _client: ReturnType<typeof postgres> | null = null;
let _db: OrchestratorDb | null = null;

/**
 * Use Neon HTTP driver when USE_NEON_HTTP=1 is set (works from Windows/constrained
 * environments where TCP to Neon hangs). Falls back to postgres.js TCP driver.
 */
export function getOrchestratorDb(): OrchestratorDb {
  if (_db) return _db;
  const url = getDatabaseUrl();
  if (process.env.USE_NEON_HTTP === "1") {
    const sql = neon(url);
    _db = drizzleNeon(sql) as unknown as OrchestratorDb;
  } else {
    _client = postgres(url);
    _db = drizzlePostgres(_client);
  }
  return _db;
}

/** Test-only: reset the cached client. */
export function __resetOrchestratorDbForTests(): void {
  if (_client) _client.end({ timeout: 1 }).catch(() => {});
  _client = null;
  _db = null;
}

// ─── pipeline_runs ───────────────────────────────────────────────────────────

export async function createRun(
  projectId: string,
  phase: Phase,
  config: ProjectConfig,
): Promise<PipelineRunRow> {
  const db = getOrchestratorDb();
  const [row] = await db
    .insert(pipelineRuns)
    .values({
      projectId,
      phase,
      status: "running",
      config: JSON.stringify(config),
    })
    .returning();
  return row as PipelineRunRow;
}

export async function updateRun(
  runId: number,
  patch: { phase?: Phase; status?: RunStatus; completedAt?: Date | null },
): Promise<void> {
  const db = getOrchestratorDb();
  await db
    .update(pipelineRuns)
    .set({ ...patch, updatedAt: new Date() })
    .where(eq(pipelineRuns.id, runId));
}

/**
 * Returns the most recent run for a project that is not yet `complete`. Used
 * by `resumePipeline()` to pick up where a previous session left off (D-09).
 */
export async function getLastIncompleteRun(
  projectId: string,
): Promise<PipelineRunRow | null> {
  const db = getOrchestratorDb();
  const rows = await db
    .select()
    .from(pipelineRuns)
    .where(
      and(
        eq(pipelineRuns.projectId, projectId),
        ne(pipelineRuns.status, "complete"),
      ),
    )
    .orderBy(desc(pipelineRuns.startedAt))
    .limit(1);
  return (rows[0] as PipelineRunRow | undefined) ?? null;
}

// ─── pipeline_pages ──────────────────────────────────────────────────────────

export async function createPage(input: {
  runId: number;
  projectId: string;
  pageName: string;
  pageIndex: number;
  phase: Phase;
}): Promise<PipelinePageRow> {
  const db = getOrchestratorDb();
  const [row] = await db
    .insert(pipelinePages)
    .values({
      runId: input.runId,
      projectId: input.projectId,
      pageName: input.pageName,
      pageIndex: input.pageIndex,
      phase: input.phase,
      status: "pending",
    })
    .returning();
  return row as PipelinePageRow;
}

export async function updatePage(
  pageId: number,
  patch: {
    status?: PageStatus;
    error?: string | null;
    output?: string | null;
    startedAt?: Date | null;
    completedAt?: Date | null;
  },
): Promise<void> {
  const db = getOrchestratorDb();
  await db.update(pipelinePages).set(patch).where(eq(pipelinePages.id, pageId));
}

/**
 * Returns all pages for a run+phase that have NOT yet completed. Used to
 * resume a phase from the last in-progress page (D-07, D-09, D-10).
 */
export async function getIncompletePages(
  runId: number,
  phase: Phase,
): Promise<PipelinePageRow[]> {
  const db = getOrchestratorDb();
  const rows = await db
    .select()
    .from(pipelinePages)
    .where(
      and(
        eq(pipelinePages.runId, runId),
        eq(pipelinePages.phase, phase),
        ne(pipelinePages.status, "complete"),
      ),
    )
    .orderBy(pipelinePages.pageIndex);
  return rows as PipelinePageRow[];
}

export async function getPagesForPhase(
  runId: number,
  phase: Phase,
): Promise<PipelinePageRow[]> {
  const db = getOrchestratorDb();
  const rows = await db
    .select()
    .from(pipelinePages)
    .where(and(eq(pipelinePages.runId, runId), eq(pipelinePages.phase, phase)))
    .orderBy(pipelinePages.pageIndex);
  return rows as PipelinePageRow[];
}
