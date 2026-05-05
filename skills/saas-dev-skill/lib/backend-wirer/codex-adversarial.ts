import Anthropic from "@anthropic-ai/sdk";
import type {
  RouteCodeBlock,
  SchemaCodeBlock,
} from "./types.js";
import { getAnthropicApiKey, getAnthropicBaseUrl } from "../env.js";

/**
 * Codex adversarial security review for backend code (Plan 05-05).
 *
 * Asks Claude (via Anthropic API) to apply the codex-cli-runtime skill in an
 * attacker mindset and surface SQL injection / auth bypass / race condition /
 * input validation vulnerabilities. NOT a real Codex CLI invocation.
 *
 * Fail-open: any error returns `{ passed: true, findings: [] }`.
 */

export type AdversarialSeverity = "critical" | "high" | "medium" | "low";
export type AdversarialCategory =
  | "sql-injection"
  | "auth-bypass"
  | "race-condition"
  | "input-validation"
  | "other";

export interface AdversarialFinding {
  severity: AdversarialSeverity;
  category: AdversarialCategory;
  description: string;
  file: string;
  mitigation: string;
}

export interface AdversarialReviewResult {
  passed: boolean;
  findings: AdversarialFinding[];
}

export interface AdversarialReviewInput {
  routes: RouteCodeBlock[];
  schema: SchemaCodeBlock[];
  // Storage functions are passed as raw code strings — Phase 5 generates them
  // before this review runs.
  storage: Array<{ code: string }>;
}

const MODEL = "claude-sonnet-4-5";

function getClient(): Anthropic {
  return new Anthropic({
    apiKey: getAnthropicApiKey(),
    baseURL: getAnthropicBaseUrl(),
  });
}

export async function adversarialReview(
  input: AdversarialReviewInput
): Promise<AdversarialReviewResult> {
  try {
    const client = getClient();
    const codeContext = `ROUTES:
${input.routes.map((r) => r.code).join("\n\n")}

SCHEMA:
${input.schema.map((s) => s.drizzleCode).join("\n\n")}

STORAGE:
${input.storage.map((s) => s.code).join("\n\n")}`;

    const response = await client.messages.create({
      model: MODEL,
      max_tokens: 3072,
      messages: [
        {
          role: "user",
          content: `Apply the codex-cli-runtime skill to perform an adversarial security review on this backend code. Think like an attacker.

Find vulnerabilities in:
1. SQL Injection — raw SQL, unparameterized queries, string concatenation in queries
2. Auth Bypass — missing auth checks, weak session validation, insecure direct object refs
3. Race Conditions — concurrent access issues, TOCTOU bugs, missing transactions
4. Input Validation — missing Zod validation, type coercion footguns, mass assignment

Code:
${codeContext}

Return findings in EXACTLY this format. One finding per line. Each line must start with the section header on its own line and findings beneath it:

CRITICAL:
<category> | <description> | <mitigation>

HIGH:
<category> | <description> | <mitigation>

MEDIUM:
<category> | <description> | <mitigation>

LOW:
<category> | <description> | <mitigation>

Use category tokens exactly: sql-injection, auth-bypass, race-condition, input-validation, other.
If a section has no findings, write "none" on the next line.`,
        },
      ],
    });

    const block = response.content[0];
    const text = block && block.type === "text" ? block.text : "";
    return parseAdversarialReview(text);
  } catch (err) {
    console.warn("[codex-adversarial] unavailable:", (err as Error).message);
    return { passed: true, findings: [] };
  }
}

const VALID_CATEGORIES: AdversarialCategory[] = [
  "sql-injection",
  "auth-bypass",
  "race-condition",
  "input-validation",
  "other",
];

export function parseAdversarialReview(text: string): AdversarialReviewResult {
  const findings: AdversarialFinding[] = [];
  let active: AdversarialSeverity | null = null;

  for (const raw of text.split(/\r?\n/)) {
    const headerMatch = raw.match(/^\s*(CRITICAL|HIGH|MEDIUM|LOW)\s*:\s*$/i);
    if (headerMatch) {
      active = headerMatch[1].toLowerCase() as AdversarialSeverity;
      continue;
    }
    if (!active) continue;

    const line = raw.trim();
    if (!line || /^none$/i.test(line)) continue;

    // Format: <category> | <description> | <mitigation>
    const parts = line.split("|").map((p) => p.trim());
    if (parts.length < 2) continue;

    const rawCategory = parts[0].toLowerCase();
    const category: AdversarialCategory = VALID_CATEGORIES.includes(
      rawCategory as AdversarialCategory
    )
      ? (rawCategory as AdversarialCategory)
      : "other";

    findings.push({
      severity: active,
      category,
      description: parts[1] ?? "",
      file: "generated-code",
      mitigation: parts[2] ?? "See review output",
    });
  }

  const blockers = findings.filter(
    (f) => f.severity === "critical" || f.severity === "high"
  );
  return { passed: blockers.length === 0, findings };
}
