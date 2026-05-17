// lib/intake/competitive-researcher.ts
// Researches competitor websites to extract copy patterns, structure patterns,
// UX flows, and synthesize competitive intelligence for copy and UI generation.

import { z } from "zod";
import Anthropic from "../claude-subprocess.js";
import { extractJsonFromResponse } from "../spec-parser/restructure-spec.js";
import type { SpecOutput } from "@shared/spec-schema.js";

// ─── Types ───────────────────────────────────────────────────────────────────

export const CompetitorIntelSchema = z.object({
  url: z.string(),
  name: z.string(),
  copyPatterns: z.array(z.string()).default([]),
  structurePatterns: z.array(z.string()).default([]),
  uxPatterns: z.array(z.string()).default([]),
  whatToAdopt: z.array(z.string()).default([]),
  whatToAvoid: z.array(z.string()).default([]),
  rawNotes: z.string().default(""),
});
export type CompetitorIntel = z.infer<typeof CompetitorIntelSchema>;

export const CompetitiveIntelSchema = z.object({
  competitors: z.array(CompetitorIntelSchema),
  synthesizedInsights: z.string(),
  copyInfluences: z.string(),
  structureInfluences: z.string(),
});
export type CompetitiveIntel = z.infer<typeof CompetitiveIntelSchema>;

// ─── Fetch helpers ───────────────────────────────────────────────────────────

async function fetchPageContent(url: string): Promise<string | null> {
  try {
    const resp = await fetch(url, {
      headers: { "User-Agent": "Mozilla/5.0 (compatible; SaaS-Dev-Researcher/1.0)" },
      signal: AbortSignal.timeout(15000),
    });
    if (!resp.ok) return null;
    const html = await resp.text();
    // Strip scripts and styles, keep text content
    return html
      .replace(/<script[\s\S]*?<\/script>/gi, "")
      .replace(/<style[\s\S]*?<\/style>/gi, "")
      .replace(/<[^>]+>/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .slice(0, 15000);
  } catch {
    return null;
  }
}

// ─── Analysis ────────────────────────────────────────────────────────────────

function getClient(): Anthropic {
  return new Anthropic();
}

const ANALYSIS_SYSTEM = `You are a competitive intelligence analyst for SaaS products. Analyze competitor websites to extract actionable patterns for copy, structure, and UX design.

Be specific and tactical — not generic observations. Focus on patterns that a design and copy team can directly apply or intentionally avoid.`;

async function analyzeCompetitor(
  url: string,
  pageContent: string | null,
  brandVoice: string,
  specSummary: string,
): Promise<CompetitorIntel> {
  const client = getClient();

  const contentSection = pageContent
    ? `Here is the extracted text content from ${url}:\n\n${pageContent}`
    : `I could not fetch ${url} directly. Analyze based on your knowledge of this product/company. If you don't have enough information, provide what you can and note the limitation.`;

  const response = await client.messages.create({
    model: "claude-haiku-4-5-20251001",
    max_tokens: 2048,
    system: ANALYSIS_SYSTEM,
    messages: [{
      role: "user",
      content: `Analyze this competitor for a SaaS product.

URL: ${url}
${contentSection}

Our product's brand voice summary: ${brandVoice.slice(0, 500)}
Our product's pages: ${specSummary}

Return a JSON object:
{
  "url": "${url}",
  "name": "competitor name",
  "copyPatterns": ["specific copy patterns observed — tone, CTA style, heading style, microcopy patterns"],
  "structurePatterns": ["page layout patterns — nav structure, content hierarchy, dashboard layout, information density"],
  "uxPatterns": ["UX flow patterns — onboarding flow, empty states, progressive disclosure, interaction patterns"],
  "whatToAdopt": ["specific things worth adopting — be tactical, not generic"],
  "whatToAvoid": ["specific things to avoid — anti-patterns, tone mismatches, confusing flows"],
  "rawNotes": "free-form analysis notes"
}

Return ONLY valid JSON.`,
    }],
  });

  const text = response.content[0];
  if (text.type !== "text") {
    return { url, name: url, copyPatterns: [], structurePatterns: [], uxPatterns: [], whatToAdopt: [], whatToAvoid: [], rawNotes: "Analysis failed: unexpected response type" };
  }

  try {
    const parsed = extractJsonFromResponse(text.text);
    return CompetitorIntelSchema.parse(parsed);
  } catch {
    return { url, name: url, copyPatterns: [], structurePatterns: [], uxPatterns: [], whatToAdopt: [], whatToAvoid: [], rawNotes: text.text.slice(0, 500) };
  }
}

async function synthesizeIntel(
  competitors: CompetitorIntel[],
  brandVoice: string,
): Promise<{ synthesizedInsights: string; copyInfluences: string; structureInfluences: string }> {
  const client = getClient();

  const competitorSummary = competitors.map((c) =>
    `## ${c.name} (${c.url})\nCopy: ${c.copyPatterns.join("; ")}\nStructure: ${c.structurePatterns.join("; ")}\nAdopt: ${c.whatToAdopt.join("; ")}\nAvoid: ${c.whatToAvoid.join("; ")}`
  ).join("\n\n");

  const response = await client.messages.create({
    model: "claude-haiku-4-5-20251001",
    max_tokens: 2048,
    system: ANALYSIS_SYSTEM,
    messages: [{
      role: "user",
      content: `Synthesize competitive intelligence from these analyses into actionable guides.

Our brand voice: ${brandVoice.slice(0, 500)}

Competitor analyses:
${competitorSummary}

Return a JSON object:
{
  "synthesizedInsights": "2-3 paragraph synthesis of key competitive patterns and how our product should position against them",
  "copyInfluences": "Plain language guide for copy writers — what to learn from competitors while maintaining our distinct voice. Be specific: 'Competitor X uses short imperative CTAs like [example] — adopt this pattern but with our operator-focused vocabulary.'",
  "structureInfluences": "Plain language guide for UI designers — what structural patterns to consider from competitors. Be specific: 'Competitor Y uses a floating action panel for key metrics — consider this for our Command Center.'"
}

Return ONLY valid JSON.`,
    }],
  });

  const text = response.content[0];
  if (text.type !== "text") {
    return { synthesizedInsights: "", copyInfluences: "", structureInfluences: "" };
  }

  try {
    const parsed = extractJsonFromResponse(text.text) as { synthesizedInsights: string; copyInfluences: string; structureInfluences: string };
    return {
      synthesizedInsights: parsed.synthesizedInsights ?? "",
      copyInfluences: parsed.copyInfluences ?? "",
      structureInfluences: parsed.structureInfluences ?? "",
    };
  } catch {
    return { synthesizedInsights: "", copyInfluences: "", structureInfluences: "" };
  }
}

// ─── Public API ──────────────────────────────────────────────────────────────

/**
 * Research competitor websites and produce competitive intelligence.
 * Fetches each URL, analyzes with Claude, then synthesizes across all competitors.
 * Graceful on failure — unreachable URLs produce empty intel entries, not errors.
 */
export async function researchCompetitors(
  urls: string[],
  brandVoice: string,
  spec: SpecOutput,
): Promise<CompetitiveIntel> {
  const specSummary = spec.pages
    .map((p) => `${p.name} (${p.route}) — ${p.purpose}`)
    .join("; ");

  console.log(`[competitive-intel] Researching ${urls.length} competitor(s)...`);

  // Fetch all pages in parallel
  const fetches = await Promise.all(
    urls.map(async (url) => {
      const content = await fetchPageContent(url);
      if (!content) {
        console.warn(`[competitive-intel] Could not fetch ${url} — analyzing from knowledge base.`);
      }
      return { url, content };
    }),
  );

  // Analyze each competitor
  const competitors: CompetitorIntel[] = [];
  for (const { url, content } of fetches) {
    try {
      const intel = await analyzeCompetitor(url, content, brandVoice, specSummary);
      competitors.push(intel);
      console.log(`[competitive-intel] Analyzed: ${intel.name} — ${intel.whatToAdopt.length} patterns to adopt, ${intel.whatToAvoid.length} to avoid`);
    } catch (err) {
      console.warn(`[competitive-intel] Failed to analyze ${url}: ${err instanceof Error ? err.message : String(err)}`);
      competitors.push({
        url,
        name: url,
        copyPatterns: [],
        structurePatterns: [],
        uxPatterns: [],
        whatToAdopt: [],
        whatToAvoid: [],
        rawNotes: `Analysis failed: ${err instanceof Error ? err.message : String(err)}`,
      });
    }
  }

  // Synthesize across all competitors
  const synthesis = competitors.some((c) => c.copyPatterns.length > 0 || c.structurePatterns.length > 0)
    ? await synthesizeIntel(competitors, brandVoice)
    : { synthesizedInsights: "", copyInfluences: "", structureInfluences: "" };

  return {
    competitors,
    ...synthesis,
  };
}

/**
 * Format competitive intel as a markdown report.
 */
export function formatCompetitiveIntelReport(intel: CompetitiveIntel): string {
  const lines: string[] = ["# Competitive Intelligence Report", ""];

  for (const c of intel.competitors) {
    lines.push(`## ${c.name}`);
    lines.push(`URL: ${c.url}`, "");
    if (c.copyPatterns.length > 0) {
      lines.push("### Copy Patterns");
      c.copyPatterns.forEach((p) => lines.push(`- ${p}`));
      lines.push("");
    }
    if (c.structurePatterns.length > 0) {
      lines.push("### Structure Patterns");
      c.structurePatterns.forEach((p) => lines.push(`- ${p}`));
      lines.push("");
    }
    if (c.uxPatterns.length > 0) {
      lines.push("### UX Patterns");
      c.uxPatterns.forEach((p) => lines.push(`- ${p}`));
      lines.push("");
    }
    if (c.whatToAdopt.length > 0) {
      lines.push("### What to Adopt");
      c.whatToAdopt.forEach((p) => lines.push(`- ${p}`));
      lines.push("");
    }
    if (c.whatToAvoid.length > 0) {
      lines.push("### What to Avoid");
      c.whatToAvoid.forEach((p) => lines.push(`- ${p}`));
      lines.push("");
    }
    lines.push("---", "");
  }

  if (intel.synthesizedInsights) {
    lines.push("## Synthesized Insights", "", intel.synthesizedInsights, "");
  }
  if (intel.copyInfluences) {
    lines.push("## Copy Influences", "", intel.copyInfluences, "");
  }
  if (intel.structureInfluences) {
    lines.push("## Structure Influences", "", intel.structureInfluences, "");
  }

  return lines.join("\n");
}
