import Anthropic from "../claude-subprocess.js";
import pRetry from "p-retry";
import { BackendSpecSchema } from "@shared/spec-schema.js";
import type { BackendSpec, PageSpecFull } from "@shared/spec-schema.js";
import { extractJsonFromResponse } from "./restructure-spec.js";

/**
 * System prompt instructing Claude to derive a BackendSpec from a PageSpecFull[]
 * data layer. Key behaviors:
 *
 * - D-10 / Pitfall 4: Infer CRUD endpoints for every dataRequirements entry,
 *   even when the data requirement has no explicit source field.
 * - Provenance propagation: endpoints matching an explicit apiEndpoints[] entry
 *   from the page data layer get source: "explicit". All auto-derived endpoints
 *   get source: "inferred".
 * - authRequired: set based on page authLevel (public = false, authenticated/admin = true).
 * - uiPageRef: set to the page route for traceability.
 * - drizzleTableHints: infer from data models implied by dataRequirements.
 * - mismatches: flag any inconsistencies between derived endpoints and existing apiEndpoints.
 */
const DERIVE_BACKEND_SYSTEM_PROMPT = `You are a backend architect. Given an array of PageSpecFull objects (UI page specs), derive a complete BackendSpec JSON object that defines all the API endpoints needed to power those pages.

OUTPUT FORMAT: Return ONLY a valid JSON object — no preamble, no explanation, no markdown fences. The JSON must match this exact shape:

{
  "endpoints": [
    {
      "method": "GET | POST | PUT | PATCH | DELETE",
      "path": "/api/path (must start with /)",
      "description": "what this endpoint does",
      "requestBody": ["field1", "field2"],
      "responseFields": ["field1", "field2"],
      "authRequired": true,
      "uiPageRef": "/page-route",
      "source": "explicit | inferred"
    }
  ],
  "drizzleTableHints": ["table_name1", "table_name2"],
  "backgroundJobs": ["job description"],
  "mismatches": ["any inconsistencies between derived and explicit endpoints"]
}

DERIVATION RULES (apply all of these):

1. For every page, inspect its dataRequirements array. For each entry, infer the necessary CRUD endpoints even if the dataRequirements entry has no source field specified. Always derive endpoints — never skip a dataRequirements entry.

2. PROVENANCE PROPAGATION (critical):
   - For each derived endpoint, check the page's apiEndpoints[] array for a matching path.
   - If the derived endpoint path matches an entry in page.apiEndpoints[], set source: "explicit".
   - If the derived endpoint was NOT explicitly listed in page.apiEndpoints[], set source: "inferred".
   - The default is source: "inferred" — only set source: "explicit" when there is a clear match in the page's apiEndpoints[].

3. AUTH RULES:
   - If page.authLevel is "public", set authRequired: false on all endpoints derived from that page.
   - If page.authLevel is "authenticated" or "admin", set authRequired: true on all endpoints derived from that page.

4. TRACEABILITY: Always set uiPageRef to the page's route for every endpoint.

5. TABLE HINTS: Populate drizzleTableHints with table names implied by the data models across all pages.

6. MISMATCHES: If a page has an apiEndpoints[] entry that doesn't seem to match any dataRequirement, flag it in mismatches.

Return ONLY the JSON object. No other text.`;

/**
 * Auto-derives a BackendSpec from an array of PageSpecFull objects.
 *
 * For each page's dataRequirements, Claude infers CRUD endpoints and applies
 * provenance propagation:
 * - source: "explicit" for endpoints matching the page's explicit apiEndpoints
 * - source: "inferred" for all auto-derived endpoints
 *
 * @param pages - Array of parsed page specs (from SpecOutput.pages)
 * @returns Validated BackendSpec
 */
export async function deriveBackendSpec(pages: PageSpecFull[]): Promise<BackendSpec> {
  const client = new Anthropic();

  return pRetry(
    async () => {
      const response = await client.messages.create({
        model: "claude-sonnet-4-5",
        max_tokens: 8192,
        system: DERIVE_BACKEND_SYSTEM_PROMPT,
        messages: [
          {
            role: "user",
            content: JSON.stringify(pages, null, 2),
          },
        ],
      });

      const firstContent = response.content[0];
      if (firstContent.type !== "text") {
        throw new Error("Unexpected response type from Anthropic API");
      }

      const parsed = extractJsonFromResponse(firstContent.text);
      return BackendSpecSchema.parse(parsed);
    },
    { retries: 2, minTimeout: 1000 }
  );
}
