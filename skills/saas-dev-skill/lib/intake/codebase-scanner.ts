// lib/intake/codebase-scanner.ts
// Scans an existing codebase to extract what already exists.

import fs from "node:fs";
import path from "node:path";
import { detectFramework, type FrameworkDetectionResult } from "../detect-framework.js";

export interface CodebaseScan {
  framework: FrameworkDetectionResult;
  existingPages: string[];
  existingEndpoints: string[];
  existingTables: string[];
  hasAuth: boolean;
  hasDatabase: boolean;
}

/**
 * Scan an existing codebase and extract what's already built.
 */
export function scanCodebase(projectRoot: string): CodebaseScan {
  const framework = detectFrameworkFromRoot(projectRoot);
  const existingPages = scanPages(projectRoot);
  const existingEndpoints = scanEndpoints(projectRoot);
  const existingTables = scanTables(projectRoot);
  const hasAuth = detectAuth(projectRoot);
  const hasDatabase = detectDatabase(projectRoot);

  return {
    framework,
    existingPages,
    existingEndpoints,
    existingTables,
    hasAuth,
    hasDatabase,
  };
}

function detectFrameworkFromRoot(projectRoot: string): FrameworkDetectionResult {
  const pkgPath = path.join(projectRoot, "package.json");
  if (!fs.existsSync(pkgPath)) {
    return {
      framework: "unknown",
      detected: { react: false, vite: false, tailwind: false, shadcn: false },
      confidence: "LOW",
      missing: ["react", "vite", "tailwindcss", "shadcn/ui (@radix-ui packages or components.json)"],
    };
  }
  const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf-8"));
  const hasComponentsJson = fs.existsSync(path.join(projectRoot, "components.json"));
  return detectFramework(pkg, hasComponentsJson);
}

function scanPages(projectRoot: string): string[] {
  const pagesDir = path.join(projectRoot, "client", "src", "pages");
  if (!fs.existsSync(pagesDir)) return [];
  try {
    return fs.readdirSync(pagesDir)
      .filter((f) => f.endsWith(".tsx") || f.endsWith(".ts"))
      .map((f) => f.replace(/\.(tsx?|jsx?)$/, ""));
  } catch {
    return [];
  }
}

function scanEndpoints(projectRoot: string): string[] {
  const routesFile = path.join(projectRoot, "server", "routes.ts");
  if (!fs.existsSync(routesFile)) return [];
  try {
    const content = fs.readFileSync(routesFile, "utf-8");
    const endpoints: string[] = [];
    const re = /app\.(get|post|put|patch|delete)\s*\(\s*["'`](\/[^"'`]*)["'`]/gi;
    let match: RegExpExecArray | null;
    while ((match = re.exec(content)) !== null) {
      endpoints.push(`${match[1].toUpperCase()} ${match[2]}`);
    }
    return endpoints;
  } catch {
    return [];
  }
}

function scanTables(projectRoot: string): string[] {
  const schemaFile = path.join(projectRoot, "shared", "schema.ts");
  if (!fs.existsSync(schemaFile)) return [];
  try {
    const content = fs.readFileSync(schemaFile, "utf-8");
    const tables: string[] = [];
    const re = /pgTable\s*\(\s*["'`]([^"'`]+)["'`]/g;
    let match: RegExpExecArray | null;
    while ((match = re.exec(content)) !== null) {
      tables.push(match[1]);
    }
    return tables;
  } catch {
    return [];
  }
}

function detectAuth(projectRoot: string): boolean {
  const pkgPath = path.join(projectRoot, "package.json");
  if (!fs.existsSync(pkgPath)) return false;
  try {
    const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf-8"));
    const allDeps = { ...pkg.dependencies, ...pkg.devDependencies };
    return "@clerk/clerk-react" in allDeps || "@clerk/express" in allDeps ||
      "firebase" in allDeps || "firebase-admin" in allDeps ||
      "@supabase/supabase-js" in allDeps || "passport" in allDeps;
  } catch {
    return false;
  }
}

function detectDatabase(projectRoot: string): boolean {
  const pkgPath = path.join(projectRoot, "package.json");
  if (!fs.existsSync(pkgPath)) return false;
  try {
    const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf-8"));
    const allDeps = { ...pkg.dependencies, ...pkg.devDependencies };
    return "@neondatabase/serverless" in allDeps || "postgres" in allDeps ||
      "pg" in allDeps || "@supabase/supabase-js" in allDeps;
  } catch {
    return false;
  }
}

/**
 * Format codebase scan results as a human-readable summary.
 */
export function formatCodebaseSummary(scan: CodebaseScan): string {
  const lines: string[] = [];
  lines.push(`Framework: ${scan.framework.framework} (${scan.framework.confidence} confidence)`);
  if (scan.existingPages.length > 0) {
    lines.push(`Existing pages (${scan.existingPages.length}): ${scan.existingPages.join(", ")}`);
  }
  if (scan.existingEndpoints.length > 0) {
    lines.push(`Existing endpoints (${scan.existingEndpoints.length}): ${scan.existingEndpoints.slice(0, 10).join(", ")}${scan.existingEndpoints.length > 10 ? "..." : ""}`);
  }
  if (scan.existingTables.length > 0) {
    lines.push(`Existing tables (${scan.existingTables.length}): ${scan.existingTables.join(", ")}`);
  }
  lines.push(`Auth detected: ${scan.hasAuth}`);
  lines.push(`Database detected: ${scan.hasDatabase}`);
  return lines.join("\n");
}
