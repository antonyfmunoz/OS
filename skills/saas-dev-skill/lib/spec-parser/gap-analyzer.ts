// lib/spec-parser/gap-analyzer.ts
// Analyzes a draft SpecOutput for missing pages, flows, states, and assumptions.
// Pure static checks + optional LLM contextual analysis.

import Anthropic from "@anthropic-ai/sdk";
import type { SpecOutput, PageSpecFull } from "@shared/spec-schema.js";
import { getAnthropicApiKey, getAnthropicBaseUrl } from "../env.js";

// ─── Types ───────────────────────────────────────────────────────────────────

export interface GapItem {
  severity: "blocking" | "recommended" | "optional";
  category: string;
  description: string;
  affectedPages: string[];
  suggestedResolution: string;
}

export interface GapAnalysis {
  missingPages: GapItem[];
  missingFlows: GapItem[];
  missingStates: GapItem[];
  assumptions: GapItem[];
  suggestions: GapItem[];
  questions: GapItem[];
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function pageRoutes(spec: SpecOutput): Set<string> {
  return new Set(spec.pages.map((p) => p.route));
}

function hasPageMatching(spec: SpecOutput, pattern: RegExp): boolean {
  return spec.pages.some(
    (p) => pattern.test(p.route) || pattern.test(p.name.toLowerCase()),
  );
}

function hasAuthenticatedPages(spec: SpecOutput): boolean {
  return spec.pages.some(
    (p) => p.authLevel === "authenticated" || p.authLevel === "admin",
  );
}

function hasSignupOrRegister(spec: SpecOutput): boolean {
  return hasPageMatching(spec, /sign[-_]?up|register/i);
}

function hasPasswordReset(spec: SpecOutput): boolean {
  return hasPageMatching(spec, /reset[-_]?password|forgot[-_]?password/i);
}

function has404Page(spec: SpecOutput): boolean {
  return hasPageMatching(spec, /not[-_]?found|404/i);
}

function hasOnboarding(spec: SpecOutput): boolean {
  return hasPageMatching(spec, /onboard|welcome|setup|getting[-_]?started/i);
}

function hasProfileOrSettings(spec: SpecOutput): boolean {
  return hasPageMatching(spec, /profile|settings|account|preferences/i);
}

// ─── Static Gap Checks ──────────────────────────────────────────────────────

function checkMissingOnboarding(spec: SpecOutput): GapItem | null {
  if (hasSignupOrRegister(spec) && !hasOnboarding(spec)) {
    return {
      severity: "blocking",
      category: "missing-flow",
      description:
        "Spec has signup/register but no onboarding or welcome page. New users have no guided first-run experience.",
      affectedPages: spec.pages
        .filter((p) => /sign[-_]?up|register/i.test(p.route) || /sign[-_]?up|register/i.test(p.name.toLowerCase()))
        .map((p) => p.route),
      suggestedResolution:
        "Add an onboarding/welcome page that guides new users through initial setup after registration.",
    };
  }
  return null;
}

function checkMissing404(spec: SpecOutput): GapItem | null {
  if (!has404Page(spec)) {
    return {
      severity: "recommended",
      category: "missing-page",
      description: "No 404/not-found page in spec. Users hitting invalid routes will see a blank or framework-default error.",
      affectedPages: [],
      suggestedResolution: "Add a NotFound page at /* or /404 with navigation back to home.",
    };
  }
  return null;
}

function checkMissingEmptyStates(spec: SpecOutput): GapItem[] {
  return spec.pages
    .filter((p) => p.dataRequirements.length > 0 && !p.emptyState)
    .map((p) => ({
      severity: "recommended" as const,
      category: "missing-state",
      description: `Page "${p.name}" has data requirements but no emptyState defined.`,
      affectedPages: [p.route],
      suggestedResolution: `Define what "${p.name}" shows when the user has no data yet (first-run experience).`,
    }));
}

function checkMissingErrorStates(spec: SpecOutput): GapItem[] {
  return spec.pages
    .filter((p) => p.apiEndpoints.length > 0 && !p.errorState)
    .map((p) => ({
      severity: "recommended" as const,
      category: "missing-state",
      description: `Page "${p.name}" has API endpoints but no errorState defined.`,
      affectedPages: [p.route],
      suggestedResolution: `Define what "${p.name}" shows when API calls fail (error message, retry button, fallback content).`,
    }));
}

function checkMissingMobileConsiderations(spec: SpecOutput): GapItem[] {
  return spec.pages
    .filter(
      (p) =>
        p.components.length > 3 &&
        !p.mobileConsiderations &&
        p.layoutHint &&
        /grid|panel|sidebar|multi|column/i.test(p.layoutHint),
    )
    .map((p) => ({
      severity: "optional" as const,
      category: "missing-mobile",
      description: `Page "${p.name}" has a complex layout ("${p.layoutHint}") but no mobileConsiderations.`,
      affectedPages: [p.route],
      suggestedResolution: `Add mobile layout notes for "${p.name}" — how do panels stack, what collapses, what scrolls horizontally.`,
    }));
}

function checkAuthGaps(spec: SpecOutput): GapItem | null {
  if (hasAuthenticatedPages(spec) && hasSignupOrRegister(spec) && !hasPasswordReset(spec)) {
    return {
      severity: "blocking",
      category: "auth-gap",
      description:
        "Authenticated pages and signup exist, but no password reset/forgot password flow. Users who forget their password are locked out.",
      affectedPages: spec.pages
        .filter((p) => p.authLevel === "authenticated" || p.authLevel === "admin")
        .map((p) => p.route),
      suggestedResolution:
        "Add a ForgotPassword page (public) and a ResetPassword page (public) to the spec.",
    };
  }
  return null;
}

function checkMissingProfile(spec: SpecOutput): GapItem | null {
  if (hasAuthenticatedPages(spec) && !hasProfileOrSettings(spec)) {
    return {
      severity: "recommended",
      category: "missing-page",
      description:
        "Authenticated app with no settings, profile, or account page. Users cannot manage their account.",
      affectedPages: [],
      suggestedResolution:
        "Add a Settings or Profile page where users can update their account details, change password, and manage preferences.",
    };
  }
  return null;
}

function checkOrphanedRoutes(spec: SpecOutput): GapItem[] {
  const routes = pageRoutes(spec);
  const gaps: GapItem[] = [];

  for (const page of spec.pages) {
    for (const dep of page.dependsOn) {
      if (!routes.has(dep)) {
        gaps.push({
          severity: "blocking",
          category: "orphaned-route",
          description: `Page "${page.name}" depends on route "${dep}" which does not exist in the spec.`,
          affectedPages: [page.route],
          suggestedResolution: `Either add a page at "${dep}" or remove it from "${page.name}".dependsOn.`,
        });
      }
    }
  }

  return gaps;
}

// ─── LLM Contextual Analysis ────────────────────────────────────────────────

async function llmContextualAnalysis(spec: SpecOutput): Promise<GapItem[]> {
  const client = new Anthropic({
    apiKey: getAnthropicApiKey(),
    baseURL: getAnthropicBaseUrl(),
  });

  const specSummary = spec.pages
    .map(
      (p) =>
        `- ${p.name} (${p.route}) — ${p.purpose} [auth: ${p.authLevel}, components: ${p.components.length}]`,
    )
    .join("\n");

  const response = await client.messages.create({
    model: "claude-haiku-4-5-20251001",
    max_tokens: 2048,
    system: `You are a SaaS product analyst. Given a spec summary, identify missing pages or flows that a product of this type typically needs. Return a JSON array of objects with: { "description": "what is missing", "suggestedResolution": "how to fix it", "affectedPages": ["routes affected"] }. Return ONLY the JSON array, no other text. Focus on genuinely missing functionality, not stylistic preferences. Limit to 5 most important items.`,
    messages: [
      {
        role: "user",
        content: `Here is the page spec for a SaaS product:\n\n${specSummary}\n\nWhat important pages or flows are missing for a product of this type?`,
      },
    ],
  });

  const text = response.content[0];
  if (text.type !== "text") return [];

  const parsed = JSON.parse(text.text);
  if (!Array.isArray(parsed)) return [];

  return parsed.map(
    (item: { description: string; suggestedResolution: string; affectedPages?: string[] }) => ({
      severity: "optional" as const,
      category: "llm-suggestion",
      description: item.description,
      affectedPages: item.affectedPages ?? [],
      suggestedResolution: item.suggestedResolution,
    }),
  );
}

// ─── Main Analyzer ───────────────────────────────────────────────────────────

export async function analyzeGaps(
  spec: SpecOutput,
  options: { skipLlm?: boolean } = {},
): Promise<GapAnalysis> {
  const analysis: GapAnalysis = {
    missingPages: [],
    missingFlows: [],
    missingStates: [],
    assumptions: [],
    suggestions: [],
    questions: [],
  };

  // Missing flows
  const onboarding = checkMissingOnboarding(spec);
  if (onboarding) analysis.missingFlows.push(onboarding);

  const authGap = checkAuthGaps(spec);
  if (authGap) analysis.missingFlows.push(authGap);

  // Missing pages
  const notFound = checkMissing404(spec);
  if (notFound) analysis.missingPages.push(notFound);

  const profile = checkMissingProfile(spec);
  if (profile) analysis.missingPages.push(profile);

  // Orphaned routes (blocking)
  const orphaned = checkOrphanedRoutes(spec);
  analysis.missingPages.push(...orphaned);

  // Missing states
  analysis.missingStates.push(...checkMissingEmptyStates(spec));
  analysis.missingStates.push(...checkMissingErrorStates(spec));
  analysis.missingStates.push(...checkMissingMobileConsiderations(spec));

  // LLM contextual suggestions (graceful degradation)
  if (!options.skipLlm) {
    try {
      const llmSuggestions = await llmContextualAnalysis(spec);
      analysis.suggestions.push(...llmSuggestions);
    } catch {
      // LLM analysis is best-effort — static checks still run
    }
  }

  return analysis;
}

export function hasBlockingGaps(analysis: GapAnalysis): boolean {
  const all = [
    ...analysis.missingPages,
    ...analysis.missingFlows,
    ...analysis.missingStates,
    ...analysis.assumptions,
    ...analysis.suggestions,
    ...analysis.questions,
  ];
  return all.some((g) => g.severity === "blocking");
}
