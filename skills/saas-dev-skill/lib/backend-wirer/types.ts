import { z } from "zod";

// Re-export BackendSpec and BackendEndpointSpec from shared spec-schema for convenience
export type { BackendSpec, BackendEndpointSpec } from "@shared/spec-schema.js";
export { BackendSpecSchema } from "@shared/spec-schema.js";

// ─── SECTION 1: BackendBrownfieldInventory ────────────────────────────────────

/**
 * Typed snapshot of existing backend state — produced before any backend files are written (D-04).
 * Enables collision detection and safe insertion point calculation.
 */
export const BackendBrownfieldInventorySchema = z.object({
  /** All /api/... paths extracted from server/routes.ts */
  existingRoutePaths: z.array(z.string()),
  /** All async method names extracted from server/storage.ts */
  existingStorageFunctions: z.array(z.string()),
  /** All pgTable names extracted from shared/schema.ts */
  existingTableNames: z.array(z.string()),
  /** Byte offset of "const httpServer = createServer(app)" in routes.ts — -1 if not found */
  routesInsertionOffset: z.number(),
  /** Byte offset of last "}" in storage.ts (end of class) */
  storageInsertionOffset: z.number(),
  /** Byte offset at end of schema.ts (append at end) */
  schemaInsertionOffset: z.number(),
});

export type BackendBrownfieldInventory = z.infer<typeof BackendBrownfieldInventorySchema>;

// ─── SECTION 2: RouteCodeBlock ────────────────────────────────────────────────

/**
 * A single Express route handler block to be inserted into routes.ts (D-06, D-08, D-09).
 * Includes optional inline Zod validation schema per existing routes.ts pattern.
 */
export const RouteCodeBlockSchema = z.object({
  method: z.string(),
  path: z.string(),
  code: z.string(),
  /** Optional inline Zod schema code to place before the route handler */
  zodSchemaCode: z.string().optional(),
});

export type RouteCodeBlock = z.infer<typeof RouteCodeBlockSchema>;

// ─── SECTION 3: SchemaCodeBlock ───────────────────────────────────────────────

/**
 * A complete Drizzle table definition to be appended to shared/schema.ts (D-15).
 * Includes the table, insert schema, and type exports — matching existing co-location pattern.
 */
export const SchemaCodeBlockSchema = z.object({
  tableName: z.string(),
  drizzleCode: z.string(),
  zodInsertCode: z.string(),
  typeExportCode: z.string(),
});

export type SchemaCodeBlock = z.infer<typeof SchemaCodeBlockSchema>;

// ─── SECTION 4: StorageCodeBlock ─────────────────────────────────────────────

/**
 * A single CRUD function to be appended to the storage class in server/storage.ts (D-07).
 */
export const StorageCodeBlockSchema = z.object({
  functionName: z.string(),
  code: z.string(),
  tableName: z.string(),
});

export type StorageCodeBlock = z.infer<typeof StorageCodeBlockSchema>;

// ─── SECTION 5: HookInjection ─────────────────────────────────────────────────

/**
 * Describes a TanStack Query hook injection into an existing Phase 4 page component (D-02).
 * The replacePattern is used to find the exact location in the page file to inject the hook.
 */
export const HookInjectionSchema = z.object({
  /** Relative path to the page file from project root */
  pageFilePath: z.string(),
  /** Import statement to add at the top of the page file */
  hookImport: z.string(),
  /** Hook call code to inject into the component body */
  hookCode: z.string(),
  /** String pattern in the existing page file to replace with hookCode */
  replacePattern: z.string(),
});

export type HookInjection = z.infer<typeof HookInjectionSchema>;

// ─── SECTION 6: WiringValidationResult ───────────────────────────────────────

/**
 * Result of cross-checking BackendSpec against existing backend state (D-03).
 * Empty gaps + empty collisions = valid: true.
 */
export const WiringValidationResultSchema = z.object({
  /** True only when gaps and collisions are both empty */
  valid: z.boolean(),
  /** Data requirements with no corresponding endpoint */
  gaps: z.array(z.string()),
  /** New endpoint paths that conflict with existing routes */
  collisions: z.array(z.string()),
});

export type WiringValidationResult = z.infer<typeof WiringValidationResultSchema>;

// ─── SECTION 7: BackendWiringPlan ─────────────────────────────────────────────

/**
 * Composite plan for all backend wiring operations — output of the plan generation step.
 * Consumed by route-generator, schema-generator, storage-generator, and hook-injector modules.
 */
export const BackendWiringPlanSchema = z.object({
  newRoutes: z.array(RouteCodeBlockSchema),
  newSchemaBlocks: z.array(SchemaCodeBlockSchema),
  newStorageFunctions: z.array(StorageCodeBlockSchema),
  hookInjections: z.array(HookInjectionSchema),
  validationResult: WiringValidationResultSchema,
});

export type BackendWiringPlan = z.infer<typeof BackendWiringPlanSchema>;
