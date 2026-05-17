// lib/agents/product-intel-agent.ts
// Wraps the competitive researcher and adds a product analysis layer.
// Produces ProductInsights that feed downstream agents (architecture, design, copy).

import Anthropic from "../claude-subprocess.js";
import { extractJsonFromResponse } from "../spec-parser/restructure-spec.js";
import { researchCompetitors } from "../intake/competitive-researcher.js";
import { ArtifactStore } from "./artifact-store.js";
import type { ProductInsights } from "./types.js";
import type { ProjectBrief } from "../intake/types.js";

const SYSTEM_PROMPT = `You are a senior product strategist with deep SaaS market knowledge. You analyze products to identify design, copy, and architecture patterns that will make them distinctive and successful.`;

function buildAnalysisPrompt(brief: ProjectBrief, competitiveIntelSummary: string): string {
  const pagesSummary = brief.spec.pages
    .map((p) => `- ${p.name} (${p.route}): ${p.purpose}`)
    .join("\n");

  return `Analyze this SaaS product and produce strategic recommendations.

## Product
Name: ${brief.productName}
Description: ${brief.productDescription}
${brief.productVision ? `Vision: ${brief.productVision}` : ""}

## Target Users
${brief.targetUsers.length > 0 ? brief.targetUsers.map((u) => `- ${u}`).join("\n") : "Not specified"}

## Jobs to Be Done
${brief.jobsToBeDone.length > 0 ? brief.jobsToBeDone.map((j) => `- ${j}`).join("\n") : "Not specified"}

## Spec Pages
${pagesSummary}

## Competitive Intelligence
${competitiveIntelSummary || "No competitive intelligence available."}

Based on all the above, return a JSON object with these fields:

{
  "productCategory": "what type of SaaS this is (e.g. project management, CRM, analytics platform, etc.)",
  "targetUserProfile": "detailed user persona — who they are, what they care about, their technical sophistication, their pain points, what motivates them to switch tools",
  "designRecommendations": [
    "5-8 specific, actionable design recommendations — reference competitor patterns where relevant, be tactical not generic"
  ],
  "copyRecommendations": [
    "5-8 specific, actionable copy recommendations — tone, CTA style, microcopy patterns, heading conventions, how to differentiate voice"
  ],
  "architectureRecommendations": [
    "5-8 specific, actionable architecture recommendations — data model choices, API patterns, state management, real-time needs, performance considerations"
  ],
  "marketPositioning": "2-3 paragraphs on how to position this product against competitors — what makes it distinctive, what gap it fills, what narrative to build around it"
}

Return ONLY valid JSON.`;
}

function summarizeCompetitiveIntel(brief: ProjectBrief): string {
  const intel = brief.competitiveIntel;
  if (!intel) return "";

  const parts: string[] = [];

  for (const c of intel.competitors) {
    const lines = [`### ${c.name} (${c.url})`];
    if (c.copyPatterns.length > 0) lines.push(`Copy patterns: ${c.copyPatterns.join("; ")}`);
    if (c.structurePatterns.length > 0) lines.push(`Structure patterns: ${c.structurePatterns.join("; ")}`);
    if (c.uxPatterns.length > 0) lines.push(`UX patterns: ${c.uxPatterns.join("; ")}`);
    if (c.whatToAdopt.length > 0) lines.push(`Adopt: ${c.whatToAdopt.join("; ")}`);
    if (c.whatToAvoid.length > 0) lines.push(`Avoid: ${c.whatToAvoid.join("; ")}`);
    parts.push(lines.join("\n"));
  }

  if (intel.synthesizedInsights) parts.push(`\nSynthesis: ${intel.synthesizedInsights}`);
  if (intel.copyInfluences) parts.push(`Copy influences: ${intel.copyInfluences}`);
  if (intel.structureInfluences) parts.push(`Structure influences: ${intel.structureInfluences}`);

  return parts.join("\n\n");
}

export async function runProductIntelAgent(
  brief: ProjectBrief,
  store: ArtifactStore,
): Promise<ProductInsights> {
  console.log("[product-intel] Starting product intelligence analysis...");

  // Step 1: Resolve competitive intel — use existing or research from reference URLs
  let competitiveIntelGenerated = false;

  if (!brief.competitiveIntel && brief.visualIntent?.referenceUrls && brief.visualIntent.referenceUrls.length > 0) {
    console.log(`[product-intel] No competitive intel found — researching ${brief.visualIntent.referenceUrls.length} reference URL(s)...`);
    brief.competitiveIntel = await researchCompetitors(
      brief.visualIntent.referenceUrls,
      brief.brandVoice,
      brief.spec,
    );
    competitiveIntelGenerated = true;
    console.log("[product-intel] Competitive research complete.");
  }

  const competitiveIntelSummary = summarizeCompetitiveIntel(brief);

  // Step 2: Call Claude for product analysis
  console.log("[product-intel] Generating product insights...");

  const client = new Anthropic();

  const response = await client.messages.create({
    model: "claude-haiku-4-5-20251001",
    max_tokens: 4096,
    system: SYSTEM_PROMPT,
    messages: [
      {
        role: "user",
        content: buildAnalysisPrompt(brief, competitiveIntelSummary),
      },
    ],
  });

  const text = response.content[0];
  if (!text || text.type !== "text") {
    throw new Error("[product-intel] Unexpected response type from Claude");
  }

  // Step 3: Parse response
  const parsed = extractJsonFromResponse(text.text) as {
    productCategory: string;
    targetUserProfile: string;
    designRecommendations: string[];
    copyRecommendations: string[];
    architectureRecommendations: string[];
    marketPositioning: string;
  };

  const insights: ProductInsights = {
    productCategory: parsed.productCategory,
    targetUserProfile: parsed.targetUserProfile,
    competitiveIntel: brief.competitiveIntel ?? null,
    designRecommendations: parsed.designRecommendations,
    copyRecommendations: parsed.copyRecommendations,
    architectureRecommendations: parsed.architectureRecommendations,
    marketPositioning: parsed.marketPositioning,
  };

  // Step 4: Persist artifacts
  store.setProductInsights(insights);
  console.log("[product-intel] Product insights written to artifact store.");

  if (competitiveIntelGenerated && brief.competitiveIntel) {
    store.setCompetitiveIntel(brief.competitiveIntel);
    console.log("[product-intel] Competitive intel written to artifact store.");
  }

  console.log(`[product-intel] Complete — category: ${insights.productCategory}, ${insights.designRecommendations.length} design recs, ${insights.copyRecommendations.length} copy recs, ${insights.architectureRecommendations.length} arch recs.`);

  return insights;
}
