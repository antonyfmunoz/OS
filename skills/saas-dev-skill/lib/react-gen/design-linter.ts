// lib/react-gen/design-linter.ts
// Programmatic checker that scans component code for design system violations.
// Runs after generation and before writing to disk to enforce design consistency.

import type { DesignSystem, DesignTokens } from "../agents/types.js";

export interface DesignViolation {
  file: string;
  line: number;
  violation: string;
  suggestion: string;
}

// ─── Helpers ────────────────────────────────────────────────────────────────

function getAllColors(tokens: DesignTokens): Set<string> {
  const colors = new Set<string>();
  for (const value of Object.values(tokens.colors)) {
    colors.add(value.toLowerCase());
  }
  return colors;
}

function isInsideImportOrComment(line: string): boolean {
  const trimmed = line.trim();
  return (
    trimmed.startsWith("import ") ||
    trimmed.startsWith("//") ||
    trimmed.startsWith("*") ||
    trimmed.startsWith("/*")
  );
}

// ─── Main Linter ────────────────────────────────────────────────────────────

export function lintDesignSystem(
  code: string,
  designSystem: DesignSystem,
  filePath: string,
): DesignViolation[] {
  const violations: DesignViolation[] = [];
  const lines = code.split("\n");
  const allowedColors = getAllColors(designSystem.tokens);
  const allowedFont = designSystem.tokens.typography.fontFamily.toLowerCase();

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const lineNum = i + 1;

    if (isInsideImportOrComment(line)) continue;

    // 1. Hardcoded hex colors not in design system
    const hexPattern = /#[0-9A-Fa-f]{3,8}\b/g;
    let hexMatch: RegExpExecArray | null;
    while ((hexMatch = hexPattern.exec(line)) !== null) {
      const hex = hexMatch[0].toLowerCase();
      // Allow common safe values
      if (hex === "#000" || hex === "#fff" || hex === "#ffffff" || hex === "#000000") continue;
      // Allow hex inside CSS variable references
      const beforeHex = line.slice(Math.max(0, hexMatch.index - 20), hexMatch.index);
      if (/var\s*\(\s*--/.test(beforeHex)) continue;
      // Allow in tailwind config objects where tokens are being defined
      if (/['"]?DEFAULT['"]?\s*:/.test(line)) continue;

      if (!allowedColors.has(hex)) {
        // Normalize 3-char to 6-char for comparison
        let normalized = hex;
        if (hex.length === 4) {
          normalized = `#${hex[1]}${hex[1]}${hex[2]}${hex[2]}${hex[3]}${hex[3]}`;
        }
        if (!allowedColors.has(normalized)) {
          violations.push({
            file: filePath,
            line: lineNum,
            violation: `Hardcoded color ${hexMatch[0]} is not in the design system`,
            suggestion: "Use a CSS variable (var(--color-*)) or Tailwind token class instead",
          });
        }
      }
    }

    // 2. Hardcoded font families not in design system (CSS and JSX camelCase)
    const fontFamilyPattern = /(?:font-family|fontFamily)\s*[:=]\s*['"]?([^;'"}\n]+)/gi;
    let fontMatch: RegExpExecArray | null;
    while ((fontMatch = fontFamilyPattern.exec(line)) !== null) {
      const fontValue = fontMatch[1].trim().toLowerCase();
      // Allow CSS variable references
      if (fontValue.includes("var(--")) continue;
      // Allow system font stacks
      if (fontValue.startsWith("system-ui") || fontValue.startsWith("inherit")) continue;
      // Check if the design system font is in the declaration
      if (!fontValue.includes(allowedFont)) {
        violations.push({
          file: filePath,
          line: lineNum,
          violation: `Font family "${fontMatch[1].trim()}" is not the design system font (${designSystem.tokens.typography.fontFamily})`,
          suggestion: `Use var(--font-family) or the font-sans Tailwind class`,
        });
      }
    }

    // Also check Tailwind font classes for non-system fonts
    const twFontPattern = /font-\[['"]([^'"]+)['"]\]/g;
    let twFontMatch: RegExpExecArray | null;
    while ((twFontMatch = twFontPattern.exec(line)) !== null) {
      const fontName = twFontMatch[1].toLowerCase();
      if (!fontName.includes(allowedFont) && fontName !== "inherit") {
        violations.push({
          file: filePath,
          line: lineNum,
          violation: `Arbitrary font "${twFontMatch[1]}" is not in the design system`,
          suggestion: `Use font-sans (maps to ${designSystem.tokens.typography.fontFamily})`,
        });
      }
    }

    // 3. Inline box-shadow without primary color tint (CSS and JSX camelCase)
    const boxShadowPattern = /(?:box-shadow|boxShadow)\s*[:=]\s*['"]?([^;'"}\n]+)/gi;
    let shadowMatch: RegExpExecArray | null;
    while ((shadowMatch = boxShadowPattern.exec(line)) !== null) {
      const shadowValue = shadowMatch[1].trim().toLowerCase();
      // Allow CSS variable references
      if (shadowValue.includes("var(--")) continue;
      // Allow none/inherit
      if (shadowValue === "none" || shadowValue === "inherit") continue;
      // Check if shadow uses rgba with a color from the system or is too generic
      const primaryHex = designSystem.tokens.colors.primary?.toLowerCase();
      if (primaryHex && !shadowValue.includes(primaryHex) && /rgba?\s*\(\s*0\s*,\s*0\s*,\s*0/.test(shadowValue)) {
        violations.push({
          file: filePath,
          line: lineNum,
          violation: "Box shadow uses generic black rgba instead of primary color tint",
          suggestion: `Tint shadows with the primary color or use var(--shadow-*) tokens`,
        });
      }
    }

    // 4. Arbitrary Tailwind color values (text-[#xxx], bg-[#xxx])
    const twArbitraryColorPattern = /(?:text|bg|border|ring|shadow|fill|stroke)-\[#[0-9A-Fa-f]{3,8}\]/g;
    let twColorMatch: RegExpExecArray | null;
    while ((twColorMatch = twArbitraryColorPattern.exec(line)) !== null) {
      violations.push({
        file: filePath,
        line: lineNum,
        violation: `Arbitrary Tailwind color "${twColorMatch[0]}" bypasses the design system`,
        suggestion: "Use a design token class (text-primary, bg-surface, border-border, etc.)",
      });
    }

    // 5. Inline style color properties with hardcoded values
    const inlineColorPattern = /(?:color|backgroundColor|borderColor|background)\s*:\s*['"]#[0-9A-Fa-f]{3,8}['"]/gi;
    let inlineMatch: RegExpExecArray | null;
    while ((inlineMatch = inlineColorPattern.exec(line)) !== null) {
      violations.push({
        file: filePath,
        line: lineNum,
        violation: `Inline style with hardcoded color: ${inlineMatch[0]}`,
        suggestion: "Use CSS variable: var(--color-*) or Tailwind class",
      });
    }
  }

  return violations;
}

// ─── Design Contract Generator ──────────────────────────────────────────────

export function generateDesignContract(tokens: DesignTokens): string {
  const colorEntries = Object.entries(tokens.colors)
    .map(([key, value]) => `  ${key}: '${value}'`)
    .join(",\n");

  const spacingEntries = Object.entries(tokens.spacing)
    .map(([key, value]) => `  '${key}': '${value}'`)
    .join(",\n");

  const radiusEntries = Object.entries(tokens.borderRadius)
    .map(([key, value]) => `  ${key}: '${value}'`)
    .join(",\n");

  const shadowEntries = Object.entries(tokens.shadows)
    .map(([key, value]) => `  ${key}: '${value.replace(/'/g, "\\'")}'`)
    .join(",\n");

  return `// AUTO-GENERATED by design-system-agent — do not edit manually.
// Every component imports this. Violating these constraints = TypeScript error.

export const COLORS = {
${colorEntries},
} as const;

export type ColorKey = keyof typeof COLORS;
export type PrimaryColor = typeof COLORS.primary;
export type AllowedColors = typeof COLORS[keyof typeof COLORS];

export const SPACING = {
${spacingEntries},
} as const;

export type SpacingKey = keyof typeof SPACING;

export const BORDER_RADIUS = {
${radiusEntries},
} as const;

export type RadiusKey = keyof typeof BORDER_RADIUS;

export const SHADOWS = {
${shadowEntries},
} as const;

export type ShadowKey = keyof typeof SHADOWS;

export const FONT_FAMILY = '${tokens.typography.fontFamily}' as const;

/** Helper that enforces only design system colors can be used inline */
export function designColor(color: AllowedColors): string {
  return color;
}

/** Helper that enforces only design system spacing values */
export function designSpacing(spacing: typeof SPACING[SpacingKey]): string {
  return spacing;
}
`;
}
