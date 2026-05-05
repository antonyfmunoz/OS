import { describe, it, expect } from "vitest";
import { DESIGN_TOKENS, DESIGN_RULES } from "../../../lib/react-gen/design-tokens.js";

describe("DESIGN_TOKENS", () => {
  it("has all required color fields", () => {
    expect(DESIGN_TOKENS.colors.primary).toBe("#6a37d4");
    expect(DESIGN_TOKENS.colors.primaryHover).toBe("#5a2dc0");
    expect(DESIGN_TOKENS.colors.secondary).toBe("#6448b2");
    expect(DESIGN_TOKENS.colors.tertiary).toBe("#ae8dff");
    expect(DESIGN_TOKENS.colors.surface).toBe("#f5f6f7");
    expect(DESIGN_TOKENS.colors.background).toBe("#ffffff");
    expect(DESIGN_TOKENS.colors.onSurface).toBe("#2c2f30");
    expect(DESIGN_TOKENS.colors.onSurfaceVariant).toBe("#595c5d");
    expect(DESIGN_TOKENS.colors.outlineVariant).toBe("#abadae");
    expect(DESIGN_TOKENS.colors.surfaceContainerLow).toBe("#eff1f2");
  });

  it("has glassmorphism settings", () => {
    expect(DESIGN_TOKENS.glassmorphism.background).toBe("rgba(255,255,255,0.7)");
    expect(DESIGN_TOKENS.glassmorphism.backdropFilter).toBe("blur(16px)");
    expect(DESIGN_TOKENS.glassmorphism.shadow).toContain("rgba(106,55,212,0.08)");
  });

  it("has typography and spacing", () => {
    expect(DESIGN_TOKENS.borderRadius).toBe("12px");
    expect(DESIGN_TOKENS.font).toBe("Inter");
    expect(DESIGN_TOKENS.spacing.cardPadding).toBe("32px");
  });
});

describe("DESIGN_RULES", () => {
  it("contains all 14 mandatory rules", () => {
    expect(DESIGN_RULES).toContain("NO gradients");
    expect(DESIGN_RULES).toContain("Glassmorphism");
    expect(DESIGN_RULES).toContain("Ambient shadow");
    expect(DESIGN_RULES).toContain("NO 1px solid borders");
    expect(DESIGN_RULES).toContain("Inter font exclusively");
    expect(DESIGN_RULES).toContain("lucide-react icons exclusively");
    expect(DESIGN_RULES).toContain("shadcn/ui primitives");
    expect(DESIGN_RULES).toContain("12px border radius");
    expect(DESIGN_RULES).toContain("#000000");
    expect(DESIGN_RULES).toContain("32px padding");
    expect(DESIGN_RULES).toContain("surface-container-low");
    expect(DESIGN_RULES).toContain("UniversalLayout");
    expect(DESIGN_RULES).toContain("loading state, error state, empty state");
    expect(DESIGN_RULES).toContain("375px");
  });

  it("is a non-empty string", () => {
    expect(typeof DESIGN_RULES).toBe("string");
    expect(DESIGN_RULES.trim().length).toBeGreaterThan(100);
  });
});
