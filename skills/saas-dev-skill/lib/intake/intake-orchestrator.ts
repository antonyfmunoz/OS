// lib/intake/intake-orchestrator.ts
// Unified intake phase — collects everything needed before any generation starts.
// Produces a ProjectBrief that all downstream phases consume.
//
// Three modes:
//   A. Greenfield: no code, no docs — structured conversation
//   B. Docs-only: PRD/design-system/specs present — scan, gap-fill, synthesize
//   C. Existing codebase: scan code + docs, synthesize, ask about gaps

import fs from "node:fs";
import path from "node:path";
import { SpecOutputSchema } from "@shared/spec-schema.js";
import type { SpecOutput } from "@shared/spec-schema.js";
import { restructureSpec } from "../spec-parser/restructure-spec.js";
import { deriveBackendSpec } from "../spec-parser/derive-backend-spec.js";
import { analyzeGaps, hasBlockingGaps } from "../spec-parser/gap-analyzer.js";
import { formatGapReport } from "../spec-parser/spec-approval.js";
import { inferBrandVoice, loadBrandVoice } from "../spec-parser/brand-voice-inferrer.js";
import { detectIntakeMode } from "./mode-detector.js";
import { scanPlanningDocs, identifyMissingDocs, type ScannedDocs } from "./doc-scanner.js";
import { scanCodebase, formatCodebaseSummary } from "./codebase-scanner.js";
import {
  ProjectBriefSchema,
  TechStackSchema,
  type ProjectBrief,
  type IntakeMode,
} from "./types.js";
import {
  researchCompetitors,
  formatCompetitiveIntelReport,
  type CompetitiveIntel,
} from "./competitive-researcher.js";
import type { ProjectConfig } from "../../shared/design-schema.js";

export { type IntakeMode } from "./types.js";

export interface VisualIntentInput {
  /** 1-3 URLs of sites/apps whose UI the user admires. */
  referenceUrls?: string[];
  /** One word to describe the desired feel: minimal, bold, editorial, luxury, technical, warm, clinical, futuristic. */
  feelWord?: string;
  /** Things the user hates in UI design. */
  avoidances?: string[];
  /** Color mode preference. */
  colorMode?: "light" | "dark" | "user-choice";
}

export interface IntakeOptions {
  /** Competitor URLs to research during intake. */
  competitorUrls?: string[];
  /** Visual intent answers from the user. */
  visualIntent?: VisualIntentInput;
}

export interface IntakeResult {
  brief: ProjectBrief;
  mode: IntakeMode;
  gapReport: string | null;
}

/**
 * Run the intake phase for a project.
 * Detects mode automatically and collects everything needed.
 *
 * For greenfield mode (no docs, no code), this returns a minimal ProjectBrief
 * with empty spec — the caller (skill) must run a conversation to fill it.
 *
 * For docs-only and existing-codebase modes, this synthesizes a ProjectBrief
 * from available materials.
 */
export async function runIntake(
  config: ProjectConfig,
  options: IntakeOptions = {},
): Promise<IntakeResult> {
  const projectRoot = path.resolve(config.repoPath);
  const mode = detectIntakeMode(projectRoot);

  switch (mode) {
    case "greenfield":
      return runGreenfieldIntake(config, projectRoot, options);
    case "docs-only":
      return runDocsOnlyIntake(config, projectRoot, options);
    case "existing-codebase":
      return runExistingCodebaseIntake(config, projectRoot, options);
  }
}

async function runGreenfieldIntake(
  _config: ProjectConfig,
  _projectRoot: string,
  options: IntakeOptions = {},
): Promise<IntakeResult> {
  // Greenfield mode produces a skeleton brief. The spec field needs a valid
  // SpecOutput — use a minimal placeholder that the collaborative flow will
  // replace once the conversation completes.
  const { visualIntent, visualResearch } = await resolveVisualIntent(options.visualIntent);

  const brief = ProjectBriefSchema.parse({
    productName: "Untitled Project",
    productDescription: "No description yet — run collaborative intake to define.",
    productVision: "",
    targetUsers: [],
    jobsToBeDone: [],
    brandVoice: "",
    designSystem: "",
    techStack: TechStackSchema.parse({}),
    authProvider: "clerk",
    dbProvider: "neon",
    deployTarget: "vps",
    spec: { pages: [{ name: "Placeholder", route: "/", purpose: "Placeholder for greenfield intake", components: [], authLevel: "public", priority: 1, dependsOn: [], specVersion: 1, source: "inferred", dataRequirements: [], apiEndpoints: [], validationRules: [], events: [], featureFlagCandidates: [] }] },
    visualIntent,
    visualResearch,
    isGreenfield: true,
    existingCodeScanned: false,
    sourceDocs: [],
  });

  return { brief, mode: "greenfield", gapReport: null };
}

async function runDocsOnlyIntake(
  config: ProjectConfig,
  projectRoot: string,
  options: IntakeOptions = {},
): Promise<IntakeResult> {
  const docs = scanPlanningDocs(projectRoot);
  const planningDir = path.join(projectRoot, ".planning");

  // Try to load or produce the spec
  const spec = await resolveSpec(docs, planningDir);

  // Run gap analysis
  let gapReport: string | null = null;
  const skipGaps = process.env.SKIP_GAP_ANALYSIS === "true";
  if (!skipGaps) {
    const gaps = await analyzeGaps(spec, { skipLlm: false });
    gapReport = formatGapReport(spec, gaps);
    persistGapReport(projectRoot, gapReport);
    if (hasBlockingGaps(gaps)) {
      console.warn("[intake] Blocking gaps found — see GAP-ANALYSIS.md. Brief still produced for review.");
    }
  }

  // Infer brand voice if missing
  let brandVoice = docs.brandVoice ?? "";
  if (!brandVoice && docs.prd) {
    const result = await inferBrandVoice(docs.prd, planningDir);
    brandVoice = result?.content ?? "";
  }

  // Derive backend spec if missing
  if (!spec.backendSpec || spec.backendSpec.endpoints.length === 0) {
    try {
      spec.backendSpec = await deriveBackendSpec(spec.pages);
    } catch {
      // Best-effort
    }
  }

  // Extract product metadata from PRD or spec
  const productMeta = extractProductMeta(docs);

  // Competitive research (if URLs provided)
  const competitiveIntel = await runCompetitiveResearchIfRequested(
    options.competitorUrls, brandVoice, spec, projectRoot,
  );

  // Visual intent
  const { visualIntent, visualResearch } = await resolveVisualIntent(options.visualIntent);

  const brief = ProjectBriefSchema.parse({
    ...productMeta,
    brandVoice,
    designSystem: docs.designSystem ?? "",
    techStack: TechStackSchema.parse({}),
    authProvider: detectAuthFromSpec(spec),
    dbProvider: "neon",
    deployTarget: "vps",
    spec,
    competitiveIntel,
    visualIntent,
    visualResearch,
    isGreenfield: false,
    existingCodeScanned: false,
    sourceDocs: docs.sourceDocs,
  });

  return { brief, mode: "docs-only", gapReport };
}

async function runExistingCodebaseIntake(
  config: ProjectConfig,
  projectRoot: string,
  options: IntakeOptions = {},
): Promise<IntakeResult> {
  const docs = scanPlanningDocs(projectRoot);
  const codeScan = scanCodebase(projectRoot);
  const planningDir = path.join(projectRoot, ".planning");

  console.log(`[intake] Codebase scan:\n${formatCodebaseSummary(codeScan)}`);

  // Try to load or produce the spec
  const spec = await resolveSpec(docs, planningDir);

  // Gap analysis
  let gapReport: string | null = null;
  const skipGaps = process.env.SKIP_GAP_ANALYSIS === "true";
  if (!skipGaps) {
    const gaps = await analyzeGaps(spec, { skipLlm: false });
    gapReport = formatGapReport(spec, gaps);
    persistGapReport(projectRoot, gapReport);
  }

  // Brand voice
  let brandVoice = docs.brandVoice ?? "";
  if (!brandVoice && docs.prd) {
    const result = await inferBrandVoice(docs.prd, planningDir);
    brandVoice = result?.content ?? "";
  }

  // Backend spec
  if (!spec.backendSpec || spec.backendSpec.endpoints.length === 0) {
    try {
      spec.backendSpec = await deriveBackendSpec(spec.pages);
    } catch {
      // Best-effort
    }
  }

  const productMeta = extractProductMeta(docs);

  // Competitive research (if URLs provided)
  const competitiveIntel = await runCompetitiveResearchIfRequested(
    options.competitorUrls, brandVoice, spec, projectRoot,
  );

  // Detect auth/db from actual dependencies
  const authProvider = codeScan.hasAuth ? "clerk" : "none";
  const dbProvider = codeScan.hasDatabase ? "neon" : "other";

  // Visual intent
  const { visualIntent, visualResearch } = await resolveVisualIntent(options.visualIntent);

  const brief = ProjectBriefSchema.parse({
    ...productMeta,
    brandVoice,
    designSystem: docs.designSystem ?? "",
    techStack: {
      frontend: codeScan.framework.detected.react ? "react" : "unknown",
      buildTool: codeScan.framework.detected.vite ? "vite" : "unknown",
      styling: codeScan.framework.detected.tailwind ? "tailwind" : "unknown",
      componentLib: codeScan.framework.detected.shadcn ? "shadcn/ui" : "unknown",
      language: "typescript",
    },
    authProvider,
    dbProvider,
    deployTarget: "vps",
    spec,
    competitiveIntel,
    visualIntent,
    visualResearch,
    isGreenfield: false,
    existingCodeScanned: true,
    sourceDocs: docs.sourceDocs,
  });

  return { brief, mode: "existing-codebase", gapReport };
}

// ─── Visual Intent ───────────────────────────────────────────────────────────

interface VisualResearchEntry {
  url: string;
  observations: string;
}

async function resolveVisualIntent(
  input: VisualIntentInput | undefined,
): Promise<{
  visualIntent?: { referenceUrls: string[]; feelWord: string; avoidances: string[]; colorMode: "light" | "dark" | "user-choice" };
  visualResearch?: VisualResearchEntry[];
}> {
  if (!input) return {};

  const visualIntent = {
    referenceUrls: input.referenceUrls ?? [],
    feelWord: input.feelWord ?? "",
    avoidances: input.avoidances ?? [],
    colorMode: input.colorMode ?? "light" as const,
  };

  // If reference URLs provided, fetch and extract visual observations
  let visualResearch: VisualResearchEntry[] | undefined;
  if (visualIntent.referenceUrls.length > 0) {
    visualResearch = [];
    for (const url of visualIntent.referenceUrls) {
      try {
        const observations = await fetchVisualObservations(url);
        if (observations) {
          visualResearch.push({ url, observations });
        }
      } catch {
        console.warn(`[intake] Could not fetch visual reference: ${url}`);
      }
    }
    if (visualResearch.length === 0) visualResearch = undefined;
  }

  return { visualIntent, visualResearch };
}

async function fetchVisualObservations(url: string): Promise<string | null> {
  // Best-effort: describe what we'd observe at the URL
  // In a full implementation this would use web_fetch + Claude vision.
  // For now, record the URL as a reference for the generation prompt.
  return `Reference site provided — apply layout patterns, color usage, typography choices, and spacing density observed at this URL.`;
}

// ─── Competitive Research ─────────────────────────────────────────────────────

async function runCompetitiveResearchIfRequested(
  urls: string[] | undefined,
  brandVoice: string,
  spec: SpecOutput,
  projectRoot: string,
): Promise<CompetitiveIntel | undefined> {
  if (!urls || urls.length === 0) return undefined;

  try {
    const intel = await researchCompetitors(urls, brandVoice, spec);

    // Persist to .planning/output/research/
    const researchDir = path.join(projectRoot, ".planning", "output", "research");
    if (!fs.existsSync(researchDir)) {
      fs.mkdirSync(researchDir, { recursive: true });
    }
    fs.writeFileSync(
      path.join(researchDir, "COMPETITIVE-INTEL.json"),
      JSON.stringify(intel, null, 2) + "\n",
      "utf-8",
    );
    fs.writeFileSync(
      path.join(researchDir, "COMPETITIVE-INTEL.md"),
      formatCompetitiveIntelReport(intel) + "\n",
      "utf-8",
    );
    console.log(`[intake] Competitive intel saved to .planning/output/research/`);

    return intel;
  } catch (err) {
    console.warn(`[intake] Competitive research failed — continuing without it. ${err instanceof Error ? err.message : String(err)}`);
    return undefined;
  }
}

// ─── Helpers ────────────────────────────────────────────────────────────────

async function resolveSpec(docs: ScannedDocs, planningDir: string): Promise<SpecOutput> {
  // Try pre-validated JSON spec first
  for (const specFile of docs.specFiles) {
    if (specFile.path.endsWith(".json")) {
      try {
        const parsed = JSON.parse(specFile.content);
        const result = SpecOutputSchema.safeParse(parsed);
        if (result.success) return result.data;
      } catch {
        // Invalid — try next
      }
    }
  }

  // Fall back to LLM restructuring from PRD or requirements
  const rawText = docs.prd ?? docs.requirements ?? docs.specFiles[0]?.content;
  if (!rawText) {
    throw new Error(
      "[intake] No spec source found. Provide PRD.md, REQUIREMENTS.md, or a spec file in .planning/specs/.",
    );
  }
  return restructureSpec(rawText);
}

function extractProductMeta(docs: ScannedDocs): {
  productName: string;
  productDescription: string;
  productVision: string;
  targetUsers: string[];
  jobsToBeDone: string[];
} {
  const text = docs.prd ?? docs.requirements ?? "";
  // Extract product name from first heading
  const nameMatch = text.match(/^#\s+(.+?)(?:\s*[-—]|$)/m);
  const productName = nameMatch?.[1]?.trim() ?? "Untitled Project";

  // Extract description from executive summary or first paragraph
  const summaryMatch = text.match(/##\s*(?:\d+\.\s*)?Executive Summary\s*\n+([\s\S]*?)(?=\n##|\n---)/i);
  const productDescription = summaryMatch?.[1]?.trim() ?? text.slice(0, 500).trim();

  // Extract vision
  const visionMatch = text.match(/##\s*(?:\d+\.\s*)?Product Vision\s*\n+([\s\S]*?)(?=\n##|\n---)/i);
  const productVision = visionMatch?.[1]?.trim() ?? "";

  // Extract target users — handles bullet lists, "Primary:/Secondary:" prose, and plain paragraphs
  const usersMatch = text.match(/##\s*(?:\d+\.\s*)?Target Users[^#]*?\n+([\s\S]*?)(?=\n##|\n---)/i);
  const targetUsers: string[] = [];
  if (usersMatch) {
    const block = usersMatch[1].trim();
    const bullets = block.split("\n")
      .filter((l) => l.trim().startsWith("-") || l.trim().startsWith("*"))
      .map((l) => l.replace(/^[\s*-]+/, "").trim())
      .filter(Boolean);

    if (bullets.length > 0) {
      targetUsers.push(...bullets.slice(0, 5));
    } else {
      // Parse "Primary: ...", "Secondary: ..." prose lines
      const lines = block.split("\n").map((l) => l.trim()).filter(Boolean);
      for (const line of lines) {
        const labelMatch = line.match(/^(Primary|Secondary|Tertiary)\s*:\s*(.+)/i);
        if (labelMatch) {
          targetUsers.push(labelMatch[2].trim());
        } else if (targetUsers.length === 0) {
          // First non-labeled paragraph — use as-is
          targetUsers.push(line);
        }
      }
    }
  }

  return { productName, productDescription, productVision, targetUsers: targetUsers.slice(0, 5), jobsToBeDone: [] };
}

function detectAuthFromSpec(spec: SpecOutput): "clerk" | "firebase" | "supabase" | "custom" | "none" {
  const hasAuthPages = spec.pages.some(
    (p) => p.authLevel === "authenticated" || p.authLevel === "admin",
  );
  return hasAuthPages ? "clerk" : "none";
}

function persistGapReport(projectRoot: string, report: string): void {
  const outputDir = path.join(projectRoot, ".planning", "output", "spec");
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }
  fs.writeFileSync(path.join(outputDir, "GAP-ANALYSIS.md"), report, "utf-8");
}

/**
 * Load a previously stored ProjectBrief from pipeline_runs.config.
 * Returns null if the config doesn't contain a brief.
 */
export function loadBriefFromConfig(configJson: string): ProjectBrief | null {
  try {
    const parsed = JSON.parse(configJson);
    if (parsed.brief) {
      const result = ProjectBriefSchema.safeParse(parsed.brief);
      return result.success ? result.data : null;
    }
    return null;
  } catch {
    return null;
  }
}
