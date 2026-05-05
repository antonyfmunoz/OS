/**
 * Re-exports from shared/spec-schema.ts for use within lib/spec-parser modules.
 * Consumers outside the parser should import directly from @shared/spec-schema.
 */

export type {
  PageSpecCore,
  PageSpecUI,
  PageSpecData,
  PageSpecAnalytics,
  PageSpecFull,
  SharedComponentSpec,
  BackendSpec,
  SpecOutput,
  SpecItemSource,
} from "@shared/spec-schema.js";

export {
  PageSpecCore as PageSpecCoreSchema,
  PageSpecFull as PageSpecFullSchema,
  SpecOutputSchema,
  SpecItemSource as SpecItemSourceSchema,
  SharedComponentSpec as SharedComponentSpecSchema,
  BackendSpecSchema,
} from "@shared/spec-schema.js";
