import { pgTable, text, serial, integer, timestamp, varchar, numeric, uniqueIndex } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

// ─── SECTION 1: Design Memory Tables ─────────────────────────────────────────

export const dmProjects = pgTable("dm_projects", {
  id: serial("id").primaryKey(),
  projectId: text("project_id").notNull().unique(),
  name: text("name").notNull(),
  repoPath: text("repo_path").notNull(),
  framework: text("framework").notNull(),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

// IMMUTABLE REVISION MODEL: Each token update creates a NEW row with incremented version. Rows are never updated. (D-03)
export const dmTokens = pgTable("dm_tokens", {
  id: serial("id").primaryKey(),
  projectId: text("project_id").notNull(),
  version: integer("version").notNull().default(1),
  colorPrimary: varchar("color_primary", { length: 9 }),
  colorSecondary: varchar("color_secondary", { length: 9 }),
  colorBackground: varchar("color_background", { length: 9 }),
  colorSurface: varchar("color_surface", { length: 9 }),
  colorText: varchar("color_text", { length: 9 }),
  colorAccent: varchar("color_accent", { length: 9 }),
  typeFontFamily: text("type_font_family"),
  typeSizeBase: numeric("type_size_base"),
  typeScaleRatio: numeric("type_scale_ratio"),
  spacingUnit: numeric("spacing_unit"),
  borderRadius: numeric("border_radius"),
  shadowStyle: text("shadow_style"),
  componentDirection: text("component_direction"),
  createdAt: timestamp("created_at").defaultNow(),
}, (table) => ({
  projectVersionIdx: uniqueIndex("dm_tokens_project_version_idx").on(table.projectId, table.version),
}));

// DESIGN.md export storage — one row per export, immutable, versioned per project (D-08)
export const dmDesignMd = pgTable("dm_design_md", {
  id: serial("id").primaryKey(),
  projectId: text("project_id").notNull(),
  version: integer("version").notNull(),
  content: text("content").notNull(),
  exportedAt: timestamp("exported_at").notNull().defaultNow(),
});

export const dmPages = pgTable("dm_pages", {
  id: serial("id").primaryKey(),
  projectId: text("project_id").notNull(),
  pageName: text("page_name").notNull(),
  pageSlug: text("page_slug").notNull(),
  purpose: text("purpose"),
  approvedAt: timestamp("approved_at"),
  tokenVersionRef: integer("token_version_ref"),
  screenshotUrl: text("screenshot_url"),
  createdAt: timestamp("created_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

export const dmPatterns = pgTable("dm_patterns", {
  id: serial("id").primaryKey(),
  projectId: text("project_id").notNull(),
  name: text("name").notNull(),
  variant: text("variant"),
  propsShape: text("props_shape"),
  usageContext: text("usage_context"),
  shadcnComponent: text("shadcn_component"),
  pageSlugRef: text("page_slug_ref"),
  createdAt: timestamp("created_at").defaultNow(),
});

// ─── SECTION 2: Pipeline State Tables ────────────────────────────────────────

// Pipeline state persisted in Neon PostgreSQL only — no JSON files in repo (D-06)

export const pipelineRuns = pgTable("pipeline_runs", {
  id: serial("id").primaryKey(),
  projectId: text("project_id").notNull(),
  phase: text("phase").notNull(),
  status: text("status").notNull().default("running"),
  config: text("config").notNull(),
  startedAt: timestamp("started_at").defaultNow(),
  updatedAt: timestamp("updated_at").defaultNow(),
  completedAt: timestamp("completed_at"),
});

export const pipelinePages = pgTable("pipeline_pages", {
  id: serial("id").primaryKey(),
  runId: integer("run_id").notNull(),
  projectId: text("project_id").notNull(),
  pageName: text("page_name").notNull(),
  pageIndex: integer("page_index").notNull(),
  phase: text("phase").notNull(),
  status: text("status").notNull().default("pending"),
  error: text("error"),
  output: text("output"),
  startedAt: timestamp("started_at"),
  completedAt: timestamp("completed_at"),
}, (table) => ({
  runPagePhaseIdx: uniqueIndex("pipeline_pages_run_page_phase_idx").on(table.runId, table.pageIndex, table.phase),
}));

// ─── SECTION 3: Insert Schemas (drizzle-zod) ─────────────────────────────────

export const insertDmProjectSchema = createInsertSchema(dmProjects);
export const insertDmTokenSchema = createInsertSchema(dmTokens);
export const insertDmPageSchema = createInsertSchema(dmPages);
export const insertDmPatternSchema = createInsertSchema(dmPatterns);
export const insertDmDesignMdSchema = createInsertSchema(dmDesignMd);
export const insertPipelineRunSchema = createInsertSchema(pipelineRuns);
export const insertPipelinePageSchema = createInsertSchema(pipelinePages);

// ─── SECTION 4: Zod Pipeline State Contracts (D-08) ──────────────────────────

// Pipeline state contracts — each phase defines its own I/O shape (D-08)

export const PageStateSchema = z.object({
  pageName: z.string(),
  pageIndex: z.number().int().min(0),
  status: z.enum(["pending", "in_progress", "complete", "failed"]),
  error: z.string().nullable().default(null),
  output: z.unknown().nullable().default(null),
});

export const ProjectConfigSchema = z.object({
  projectId: z.string().min(1),
  repoPath: z.string().min(1),
  framework: z.enum(["react-vite-tailwind-shadcn"]),
  // Path overrides — defaults work for the standard project layout
  designSystemPath: z.string().default(".planning/design-system.md"),
  outputPath: z.string().default(".planning/output"),
  clientSrcPath: z.string().default("client/src"),
  serverPath: z.string().default("server"),
  defaultBranch: z.string().default("main"),
  featureBranchPrefix: z.string().default("feature/"),
});

export const PipelineRunSchema = z.object({
  projectId: z.string().min(1),
  phase: z.enum(["spec", "copy", "react-gen", "integration", "backend", "deploy"]),
  status: z.enum(["running", "paused", "complete", "failed"]).default("running"),
  config: z.lazy(() => ProjectConfigSchema),
});

/** @deprecated Use SpecOutputSchema from shared/spec-schema.ts instead. Kept for Phase 1 test compatibility. */
export const SpecPhaseOutputSchema = z.object({
  pages: z.array(z.object({
    name: z.string(),
    purpose: z.string(),
    components: z.array(z.string()),
    dataRequirements: z.array(z.string()),
  })),
});

// React-gen phase output — direct React component generation (replaces Stitch)
export const ReactGenPhaseOutputSchema = z.object({
  filePath: z.string(),
  componentCode: z.string(),
  reviewScore: z.number().min(0).max(1),
  reviewFeedback: z.array(z.string()).default([]),
  passed: z.boolean(),
  retried: z.boolean().default(false),
});

// ─── SECTION 5: Type Exports ──────────────────────────────────────────────────

export type ProjectConfig = z.infer<typeof ProjectConfigSchema>;
export type PageState = z.infer<typeof PageStateSchema>;
export type PipelineRun = z.infer<typeof PipelineRunSchema>;
export type SpecPhaseOutput = z.infer<typeof SpecPhaseOutputSchema>;
export type ReactGenPhaseOutput = z.infer<typeof ReactGenPhaseOutputSchema>;
