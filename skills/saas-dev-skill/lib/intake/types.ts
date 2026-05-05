// lib/intake/types.ts
// Shared types for the unified intake phase.

import { z } from "zod";
import { SpecOutputSchema } from "@shared/spec-schema.js";
import { CompetitiveIntelSchema } from "./competitive-researcher.js";

export type IntakeMode = "greenfield" | "docs-only" | "existing-codebase";

export const TechStackSchema = z.object({
  frontend: z.string().default("react"),
  buildTool: z.string().default("vite"),
  styling: z.string().default("tailwind"),
  componentLib: z.string().default("shadcn/ui"),
  language: z.string().default("typescript"),
});
export type TechStack = z.infer<typeof TechStackSchema>;

export const ProjectBriefSchema = z.object({
  // Product
  productName: z.string().min(1),
  productDescription: z.string().min(1),
  productVision: z.string().default(""),
  targetUsers: z.array(z.string()).default([]),
  jobsToBeDone: z.array(z.string()).default([]),

  // Brand
  brandVoice: z.string().default(""),
  designSystem: z.string().default(""),

  // Tech
  techStack: TechStackSchema,
  authProvider: z.enum(["clerk", "firebase", "supabase", "custom", "none"]).default("clerk"),
  dbProvider: z.enum(["neon", "supabase", "planetscale", "other"]).default("neon"),
  deployTarget: z.enum(["vercel", "railway", "vps", "other"]).default("vps"),

  // Scope
  spec: SpecOutputSchema,

  // Competitive Intelligence
  competitiveIntel: CompetitiveIntelSchema.optional(),

  // Visual Intent (from intake questions)
  visualIntent: z.object({
    referenceUrls: z.array(z.string()).default([]),
    feelWord: z.string().default(""),
    avoidances: z.array(z.string()).default([]),
    colorMode: z.enum(["light", "dark", "user-choice"]).default("light"),
  }).optional(),

  // Visual Research (observations from reference URLs)
  visualResearch: z.array(z.object({
    url: z.string(),
    observations: z.string(),
  })).optional(),

  // Meta
  isGreenfield: z.boolean(),
  existingCodeScanned: z.boolean().default(false),
  sourceDocs: z.array(z.string()).default([]),
});
export type ProjectBrief = z.infer<typeof ProjectBriefSchema>;
