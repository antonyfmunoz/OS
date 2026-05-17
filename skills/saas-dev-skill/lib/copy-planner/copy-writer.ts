// lib/copy-planner/copy-writer.ts
// Generates all UI copy for a project in one Claude call for cross-page voice coherence.

import { createHash } from "node:crypto";
import Anthropic from "../claude-subprocess.js";
import { extractJsonFromResponse } from "../spec-parser/restructure-spec.js";
import { ProjectCopySchema, type ProjectCopy } from "./types.js";
import type { SpecOutput } from "@shared/spec-schema.js";
import type { ProjectBrief } from "../intake/types.js";

function getClient(): Anthropic {
  return new Anthropic();
}

function hashBrandVoice(brandVoice: string): string {
  return createHash("sha256").update(brandVoice).digest("hex").slice(0, 12);
}

const COPY_SCHEMA_REMINDER = `Return a JSON object with this exact shape:
{
  "pages": [
    {
      "pageName": "string (must match the page name from the spec)",
      "pageHeading": "string (the main heading visible on the page)",
      "pageSubheading": "string (optional secondary heading)",
      "sections": [{ "name": "string", "heading": "string", "body": "string (optional)" }],
      "ctas": [{ "id": "string (kebab-case)", "label": "string (the button text)", "context": "string (where/when this CTA appears)" }],
      "emptyState": "string (what shows when there is no data yet)",
      "errorMessages": { "key": "message" },
      "placeholders": { "fieldName": "placeholder text" },
      "helperText": { "fieldName": "helper text" },
      "successMessages": { "actionName": "success message" },
      "navLabel": "string (short label for navigation)"
    }
  ],
  "generatedAt": "ISO timestamp",
  "brandVoiceHash": "string"
}

Return ONLY valid JSON. No markdown fences, no explanation.`;

/**
 * Generate all UI copy for every page in the product in one call.
 * Whole-product generation produces more coherent cross-page voice than per-page.
 */
export async function generateProjectCopy(
  spec: SpecOutput,
  brandVoice: string,
  projectBrief: ProjectBrief,
): Promise<ProjectCopy> {
  const client = getClient();
  const voiceHash = hashBrandVoice(brandVoice);

  const pagesContext = spec.pages.map((p) => ({
    name: p.name,
    route: p.route,
    purpose: p.purpose,
    components: p.components,
    authLevel: p.authLevel,
    layoutHint: p.layoutHint,
    emptyState: p.emptyState,
    errorState: p.errorState,
    dataRequirements: p.dataRequirements,
  }));

  const userPrompt = `Write all UI copy for every page in this SaaS product.

Product: ${projectBrief.productName}
Description: ${projectBrief.productDescription.slice(0, 500)}
Target users: ${projectBrief.targetUsers.join("; ")}

Use the brand voice EXACTLY — commanding, operator-focused, specific, no generic SaaS language. Every heading, CTA, empty state, and error message must sound like it was written by this brand, not a template.
${projectBrief.competitiveIntel?.copyInfluences ? `\nCompetitive intelligence — learn from these but maintain our distinct brand voice:\n${projectBrief.competitiveIntel.copyInfluences}\n` : ""}
For each page produce: pageHeading, pageSubheading, sections (with headings and body copy), all CTA labels with context, emptyState, errorMessages (keyed by error type), placeholders (keyed by field name), helperText (keyed by field name), successMessages (keyed by action), navLabel.

Pages:
${JSON.stringify(pagesContext, null, 2)}

${COPY_SCHEMA_REMINDER}

Set generatedAt to "${new Date().toISOString()}" and brandVoiceHash to "${voiceHash}".`;

  const stream = client.messages.stream({
    model: "claude-sonnet-4-5",
    max_tokens: 16000,
    system: brandVoice,
    messages: [{ role: "user", content: userPrompt }],
  });
  const finalMessage = await stream.finalMessage();
  const text = finalMessage.content[0];
  if (text.type !== "text") {
    throw new Error("[copy-writer] Unexpected response type from Claude");
  }

  const parsed = extractJsonFromResponse(text.text);
  const result = ProjectCopySchema.safeParse(parsed);
  if (result.success) return result.data;

  // Retry once with schema reminder
  const errorDetails = result.error.errors
    .map((e) => `${e.path.join(".")}: ${e.message}`)
    .join("\n");

  const retryStream = client.messages.stream({
    model: "claude-sonnet-4-5",
    max_tokens: 16000,
    system: brandVoice,
    messages: [
      { role: "user", content: userPrompt },
      { role: "assistant", content: text.text },
      {
        role: "user",
        content: `The JSON failed validation. Fix these errors and return corrected JSON only:\n\n${errorDetails}\n\n${COPY_SCHEMA_REMINDER}`,
      },
    ],
  });
  const retryMessage = await retryStream.finalMessage();
  const retryText = retryMessage.content[0];
  if (retryText.type !== "text") {
    throw new Error("[copy-writer] Retry response not text");
  }

  const retryParsed = extractJsonFromResponse(retryText.text);
  return ProjectCopySchema.parse(retryParsed);
}
