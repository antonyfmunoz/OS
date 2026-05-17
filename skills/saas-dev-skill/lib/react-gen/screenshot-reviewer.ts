// lib/react-gen/screenshot-reviewer.ts
// Playwright-based screenshot capture + Claude vision quality gate.
// Takes a screenshot of a rendered page and scores it against design rules.

import fs from "node:fs";
import path from "node:path";
import Anthropic from "../claude-subprocess.js";
import { DESIGN_RULES } from "./design-tokens.js";

export interface ScreenshotReviewInput {
  /** Full URL to navigate to (e.g. http://localhost:5173/dashboard). */
  url: string;
  /** Page name for file naming. */
  pageName: string;
  /** Design system content for scoring context. */
  designSystem: string;
  /** Project root for screenshot output path. */
  projectRoot: string;
}

export interface ScreenshotReviewOutput {
  score: number;
  issues: string[];
  screenshotPath: string;
}

function getClient(): Anthropic {
  return new Anthropic();
}

function toKebabCase(name: string): string {
  return name
    .replace(/([a-z])([A-Z])/g, "$1-$2")
    .replace(/\s+/g, "-")
    .toLowerCase();
}

/**
 * Take a full-page screenshot via Playwright and review it with Claude vision.
 * Returns a score (0-1), list of issues, and the screenshot path.
 */
export async function screenshotAndReview(
  input: ScreenshotReviewInput,
): Promise<ScreenshotReviewOutput> {
  const { url, pageName, designSystem, projectRoot } = input;

  // Ensure output directory exists
  const screenshotDir = path.join(projectRoot, ".planning", "output", "screenshots");
  if (!fs.existsSync(screenshotDir)) {
    fs.mkdirSync(screenshotDir, { recursive: true });
  }

  const kebabName = toKebabCase(pageName);
  const screenshotPath = path.join(screenshotDir, `${kebabName}.png`);

  // Dynamic import — Playwright is a devDependency, may not always be available
  let chromium: typeof import("playwright").chromium;
  try {
    const pw = await import("playwright");
    chromium = pw.chromium;
  } catch {
    console.warn("[screenshot-reviewer] Playwright not available — using conservative score 0.5");
    return { score: 0.5, issues: ["Playwright not available — screenshot review skipped"], screenshotPath: "" };
  }

  // Launch browser, take screenshot
  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();

    await page.goto(url, { waitUntil: "networkidle", timeout: 15000 });
    await page.screenshot({ path: screenshotPath, fullPage: true });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    console.warn(`[screenshot-reviewer] Screenshot failed for ${pageName}: ${msg} — using conservative score 0.5`);
    return { score: 0.5, issues: [`Screenshot capture failed: ${msg}`], screenshotPath: "" };
  } finally {
    if (browser) await browser.close();
  }

  // Read screenshot as base64 for Claude vision
  const screenshotBuffer = fs.readFileSync(screenshotPath);
  const base64Image = screenshotBuffer.toString("base64");

  // Send to Claude vision for review
  const client = getClient();
  try {
    const response = await client.messages.create({
      model: "claude-sonnet-4-5",
      max_tokens: 2000,
      messages: [
        {
          role: "user",
          content: [
            {
              type: "image",
              source: {
                type: "base64",
                media_type: "image/png",
                data: base64Image,
              },
            },
            {
              type: "text",
              text: `Score this UI screenshot 0-1 against these design rules. Be harsh — generic AI slop scores below 0.5.

DESIGN RULES:
${DESIGN_RULES}

${designSystem ? `DESIGN SYSTEM:\n${designSystem}\n` : ""}

Score criteria:
- Color compliance (no gradients, correct primary #6a37d4, no pure black)
- Typography (Inter font, proper hierarchy)
- Spacing and layout quality (not cramped, not wasteful)
- Visual polish (glassmorphism where appropriate, ambient shadows)
- Overall aesthetic (does it look like a premium product or generic AI output?)
- Component quality (proper use of cards, buttons, inputs)
- Responsiveness indicators (layout structure)

Return JSON only: { "score": 0.0-1.0, "issues": ["specific issue 1", "specific issue 2"] }`,
            },
          ],
        },
      ],
    });

    const text = response.content[0];
    if (text.type !== "text") {
      return { score: 0.5, issues: ["Vision review returned non-text response"], screenshotPath };
    }

    const cleaned = text.text.replace(/```json?\s*/g, "").replace(/```/g, "").trim();
    const parsed = JSON.parse(cleaned) as { score: number; issues: string[] };
    return {
      score: Math.max(0, Math.min(1, parsed.score)),
      issues: Array.isArray(parsed.issues) ? parsed.issues : [],
      screenshotPath,
    };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    console.warn(`[screenshot-reviewer] Vision review failed: ${msg} — using conservative score 0.5`);
    return { score: 0.5, issues: [`Vision review failed: ${msg}`], screenshotPath };
  }
}
