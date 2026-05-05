// lib/react-gen/edit-mode.ts
// Post-build editing: surgical, file-level component updates with instant Vite preview.
// Applies the same validation pipeline as generation: import check, null safety, tsc.

import fs from "node:fs";
import path from "node:path";
import Anthropic from "@anthropic-ai/sdk";
import { getAnthropicApiKey, getAnthropicBaseUrl } from "../env.js";
import { DESIGN_RULES } from "./design-tokens.js";
import {
  autoFixImports,
  validateImports,
  scanForNullUnsafePatterns,
  runTscCheck,
} from "./component-writer.js";
import type { ProjectBrief } from "../intake/types.js";

function getClient(): Anthropic {
  return new Anthropic({
    apiKey: getAnthropicApiKey(),
    baseURL: getAnthropicBaseUrl(),
  });
}

function toKebabCase(name: string): string {
  return name
    .replace(/([a-z])([A-Z])/g, "$1-$2")
    .replace(/\s+/g, "-")
    .toLowerCase();
}

export interface EditResult {
  editApplied: boolean;
  tsErrors: string[];
  fixAttempts: number;
  compiledClean: boolean;
  importViolations: string[];
  nullSafetyIssues: string[];
}

const MAX_FIX_ATTEMPTS = 3;

export async function editPage(opts: {
  pageName: string;
  instruction: string;
  projectRoot: string;
  projectBrief: ProjectBrief;
}): Promise<EditResult> {
  const { pageName, instruction, projectRoot, projectBrief } = opts;
  const kebabName = toKebabCase(pageName);
  const filePath = path.join(projectRoot, "client", "src", "pages", `${kebabName}-page.tsx`);

  if (!fs.existsSync(filePath)) {
    throw new Error(`Page file not found: ${filePath}. Check the page name and try again.`);
  }

  const currentCode = fs.readFileSync(filePath, "utf-8");
  const client = getClient();

  const systemParts = [
    "You are a world-class React/TypeScript developer editing an existing component.",
    "Preserve the overall structure and imports. Only change what the user asks for.",
    "Follow the design system without deviation.",
    "",
    DESIGN_RULES,
    "",
    "ALLOWED IMPORTS — only these are permitted:",
    "- react, lucide-react, @/components/ui/*, @/components/*, wouter",
    "- @tanstack/react-query, @clerk/clerk-react, @/hooks/*, @/lib/*",
    "- framer-motion, recharts, date-fns, react-beautiful-dnd",
    "- react-hook-form, @hookform/resolvers, zod",
    "",
    "NULL SAFETY: guard all arrays with ?? [], use ?. for optional access.",
  ];

  if (projectBrief.designSystem) {
    systemParts.push("", "DESIGN SYSTEM:", projectBrief.designSystem.slice(0, 2000));
  }
  if (projectBrief.brandVoice) {
    systemParts.push("", "BRAND VOICE:", projectBrief.brandVoice.slice(0, 1000));
  }

  async function generateEdit(extraFeedback?: string): Promise<string> {
    const userContent = `Edit this React component. Apply the requested change while keeping everything else intact.

CURRENT CODE:
${currentCode}

REQUESTED CHANGE:
${instruction}
${extraFeedback ? `\nADDITIONAL REQUIREMENTS:\n${extraFeedback}` : ""}

Return the COMPLETE updated file. No markdown fences, no explanations. Only the code.`;

    const stream = client.messages.stream({
      model: "claude-sonnet-4-5",
      max_tokens: 16000,
      system: systemParts.join("\n"),
      messages: [{ role: "user", content: userContent }],
    });

    const msg = await stream.finalMessage();
    const text = msg.content[0];
    if (text.type !== "text") throw new Error("Non-text response from Claude during edit");

    return text.text
      .replace(/^```(?:tsx?|typescript|javascript)?\s*\n?/m, "")
      .replace(/\n?```\s*$/m, "")
      .trim();
  }

  let code = await generateEdit();
  let fixAttempts = 0;

  // Step 1: Auto-fix known bad imports
  code = autoFixImports(code);

  // Step 2: Validate imports — regenerate if violations
  let importCheck = validateImports(code);
  let importViolations = importCheck.violations;
  if (!importCheck.valid) {
    code = await generateEdit(
      `The edit used forbidden imports: ${importViolations.join(", ")}. ` +
      `Only use imports from the ALLOWED IMPORTS list.`,
    );
    code = autoFixImports(code);
    importCheck = validateImports(code);
    importViolations = importCheck.violations;
    fixAttempts++;
  }

  // Step 3: Null safety scan — regenerate if issues
  let nullSafetyIssues = scanForNullUnsafePatterns(code);
  if (nullSafetyIssues.length > 0) {
    const issueList = nullSafetyIssues.map((i) => `- ${i}`).join("\n");
    code = await generateEdit(
      `The edit has null safety issues:\n${issueList}\n\nUse (arr ?? []).map() and optional chaining.`,
    );
    code = autoFixImports(code);
    nullSafetyIssues = scanForNullUnsafePatterns(code);
    fixAttempts++;
  }

  // Step 4: Write to disk
  fs.writeFileSync(filePath, code, "utf-8");

  // Step 5: TypeScript compile check with fix loop (scoped to this file)
  let tscResult = runTscCheck(projectRoot, filePath);
  let tsErrors = tscResult.errors;

  while (!tscResult.clean && fixAttempts < MAX_FIX_ATTEMPTS) {
    fixAttempts++;
    const errorList = tscResult.errors.slice(0, 15).map((e) => `- ${e}`).join("\n");
    code = await generateEdit(
      `The edit has TypeScript compilation errors. Fix these exactly:\n${errorList}`,
    );
    code = autoFixImports(code);
    fs.writeFileSync(filePath, code, "utf-8");
    tscResult = runTscCheck(projectRoot, filePath);
    tsErrors = tscResult.errors;
  }

  const compiledClean = tscResult.clean;

  if (compiledClean) {
    console.log(`✓ Updated ${pageName} — Vite will hot-reload`);
  } else {
    console.warn(`⚠ Updated ${pageName} with ${tsErrors.length} remaining TS errors after ${fixAttempts} fix attempts`);
  }

  return {
    editApplied: true,
    tsErrors,
    fixAttempts,
    compiledClean,
    importViolations,
    nullSafetyIssues,
  };
}
