// lib/copy-planner/copy-reviewer.ts
// Reviews all project copy at once for cross-page voice consistency and brand compliance.

import Anthropic from "@anthropic-ai/sdk";
import { z } from "zod";
import { getAnthropicApiKey, getAnthropicBaseUrl } from "../env.js";
import { extractJsonFromResponse } from "../spec-parser/restructure-spec.js";
import { ProjectCopySchema, type ProjectCopy } from "./types.js";

function getClient(): Anthropic {
  return new Anthropic({
    apiKey: getAnthropicApiKey(),
    baseURL: getAnthropicBaseUrl(),
  });
}

const CopyReviewResultSchema = z.object({
  overallScore: z.number().min(0).max(1),
  passed: z.boolean(),
  pageResults: z.array(z.object({
    pageName: z.string(),
    score: z.number().min(0).max(1),
    issues: z.array(z.string()),
  })),
  revisedCopy: ProjectCopySchema,
});
export type CopyReviewResult = z.infer<typeof CopyReviewResultSchema>;

/**
 * Review all project copy for brand voice compliance and cross-page consistency.
 * Always returns revised copy — even if passed, it's polished.
 */
export async function reviewProjectCopy(
  copy: ProjectCopy,
  brandVoice: string,
): Promise<CopyReviewResult> {
  const client = getClient();

  const userPrompt = `Review this UI copy for a SaaS product. Score each page 0-1 on brand voice compliance, then produce a revised version that fixes all issues.

Review criteria:
1. Does every heading, CTA, and message match the brand voice tone?
2. Is copy consistent across pages (same terminology, same patterns)?
3. Are CTAs verb-forward and action-oriented?
4. Are empty states warm and actionable (not generic)?
5. Are error messages blame-free and specific?
6. Is there any generic SaaS language that should be replaced?
7. Are nav labels concise and outcome-focused?

Current copy:
${JSON.stringify(copy, null, 2)}

Return a JSON object with this exact shape:
{
  "overallScore": 0.0-1.0,
  "passed": true if overallScore >= 0.8,
  "pageResults": [
    { "pageName": "string", "score": 0.0-1.0, "issues": ["issue description"] }
  ],
  "revisedCopy": { <the full ProjectCopy object with all fixes applied> }
}

The revisedCopy must have the same structure as the input copy — same pages array with all fields. Polish everything, even pages that scored well. The revisedCopy.generatedAt and revisedCopy.brandVoiceHash should match the input.

Return ONLY valid JSON. No markdown fences, no explanation.`;

  const stream = client.messages.stream({
    model: "claude-sonnet-4-5",
    max_tokens: 20000,
    system: brandVoice,
    messages: [{ role: "user", content: userPrompt }],
  });
  const finalMessage = await stream.finalMessage();
  const text = finalMessage.content[0];
  if (text.type !== "text") {
    throw new Error("[copy-reviewer] Unexpected response type");
  }

  const parsed = extractJsonFromResponse(text.text);
  return CopyReviewResultSchema.parse(parsed);
}
