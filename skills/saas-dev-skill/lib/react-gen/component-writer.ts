// lib/react-gen/component-writer.ts
// Generates a single production-ready React/TypeScript page component using Claude.
// Validates output against design rules, retries on failure, runs design self-review.

import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";
import Anthropic from "@anthropic-ai/sdk";
import { getAnthropicApiKey, getAnthropicBaseUrl } from "../env.js";
import { DESIGN_RULES } from "./design-tokens.js";
import { lintDesignSystem, type DesignViolation } from "./design-linter.js";
import { loadDesignSkills } from "./skill-loader.js";
import type { PageSpecFull } from "@shared/spec-schema.js";
import type { PageCopy } from "../copy-planner/types.js";
import type { ProjectBrief } from "../intake/types.js";
import type { DesignSystem } from "../agents/types.js";

export interface ComponentWriterInput {
  page: PageSpecFull;
  pageCopy: PageCopy | null;
  designSystem: string;
  designSystemArtifact?: DesignSystem;
  brandVoice: string;
  sharedComponentPaths: Record<string, string>;
  competitiveIntel?: string;
  priorPageSummary?: string;
  projectBrief: ProjectBrief;
  projectRoot: string;
}

export interface ComponentWriterOutput {
  pageName: string;
  filePath: string;
  componentCode: string;
  reviewScore: number;
  reviewFeedback: string[];
  passed: boolean;
  retried: boolean;
  tsErrors: string[];
  fixAttempts: number;
  compiledClean: boolean;
  importViolations: string[];
  nullSafetyIssues: string[];
  designViolations: DesignViolation[];
  designClean: boolean;
}

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

function toPascalCase(name: string): string {
  return name.replace(/(^|[\s-])(\w)/g, (_, _sep, ch) => ch.toUpperCase()).replace(/[\s-]/g, "");
}

// Known invalid lucide-react exports to catch in validation
const BANNED_IMPORTS = [
  /from\s+['"]next\//,
  /from\s+['"]@mui\//,
  /from\s+['"]@material/,
  /from\s+['"]material-ui/,
];

interface ValidationResult {
  valid: boolean;
  errors: string[];
}

function validateComponent(code: string): ValidationResult {
  const errors: string[] = [];

  if (!/export\s+default\s+function/.test(code)) {
    errors.push("Missing `export default function` declaration");
  }

  for (const pattern of BANNED_IMPORTS) {
    if (pattern.test(code)) {
      errors.push(`Contains banned import: ${pattern.source}`);
    }
  }

  if (/linear-gradient|radial-gradient/.test(code)) {
    errors.push("Contains CSS gradient — gradients are banned by design rules");
  }

  if (/#000000/.test(code) || /color:\s*['"]?black['"]?/.test(code)) {
    errors.push("Uses pure black (#000000 or 'black') — must use #2c2f30");
  }

  // Check file isn't truncated (common with long components)
  const trimmed = code.trim();
  if (!trimmed.endsWith("}") && !trimmed.endsWith("};")) {
    errors.push("File appears truncated — does not end with closing brace");
  }

  return { valid: errors.length === 0, errors };
}

// ─── Import Allowlist ─────────────────────────────────────────────────────────

const ALLOWED_IMPORT_PATTERNS = [
  /^react$/,
  /^lucide-react$/,
  /^@\/components\/ui\/.+/,
  /^@\/components\/.+/,
  /^wouter$/,
  /^@tanstack\/react-query$/,
  /^@clerk\/clerk-react$/,
  /^@\/hooks\/.+/,
  /^@\/lib\/.+/,
  /^@xyflow\/react$/,
  /^posthog-js$/,
  /^date-fns/,
  /^recharts/,
  /^react-beautiful-dnd/,
  /^embla-carousel-react/,
  /^react-resizable-panels/,
  /^framer-motion/,
  /^class-variance-authority/,
  /^clsx$/,
  /^tailwind-merge$/,
  /^cmdk$/,
  /^vaul$/,
  /^input-otp$/,
  /^react-day-picker/,
  /^@radix-ui\/.+/,
  /^react-hook-form/,
  /^@hookform\/resolvers/,
  /^zod$/,
];

const IMPORT_AUTO_FIXES: Array<{ pattern: RegExp; replacement: string; importFix?: (line: string) => string }> = [
  {
    pattern: /from\s+['"]firebase\/auth['"]/,
    replacement: `from '@clerk/clerk-react'`,
    importFix: (line) => line.replace(/import\s*\{[^}]+\}/, "import { useUser, useClerk }"),
  },
  {
    pattern: /from\s+['"]next\/link['"]/,
    replacement: `from 'wouter'`,
    importFix: (line) => line.replace(/import\s+\w+/, "import { Link }"),
  },
  {
    pattern: /from\s+['"]next\/router['"]/,
    replacement: `from 'wouter'`,
    importFix: (line) => line.replace(/import\s*\{[^}]+\}/, "import { useLocation }"),
  },
  {
    pattern: /from\s+['"]posthog-js\/react['"]/,
    replacement: `from 'posthog-js'`,
  },
  {
    pattern: /from\s+['"]react-router-dom['"]/,
    replacement: `from 'wouter'`,
    importFix: (line) => line.replace(/import\s*\{[^}]+\}/, "import { Link, useLocation }"),
  },
];

export function autoFixImports(code: string): string {
  const lines = code.split("\n");
  return lines
    .map((line) => {
      for (const fix of IMPORT_AUTO_FIXES) {
        if (fix.pattern.test(line)) {
          let fixed = line.replace(fix.pattern, fix.replacement);
          if (fix.importFix) fixed = fix.importFix(fixed);
          return fixed;
        }
      }
      return line;
    })
    .join("\n");
}

export function validateImports(code: string): { valid: boolean; violations: string[] } {
  const violations: string[] = [];
  const importRegex = /import\s+(?:(?:\{[^}]*\}|[\w*]+)\s+from\s+)?['"]([^'"]+)['"]/g;

  let match: RegExpExecArray | null;
  while ((match = importRegex.exec(code)) !== null) {
    const source = match[1];
    // Relative imports are always allowed
    if (source.startsWith(".") || source.startsWith("/")) continue;
    const allowed = ALLOWED_IMPORT_PATTERNS.some((p) => p.test(source));
    if (!allowed) {
      violations.push(source);
    }
  }

  return { valid: violations.length === 0, violations };
}

// ─── Null Safety Scanner ──────────────────────────────────────────────────────

const NULL_UNSAFE_PATTERNS: Array<{ pattern: RegExp; description: string }> = [
  { pattern: /(?<!\?\.\s*)(?<!\?\?[^)]*)\b(\w+)\.map\s*\(/g, description: "Unguarded .map() call" },
  { pattern: /(?<!\?\.\s*)(?<!\?\?[^)]*)\b(\w+)\.reduce\s*\(/g, description: "Unguarded .reduce() call" },
  { pattern: /(?<!\?\.\s*)(?<!\?\?[^)]*)\b(\w+)\.filter\s*\(/g, description: "Unguarded .filter() call" },
  { pattern: /(?<!\?\.\s*)(?<!\?\?[^)]*)\b(\w+)\.find\s*\(/g, description: "Unguarded .find() call" },
  { pattern: /(?<!\?\.\s*)(?<!\?\?[^)]*)\b(\w+)\.length\b/g, description: "Unguarded .length access" },
];

// Safe prefixes that don't need guarding (known non-null array sources)
const SAFE_PREFIXES = new Set([
  "Object", "Array", "String", "Math", "JSON", "Date",
  "console", "window", "document", "navigator",
  "React", "Promise",
]);

// Known safe patterns: string literals, chained methods on guaranteed values
const SAFE_LINE_PATTERNS = [
  /\[\]\./, // [].method — empty array literal
  /\)\s*\.\s*(?:map|filter|reduce|find)\s*\(/, // chained after function call that returns array
  /\?\?\s*\[.*?\]\s*\)\s*\./, // (x ?? []).method — already guarded
  /\?\.\s*(?:map|filter|reduce|find)\s*\(/, // optional chaining
];

export function scanForNullUnsafePatterns(code: string): string[] {
  const issues: string[] = [];
  const lines = code.split("\n");

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    // Skip import lines and comments
    if (/^\s*(import\s|\/\/|\/\*|\*)/.test(line)) continue;

    for (const { pattern, description } of NULL_UNSAFE_PATTERNS) {
      // Reset regex state
      pattern.lastIndex = 0;
      let m: RegExpExecArray | null;
      while ((m = pattern.exec(line)) !== null) {
        const varName = m[1];
        if (SAFE_PREFIXES.has(varName)) continue;
        // Check if the line has a safe pattern around this usage
        const lineSlice = line.slice(Math.max(0, m.index - 30), m.index + m[0].length + 5);
        const isSafe = SAFE_LINE_PATTERNS.some((sp) => sp.test(lineSlice));
        if (!isSafe) {
          issues.push(`Line ${i + 1}: ${description} on '${varName}' — use optional chaining or nullish coalescing`);
        }
      }
    }
  }

  return issues;
}

// ─── TypeScript Compile Check ─────────────────────────────────────────────────

/**
 * Run tsc --noEmit scoped to a specific file (+ shared deps) to avoid
 * cross-contamination during parallel generation. When `scopeToFile` is
 * omitted, checks the entire project (used for post-build health checks).
 */
export function runTscCheck(
  projectRoot: string,
  scopeToFile?: string,
): { clean: boolean; errors: string[] } {
  try {
    let cmd: string;

    if (scopeToFile) {
      // Write a temporary tsconfig that only includes this file + shared deps.
      // This prevents errors in other in-progress parallel files from failing
      // this file's check.
      const relPath = path.relative(projectRoot, scopeToFile).replace(/\\/g, "/");
      const tempConfig = {
        extends: "./tsconfig.json",
        include: [
          relPath,
          "client/src/components/**/*",
          "client/src/lib/**/*",
          "client/src/hooks/**/*",
          "shared/**/*",
        ],
      };
      const tempConfigPath = path.join(projectRoot, `tsconfig.scopecheck.json`);
      fs.writeFileSync(tempConfigPath, JSON.stringify(tempConfig), "utf-8");
      cmd = `npx tsc --noEmit --skipLibCheck --project tsconfig.scopecheck.json`;

      try {
        execSync(cmd, {
          cwd: projectRoot,
          encoding: "utf-8",
          stdio: ["pipe", "pipe", "pipe"],
          timeout: 60_000,
        });
        return { clean: true, errors: [] };
      } catch (err: unknown) {
        const execErr = err as { stdout?: string; stderr?: string };
        const output = (execErr.stdout ?? "") + (execErr.stderr ?? "");
        // Only report errors from the scoped file, not from shared deps
        const normalizedScope = relPath.replace(/\\/g, "/");
        const errors = output
          .split("\n")
          .filter((line) => /error TS\d+/.test(line))
          .filter((line) => {
            // Include errors from the target file or generic errors
            const normalized = line.replace(/\\/g, "/");
            return normalized.includes(normalizedScope) || !normalized.includes(".ts");
          })
          .map((line) => line.trim());
        return { clean: errors.length === 0, errors };
      } finally {
        try { fs.unlinkSync(path.join(projectRoot, `tsconfig.scopecheck.json`)); } catch { /* ignore */ }
      }
    }

    // Full project check (no scoping)
    cmd = "npx tsc --noEmit --skipLibCheck";
    execSync(cmd, {
      cwd: projectRoot,
      encoding: "utf-8",
      stdio: ["pipe", "pipe", "pipe"],
      timeout: 90_000,
    });
    return { clean: true, errors: [] };
  } catch (err: unknown) {
    const execErr = err as { stdout?: string; stderr?: string };
    const output = (execErr.stdout ?? "") + (execErr.stderr ?? "");
    const errors = output
      .split("\n")
      .filter((line) => /error TS\d+/.test(line))
      .map((line) => line.trim());
    return { clean: false, errors };
  }
}

async function buildSystemPrompt(input: ComponentWriterInput): Promise<string> {
  const skillContent = await loadDesignSkills(input.projectRoot);

  const parts = [
    "You are a world-class React/TypeScript developer and UI designer.",
    "You write production-quality, pixel-perfect React components.",
    "You follow design systems without deviation.",
    "",
  ];

  // Inject skill-loaded design philosophy BEFORE mandatory rules
  // Skills provide spatial composition, motion, depth, anti-generic-AI principles
  // Mandatory design rules (colors, fonts, tokens) override any conflicting skill suggestions
  if (skillContent) {
    parts.push(skillContent, "");
  }

  // Visual intent from intake (reference sites, feel, avoidances)
  const vi = input.projectBrief.visualIntent;
  if (vi) {
    const intentParts = ["VISUAL INTENT — match this aesthetic direction:"];
    if (vi.feelWord) intentParts.push(`Feel: ${vi.feelWord}`);
    if (vi.colorMode) intentParts.push(`Color mode: ${vi.colorMode}`);
    if (vi.avoidances.length > 0) intentParts.push(`Avoid: ${vi.avoidances.join(", ")}`);
    parts.push(intentParts.join("\n"), "");
  }
  const vr = input.projectBrief.visualResearch;
  if (vr && vr.length > 0) {
    parts.push("REFERENCE SITE OBSERVATIONS:", ...vr.map((r) => `- ${r.url}: ${r.observations}`), "");
  }

  parts.push(DESIGN_RULES);

  parts.push(`
ALLOWED IMPORTS — only these are permitted, any other import is a build failure:
- react (useState, useEffect, useCallback, useMemo, useRef, etc.)
- lucide-react (icons only)
- @/components/ui/* (shadcn primitives)
- @/components/* (shared components)
- wouter (Link, useLocation, useRoute, Redirect)
- @tanstack/react-query (useQuery, useMutation, useQueryClient)
- @clerk/clerk-react (useUser, useClerk, useSignIn, useSignUp)
- @/hooks/* (custom hooks)
- @/lib/queryClient (apiRequest)
- @/lib/design-tokens
- @xyflow/react (for canvas pages only)
- framer-motion (animations)
- recharts (data visualization)
- date-fns (date utilities)
- react-beautiful-dnd (drag and drop)
- react-hook-form, @hookform/resolvers, zod (forms)

FORBIDDEN imports — using these is a build failure:
- firebase (use @clerk/clerk-react instead)
- next/* (use wouter instead)
- posthog-js/react (use posthog-js instead)
- @mui/* (use lucide-react + shadcn/ui instead)
- react-router-dom (use wouter instead)

NULL SAFETY RULES — violating these causes runtime crashes:
1. Every prop interface must use optional types: name?: string (not name: string) unless the prop is guaranteed by a parent
2. Every array must be guarded before iteration: (items ?? []).map(...) never items.map(...)
3. Every object property access on potentially undefined data must use optional chaining: user?.name never user.name
4. Components must have three states: loading (show skeleton), error (show error message with retry), data (show content)
5. useQuery results must be destructured with defaults: const { data = [], isLoading, error } = useQuery(...)
6. Never access .length, .map, .filter, .reduce, .find on a value that could be undefined
`);

  if (input.designSystem) {
    parts.push("", "DESIGN SYSTEM:", input.designSystem);
  }
  if (input.brandVoice) {
    parts.push("", "BRAND VOICE:", input.brandVoice);
  }
  if (input.competitiveIntel) {
    parts.push("", "COMPETITIVE INTELLIGENCE:", input.competitiveIntel);
  }

  return parts.join("\n");
}

function buildUserPrompt(input: ComponentWriterInput): string {
  const { page, pageCopy, sharedComponentPaths, priorPageSummary } = input;
  const componentName = toPascalCase(page.name);

  const sharedImports = Object.entries(sharedComponentPaths)
    .map(([name, filePath]) => `import { ${name} } from "${filePath}";`)
    .join("\n");

  const copySection = pageCopy
    ? `
EXACT COPY TO USE (do not invent your own):
- Heading: ${pageCopy.pageHeading}
- Subheading: ${pageCopy.pageSubheading ?? "(none)"}
- CTAs: ${pageCopy.ctas.map((c) => `${c.label} (${c.context})`).join(", ") || "(none)"}
- Empty state: ${pageCopy.emptyState}
- Placeholders: ${JSON.stringify(pageCopy.placeholders)}
- Helper text: ${JSON.stringify(pageCopy.helperText)}
- Error messages: ${JSON.stringify(pageCopy.errorMessages)}`
    : "";

  const priorContext = priorPageSummary
    ? `\nPRIOR PAGE CONTEXT (for visual consistency):\n${priorPageSummary}`
    : "";

  return `Write a complete, production-ready React/TypeScript component for this page.

PAGE SPEC:
${JSON.stringify(page, null, 2)}
${copySection}

SHARED COMPONENTS AVAILABLE:
${sharedImports || "(none built yet)"}
${priorContext}

REQUIREMENTS:
- Default export function named ${componentName}Page
- Use UniversalLayout for authenticated pages (auth pages are standalone)
- Use @tanstack/react-query for all data fetching
- Use wouter for routing/navigation
- Wire all API calls to real endpoints from the spec
- Loading: skeleton placeholders with shimmer
- Error: inline error message with retry button
- Empty: empty state from copy above
- Mobile responsive: works at 375px
- Complete file — no truncation, no TODOs, no placeholder comments
- All imports must resolve: react, lucide-react, @/components/ui/*, @/components/*, wouter, @tanstack/react-query

Return ONLY the TypeScript/React code. No markdown fences, no explanations.`;
}

async function selfReview(
  code: string,
  page: PageSpecFull,
): Promise<{ score: number; feedback: string[] }> {
  const client = getClient();

  const stream = client.messages.stream({
    model: "claude-haiku-4-5-20251001",
    max_tokens: 2000,
    system:
      "You are a UI code reviewer. Score the component 0-1 against: design rules compliance, spec compliance, copy compliance, completeness. Return JSON only: { score: number, feedback: string[] }",
    messages: [
      {
        role: "user",
        content: `Review this React component for the "${page.name}" page.

DESIGN RULES:
${DESIGN_RULES}

PAGE SPEC:
${JSON.stringify({ name: page.name, purpose: page.purpose, components: page.components, authLevel: page.authLevel }, null, 2)}

COMPONENT CODE:
${code}

Return JSON only: { "score": 0.0-1.0, "feedback": ["issue1", "issue2"] }`,
      },
    ],
  });

  const msg = await stream.finalMessage();
  const text = msg.content[0];
  if (text.type !== "text") return { score: 0.5, feedback: ["Review failed — non-text response"] };

  try {
    const cleaned = text.text.replace(/```json?\s*/g, "").replace(/```/g, "").trim();
    const parsed = JSON.parse(cleaned) as { score: number; feedback: string[] };
    return {
      score: Math.max(0, Math.min(1, parsed.score)),
      feedback: Array.isArray(parsed.feedback) ? parsed.feedback : [],
    };
  } catch {
    return { score: 0.5, feedback: ["Could not parse review response"] };
  }
}

export async function writeReactComponent(
  input: ComponentWriterInput,
): Promise<ComponentWriterOutput> {
  const client = getClient();
  const { page, projectRoot } = input;
  const kebabName = toKebabCase(page.name);
  const filePath = path.join(projectRoot, "client", "src", "pages", `${kebabName}-page.tsx`);

  const systemPrompt = await buildSystemPrompt(input);
  const userPrompt = buildUserPrompt(input);

  async function generate(extraInstructions?: string): Promise<string> {
    const messages: Anthropic.MessageParam[] = [
      { role: "user", content: extraInstructions ? `${userPrompt}\n\nADDITIONAL REQUIREMENTS:\n${extraInstructions}` : userPrompt },
    ];

    const stream = client.messages.stream({
      model: "claude-sonnet-4-5",
      max_tokens: 16000,
      system: systemPrompt,
      messages,
    });

    const msg = await stream.finalMessage();
    const text = msg.content[0];
    if (text.type !== "text") throw new Error("Non-text response from Claude");

    // Strip markdown fences if present
    return text.text
      .replace(/^```(?:tsx?|typescript|javascript)?\s*\n?/m, "")
      .replace(/\n?```\s*$/m, "")
      .trim();
  }

  let code = await generate();
  let retried = false;
  let importViolations: string[] = [];
  let nullSafetyIssues: string[] = [];
  let tsErrors: string[] = [];
  let fixAttempts = 0;

  // Step 1: Basic validation (banned imports, gradients, structure)
  const validation = validateComponent(code);
  if (!validation.valid) {
    retried = true;
    const errorList = validation.errors.map((e) => `- ${e}`).join("\n");
    code = await generate(`The previous attempt had these validation errors. Fix all of them:\n${errorList}`);
  }

  // Step 2: Auto-fix known bad imports, then validate import allowlist
  code = autoFixImports(code);
  const importCheck = validateImports(code);
  importViolations = importCheck.violations;
  if (!importCheck.valid) {
    retried = true;
    code = await generate(
      `The previous attempt used forbidden imports: ${importViolations.join(", ")}. ` +
      `Only use imports from the ALLOWED IMPORTS list. Remove or replace all forbidden imports.`,
    );
    code = autoFixImports(code);
    const recheck = validateImports(code);
    importViolations = recheck.violations;
  }

  // Step 3: Null safety scan
  nullSafetyIssues = scanForNullUnsafePatterns(code);
  if (nullSafetyIssues.length > 0) {
    retried = true;
    const issueList = nullSafetyIssues.map((i) => `- ${i}`).join("\n");
    code = await generate(
      `The previous attempt has null safety issues that will cause runtime crashes. Fix these:\n${issueList}\n\n` +
      `Use (arr ?? []).map() for arrays, optional chaining for object access, and default values for useQuery results.`,
    );
    code = autoFixImports(code);
    nullSafetyIssues = scanForNullUnsafePatterns(code);
  }

  // Step 3.5: Design system lint (if design system artifact is available)
  let designViolations: DesignViolation[] = [];
  let designFixAttempts = 0;
  if (input.designSystemArtifact) {
    designViolations = lintDesignSystem(code, input.designSystemArtifact, filePath);
    while (designViolations.length > 0 && designFixAttempts < 2) {
      designFixAttempts++;
      const violationList = designViolations
        .map((v) => `- Line ${v.line}: ${v.violation} → ${v.suggestion}`)
        .join("\n");
      code = await generate(
        `The previous attempt has design system violations. Fix these design violations:\n${violationList}\n\n` +
        `Use CSS variables (var(--color-*)) or Tailwind token classes instead of hardcoded values.`,
      );
      code = autoFixImports(code);
      designViolations = lintDesignSystem(code, input.designSystemArtifact, filePath);
    }
  }
  const designClean = designViolations.length === 0;

  // Step 4: Self-review
  const review = await selfReview(code, page);
  if (review.score < 0.8 && !retried) {
    retried = true;
    const feedbackList = review.feedback.map((f) => `- ${f}`).join("\n");
    code = await generate(`The previous attempt scored ${review.score.toFixed(2)}. Fix these issues:\n${feedbackList}`);
    code = autoFixImports(code);
    const secondReview = await selfReview(code, page);
    review.score = secondReview.score;
    review.feedback = secondReview.feedback;
  }

  // Step 5: Write to disk
  const dir = path.dirname(filePath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  fs.writeFileSync(filePath, code, "utf-8");

  // Step 6: TypeScript compile check with fix loop (max 3 attempts)
  // Scoped to this file to avoid cross-contamination during parallel generation.
  let tscResult = runTscCheck(projectRoot, filePath);
  tsErrors = tscResult.errors;

  while (!tscResult.clean && fixAttempts < 3) {
    fixAttempts++;
    const errorList = tscResult.errors.slice(0, 20).map((e) => `- ${e}`).join("\n");
    code = await generate(
      `The previous attempt has TypeScript compilation errors. Fix these exactly:\n${errorList}`,
    );
    code = autoFixImports(code);
    fs.writeFileSync(filePath, code, "utf-8");
    tscResult = runTscCheck(projectRoot, filePath);
    tsErrors = tscResult.errors;
  }

  const compiledClean = tscResult.clean;

  // Only mark passed if: imports clean + tsc clean + design clean + review score acceptable
  const passed = compiledClean && importViolations.length === 0 && designClean && review.score >= 0.8;

  return {
    pageName: page.name,
    filePath,
    componentCode: code,
    reviewScore: review.score,
    reviewFeedback: review.feedback,
    passed,
    retried,
    tsErrors,
    fixAttempts,
    compiledClean,
    importViolations,
    nullSafetyIssues,
    designViolations,
    designClean,
  };
}
