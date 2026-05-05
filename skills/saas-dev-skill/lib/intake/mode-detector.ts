// lib/intake/mode-detector.ts
// Detects which intake mode to use based on project filesystem state.

import fs from "node:fs";
import path from "node:path";
import type { IntakeMode } from "./types.js";

/**
 * Detect the appropriate intake mode for a project.
 *
 * - 'existing-codebase': client/src/ or server/ exists with real files
 * - 'docs-only': .planning/ has PRD.md or REQUIREMENTS.md (but no code)
 * - 'greenfield': no code, no docs
 */
export function detectIntakeMode(projectRoot: string): IntakeMode {
  // Check for existing codebase
  const clientSrc = path.join(projectRoot, "client", "src");
  const serverDir = path.join(projectRoot, "server");

  if (hasRealFiles(clientSrc) || hasRealFiles(serverDir)) {
    return "existing-codebase";
  }

  // Check for planning docs
  const planningDir = path.join(projectRoot, ".planning");
  if (fs.existsSync(planningDir)) {
    const prdPath = path.join(planningDir, "PRD.md");
    const reqPath = path.join(planningDir, "REQUIREMENTS.md");
    if (fs.existsSync(prdPath) || fs.existsSync(reqPath)) {
      return "docs-only";
    }

    // Check for any spec files
    const specsDir = path.join(planningDir, "specs");
    if (fs.existsSync(specsDir)) {
      const specFiles = fs.readdirSync(specsDir).filter(
        (f) => f.endsWith(".md") || f.endsWith(".json"),
      );
      if (specFiles.length > 0) return "docs-only";
    }
  }

  return "greenfield";
}

function hasRealFiles(dir: string): boolean {
  if (!fs.existsSync(dir)) return false;
  try {
    const entries = fs.readdirSync(dir, { recursive: true }) as string[];
    return entries.some(
      (e) =>
        typeof e === "string" &&
        (e.endsWith(".ts") || e.endsWith(".tsx") || e.endsWith(".js") || e.endsWith(".jsx")),
    );
  } catch {
    return false;
  }
}
