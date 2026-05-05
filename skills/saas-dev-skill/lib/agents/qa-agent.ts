// lib/agents/qa-agent.ts
// QA agent — validates the entire project after all other agents complete.
// Runs tsc, import validation, null-safety scans, and state-pattern checks
// on every generated page. Attempts auto-fix via Claude for fixable issues.

import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";
import Anthropic from "@anthropic-ai/sdk";
import { getAnthropicApiKey, getAnthropicBaseUrl } from "../env.js";
import {
  runTscCheck,
  validateImports,
  scanForNullUnsafePatterns,
  autoFixImports,
} from "../react-gen/component-writer.js";
import { lintDesignSystem } from "../react-gen/design-linter.js";
import { ArtifactStore } from "./artifact-store.js";
import type { QAReport, QAIssue, PageOutput, ConsistencyReport, DesignSystem } from "./types.js";

const SYSTEM_PROMPT =
  "You are a senior QA engineer and code reviewer. You never sign off on broken work. You fix issues precisely and minimally.";

function getClient(): Anthropic {
  return new Anthropic({
    apiKey: getAnthropicApiKey(),
    baseURL: getAnthropicBaseUrl(),
  });
}

function stripFences(text: string): string {
  return text
    .replace(/^```(?:tsx?|typescript|javascript)?\s*\n?/m, "")
    .replace(/\n?```\s*$/m, "")
    .trim();
}

function parseTscErrors(errors: string[]): QAIssue[] {
  return errors.map((msg) => {
    const fileMatch = msg.match(/^([^(]+)\((\d+),/);
    return {
      file: fileMatch ? fileMatch[1].trim() : "unknown",
      line: fileMatch ? parseInt(fileMatch[2], 10) : undefined,
      severity: "error" as const,
      category: "typescript" as const,
      message: msg,
      autoFixed: false,
    };
  });
}

function checkStatePatterns(code: string): string[] {
  const missing: string[] = [];
  const hasLoading = /isLoading|loading|skeleton|Skeleton/i.test(code);
  const hasError = /error|Error|retry|Retry/i.test(code);
  const hasEmpty = /empty|no\s+\w+\s+found|nothing|no\s+results|emptyState/i.test(code);

  if (!hasLoading) missing.push("Missing loading/skeleton state");
  if (!hasError) missing.push("Missing error/retry state");
  if (!hasEmpty) missing.push("Missing empty state");

  return missing;
}

async function attemptAutoFix(
  client: Anthropic,
  filePath: string,
  issue: QAIssue,
  fileContent: string,
): Promise<string | null> {
  try {
    const stream = client.messages.stream({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 16000,
      system: SYSTEM_PROMPT,
      messages: [
        {
          role: "user",
          content: `Fix this ${issue.category} error in the file below. Return ONLY the complete fixed file — no explanations, no markdown fences.

ERROR:
${issue.message}

FILE (${filePath}):
${fileContent}`,
        },
      ],
    });

    const msg = await stream.finalMessage();
    const text = msg.content[0];
    if (text.type !== "text") return null;
    return stripFences(text.text);
  } catch {
    return null;
  }
}

// ─── Design Consistency Check (Part 2) ──────────────────────────────────────

interface PagePattern {
  file: string;
  pageName: string;
  cssVars: Set<string>;
  tailwindColors: Set<string>;
  sharedComponents: Set<string>;
  headingClasses: Set<string>;
  spacingClasses: Set<string>;
}

function extractPatterns(code: string, filePath: string, pageName: string): PagePattern {
  const cssVars = new Set<string>();
  const tailwindColors = new Set<string>();
  const sharedComponents = new Set<string>();
  const headingClasses = new Set<string>();
  const spacingClasses = new Set<string>();

  // Extract CSS variable usage
  const varPattern = /var\(--([^)]+)\)/g;
  let m: RegExpExecArray | null;
  while ((m = varPattern.exec(code)) !== null) cssVars.add(m[1]);

  // Extract Tailwind color classes
  const twColorPattern = /(?:text|bg|border|ring)-(\w[\w-]*)/g;
  while ((m = twColorPattern.exec(code)) !== null) tailwindColors.add(m[1]);

  // Extract shared component imports
  const importPattern = /import\s+.*?\s+from\s+['"]@\/components\/([^'"]+)['"]/g;
  while ((m = importPattern.exec(code)) !== null) sharedComponents.add(m[1]);

  // Extract heading typography
  const headingPattern = /className="[^"]*?(text-(?:xs|sm|base|lg|xl|2xl|3xl|4xl|5xl|6xl)[^"]*?)"/g;
  while ((m = headingPattern.exec(code)) !== null) headingClasses.add(m[1].split(/\s+/)[0]);

  // Extract spacing patterns
  const spacingPattern = /(?:p|px|py|pt|pb|pl|pr|m|mx|my|mt|mb|ml|mr|gap|space-[xy])-(\d+)/g;
  while ((m = spacingPattern.exec(code)) !== null) spacingClasses.add(m[0]);

  return { file: filePath, pageName, cssVars, tailwindColors, sharedComponents, headingClasses, spacingClasses };
}

function findOutlier(patterns: PagePattern[], accessor: (p: PagePattern) => Set<string>, type: string): { outlier: string; description: string } | null {
  if (patterns.length < 2) return null;

  // Build a frequency map of which values are used by how many pages
  const valueCounts = new Map<string, number>();
  for (const p of patterns) {
    for (const val of accessor(p)) {
      valueCounts.set(val, (valueCounts.get(val) ?? 0) + 1);
    }
  }

  // Find values that only one page uses (potential outlier)
  for (const p of patterns) {
    const uniqueValues: string[] = [];
    for (const val of accessor(p)) {
      if ((valueCounts.get(val) ?? 0) === 1 && patterns.length > 2) {
        uniqueValues.push(val);
      }
    }
    if (uniqueValues.length > 0) {
      return {
        outlier: p.pageName,
        description: `${p.pageName} uses unique ${type} values: ${uniqueValues.slice(0, 5).join(", ")}`,
      };
    }
  }

  return null;
}

export async function checkDesignConsistency(
  pageFiles: string[],
  designSystem: DesignSystem,
  pageOutputs: PageOutput[],
): Promise<ConsistencyReport> {
  const patterns: PagePattern[] = [];

  for (const filePath of pageFiles) {
    if (!fs.existsSync(filePath)) continue;
    const code = fs.readFileSync(filePath, "utf-8");
    const pageName = pageOutputs.find((p) => {
      const normalizedP = p.filePath.replace(/\\/g, "/");
      const normalizedF = filePath.replace(/\\/g, "/");
      return normalizedP === normalizedF || normalizedF.endsWith(normalizedP);
    })?.pageName ?? path.basename(filePath, ".tsx");
    patterns.push(extractPatterns(code, filePath, pageName));
  }

  const findings: ConsistencyReport["findings"] = [];

  // Check color consistency
  const colorOutlier = findOutlier(patterns, (p) => p.tailwindColors, "color");
  if (colorOutlier) {
    findings.push({
      type: "color",
      description: colorOutlier.description,
      pages: patterns.map((p) => p.pageName),
      outlierPage: colorOutlier.outlier,
      fix: "Align color usage with the majority pattern using design system tokens",
    });
  }

  // Check component consistency (are all pages using the same nav components?)
  const componentOutlier = findOutlier(patterns, (p) => p.sharedComponents, "component");
  if (componentOutlier) {
    findings.push({
      type: "component",
      description: componentOutlier.description,
      pages: patterns.map((p) => p.pageName),
      outlierPage: componentOutlier.outlier,
      fix: "Use the same shared components for navigation and layout across all pages",
    });
  }

  // Check typography consistency
  const typographyOutlier = findOutlier(patterns, (p) => p.headingClasses, "typography");
  if (typographyOutlier) {
    findings.push({
      type: "typography",
      description: typographyOutlier.description,
      pages: patterns.map((p) => p.pageName),
      outlierPage: typographyOutlier.outlier,
      fix: "Use consistent heading sizes from the design system typography scale",
    });
  }

  // Check spacing consistency
  const spacingOutlier = findOutlier(patterns, (p) => p.spacingClasses, "spacing");
  if (spacingOutlier) {
    findings.push({
      type: "spacing",
      description: spacingOutlier.description,
      pages: patterns.map((p) => p.pageName),
      outlierPage: spacingOutlier.outlier,
      fix: "Use consistent spacing values from the design system spacing scale",
    });
  }

  // Run design linter on each page
  for (const filePath of pageFiles) {
    if (!fs.existsSync(filePath)) continue;
    const code = fs.readFileSync(filePath, "utf-8");
    const violations = lintDesignSystem(code, designSystem, filePath);
    if (violations.length > 0) {
      const pageName = patterns.find((p) => p.file === filePath)?.pageName ?? path.basename(filePath);
      findings.push({
        type: "color",
        description: `${pageName} has ${violations.length} design system violations: ${violations.slice(0, 3).map((v) => v.violation).join("; ")}`,
        pages: [pageName],
        outlierPage: pageName,
        fix: violations.map((v) => `Line ${v.line}: ${v.suggestion}`).join("; "),
      });
    }
  }

  return {
    consistent: findings.length === 0,
    findings,
    pagesChecked: patterns.length,
  };
}

// ─── Visual Regression via Screenshots (Part 4) ────────────────────────────

export interface VisualConsistencyResult {
  consistent: boolean;
  issues: string[];
  screenshotPaths: string[];
  iterations: number;
}

async function captureScreenshots(
  projectRoot: string,
  pageOutputs: PageOutput[],
): Promise<string[]> {
  const screenshotDir = path.join(projectRoot, ".planning", "artifacts", "screenshots");
  if (!fs.existsSync(screenshotDir)) {
    fs.mkdirSync(screenshotDir, { recursive: true });
  }

  const screenshotPaths: string[] = [];

  // Check if Playwright is available
  try {
    execSync("npx playwright --version", { cwd: projectRoot, stdio: "pipe", timeout: 10_000 });
  } catch {
    console.log("  [qa] Playwright not available — skipping visual regression");
    return [];
  }

  // Check if dev server is running by testing localhost:5173
  try {
    execSync("curl -s -o /dev/null -w '%{http_code}' http://localhost:5173", { stdio: "pipe", timeout: 5_000 });
  } catch {
    console.log("  [qa] Dev server not running — skipping visual regression");
    return [];
  }

  for (const page of pageOutputs) {
    const screenshotPath = path.join(screenshotDir, `${page.pageName}.png`);
    try {
      const route = page.route.startsWith("/") ? page.route : `/${page.route}`;
      const script = `
        const { chromium } = require('playwright');
        (async () => {
          const browser = await chromium.launch();
          const pg = await browser.newPage();
          await pg.setViewportSize({ width: 1440, height: 900 });
          await pg.goto('http://localhost:5173${route}', { waitUntil: 'networkidle', timeout: 15000 });
          await pg.screenshot({ path: '${screenshotPath.replace(/\\/g, "/")}' });
          await browser.close();
        })();
      `;
      execSync(`node -e "${script.replace(/"/g, '\\"').replace(/\n/g, " ")}"`, {
        cwd: projectRoot,
        stdio: "pipe",
        timeout: 30_000,
      });
      if (fs.existsSync(screenshotPath)) {
        screenshotPaths.push(screenshotPath);
      }
    } catch {
      console.log(`  [qa] Screenshot failed for ${page.pageName} — skipping`);
    }
  }

  return screenshotPaths;
}

async function reviewScreenshotsForConsistency(
  client: Anthropic,
  screenshotPaths: string[],
): Promise<{ consistent: boolean; issues: string[] }> {
  if (screenshotPaths.length === 0) {
    return { consistent: true, issues: [] };
  }

  const imageContent: Anthropic.ImageBlockParam[] = [];
  for (const imgPath of screenshotPaths) {
    const data = fs.readFileSync(imgPath);
    imageContent.push({
      type: "image",
      source: {
        type: "base64",
        media_type: "image/png",
        data: data.toString("base64"),
      },
    });
  }

  try {
    const stream = client.messages.stream({
      model: "claude-sonnet-4-5",
      max_tokens: 2000,
      system: "You are a senior UI designer reviewing screenshots for visual consistency. Return JSON only.",
      messages: [
        {
          role: "user",
          content: [
            ...imageContent,
            {
              type: "text",
              text: `Review these ${screenshotPaths.length} page screenshots for design consistency.
Check: Are colors consistent? Is typography consistent? Is spacing consistent? Does every page feel like it belongs to the same product?
Return JSON: { "consistent": boolean, "issues": ["issue description with specific page name"] }`,
            },
          ],
        },
      ],
    });

    const msg = await stream.finalMessage();
    const text = msg.content[0];
    if (text.type !== "text") return { consistent: true, issues: [] };

    const cleaned = text.text.replace(/```json?\s*/g, "").replace(/```/g, "").trim();
    const parsed = JSON.parse(cleaned) as { consistent: boolean; issues: string[] };
    return {
      consistent: parsed.consistent ?? true,
      issues: Array.isArray(parsed.issues) ? parsed.issues : [],
    };
  } catch {
    return { consistent: true, issues: [] };
  }
}

export async function runQAAgent(store: ArtifactStore): Promise<QAReport> {
  const projectRoot = store.getProjectRoot();
  const pageOutputs = store.getPageOutputs() ?? [];
  const architecture = store.getArchitecture();
  const backendRoutes = store.getBackendRoutes() ?? [];
  const client = getClient();

  const allIssues: QAIssue[] = [];
  const pageResultsMap = new Map<string, QAIssue[]>();

  // Initialize per-page issue tracking
  for (const page of pageOutputs) {
    pageResultsMap.set(page.pageName, []);
  }

  // Step 1: Full project tsc check (no scope)
  let tscResult = runTscCheck(projectRoot);
  const tscIssues = parseTscErrors(tscResult.errors);
  allIssues.push(...tscIssues);

  // Assign tsc errors to pages where possible
  for (const issue of tscIssues) {
    for (const page of pageOutputs) {
      const normalizedIssue = issue.file.replace(/\\/g, "/");
      const normalizedPage = page.filePath.replace(/\\/g, "/");
      if (normalizedIssue.includes(normalizedPage) || normalizedPage.includes(normalizedIssue)) {
        const pageIssues = pageResultsMap.get(page.pageName) ?? [];
        pageIssues.push(issue);
        pageResultsMap.set(page.pageName, pageIssues);
      }
    }
  }

  // Step 2: Per-page validation
  for (const page of pageOutputs) {
    const fullPath = path.isAbsolute(page.filePath)
      ? page.filePath
      : path.join(projectRoot, page.filePath);

    if (!fs.existsSync(fullPath)) continue;

    const code = fs.readFileSync(fullPath, "utf-8");
    const pageIssues = pageResultsMap.get(page.pageName) ?? [];

    // Import validation
    const importCheck = validateImports(code);
    for (const violation of importCheck.violations) {
      const issue: QAIssue = {
        file: fullPath,
        severity: "error",
        category: "import",
        message: `Forbidden import: ${violation}`,
        autoFixed: false,
      };
      allIssues.push(issue);
      pageIssues.push(issue);
    }

    // Null safety scan
    const nullIssues = scanForNullUnsafePatterns(code);
    for (const msg of nullIssues) {
      const lineMatch = msg.match(/^Line (\d+):/);
      const issue: QAIssue = {
        file: fullPath,
        line: lineMatch ? parseInt(lineMatch[1], 10) : undefined,
        severity: "warning",
        category: "null-safety",
        message: msg,
        autoFixed: false,
      };
      allIssues.push(issue);
      pageIssues.push(issue);
    }

    // State pattern check
    const stateMissing = checkStatePatterns(code);
    for (const msg of stateMissing) {
      const issue: QAIssue = {
        file: fullPath,
        severity: "warning",
        category: "state",
        message: msg,
        autoFixed: false,
      };
      allIssues.push(issue);
      pageIssues.push(issue);
    }

    pageResultsMap.set(page.pageName, pageIssues);
  }

  // Step 3: Auto-fix loop (max 3 iterations)
  let iterations = 0;
  const fixableCategories = new Set<QAIssue["category"]>(["typescript", "import", "null-safety"]);

  while (iterations < 3) {
    const unfixed = allIssues.filter((i) => !i.autoFixed && fixableCategories.has(i.category));
    if (unfixed.length === 0) break;

    iterations++;

    // Group issues by file for efficient fixing
    const issuesByFile = new Map<string, QAIssue[]>();
    for (const issue of unfixed) {
      const existing = issuesByFile.get(issue.file) ?? [];
      existing.push(issue);
      issuesByFile.set(issue.file, existing);
    }

    for (const [filePath, fileIssues] of issuesByFile) {
      if (!fs.existsSync(filePath)) continue;

      let code = fs.readFileSync(filePath, "utf-8");

      // Build a combined error message for all issues in this file
      const combinedMessage = fileIssues.map((i) => i.message).join("\n");
      const combinedIssue: QAIssue = {
        file: filePath,
        severity: "error",
        category: fileIssues[0].category,
        message: combinedMessage,
        autoFixed: false,
      };

      const fixed = await attemptAutoFix(client, filePath, combinedIssue, code);
      if (fixed) {
        // Apply auto-fix for known bad imports before writing
        const finalCode = autoFixImports(fixed);
        fs.writeFileSync(filePath, finalCode, "utf-8");

        // Mark all issues for this file as auto-fixed
        for (const issue of fileIssues) {
          issue.autoFixed = true;
        }
      }
    }

    // Re-run tsc to check if fixes resolved the errors
    tscResult = runTscCheck(projectRoot);
    if (tscResult.clean) break;

    // Add any new tsc errors that appeared after fixes
    const newTscIssues = parseTscErrors(tscResult.errors);
    for (const newIssue of newTscIssues) {
      const alreadyTracked = allIssues.some(
        (existing) =>
          existing.category === "typescript" &&
          existing.message === newIssue.message &&
          existing.file === newIssue.file,
      );
      if (!alreadyTracked) {
        allIssues.push(newIssue);
      }
    }
  }

  // Step 4: Design consistency check
  const designSystem = store.getDesignSystem();
  if (designSystem && pageOutputs.length > 1) {
    const pageFiles = pageOutputs
      .map((p) => path.isAbsolute(p.filePath) ? p.filePath : path.join(projectRoot, p.filePath))
      .filter((f) => fs.existsSync(f));

    const consistencyReport = await checkDesignConsistency(pageFiles, designSystem, pageOutputs);

    if (!consistencyReport.consistent) {
      for (const finding of consistencyReport.findings) {
        const issue: QAIssue = {
          file: finding.outlierPage,
          severity: "warning",
          category: "consistency",
          message: `${finding.type}: ${finding.description}`,
          autoFixed: false,
        };
        allIssues.push(issue);

        // Try to fix the outlier page
        const outlierPage = pageOutputs.find((p) => p.pageName === finding.outlierPage);
        if (outlierPage) {
          const fullPath = path.isAbsolute(outlierPage.filePath)
            ? outlierPage.filePath
            : path.join(projectRoot, outlierPage.filePath);
          if (fs.existsSync(fullPath)) {
            const code = fs.readFileSync(fullPath, "utf-8");
            const fixIssue: QAIssue = {
              file: fullPath,
              severity: "warning",
              category: "consistency",
              message: `Design consistency: ${finding.description}. Fix: ${finding.fix}`,
              autoFixed: false,
            };
            const fixed = await attemptAutoFix(client, fullPath, fixIssue, code);
            if (fixed) {
              fs.writeFileSync(fullPath, autoFixImports(fixed), "utf-8");
              issue.autoFixed = true;
            }
          }
        }
      }
    }
  }

  // Step 5: Visual regression via Playwright screenshots
  if (pageOutputs.length > 0) {
    const screenshots = await captureScreenshots(projectRoot, pageOutputs);
    if (screenshots.length > 1) {
      const visualResult = await reviewScreenshotsForConsistency(client, screenshots);
      if (!visualResult.consistent) {
        for (const visualIssue of visualResult.issues) {
          allIssues.push({
            file: "visual-regression",
            severity: "warning",
            category: "design",
            message: visualIssue,
            autoFixed: false,
          });
        }
      }
    }
  }

  // Step 6: Build QA report
  const issuesFixed = allIssues.filter((i) => i.autoFixed).length;
  const remainingIssues = allIssues.filter((i) => !i.autoFixed);
  const tscClean = tscResult.clean;

  const pageResults = pageOutputs.map((page) => {
    const issues = pageResultsMap.get(page.pageName) ?? [];
    const hasUnfixed = issues.some((i) => !i.autoFixed);
    return {
      pageName: page.pageName,
      passed: !hasUnfixed,
      issues,
    };
  });

  const report: QAReport = {
    allPassed: tscClean && remainingIssues.length === 0,
    totalIssues: allIssues.length,
    issuesFixed,
    remainingIssues,
    iterations,
    tscClean,
    pageResults,
  };

  // Step 7: Persist report
  store.setQAReport(report);

  return report;
}
