// lib/agents/copy-agent.ts
// Wrapper agent that orchestrates brand voice loading, copy generation, and copy review.
// Delegates all heavy lifting to existing copy-planner and brand-voice-inferrer modules.

import path from "node:path";
import { generateProjectCopy } from "../copy-planner/copy-writer.js";
import { reviewProjectCopy } from "../copy-planner/copy-reviewer.js";
import { inferBrandVoice, loadBrandVoice } from "../spec-parser/brand-voice-inferrer.js";
import { ArtifactStore } from "./artifact-store.js";
import type { ProjectBrief } from "../intake/types.js";
import type { ProjectCopy } from "../copy-planner/types.js";
import type { ProductInsights } from "./types.js";

/**
 * Run the copy agent: load/infer brand voice, generate copy, review it,
 * and persist the final result to the artifact store.
 */
export async function runCopyAgent(
  brief: ProjectBrief,
  insights: ProductInsights,
  store: ArtifactStore,
): Promise<ProjectCopy> {
  // 1. Load or infer brand voice
  const planningDir = path.join(store.getProjectRoot(), ".planning");
  let brandVoice: string | null = loadBrandVoice(planningDir);

  if (!brandVoice && brief.productDescription) {
    const result = await inferBrandVoice(brief.productDescription, planningDir);
    if (result) {
      brandVoice = result.content;
    }
  }

  if (!brandVoice) {
    brandVoice = brief.brandVoice || "Professional, clear, and concise.";
  }

  // Enrich brand voice with copy recommendations from product insights
  if (insights.copyRecommendations.length > 0) {
    brandVoice += `\n\nCopy recommendations from competitive analysis:\n${insights.copyRecommendations.map((r) => `- ${r}`).join("\n")}`;
  }

  // 2. Generate copy using existing copy-writer
  const copy = await generateProjectCopy(brief.spec, brandVoice, brief);

  // 3. Review copy using existing copy-reviewer
  const review = await reviewProjectCopy(copy, brandVoice);

  // 4. Use revised copy if review failed with low score
  const finalCopy: ProjectCopy = !review.passed && review.overallScore < 0.7
    ? review.revisedCopy
    : copy;

  // 5. Persist to artifact store
  store.setProjectCopy(finalCopy);

  // 6. Return the final copy
  return finalCopy;
}
