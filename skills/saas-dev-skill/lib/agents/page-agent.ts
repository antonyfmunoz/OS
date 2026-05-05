// lib/agents/page-agent.ts
// Wraps the component-writer with full ArtifactStore context.
// Delegates all generation, validation, review, and tsc checks to writeReactComponent.

import fs from "node:fs";
import path from "node:path";
import { writeReactComponent, type ComponentWriterInput } from "../react-gen/component-writer.js";
import { ArtifactStore } from "./artifact-store.js";
import { buildConstraintsBlock } from "./design-system-agent.js";
import type { PageOutput } from "./types.js";
import type { ProjectBrief } from "../intake/types.js";
import type { PageSpecFull } from "@shared/spec-schema.js";
import type { PageCopy } from "../copy-planner/types.js";

function formatCompetitiveIntel(intel: {
  competitors: Array<{ name: string; url: string; strengths: string[]; weaknesses: string[]; designNotes: string }>;
  synthesizedInsights: string;
  copyInfluences: string;
  structureInfluences: string;
}): string {
  const sections: string[] = [];

  for (const comp of intel.competitors) {
    sections.push(
      `## ${comp.name} (${comp.url})`,
      `Strengths: ${comp.strengths.join(", ")}`,
      `Weaknesses: ${comp.weaknesses.join(", ")}`,
      `Design notes: ${comp.designNotes}`,
      "",
    );
  }

  sections.push(
    "## Synthesized Insights",
    intel.synthesizedInsights,
    "",
    "## Copy Influences",
    intel.copyInfluences,
    "",
    "## Structure Influences",
    intel.structureInfluences,
  );

  return sections.join("\n");
}

export async function runPageAgent(
  pageSpec: PageSpecFull,
  brief: ProjectBrief,
  store: ArtifactStore,
  priorPageSummary?: string,
): Promise<PageOutput> {
  // 1. Gather context from ArtifactStore

  // Design system — read the component design guide file, fall back to brief.designSystem
  const designSystemArtifact = store.getDesignSystem();
  let designSystemContent = brief.designSystem;
  if (designSystemArtifact) {
    const guidePath = designSystemArtifact.componentDesignGuidePath;
    const absoluteGuidePath = path.isAbsolute(guidePath)
      ? guidePath
      : path.join(store.getProjectRoot(), guidePath);
    if (fs.existsSync(absoluteGuidePath)) {
      designSystemContent = fs.readFileSync(absoluteGuidePath, "utf-8");
    }
  }

  // Shared component paths
  const sharedComponentPaths = store.getComponentPaths() ?? {};

  // Component interfaces — serialize for context
  const componentInterfaces = store.getComponentInterfaces() ?? [];
  if (componentInterfaces.length > 0) {
    const interfaceSummary = componentInterfaces
      .map((ci) => {
        const propsStr = ci.props
          .map((p) => `${p.name}${p.optional ? "?" : ""}: ${p.type}`)
          .join(", ");
        return `${ci.exportName} (${ci.filePath}): { ${propsStr} }`;
      })
      .join("\n");
    designSystemContent += `\n\nAVAILABLE SHARED COMPONENT INTERFACES:\n${interfaceSummary}`;
  }

  // User Supremacy constraints — inject into every page generation
  const constraintsBlock = buildConstraintsBlock(store);
  if (constraintsBlock) {
    designSystemContent += `\n\n${constraintsBlock}`;
  }

  // Component library recommendations — inject dynamic library choices
  const libRecs = store.getComponentLibraryRecommendations();
  if (libRecs) {
    designSystemContent += `\n\nANIMATION AND MOTION:
Animation library for this product: ${libRecs.animationLibrary}
Use ONLY this library for all animations. Do not use any other animation library.
Apply motion patterns appropriate for ${brief.productDescription}.

COMPONENT IMPORTS:
Use ONLY the components built by Component Library Agent.
Import from the exact paths listed above.
Do not import from libraries not in the component list.
Premium sources available: ${libRecs.premiumComponents.join(", ") || "none"}`;
  }

  // Project copy — find the PageCopy matching this page by name
  const projectCopy = store.getProjectCopy();
  let pageCopy: PageCopy | null = null;
  if (projectCopy) {
    const normalizedPageName = pageSpec.name.toLowerCase().replace(/[\s-_]/g, "");
    pageCopy =
      projectCopy.pages.find((pc) => {
        const normalizedCopyName = pc.pageName.toLowerCase().replace(/[\s-_]/g, "");
        return normalizedCopyName === normalizedPageName;
      }) ?? null;
  }

  // Competitive intel
  const competitiveIntel = store.getCompetitiveIntel();
  const competitiveIntelStr = competitiveIntel
    ? formatCompetitiveIntel(competitiveIntel)
    : undefined;

  // Brand voice — use brief.brandVoice or load from .planning/BRAND-VOICE.md
  let brandVoice = brief.brandVoice;
  if (!brandVoice) {
    const brandVoicePath = path.join(store.getProjectRoot(), ".planning", "BRAND-VOICE.md");
    if (fs.existsSync(brandVoicePath)) {
      brandVoice = fs.readFileSync(brandVoicePath, "utf-8");
    }
  }

  // 2. Build ComponentWriterInput
  const input: ComponentWriterInput = {
    page: pageSpec,
    pageCopy,
    designSystem: designSystemContent,
    designSystemArtifact: designSystemArtifact ?? undefined,
    brandVoice: brandVoice || "",
    sharedComponentPaths,
    competitiveIntel: competitiveIntelStr,
    priorPageSummary,
    projectBrief: brief,
    projectRoot: store.getProjectRoot(),
  };

  // 3. Delegate to writeReactComponent (handles generation, validation, review, tsc check)
  const writerOutput = await writeReactComponent(input);

  // 4. Convert ComponentWriterOutput to PageOutput
  const pageOutput: PageOutput = {
    pageName: writerOutput.pageName,
    filePath: writerOutput.filePath,
    route: pageSpec.route,
    componentCode: writerOutput.componentCode,
    reviewScore: writerOutput.reviewScore,
    reviewFeedback: writerOutput.reviewFeedback,
    passed: writerOutput.passed,
    tsErrors: writerOutput.tsErrors,
    fixAttempts: writerOutput.fixAttempts,
    compiledClean: writerOutput.compiledClean,
    importViolations: writerOutput.importViolations,
    nullSafetyIssues: writerOutput.nullSafetyIssues,
  };

  // 5. Persist to ArtifactStore
  store.addPageOutput(pageOutput);

  // 6. Return
  return pageOutput;
}
