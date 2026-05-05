import { z } from "zod";

// ─── TaxonomyReport ───────────────────────────────────────────────────────────

// TaxonomyReport — output of taxonomy auditor (D-06)
// Addresses review concern: structured validation result, not throw
export const TaxonomyReportSchema = z.object({
  valid: z.boolean(),                           // false if empty input or collisions detected
  errors: z.array(z.string()).default([]),       // validation errors (e.g. "no page specs provided")
  warnings: z.array(z.string()).default([]),     // non-fatal warnings
  totalPages: z.number(),
  pagesWithEvents: z.number(),
  pagesWithoutEvents: z.array(z.string()),      // page names with 0 events
  totalEvents: z.number(),
  allEvents: z.array(z.object({
    pageName: z.string(),
    eventName: z.string(),
    originalName: z.string(),                   // pre-normalization name for collision tracing
    trigger: z.string(),
  })),
  allFlagCandidates: z.array(z.string()),
  collisions: z.array(z.string()),              // snake_case names that collapse 2+ distinct originals
});
export type TaxonomyReport = z.infer<typeof TaxonomyReportSchema>;

// ─── AnalyticsInjection ───────────────────────────────────────────────────────

// AnalyticsInjection — describes what to inject into a page file (D-02)
// Addresses review: includes injectionStatus to distinguish auto vs manual-required
export const AnalyticsInjectionSchema = z.object({
  pageFilePath: z.string(),
  pageName: z.string(),
  importCode: z.string(),
  hookCode: z.string(),
  captureCode: z.string(),                      // auto-injectable code (useEffect for load events)
  manualCaptures: z.array(z.object({            // events requiring manual handler wiring (click/submit)
    eventName: z.string(),
    trigger: z.string(),
    captureSnippet: z.string(),                 // posthog?.capture("event_name", {...}) — copy-paste ready
    properties: z.array(z.string()),
  })).default([]),
  events: z.array(z.object({
    name: z.string(),
    trigger: z.string(),
    properties: z.array(z.string()),
  })),
});
export type AnalyticsInjection = z.infer<typeof AnalyticsInjectionSchema>;

// ─── HostingTarget ────────────────────────────────────────────────────────────

// HostingTarget — user's hosting choice (D-08)
export type HostingTarget = "railway" | "render" | "fly" | "custom";

// ─── DeployConfig ─────────────────────────────────────────────────────────────

// DeployConfig — output of docker-config-generator (D-09, D-10)
export interface DeployConfig {
  target: HostingTarget;
  dockerfile: string;               // full Dockerfile content
  dockerignore: string;             // .dockerignore content (addresses Codex review)
  platformConfig: string;           // railway.toml | render.yaml | fly.toml content
  platformConfigFilename: string;   // filename for the platform config
  dockerCompose?: string;           // only for "custom" target
}

// ─── EnvVarEntry ──────────────────────────────────────────────────────────────

// EnvVarEntry — single discovered env var (D-11)
// Addresses review: includes scope and source locations
export interface EnvVarEntry {
  name: string;
  source: "server" | "client";      // process.env = server, import.meta.env = client
  files: string[];                  // files where found
  required: boolean;                // true if used without fallback (no ?? or || default)
}

// ─── DeployOutcome ────────────────────────────────────────────────────────────

// DeployOutcome — deployment result modeling (addresses review: "skipped/staged/deployed/failed")
export type DeployOutcome = "skipped" | "staged" | "deployed" | "failed-preflight" | "failed-runtime";

// ─── DeployRunnerResult ───────────────────────────────────────────────────────

// DeployRunnerResult — output of deploy execution (D-17)
export interface DeployRunnerResult {
  target: HostingTarget;
  outcome: DeployOutcome;
  confirmed: boolean;
  executed: boolean;
  output?: string;
  error?: string;
}

// ─── PostHogSetupResult ───────────────────────────────────────────────────────

// PostHogSetupResult — output of posthog-setup (D-03, D-15)
export interface PostHogSetupResult {
  apiKeyPresent: boolean;
  personalApiKeyPresent: boolean;
  projectIdPresent: boolean;
  setupGuideGenerated: boolean;
  flagsCreated: string[];
  flagsFailed: string[];
  flagWarnings: string[];           // addresses review: surface flag failures as warnings
}

// ─── PreflightResult ──────────────────────────────────────────────────────────

// PreflightResult — addresses review: credential/config validation before deploy
export interface PreflightResult {
  ready: boolean;
  missingSecrets: string[];
  missingCLI: string[];
  warnings: string[];
}
