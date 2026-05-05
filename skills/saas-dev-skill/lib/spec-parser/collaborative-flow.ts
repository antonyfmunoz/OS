import Anthropic from "@anthropic-ai/sdk";
import { SpecOutputSchema } from "@shared/spec-schema.js";
import type { SpecOutput } from "@shared/spec-schema.js";
import { extractJsonFromResponse } from "./restructure-spec.js";
import { getAnthropicApiKey, getAnthropicBaseUrl } from "../env.js";

// ─── Question Sequence ────────────────────────────────────────────────────────

/**
 * Domain-first questioning sequence for collaborative spec creation (SPEC-02).
 * Each stage covers one aspect of the product definition, progressing from
 * high-level vision to specific page detail to implied requirements.
 */
export const QUESTION_SEQUENCE = [
  "vision",      // What is this product? Who is it for? What problem does it solve?
  "user-flows",  // What are the 3-5 core things a user does? Walk me through each.
  "pages",       // What pages/screens do those flows require? List them.
  "page-detail", // For each page: what components, data, auth level?
  "implied",     // Review: what requirements are implied but not stated? (errors, empty states, auth gates, loading)
] as const;

export type QuestionStage = (typeof QUESTION_SEQUENCE)[number];

// ─── CollaborativeState ───────────────────────────────────────────────────────

/**
 * State for the collaborative spec creation session.
 *
 * Note on persistence (addresses Gemini MEDIUM concern): For v1, collaborative
 * state lives in the Claude Code conversation context. The skill manages state
 * through the QUESTION_SEQUENCE loop within a single session. Future versions
 * could persist CollaborativeState to Neon's pipeline_runs table as JSON for
 * cross-session resume.
 */
export interface CollaborativeState {
  stage: QuestionStage;
  stageIndex: number;
  messages: Array<{ role: "user" | "assistant"; content: string }>;
  /** URLs, screenshots, "make it like X" references accepted at any point (D-08) */
  references: string[];
  partialSpec: Partial<SpecOutput> | null;
  complete: boolean;
}

// ─── createInitialState ───────────────────────────────────────────────────────

/**
 * Returns initial collaborative state, ready for the vision stage.
 */
export function createInitialState(): CollaborativeState {
  return {
    stage: "vision",
    stageIndex: 0,
    messages: [],
    references: [],
    partialSpec: null,
    complete: false,
  };
}

// ─── buildSystemPromptForStage ────────────────────────────────────────────────

/**
 * Returns a system prompt for Claude tailored to the current questioning stage.
 * Each prompt includes priorContext so Claude has full conversation history.
 * Each prompt also instructs Claude to accept references (D-08).
 */
export function buildSystemPromptForStage(
  stage: QuestionStage,
  priorContext: string
): string {
  const referenceNote = `
At any point in this conversation, accept references the user provides — URLs, screenshots, descriptions like "make it like [product]", or example apps. Note them and incorporate their patterns into your understanding of the spec.`;

  const contextSection = priorContext
    ? `\n\nPrior conversation context:\n${priorContext}`
    : "";

  switch (stage) {
    case "vision":
      return `You are a SaaS product spec collaborator. Your goal is to understand this product at a high level.

Ask the user about:
1. What is the product? What does it do?
2. Who is the target audience? What is their pain point?
3. What core problem does this product solve?
4. What is the revenue model (subscription, one-time, freemium)?

Keep questions conversational and focused. Don't overwhelm the user — pick the most important questions if they haven't answered yet.${referenceNote}${contextSection}`;

    case "user-flows":
      return `You are a SaaS product spec collaborator. You now understand the product vision. Your goal is to map out the core user journeys.

Ask the user to describe the 3-5 core things a user does in this product. For each user journey, ask them to walk through it step by step — what does the user do, what does the system show, what happens next?

Focus on the most critical flows first. Examples: "a user signs up and sets up their account", "a user creates their first project", "a user views their analytics dashboard".

Keep the conversation flowing — if the user describes a flow well, confirm your understanding and move to the next one.${referenceNote}${contextSection}`;

    case "pages":
      return `You are a SaaS product spec collaborator. You now have a clear picture of the user flows. Your goal is to identify all required pages/screens.

Based on the flows we've discussed, derive the page list. Present your understanding of what pages are needed and ask the user to confirm or add to it.

For each page group, ask:
- Auth pages (login, signup, forgot password)?
- Core feature pages from the flows?
- Settings/profile pages?
- Admin pages if applicable?

Present your derived page list clearly and ask the user to confirm, correct, or add pages.${referenceNote}${contextSection}`;

    case "page-detail":
      return `You are a SaaS product spec collaborator. You now have the page list. Your goal is to understand the detail of each page.

For each page, ask about:
1. What components/UI elements does this page need?
2. What data does it display or collect?
3. What is the auth level? (public, authenticated, admin)
4. Any layout preferences or special considerations?

Work through pages systematically. If the user gives a comprehensive answer for one page, acknowledge it and move to the next. Focus on components, data needs, and auth level as the essentials.${referenceNote}${contextSection}`;

    case "implied":
      return `You are a SaaS product spec collaborator. You now have detailed page specs. Your final goal is to surface implied requirements.

Review all the information gathered and ask the user about:
1. Error states — what happens when data fails to load, form submission fails, or the user encounters an error?
2. Empty states — what do pages look like before the user has any data?
3. Loading states — what do data-driven pages show while loading?
4. Auth gates — are there any pages or features that need special auth handling?
5. 404/not-found handling — what happens when the user navigates to a nonexistent route?

Present your implied requirements and ask the user to confirm or add anything missing.${referenceNote}${contextSection}`;

    default: {
      // TypeScript exhaustiveness — this branch should never be reached
      const _exhaustive: never = stage;
      return `Unknown stage: ${_exhaustive}`;
    }
  }
}

// ─── isFlowComplete ───────────────────────────────────────────────────────────

/**
 * Returns true when all questioning stages are complete and a partial spec exists.
 * stageIndex >= QUESTION_SEQUENCE.length means all 5 stages have been answered.
 */
export function isFlowComplete(state: CollaborativeState): boolean {
  return state.stageIndex >= QUESTION_SEQUENCE.length && state.partialSpec !== null;
}

// ─── extractSpecFromConversation ──────────────────────────────────────────────

/**
 * Extracts a complete SpecOutput from the full collaborative conversation history.
 *
 * Sends all messages to Claude with a system prompt that instructs it to:
 * - Extract a complete SpecOutput JSON from the conversation
 * - Mark items the user explicitly mentioned as source: "explicit"
 * - Mark items Claude inferred as source: "inferred"
 *
 * Validates with SpecOutputSchema.parse() before returning.
 */
export async function extractSpecFromConversation(
  messages: Array<{ role: "user" | "assistant"; content: string }>
): Promise<SpecOutput> {
  const client = new Anthropic({
    apiKey: getAnthropicApiKey(),
    baseURL: getAnthropicBaseUrl(),
  });

  const systemPrompt = `You are a SaaS product spec extractor. You have been given the full transcript of a collaborative spec creation conversation. Your job is to extract all gathered information into a precise SpecOutput JSON object.

OUTPUT FORMAT: Return ONLY a valid JSON object — no preamble, no explanation, no markdown fences. The JSON must match this exact shape:

{
  "pages": [
    {
      "name": "string (PascalCase component name, e.g. Dashboard)",
      "route": "string (must start with /, e.g. /dashboard)",
      "purpose": "string (1-2 sentence description)",
      "components": ["string array of component names"],
      "authLevel": "public | authenticated | admin",
      "priority": "integer starting at 1",
      "dependsOn": ["routes this page depends on"],
      "specVersion": 1,
      "source": "explicit | inferred",
      "layoutHint": "optional layout description",
      "emptyState": "optional description of empty state",
      "loadingState": "optional description of loading state",
      "errorState": "optional description of error state",
      "mobileConsiderations": "optional mobile notes",
      "dataRequirements": [{ "component": "ComponentName", "fields": ["field1"] }],
      "apiEndpoints": [{ "endpoint": "/api/path", "source": "explicit | inferred" }],
      "validationRules": ["validation rules"],
      "events": [{ "name": "event_name", "trigger": "trigger description", "properties": [], "source": "explicit | inferred" }],
      "featureFlagCandidates": []
    }
  ],
  "sharedComponents": [
    {
      "id": "unique-kebab-case-id",
      "name": "ComponentName",
      "purpose": "what this shared component does",
      "usedByPages": ["/route1"],
      "props": ["prop1"],
      "source": "explicit | inferred"
    }
  ],
  "suggestedOrder": ["/route1", "/route2"],
  "backendSpec": {
    "endpoints": [
      {
        "method": "GET | POST | PUT | PATCH | DELETE",
        "path": "/api/path",
        "description": "what this endpoint does",
        "requestBody": [],
        "responseFields": [],
        "authRequired": true,
        "source": "explicit | inferred"
      }
    ],
    "drizzleTableHints": [],
    "backgroundJobs": [],
    "mismatches": []
  }
}

PROVENANCE RULES (critical for the confirmation gate):
- Set source: "explicit" on any page, component, endpoint, or event that the user explicitly described in the conversation
- Set source: "inferred" on anything you add, expand, or derive that was NOT in the user's conversation
- This applies to: each page source, each apiEndpoints[].source, each events[].source, each sharedComponent.source, each backendSpec endpoint source

GAP-FILLING RULES (always apply):
1. If user mentions authenticated features, add a Login page (source: "inferred") if not present
2. Infer emptyState, loadingState, errorState for all data-driven pages
3. Infer API endpoints from data requirements
4. Set dependsOn based on page relationships
5. Populate suggestedOrder starting with auth pages
6. Add analytics events for key user actions

Return ONLY the JSON object. No other text.`;

  const response = await client.messages.create({
    model: "claude-sonnet-4-5",
    max_tokens: 8192,
    system: systemPrompt,
    messages: messages as Anthropic.MessageParam[],
  });

  const firstContent = response.content[0];
  if (firstContent.type !== "text") {
    throw new Error("Unexpected response type from Anthropic API");
  }

  const parsed = extractJsonFromResponse(firstContent.text);
  return SpecOutputSchema.parse(parsed);
}
