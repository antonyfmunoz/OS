import Anthropic from "../claude-subprocess.js";
import pRetry from "p-retry";
import { SpecOutputSchema } from "@shared/spec-schema.js";
import type { SpecOutput } from "@shared/spec-schema.js";

/**
 * Strips markdown fences (```json...``` or ```...```) and parses JSON.
 * Returns the parsed object, throws on invalid JSON.
 */
export function extractJsonFromResponse(text: string): unknown {
  let s = text.trim();

  // 1. Strip a leading ```json / ``` fence and the matching closing fence,
  //    even if there's preamble/trailing text around them.
  const fenceOpen = s.match(/```(?:json)?\s*\n?/);
  if (fenceOpen && fenceOpen.index !== undefined) {
    const after = s.slice(fenceOpen.index + fenceOpen[0].length);
    const closeIdx = after.lastIndexOf("```");
    s = closeIdx === -1 ? after : after.slice(0, closeIdx);
    s = s.trim();
  }

  // 2. Direct parse attempt.
  try {
    return JSON.parse(s);
  } catch {
    // fall through
  }

  // 3. Fallback: extract the outermost balanced JSON object/array by scanning
  //    for the first { or [ and matching braces, skipping strings/escapes.
  const firstObj = s.indexOf("{");
  const firstArr = s.indexOf("[");
  const start =
    firstObj === -1 ? firstArr : firstArr === -1 ? firstObj : Math.min(firstObj, firstArr);
  if (start === -1) {
    throw new Error(`No JSON object or array found in response: ${text.slice(0, 200)}`);
  }
  const open = s[start];
  const close = open === "{" ? "}" : "]";
  let depth = 0;
  let inString = false;
  let escape = false;
  for (let i = start; i < s.length; i++) {
    const ch = s[i];
    if (escape) { escape = false; continue; }
    if (ch === "\\") { escape = true; continue; }
    if (ch === '"') { inString = !inString; continue; }
    if (inString) continue;
    if (ch === open) depth++;
    else if (ch === close) {
      depth--;
      if (depth === 0) {
        return JSON.parse(s.slice(start, i + 1));
      }
    }
  }
  throw new Error(`Unbalanced JSON in response: ${text.slice(0, 200)}`);
}

/**
 * System prompt instructing Claude to restructure any spec input into a
 * validated SpecOutput JSON object.
 *
 * Key instructions per design decisions:
 * - D-02: fill technical gaps (infer missing components, states, etc.)
 * - D-05: populate all four layers for every page
 * - D-13: detect page dependencies and populate dependsOn arrays
 * - D-14: set priority values with foundational pages as priority 1
 * - D-15: include suggestedOrder array of routes
 * - D-20: identify shared components across pages
 * - SPEC-05: always infer implied requirements
 * - Provenance: source: "explicit" for user-described items, source: "inferred" for AI additions
 */
const RESTRUCTURE_SYSTEM_PROMPT = `You are a SaaS product spec analyzer. Your job is to take any format of product specification (markdown, plain text, Notion export, bullet list, or prose) and restructure it into a precise JSON object.

OUTPUT FORMAT: Return ONLY a valid JSON object — no preamble, no explanation, no markdown fences. The JSON must match this exact shape:

{
  "pages": [
    {
      "name": "string (PascalCase component name, e.g. Dashboard)",
      "route": "string (must start with /, e.g. /dashboard)",
      "purpose": "string (1-2 sentence description of what this page does)",
      "components": ["string array of component names on this page"],
      "authLevel": "public | authenticated | admin",
      "priority": "integer starting at 1 (foundational pages like login/signup = 1, core features = 2, settings/admin = 3+)",
      "dependsOn": ["routes this page depends on, e.g. /auth/callback depends on /login"],
      "specVersion": 1,
      "source": "explicit | inferred (explicit if user described this page, inferred if you added it)",
      "layoutHint": "optional layout description, e.g. sidebar-main, centered, full-width-grid",
      "emptyState": "optional description of what the empty state looks like and says",
      "loadingState": "optional description of loading state for data-driven pages",
      "errorState": "optional description of error state when data fails to load",
      "mobileConsiderations": "optional notes about mobile layout differences",
      "dataRequirements": [
        { "component": "ComponentName", "fields": ["field1", "field2"] }
      ],
      "apiEndpoints": [
        { "endpoint": "/api/path", "source": "explicit | inferred" }
      ],
      "validationRules": ["array of validation rules for forms on this page"],
      "events": [
        {
          "name": "event_name (snake_case)",
          "trigger": "what triggers this event, e.g. page load, button click",
          "properties": ["property1", "property2"],
          "source": "explicit | inferred"
        }
      ],
      "featureFlagCandidates": ["feature flags that could control rollout of features on this page"]
    }
  ],
  "sharedComponents": [
    {
      "id": "unique-kebab-case-id",
      "name": "ComponentName",
      "purpose": "what this shared component does",
      "usedByPages": ["/route1", "/route2"],
      "props": ["prop1", "prop2"],
      "source": "explicit | inferred"
    }
  ],
  "suggestedOrder": ["/route1", "/route2"],
  "backendSpec": {
    "endpoints": [
      {
        "method": "GET | POST | PUT | PATCH | DELETE",
        "path": "/api/path (must start with /)",
        "description": "what this endpoint does",
        "requestBody": ["field1", "field2"],
        "responseFields": ["field1", "field2"],
        "authRequired": true,
        "uiPageRef": "/dashboard",
        "source": "explicit | inferred"
      }
    ],
    "drizzleTableHints": ["table names to create in the database"],
    "backgroundJobs": ["async jobs needed, e.g. send-welcome-email"],
    "mismatches": ["any UI/backend inconsistencies detected"]
  }
}

PROVENANCE RULES (critical for the confirmation gate):
- Set source: "explicit" on any page, component, endpoint, or event that the user explicitly described in their input
- Set source: "inferred" on anything you add, expand, or derive that was NOT in the user's input
- This applies to: each page's source field, each apiEndpoints[].source, each events[].source, each sharedComponent.source, each backendSpec endpoint's source

GAP-FILLING RULES (always apply these):
1. If user mentions a protected/authenticated feature, add a Login page with authLevel: "public" (source: "inferred") if not present
2. If user mentions any data display, add emptyState, loadingState, and errorState for that page
3. If user mentions forms, infer appropriate validation rules
4. If multiple pages share navigation (sidebar, header, nav), extract these as sharedComponents
5. Infer API endpoints from data requirements and form submissions
6. Set dependsOn based on page relationships (e.g., detail pages depend on list pages)
7. Populate suggestedOrder starting with auth pages, then core features, then secondary, then settings/admin
8. Add analytics events for key user actions even if not explicitly mentioned
9. For dashboard/analytics pages, always populate all four layers (dataRequirements, apiEndpoints, events, emptyState/loadingState/errorState)
10. Infer shared backend tables from page data requirements

AUTH INFERENCE:
- Pages with login/signup/reset-password in name/route → authLevel: "public"
- Admin pages → authLevel: "admin"
- Everything else that requires the user to be logged in → authLevel: "authenticated"

PRIORITY RULES:
- Auth pages (login, signup, forgot-password) → priority: 1
- Core app shell (layout, nav) → priority: 1
- Primary feature pages → priority: 2
- Secondary features, settings → priority: 3
- Admin pages → priority: 4

Return ONLY the JSON object. No other text.`;

/**
 * Restructures raw spec input into a validated SpecOutput using Claude AI.
 *
 * Uses p-retry for transient error handling. If Zod validation fails on the
 * first attempt, sends validation errors back to Claude for self-correction.
 *
 * @param rawInput - Raw spec text in any format
 * @returns Validated SpecOutput
 */
export async function restructureSpec(rawInput: string): Promise<SpecOutput> {
  const client = new Anthropic();

  // Stream long responses — Anthropic SDK refuses non-streaming calls that
  // may exceed 10 minutes (triggered at high max_tokens). We accumulate text
  // deltas and then feed the full text through the JSON extractor.
  async function callOnce(msgs: Anthropic.MessageParam[]): Promise<string> {
    const stream = client.messages.stream({
      model: "claude-sonnet-4-5",
      max_tokens: 32000,
      system: RESTRUCTURE_SYSTEM_PROMPT,
      messages: msgs,
    });
    const finalMessage = await stream.finalMessage();
    const firstContent = finalMessage.content[0];
    if (!firstContent || firstContent.type !== "text") {
      throw new Error("Unexpected response type from Anthropic API");
    }
    return firstContent.text;
  }

  return pRetry(
    async () => {
      const messages: Anthropic.MessageParam[] = [
        { role: "user", content: rawInput },
      ];

      const firstText = await callOnce(messages);
      const parsed = extractJsonFromResponse(firstText);

      // Attempt Zod validation — on failure, ask Claude to self-correct
      const validationResult = SpecOutputSchema.safeParse(parsed);
      if (validationResult.success) {
        return validationResult.data;
      }

      // Self-correction: send validation errors back to Claude (up to 2 retries)
      const errorDetails = validationResult.error.errors
        .map((e) => `${e.path.join(".")}: ${e.message}`)
        .join("\n");

      const correctionMessages: Anthropic.MessageParam[] = [
        { role: "user", content: rawInput },
        { role: "assistant", content: firstText },
        {
          role: "user",
          content: `The JSON you returned failed validation. Please fix these errors and return the corrected JSON only:\n\n${errorDetails}`,
        },
      ];

      let correctionAttempts = 0;
      while (correctionAttempts < 2) {
        const correctionText = await callOnce(correctionMessages);

        const correctedParsed = extractJsonFromResponse(correctionText);
        const correctionResult = SpecOutputSchema.safeParse(correctedParsed);
        if (correctionResult.success) {
          return correctionResult.data;
        }

        // Update messages for next correction round
        correctionMessages.push(
          { role: "assistant", content: correctionText },
          {
            role: "user",
            content: `Still invalid. Fix these errors:\n\n${correctionResult.error.errors
              .map((e) => `${e.path.join(".")}: ${e.message}`)
              .join("\n")}`,
          }
        );
        correctionAttempts++;
      }

      // If still failing after correction attempts, throw to trigger pRetry
      throw new Error(
        `Spec restructuring failed Zod validation after ${correctionAttempts} correction attempts: ${errorDetails}`
      );
    },
    {
      retries: 3,
      minTimeout: 1000,
      factor: 2,
    }
  );
}
