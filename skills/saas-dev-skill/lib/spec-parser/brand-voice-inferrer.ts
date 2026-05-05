// lib/spec-parser/brand-voice-inferrer.ts
// Infers brand voice from a PRD/spec document via Claude.
// Writes result to .planning/BRAND-VOICE.md for injection into Stitch prompts.
// Fail-open: if Claude API is unavailable, logs a warning and returns null.

import fs from "node:fs";
import path from "node:path";
import Anthropic from "@anthropic-ai/sdk";
import { getAnthropicApiKey, getAnthropicBaseUrl } from "../env.js";

const BRAND_VOICE_SYSTEM_PROMPT = `You are a brand voice and SaaS copy expert. Given a product requirements document, extract the brand voice characteristics AND produce actionable copy guidance for building the product's UI and landing pages.

Return a detailed brand voice document in markdown with these sections:

# Brand Voice

## Tone
1-2 sentences describing the overall tone (e.g. professional, playful, authoritative). Be specific to THIS product.

## Personality
3-5 adjectives that define the brand personality.

## Language Style
Guidance on copy style (formal vs casual, technical vs accessible, sentence structure, vocabulary level).

## Visual Mood
How the brand voice translates to visual design (color temperature, density, whitespace, typography feel).

## UI Copy Guidelines
Specific rules as a table with columns: Element | Style | Examples. Cover:
- Button labels (verb-forward? articles?)
- Page headings (noun-based? outcome-focused?)
- Empty states (tone, CTA phrasing)
- Error messages (blame-free, actionable)
- Success/confirmation messages
- Tooltip and helper text
- AI/agent references (how to refer to AI features)

## SaaS Copy Patterns
Best practices for this specific product type:
- Value proposition framing (how to describe what the product does in one line)
- Feature descriptions (benefit-led vs feature-led)
- Onboarding copy (first-run experience, setup wizard tone)
- Upgrade/upsell language (if applicable)
- Social proof and trust signals style
- CTA hierarchy (primary vs secondary action phrasing)

## Landing Page Voice
If this product had a marketing page, what would the copy feel like:
- Hero headline style (aspirational? direct? provocative?)
- Subheadline approach
- Feature section copy style
- Testimonial framing

Be specific to THIS product. Do not be generic. Every example should feel like it belongs to this brand.`;

export interface BrandVoiceResult {
  content: string;
  sourcePath: string;
}

/**
 * Infer brand voice from a PRD document using Claude.
 * Returns the brand voice markdown content, or null if inference fails.
 *
 * @param prdText - Raw text of the PRD/spec document
 * @param outputDir - Directory to write BRAND-VOICE.md (e.g. .planning/)
 * @returns BrandVoiceResult with content and output path, or null on failure
 */
export async function inferBrandVoice(
  prdText: string,
  outputDir: string,
): Promise<BrandVoiceResult | null> {
  try {
    const client = new Anthropic({
      apiKey: getAnthropicApiKey(),
      baseURL: getAnthropicBaseUrl(),
    });

    const response = await client.messages.create({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 4096,
      system: BRAND_VOICE_SYSTEM_PROMPT,
      messages: [{ role: "user", content: prdText }],
    });

    const text = response.content[0].type === "text" ? response.content[0].text : "";
    if (!text.trim()) {
      console.warn("[brand-voice] Claude returned empty response — skipping brand voice inference.");
      return null;
    }

    const outputPath = path.join(outputDir, "BRAND-VOICE.md");
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }
    fs.writeFileSync(outputPath, text.trim() + "\n", "utf-8");

    return { content: text.trim(), sourcePath: outputPath };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    console.warn(`[brand-voice] Failed to infer brand voice — continuing without it. Error: ${message}`);
    return null;
  }
}

/**
 * Load an existing BRAND-VOICE.md file if it exists.
 * Returns the file content or null.
 */
export function loadBrandVoice(planningDir: string): string | null {
  const voicePath = path.join(planningDir, "BRAND-VOICE.md");
  try {
    if (fs.existsSync(voicePath)) {
      const content = fs.readFileSync(voicePath, "utf-8").trim();
      return content || null;
    }
    return null;
  } catch {
    return null;
  }
}
