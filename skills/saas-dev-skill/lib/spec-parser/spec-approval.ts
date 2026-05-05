// lib/spec-parser/spec-approval.ts
// Formats a GapAnalysis as a human-readable report for the approval gate.

import type { SpecOutput } from "@shared/spec-schema.js";
import type { GapAnalysis, GapItem } from "./gap-analyzer.js";

export { hasBlockingGaps } from "./gap-analyzer.js";

function formatItems(items: GapItem[], indent = ""): string {
  if (items.length === 0) return `${indent}None.\n`;
  return items
    .map(
      (g) =>
        `${indent}- **[${g.severity.toUpperCase()}]** ${g.description}\n` +
        `${indent}  Affected: ${g.affectedPages.length > 0 ? g.affectedPages.join(", ") : "global"}\n` +
        `${indent}  Resolution: ${g.suggestedResolution}`,
    )
    .join("\n\n");
}

export function formatGapReport(spec: SpecOutput, gaps: GapAnalysis): string {
  const projectName =
    spec.pages.length > 0 ? spec.pages[0].name : "Unknown Project";

  const blocking = [
    ...gaps.missingPages,
    ...gaps.missingFlows,
    ...gaps.missingStates,
    ...gaps.assumptions,
    ...gaps.questions,
  ].filter((g) => g.severity === "blocking");

  const recommended = [
    ...gaps.missingPages,
    ...gaps.missingFlows,
    ...gaps.missingStates,
    ...gaps.assumptions,
  ].filter((g) => g.severity === "recommended");

  const optional = [
    ...gaps.missingStates,
    ...gaps.suggestions,
  ].filter((g) => g.severity === "optional");

  const questions = gaps.questions;

  const sections: string[] = [];

  sections.push(`## Spec Gap Analysis — ${projectName}\n`);
  sections.push(`Analyzed ${spec.pages.length} pages.\n`);

  if (blocking.length > 0) {
    sections.push(`### Blocking Issues (must resolve before proceeding)\n`);
    sections.push(formatItems(blocking));
  }

  if (recommended.length > 0) {
    sections.push(`### Recommended Additions\n`);
    sections.push(formatItems(recommended));
  }

  if (gaps.suggestions.length > 0) {
    sections.push(`### Suggestions\n`);
    sections.push(formatItems(gaps.suggestions));
  }

  if (questions.length > 0) {
    sections.push(`### Questions\n`);
    sections.push(formatItems(questions));
  }

  if (optional.length > 0) {
    sections.push(`### Optional Improvements\n`);
    sections.push(formatItems(optional));
  }

  if (blocking.length > 0) {
    sections.push(
      `---\nTo proceed: resolve blocking issues and re-run spec phase.\nTo override: set SKIP_GAP_ANALYSIS=true in .env (not recommended).\n`,
    );
  } else {
    sections.push(`---\nNo blocking issues found. Spec is ready to lock.\n`);
  }

  return sections.join("\n");
}
