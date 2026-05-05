// lib/react-gen/skill-loader.ts
// Loads design-relevant skill content from disk for injection into generation prompts.
// Reads from ~/.claude/skills/ and .claude/skills/ — gracefully skips missing files.
// Caches result since skills don't change mid-build.

import fs from "node:fs";
import path from "node:path";
import os from "node:os";

let cachedSkillContent: string | null = null;

/** Skill file paths to look for, in priority order. */
const SKILL_SEARCH_PATHS = [
  // Home-level skills (Claude Code installed skills)
  { base: () => path.join(os.homedir(), ".claude", "skills"), patterns: [
    "frontend-design/SKILL.md",
    "ui-ux-pro-max/SKILL.md",
    "magicui/SKILL.md",
    "21st-dev/SKILL.md",
  ]},
  // Project-level saas-dev skills
  { base: (root: string) => path.join(root, ".claude", "skills", "saas-dev", "skills"), patterns: [
    "react-gen/SKILL.md",
  ]},
];

/**
 * Extract the design philosophy / principles section from a skill file.
 * Strips metadata frontmatter and non-design sections.
 */
function extractDesignContent(content: string, fileName: string): string | null {
  // Remove YAML frontmatter
  const stripped = content.replace(/^---[\s\S]*?---\s*/m, "").trim();
  if (!stripped) return null;

  // For frontend-design skill: extract philosophy, principles, and spatial composition
  if (fileName.includes("frontend-design")) {
    return `DESIGN PHILOSOPHY (from frontend-design skill):\n${stripped}`;
  }

  // For UI/UX skill: extract guidelines and principles
  if (fileName.includes("ui-ux")) {
    return `UI/UX GUIDELINES (from ui-ux-pro-max skill):\n${stripped}`;
  }

  // For component library skills: extract usage guidance
  if (fileName.includes("magicui") || fileName.includes("21st")) {
    return `COMPONENT LIBRARY GUIDANCE (from ${fileName}):\n${stripped}`;
  }

  // For react-gen skill: extract design token enforcement notes
  if (fileName.includes("react-gen")) {
    // Only include the Design Token Enforcement and Self-Review sections
    const tokenMatch = stripped.match(/### Design Token Enforcement[\s\S]*?(?=###\s|$)/);
    const reviewMatch = stripped.match(/### Self-Review[\s\S]*?(?=###\s|$)/);
    const parts: string[] = [];
    if (tokenMatch) parts.push(tokenMatch[0].trim());
    if (reviewMatch) parts.push(reviewMatch[0].trim());
    return parts.length > 0
      ? `DESIGN ENFORCEMENT NOTES (from react-gen skill):\n${parts.join("\n\n")}`
      : null;
  }

  return null;
}

/**
 * Load all design-relevant skill content for injection into generation prompts.
 * Returns combined skill content formatted for system prompt injection.
 * Gracefully skips missing skills. Caches result.
 */
export async function loadDesignSkills(projectRoot: string): Promise<string> {
  if (cachedSkillContent !== null) return cachedSkillContent;

  const sections: string[] = [];

  for (const searchPath of SKILL_SEARCH_PATHS) {
    const baseDir = searchPath.base(projectRoot);
    for (const pattern of searchPath.patterns) {
      const fullPath = path.join(baseDir, pattern);
      try {
        if (fs.existsSync(fullPath)) {
          const content = fs.readFileSync(fullPath, "utf-8");
          const extracted = extractDesignContent(content, pattern);
          if (extracted) {
            sections.push(extracted);
          }
        }
      } catch {
        // Gracefully skip unreadable files
      }
    }
  }

  if (sections.length === 0) {
    cachedSkillContent = "";
    return cachedSkillContent;
  }

  cachedSkillContent = [
    "SKILL-INJECTED DESIGN PRINCIPLES:",
    "The following principles come from installed design skills.",
    "Apply these for spatial composition, motion, depth, and avoiding generic AI aesthetics.",
    "NOTE: The mandatory design rules (colors, fonts, tokens) below OVERRIDE any conflicting suggestions here.",
    "",
    ...sections,
  ].join("\n");

  return cachedSkillContent;
}

/**
 * Reset the cache — useful for testing.
 */
export function resetSkillCache(): void {
  cachedSkillContent = null;
}
