import { describe, it, expect } from "vitest";
import { lintDesignSystem, generateDesignContract } from "../../../lib/react-gen/design-linter.js";
import type { DesignSystem } from "../../../lib/agents/types.js";

// ─── Test fixture ───────────────────────────────────────────────────────────

function makeDesignSystem(): DesignSystem {
  return {
    tokens: {
      colors: {
        primary: "#3b82f6",
        primaryHover: "#2563eb",
        secondary: "#8b5cf6",
        background: "#0f172a",
        surface: "#1e293b",
        text: "#e2e8f0",
        textSecondary: "#94a3b8",
        border: "#334155",
      },
      typography: {
        fontFamily: "Inter",
        fontSizes: { xs: "0.75rem", sm: "0.875rem", base: "1rem", lg: "1.125rem", xl: "1.25rem", "2xl": "1.5rem", "3xl": "1.875rem", "4xl": "2.25rem" },
        fontWeights: { normal: 400, medium: 500, semibold: 600, bold: 700 },
        lineHeights: { tight: "1.25", normal: "1.5", relaxed: "1.75" },
      },
      spacing: { "1": "0.25rem", "2": "0.5rem", "4": "1rem", "8": "2rem" },
      borderRadius: { none: "0", sm: "0.125rem", md: "0.375rem", lg: "0.5rem", full: "9999px" },
      shadows: { sm: "0 1px 2px rgba(0,0,0,0.05)", md: "0 4px 6px rgba(0,0,0,0.1)", focus: "0 0 0 3px rgba(59,130,246,0.3)" },
      breakpoints: { sm: "640px", md: "768px", lg: "1024px", xl: "1280px" },
    },
    tailwindConfigPath: "tailwind.config.ts",
    cssCustomPropertiesPath: "client/src/styles/design-system.css",
    componentDesignGuidePath: ".planning/artifacts/COMPONENT_DESIGN_GUIDE.md",
    aesthetic: "Bold industrial",
    colorMode: "dark",
  };
}

// ─── lintDesignSystem tests ─────────────────────────────────────────────────

describe("lintDesignSystem", () => {
  it("returns no violations for clean code using CSS variables", () => {
    const code = `import { useQuery } from "@tanstack/react-query";
export default function DashboardPage() {
  return (
    <div className="bg-primary text-white p-4">
      <h1 style={{ color: 'var(--color-text)' }}>Dashboard</h1>
    </div>
  );
}`;
    const violations = lintDesignSystem(code, makeDesignSystem(), "dashboard.tsx");
    expect(violations).toEqual([]);
  });

  it("detects hardcoded hex colors not in the design system", () => {
    const code = `export default function Page() {
  return <div style={{ color: "#FF5733" }}>Hello</div>;
}`;
    const violations = lintDesignSystem(code, makeDesignSystem(), "page.tsx");
    expect(violations.length).toBeGreaterThan(0);
    expect(violations[0].violation).toContain("#FF5733");
    expect(violations[0].suggestion).toContain("CSS variable");
  });

  it("allows hex colors that ARE in the design system", () => {
    const code = `export default function Page() {
  return <div style={{ color: "#3b82f6" }}>Primary</div>;
}`;
    const violations = lintDesignSystem(code, makeDesignSystem(), "page.tsx");
    // The hex is in the design system, so no violation for the hex itself
    // But inline style with hardcoded color still triggers
    const hexViolations = violations.filter((v) => v.violation.includes("not in the design system"));
    expect(hexViolations).toEqual([]);
  });

  it("detects arbitrary Tailwind color values", () => {
    const code = `export default function Page() {
  return <div className="text-[#FF0000] bg-[#00FF00]">Bad</div>;
}`;
    const violations = lintDesignSystem(code, makeDesignSystem(), "page.tsx");
    const twViolations = violations.filter((v) => v.violation.includes("Arbitrary Tailwind color"));
    expect(twViolations.length).toBe(2);
  });

  it("detects hardcoded font families not in design system", () => {
    const code = `export default function Page() {
  return <div style={{ fontFamily: "Roboto, sans-serif" }}>Hello</div>;
}`;
    const violations = lintDesignSystem(code, makeDesignSystem(), "page.tsx");
    const fontViolations = violations.filter((v) => v.violation.includes("font"));
    expect(fontViolations.length).toBeGreaterThan(0);
    expect(fontViolations[0].violation).toContain("Roboto");
  });

  it("allows the design system font family", () => {
    const code = `export default function Page() {
  return <div style={{ fontFamily: "Inter, sans-serif" }}>Hello</div>;
}`;
    const violations = lintDesignSystem(code, makeDesignSystem(), "page.tsx");
    const fontViolations = violations.filter((v) => v.violation.includes("font"));
    expect(fontViolations).toEqual([]);
  });

  it("detects generic black box-shadow without primary tint", () => {
    const code = `export default function Page() {
  return <div style={{ boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1)" }}>Card</div>;
}`;
    const ds = makeDesignSystem();
    const violations = lintDesignSystem(code, ds, "page.tsx");
    const shadowViolations = violations.filter((v) => v.violation.includes("box shadow") || v.violation.includes("Box shadow"));
    expect(shadowViolations.length).toBeGreaterThan(0);
  });

  it("allows box-shadow using CSS variables", () => {
    const code = `export default function Page() {
  return <div style={{ boxShadow: "var(--shadow-md)" }}>Card</div>;
}`;
    const violations = lintDesignSystem(code, makeDesignSystem(), "page.tsx");
    const shadowViolations = violations.filter((v) => v.violation.includes("shadow"));
    expect(shadowViolations).toEqual([]);
  });

  it("skips import lines and comments", () => {
    const code = `import { something } from "#internal/module";
// color: #FF5733 this is a comment
export default function Page() {
  return <div>Clean</div>;
}`;
    const violations = lintDesignSystem(code, makeDesignSystem(), "page.tsx");
    expect(violations).toEqual([]);
  });

  it("includes correct file and line in violations", () => {
    const code = `export default function Page() {
  return <div className="text-[#AABBCC]">Bad</div>;
}`;
    const violations = lintDesignSystem(code, makeDesignSystem(), "my-page.tsx");
    expect(violations[0].file).toBe("my-page.tsx");
    expect(violations[0].line).toBe(2);
  });
});

// ─── generateDesignContract tests ───────────────────────────────────────────

describe("generateDesignContract", () => {
  it("generates valid TypeScript with all color tokens", () => {
    const ds = makeDesignSystem();
    const contract = generateDesignContract(ds.tokens);

    expect(contract).toContain("AUTO-GENERATED");
    expect(contract).toContain("export const COLORS");
    expect(contract).toContain("as const");
    expect(contract).toContain("#3b82f6");
    expect(contract).toContain("primary:");
    expect(contract).toContain("secondary:");
  });

  it("exports type helpers", () => {
    const contract = generateDesignContract(makeDesignSystem().tokens);

    expect(contract).toContain("export type ColorKey");
    expect(contract).toContain("export type PrimaryColor");
    expect(contract).toContain("export type AllowedColors");
    expect(contract).toContain("export function designColor");
  });

  it("includes spacing and border radius tokens", () => {
    const contract = generateDesignContract(makeDesignSystem().tokens);

    expect(contract).toContain("export const SPACING");
    expect(contract).toContain("export const BORDER_RADIUS");
    expect(contract).toContain("export const SHADOWS");
    expect(contract).toContain("export const FONT_FAMILY");
  });

  it("includes the correct font family", () => {
    const contract = generateDesignContract(makeDesignSystem().tokens);
    expect(contract).toContain("'Inter'");
  });
});
