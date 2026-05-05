// lib/react-gen/shared-component-builder.ts
// Builds shared layout components before any pages. Sequential — each can
// import the previous. Written to disk immediately so downstream page
// generation can reference them.
//
// Shared components go through the same validation pipeline as pages:
// autoFixImports → validateImports → scanForNullUnsafePatterns → tsc check.

import fs from "node:fs";
import path from "node:path";
import Anthropic from "@anthropic-ai/sdk";
import { getAnthropicApiKey, getAnthropicBaseUrl } from "../env.js";
import { DESIGN_RULES, DESIGN_TOKENS } from "./design-tokens.js";
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

interface SharedComponentDef {
  name: string;
  fileName: string;
  relativePath: string;
  description: string;
  dependsOn: string[];
}

const SHARED_COMPONENTS: SharedComponentDef[] = [
  {
    name: "designTokens",
    fileName: "design-tokens.ts",
    relativePath: "lib/design-tokens.ts",
    description:
      "CSS variable exports and utility constants matching the design system. Export colors, shadows, border-radius, and font as named constants. No React — pure TS constants file.",
    dependsOn: [],
  },
  {
    name: "AgentChatStub",
    fileName: "agent-chat-stub.tsx",
    relativePath: "components/agent-chat-stub.tsx",
    description:
      "Minimal chat interface component. Accepts onSendMessage callback, shows messages list. Glassmorphism card with input at bottom. Used as AI assistant panel across pages.",
    dependsOn: ["designTokens"],
  },
  {
    name: "FloatingAiPanel",
    fileName: "floating-ai-panel.tsx",
    relativePath: "components/floating-ai-panel.tsx",
    description:
      "Sticky top-center floating panel that collapses/expands on click. Contains AgentChatStub. Glassmorphism background, ambient shadow. Positioned fixed at top of viewport.",
    dependsOn: ["AgentChatStub"],
  },
  {
    name: "LeftRail",
    fileName: "left-rail.tsx",
    relativePath: "components/left-rail.tsx",
    description:
      "Navigation sidebar. Surface-container-low background (#eff1f2). No dividers between items. lucide-react icons. Active state uses primary color. Collapsible on mobile. Nav items passed as props.",
    dependsOn: ["designTokens"],
  },
  {
    name: "RightRail",
    fileName: "right-rail.tsx",
    relativePath: "components/right-rail.tsx",
    description:
      "Right-side AI assistant panel. Glassmorphism background. Contains AgentChatStub. Collapsible. Fixed width 320px on desktop, slides in as drawer on mobile.",
    dependsOn: ["AgentChatStub"],
  },
  {
    name: "Header",
    fileName: "header.tsx",
    relativePath: "components/header.tsx",
    description:
      "Top navbar with glassmorphism. Contains: logo/brand text on left, context switcher (company/project selector) in center, user avatar + notifications on right. Sticky top-0.",
    dependsOn: ["designTokens"],
  },
  {
    name: "UniversalLayout",
    fileName: "universal-layout.tsx",
    relativePath: "components/universal-layout.tsx",
    description:
      "Full page layout shell. Grid: Header (top, full width), LeftRail (left column), main content (center, scrollable), optional RightRail (right column). All authenticated pages wrap in this. Handles mobile responsive collapse.",
    dependsOn: ["Header", "LeftRail", "RightRail"],
  },
];

async function generateComponent(
  def: SharedComponentDef,
  projectBrief: ProjectBrief,
  existingComponents: Record<string, string>,
): Promise<string> {
  const client = getClient();

  const existingImports = def.dependsOn
    .filter((dep) => existingComponents[dep])
    .map((dep) => {
      const depDef = SHARED_COMPONENTS.find((c) => c.name === dep);
      if (!depDef) return "";
      const importPath = `@/${depDef.relativePath}`;
      return `// Available: import from "${importPath}"`;
    })
    .join("\n");

  const tokensJson = JSON.stringify(DESIGN_TOKENS, null, 2);

  const stream = client.messages.stream({
    model: "claude-sonnet-4-5",
    max_tokens: 8000,
    system: `You are a world-class React/TypeScript developer. You write production-quality components for a SaaS application shell.

${DESIGN_RULES}

DESIGN TOKENS (use these exact values):
${tokensJson}

Product: ${projectBrief.productName}
${projectBrief.brandVoice ? `Brand voice: ${projectBrief.brandVoice.slice(0, 500)}` : ""}

ALLOWED IMPORTS — only these are permitted:
- react (useState, useEffect, useCallback, useMemo, useRef, etc.)
- lucide-react (icons only)
- @/components/ui/* (shadcn primitives)
- @/components/* (shared components)
- @/lib/* (utilities)
- wouter (Link, useLocation)
- @clerk/clerk-react (useUser, useClerk)
- framer-motion (animations)
- clsx, tailwind-merge (className utilities)

NULL SAFETY RULES:
1. Every prop interface must use optional types unless guaranteed by parent
2. Every array must be guarded: (items ?? []).map(...)
3. Every object property access on potentially undefined data must use ?. chaining
4. Components must handle missing data gracefully`,
    messages: [
      {
        role: "user",
        content: `Write a complete React/TypeScript component: ${def.name}

PURPOSE: ${def.description}

FILE PATH: client/src/${def.relativePath}

${existingImports ? `AVAILABLE IMPORTS FROM PRIOR COMPONENTS:\n${existingImports}\n` : ""}
REQUIREMENTS:
- Named export AND default export
- Full TypeScript types for all props
- lucide-react icons only
- shadcn/ui primitives where applicable (Button, Input, etc.)
- Mobile responsive
- No TODOs, no placeholder comments
- Complete file — no truncation

Return ONLY the TypeScript/React code. No markdown fences.`,
      },
    ],
  });

  const msg = await stream.finalMessage();
  const text = msg.content[0];
  if (text.type !== "text") throw new Error(`Non-text response generating ${def.name}`);

  return text.text
    .replace(/^```(?:tsx?|typescript|javascript)?\s*\n?/m, "")
    .replace(/\n?```\s*$/m, "")
    .trim();
}

const MAX_FIX_ATTEMPTS = 3;

async function generateMinimalFallback(
  def: SharedComponentDef,
  errors: string,
  existingComponents: Record<string, string>,
): Promise<string> {
  const client = getClient();

  const depImports = def.dependsOn
    .filter((dep) => existingComponents[dep])
    .map((dep) => {
      const depDef = SHARED_COMPONENTS.find((c) => c.name === dep);
      if (!depDef) return "";
      return `import { ${dep} } from "@/${depDef.relativePath.replace(/\.tsx?$/, "")}";`;
    })
    .filter(Boolean)
    .join("\n");

  const msg = await client.messages.create({
    model: "claude-sonnet-4-5",
    max_tokens: 4000,
    messages: [
      {
        role: "user",
        content: `The component "${def.name}" has persistent TypeScript errors after multiple attempts.

PURPOSE: ${def.description}
FILE PATH: client/src/${def.relativePath}

ERRORS TO AVOID:
${errors}

${depImports ? `AVAILABLE IMPORTS:\n${depImports}\n` : ""}

Write a SIMPLIFIED but WORKING version that compiles cleanly with zero TypeScript errors.
Rules:
- Named export AND default export: export function ${def.name}(...) AND export default ${def.name}
- Full TypeScript types for all props (use an exported interface ${def.name}Props)
- Only import from: react, lucide-react, @/components/ui/*, @/lib/*, wouter, framer-motion, clsx, tailwind-merge
- Remove any complex features causing errors
- The component must render something meaningful (not just an empty div)
- Keep it simple — a clean 30-50 line component is perfect
- No markdown fences — return ONLY the TypeScript/React code`,
      },
    ],
  });

  const text = msg.content[0];
  if (text.type !== "text") throw new Error(`Non-text response for minimal ${def.name}`);

  return text.text
    .replace(/^```(?:tsx?|typescript|javascript)?\s*\n?/m, "")
    .replace(/\n?```\s*$/m, "")
    .trim();
}

async function validateAndFixComponent(
  code: string,
  def: SharedComponentDef,
  projectBrief: ProjectBrief,
  existingComponents: Record<string, string>,
  projectRoot: string,
  filePath: string,
): Promise<{ code: string; fixAttempts: number; compiledClean: boolean }> {
  let current = code;
  let fixAttempts = 0;

  // Step 1: Auto-fix known bad imports
  current = autoFixImports(current);

  // Step 2: Validate imports — regenerate if violations
  const importCheck = validateImports(current);
  if (!importCheck.valid) {
    console.log(`    ⚠ Import violations in ${def.name}: ${importCheck.violations.join(", ")}`);
    current = await generateComponent(def, projectBrief, existingComponents);
    current = autoFixImports(current);
    fixAttempts++;
  }

  // Step 3: Null safety scan — regenerate if issues
  const nullIssues = scanForNullUnsafePatterns(current);
  if (nullIssues.length > 0) {
    console.log(`    ⚠ Null safety issues in ${def.name}: ${nullIssues.length} found`);
    current = await generateComponent(def, projectBrief, existingComponents);
    current = autoFixImports(current);
    fixAttempts++;
  }

  // Step 4: Write to disk and run tsc check with fix loop
  fs.writeFileSync(filePath, current, "utf-8");

  // Only .tsx files get tsc checked (design-tokens.ts is pure constants)
  if (!filePath.endsWith(".tsx")) {
    return { code: current, fixAttempts, compiledClean: true };
  }

  let tscResult = runTscCheck(projectRoot, filePath);

  while (!tscResult.clean && fixAttempts < MAX_FIX_ATTEMPTS) {
    fixAttempts++;
    console.log(`    ⚠ TSC errors in ${def.name} (attempt ${fixAttempts}/${MAX_FIX_ATTEMPTS})`);

    // Regenerate with error feedback
    current = await generateComponent(def, projectBrief, existingComponents);
    current = autoFixImports(current);
    fs.writeFileSync(filePath, current, "utf-8");
    tscResult = runTscCheck(projectRoot, filePath);
  }

  // Fallback: if still broken after MAX_FIX_ATTEMPTS, generate a minimal
  // working version that compiles cleanly. A compilable stub is better than
  // a broken full version — it unblocks all downstream page builds.
  if (!tscResult.clean) {
    console.log(`    ⟳ ${def.name}: generating minimal fallback...`);
    const errorList = tscResult.errors.slice(0, 20).map((e) => `- ${e}`).join("\n");
    current = await generateMinimalFallback(def, errorList, existingComponents);
    current = autoFixImports(current);
    fs.writeFileSync(filePath, current, "utf-8");
    tscResult = runTscCheck(projectRoot, filePath);
    fixAttempts++;

    if (tscResult.clean) {
      console.log(`    ✓ ${def.name}: minimal fallback compiles clean`);
    } else {
      console.warn(`    ✗ ${def.name}: minimal fallback still has errors — needs manual fix`);
    }
  }

  return { code: current, fixAttempts, compiledClean: tscResult.clean };
}

export async function buildSharedComponents(
  projectBrief: ProjectBrief,
  projectRoot: string,
): Promise<Record<string, string>> {
  const result: Record<string, string> = {};
  const clientSrc = path.join(projectRoot, "client", "src");

  for (const def of SHARED_COMPONENTS) {
    const filePath = path.join(clientSrc, def.relativePath);
    const dir = path.dirname(filePath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }

    console.log(`  [react-gen] Building shared: ${def.name}...`);
    const code = await generateComponent(def, projectBrief, result);

    const validated = await validateAndFixComponent(
      code, def, projectBrief, result, projectRoot, filePath,
    );

    if (!validated.compiledClean) {
      console.warn(`  ⚠ ${def.name}: compiled with errors after ${validated.fixAttempts} fix attempts`);
    }

    result[def.name] = filePath;
    console.log(`  ✓ ${def.name}${validated.fixAttempts > 0 ? ` (${validated.fixAttempts} fixes)` : ""}`);
  }

  return result;
}

export { SHARED_COMPONENTS };
