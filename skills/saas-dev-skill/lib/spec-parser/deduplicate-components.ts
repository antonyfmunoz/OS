import Anthropic from "@anthropic-ai/sdk";
import pRetry from "p-retry";
import { SharedComponentSpec } from "@shared/spec-schema.js";
import type { PageSpecFull } from "@shared/spec-schema.js";
import { extractJsonFromResponse } from "./restructure-spec.js";
import { getAnthropicApiKey, getAnthropicBaseUrl } from "../env.js";

/**
 * System prompt for AI-powered semantic deduplication of shared components.
 *
 * Key behaviors:
 * - D-20/D-21: Identify semantically identical components (different names, same purpose)
 * - Merge props arrays (Gemini LOW concern: property merging)
 * - Provenance rule: if ANY component in a merge group has source: "explicit",
 *   the merged result must be source: "explicit" (explicit always wins over inferred)
 * - Preserve all usedByPages across merged components
 */
const DEDUP_SYSTEM_PROMPT = `You are a React component architect. Given an array of SharedComponentSpec objects extracted from multiple pages of a SaaS spec, identify semantically identical components and merge them into a single canonical component.

OUTPUT FORMAT: Return ONLY a valid JSON object — no preamble, no explanation, no markdown fences. The JSON must match this exact shape:

{
  "deduplicated": [
    {
      "id": "unique-kebab-case-id",
      "name": "ComponentName",
      "purpose": "combined purpose description",
      "usedByPages": ["/route1", "/route2"],
      "props": ["prop1", "prop2"],
      "source": "explicit | inferred"
    }
  ],
  "merges": [
    {
      "merged": ["id-1", "id-2"],
      "into": "id-1"
    }
  ]
}

DEDUPLICATION RULES (apply all of these):

1. SEMANTIC MATCHING: Identify components that are functionally the same even when named differently.
   Examples of semantic matches:
   - "SidebarNav" and "LeftNavRail" → both are navigation sidebars
   - "UserAvatar" and "ProfilePicture" → both display a user's profile image
   - "DataTable" and "ItemList" → both display tabular/list data

2. MERGING RULES:
   - Keep the most descriptive name and purpose
   - Combine usedByPages arrays (union, no duplicates)
   - Merge props arrays (union of all props from all merged components, no duplicates)
   - Use the ID from the component with the most descriptive name

3. PROVENANCE RULE (critical — always apply this):
   - When merging a group of components, check ALL components in the merge group for source: "explicit"
   - If ANY component in the merge group has source: "explicit", the merged result must have source: "explicit"
   - Only set source: "inferred" on the merged result if ALL components in the merge group have source: "inferred"
   - The rule: explicit always wins over inferred when merging

4. NON-DUPLICATES: If components are genuinely different (different purposes, different usage), keep them separate in deduplicated array with empty merges array.

5. merges array: Document every merge operation — each entry lists which IDs were merged and which ID they were merged into. If no merges happen, return an empty merges array.

Return ONLY the JSON object. No other text.`;

/**
 * Result type for deduplication — includes the cleaned component list and
 * a record of what was merged (for D-22 user confirmation flow).
 */
export interface DeduplicationResult {
  deduplicated: ReturnType<typeof SharedComponentSpec.parse>[];
  merges: Array<{
    merged: string[];
    into: string;
  }>;
}

/**
 * AI-powered semantic deduplication of shared components across pages.
 *
 * Identifies semantically identical components (e.g., "SidebarNav" and "LeftNavRail")
 * and merges them into a single canonical SharedComponentSpec.
 *
 * Provenance rule: if ANY component in a merge group is source: "explicit",
 * the merged result is source: "explicit" (explicit always wins over inferred).
 *
 * @param components - Array of SharedComponentSpec objects to deduplicate
 * @param pages - Page specs for context (helps AI understand component usage)
 * @returns Deduplicated component list with merge record for D-22 confirmation
 */
export async function deduplicateComponents(
  components: ReturnType<typeof SharedComponentSpec.parse>[],
  pages: PageSpecFull[]
): Promise<DeduplicationResult> {
  // No deduplication needed for 0 or 1 components
  if (components.length <= 1) {
    return { deduplicated: components, merges: [] };
  }

  const client = new Anthropic({
    apiKey: getAnthropicApiKey(),
    baseURL: getAnthropicBaseUrl(),
  });

  return pRetry(
    async () => {
      const userMessage = JSON.stringify(
        {
          components,
          pageContext: pages.map((p) => ({ route: p.route, name: p.name, components: p.components })),
        },
        null,
        2
      );

      const response = await client.messages.create({
        model: "claude-sonnet-4-5",
        max_tokens: 4096,
        system: DEDUP_SYSTEM_PROMPT,
        messages: [{ role: "user", content: userMessage }],
      });

      const firstContent = response.content[0];
      if (firstContent.type !== "text") {
        throw new Error("Unexpected response type from Anthropic API");
      }

      const parsed = extractJsonFromResponse(firstContent.text) as {
        deduplicated: unknown[];
        merges: Array<{ merged: string[]; into: string }>;
      };

      if (!parsed || !Array.isArray(parsed.deduplicated) || !Array.isArray(parsed.merges)) {
        throw new Error("Invalid deduplication response shape");
      }

      // Validate each returned component
      const deduplicated = parsed.deduplicated.map((c) =>
        SharedComponentSpec.parse(c)
      );

      return {
        deduplicated,
        merges: parsed.merges,
      };
    },
    { retries: 2, minTimeout: 1000 }
  );
}
