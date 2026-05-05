// lib/intake/doc-scanner.ts
// Scans .planning/ directory for existing documentation and reads it all.

import fs from "node:fs";
import path from "node:path";

export interface ScannedDocs {
  prd: string | null;
  requirements: string | null;
  designSystem: string | null;
  brandVoice: string | null;
  specFiles: Array<{ path: string; content: string }>;
  sourceDocs: string[];
}

/**
 * Scan .planning/ for all known document types.
 * Returns content of each found doc, or null if not present.
 */
export function scanPlanningDocs(projectRoot: string): ScannedDocs {
  const planningDir = path.join(projectRoot, ".planning");
  const result: ScannedDocs = {
    prd: null,
    requirements: null,
    designSystem: null,
    brandVoice: null,
    specFiles: [],
    sourceDocs: [],
  };

  if (!fs.existsSync(planningDir)) return result;

  const tryRead = (relativePath: string): string | null => {
    const fullPath = path.join(planningDir, relativePath);
    if (fs.existsSync(fullPath)) {
      const content = fs.readFileSync(fullPath, "utf-8").trim();
      if (content) {
        result.sourceDocs.push(relativePath);
        return content;
      }
    }
    return null;
  };

  result.prd = tryRead("PRD.md");
  result.requirements = tryRead("REQUIREMENTS.md");
  result.designSystem = tryRead("design-system.md");
  result.brandVoice = tryRead("BRAND-VOICE.md");

  // Scan specs directory
  const specsDir = path.join(planningDir, "specs");
  if (fs.existsSync(specsDir)) {
    const files = fs.readdirSync(specsDir)
      .filter((f) => f.endsWith(".json") || f.endsWith(".md"))
      .sort();
    for (const file of files) {
      const fullPath = path.join(specsDir, file);
      const content = fs.readFileSync(fullPath, "utf-8").trim();
      if (content) {
        result.specFiles.push({ path: `specs/${file}`, content });
        result.sourceDocs.push(`specs/${file}`);
      }
    }
  }

  return result;
}

/**
 * Identify what's missing from scanned docs that intake needs to collect.
 * Returns a list of missing categories.
 */
export function identifyMissingDocs(docs: ScannedDocs): string[] {
  const missing: string[] = [];
  if (!docs.prd && !docs.requirements && docs.specFiles.length === 0) {
    missing.push("product-description");
  }
  if (!docs.designSystem) {
    missing.push("design-system");
  }
  if (!docs.brandVoice) {
    missing.push("brand-voice");
  }
  return missing;
}
