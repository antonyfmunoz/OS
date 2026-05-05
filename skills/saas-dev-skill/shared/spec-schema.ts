import { z } from "zod";

// ─── SECTION 1: Provenance Tracking ──────────────────────────────────────────

/**
 * Provenance enum for tracking whether a spec item was explicitly described by
 * the user or inferred/added by the AI during restructuring (D-03 confirmation gate).
 */
export const SpecItemSource = z.enum(["explicit", "inferred"]);
export type SpecItemSource = z.infer<typeof SpecItemSource>;

// ─── SECTION 2: Page Spec Layers ─────────────────────────────────────────────

/**
 * Core page identity and routing information.
 * Addresses: route validation (Codex MEDIUM), provenance tracking (HIGH consensus).
 */
export const PageSpecCore = z.object({
  name: z.string().min(1),
  route: z.string().min(1).regex(/^\//, "Route must start with /"),
  purpose: z.string().min(1),
  components: z.array(z.string()),
  authLevel: z.enum(["public", "authenticated", "admin"]),
  priority: z.number().int().min(1),
  dependsOn: z.array(z.string()).default([]),
  specVersion: z.number().int().default(1),
  /** Was this page explicitly in user input or AI-inferred? */
  source: SpecItemSource.default("inferred"),
});
export type PageSpecCore = z.infer<typeof PageSpecCore>;

/**
 * UI/UX layer — layout hints, states, mobile considerations.
 * For v1, page-level provenance is tracked via PageSpecCore.source.
 */
export const PageSpecUI = z.object({
  layoutHint: z.string().optional(),
  emptyState: z.string().optional(),
  loadingState: z.string().optional(),
  errorState: z.string().optional(),
  mobileConsiderations: z.string().optional(),
});
export type PageSpecUI = z.infer<typeof PageSpecUI>;

/**
 * Data layer — requirements, API endpoints, validation rules.
 */
export const PageSpecData = z.object({
  dataRequirements: z.array(
    z.object({
      component: z.string(),
      fields: z.array(z.string()),
      source: z.string().optional(),
    })
  ),
  apiEndpoints: z
    .array(
      z.object({
        endpoint: z.string(),
        source: SpecItemSource.default("inferred"),
      })
    )
    .default([]),
  validationRules: z.array(z.string()).default([]),
});
export type PageSpecData = z.infer<typeof PageSpecData>;

/**
 * Analytics layer — event tracking and feature flag candidates.
 */
export const PageSpecAnalytics = z.object({
  events: z
    .array(
      z.object({
        name: z.string(),
        trigger: z.string(),
        properties: z.array(z.string()).default([]),
        /** Was this event explicit in the user spec or AI-inferred? */
        source: SpecItemSource.default("inferred"),
      })
    )
    .default([]),
  featureFlagCandidates: z.array(z.string()).default([]),
});
export type PageSpecAnalytics = z.infer<typeof PageSpecAnalytics>;

/**
 * Complete page spec — all four layers merged via composable .merge() pattern.
 * Downstream phases (3-6) consume PageSpecFull.
 */
export const PageSpecFull = PageSpecCore.merge(PageSpecUI)
  .merge(PageSpecData)
  .merge(PageSpecAnalytics);
export type PageSpecFull = z.infer<typeof PageSpecFull>;

// ─── SECTION 3: Shared Components ────────────────────────────────────────────

/**
 * Shared component extracted across multiple pages (D-20).
 */
export const SharedComponentSpec = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  purpose: z.string(),
  usedByPages: z.array(z.string()),
  props: z.array(z.string()).default([]),
  /** Was this component explicitly described or AI-inferred from page descriptions? */
  source: SpecItemSource.default("inferred"),
});
export type SharedComponentSpec = z.infer<typeof SharedComponentSpec>;

// ─── SECTION 4: Backend Spec ──────────────────────────────────────────────────

/**
 * Individual backend API endpoint spec.
 */
export const BackendEndpointSpec = z.object({
  method: z.enum(["GET", "POST", "PUT", "PATCH", "DELETE"]),
  path: z.string().min(1).regex(/^\//, "Endpoint path must start with /"),
  description: z.string(),
  requestBody: z.array(z.string()).default([]),
  responseFields: z.array(z.string()).default([]),
  authRequired: z.boolean().default(true),
  uiPageRef: z.string().optional(),
  /** Was this endpoint explicitly in a backend spec or auto-derived from UI data layer? */
  source: SpecItemSource.default("inferred"),
});
export type BackendEndpointSpec = z.infer<typeof BackendEndpointSpec>;

/**
 * Full backend spec including endpoints, table hints, background jobs, and mismatches.
 */
export const BackendSpecSchema = z.object({
  endpoints: z.array(BackendEndpointSpec),
  drizzleTableHints: z.array(z.string()).default([]),
  backgroundJobs: z.array(z.string()).default([]),
  mismatches: z.array(z.string()).default([]),
});
export type BackendSpec = z.infer<typeof BackendSpecSchema>;

// ─── SECTION 5: Spec Output ───────────────────────────────────────────────────

/**
 * Final structured output from spec parsing and restructuring.
 * All downstream phases consume this shape.
 */
export const SpecOutputSchema = z.object({
  pages: z.array(PageSpecFull).min(1),
  sharedComponents: z.array(SharedComponentSpec).default([]),
  suggestedOrder: z.array(z.string()).default([]),
  backendSpec: BackendSpecSchema.optional(),
});
export type SpecOutput = z.infer<typeof SpecOutputSchema>;
