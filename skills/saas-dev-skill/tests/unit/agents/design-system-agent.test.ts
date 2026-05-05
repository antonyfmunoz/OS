import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

// ─── Mock response ──────────────────────────────────────────────────────────

const mockDesignSystemResponse = {
  aesthetic: "Bold industrial with electric accents",
  colorMode: "dark" as const,
  tokens: {
    colors: {
      primary: "#3b82f6",
      primaryHover: "#2563eb",
      primaryMuted: "#1e3a5f",
      secondary: "#8b5cf6",
      background: "#0f172a",
      surface: "#1e293b",
      text: "#e2e8f0",
      textSecondary: "#94a3b8",
    },
    typography: {
      fontFamily: "Inter",
      fontSizes: { xs: "0.75rem", sm: "0.875rem", base: "1rem", lg: "1.125rem", xl: "1.25rem", "2xl": "1.5rem", "3xl": "1.875rem", "4xl": "2.25rem" },
      fontWeights: { normal: 400, medium: 500, semibold: 600, bold: 700 },
      lineHeights: { tight: "1.25", normal: "1.5", relaxed: "1.75" },
    },
    spacing: { "0.5": "0.125rem", "1": "0.25rem", "2": "0.5rem", "4": "1rem", "8": "2rem" },
    borderRadius: { none: "0", sm: "0.125rem", md: "0.375rem", lg: "0.5rem", full: "9999px" },
    shadows: { sm: "0 1px 2px rgba(0,0,0,0.05)", md: "0 4px 6px rgba(0,0,0,0.1)", lg: "0 10px 15px rgba(0,0,0,0.1)", focus: "0 0 0 3px rgba(59,130,246,0.3)" },
    breakpoints: { sm: "640px", md: "768px", lg: "1024px", xl: "1280px" },
  },
  tailwindExtend: {
    colors: {
      primary: { DEFAULT: "#3b82f6", hover: "#2563eb", muted: "#1e3a5f" },
    },
    fontFamily: { sans: ["Inter", "system-ui", "sans-serif"] },
  },
  cssCustomProperties: `:root {\n  --color-primary: #3b82f6;\n  --color-background: #0f172a;\n  --font-family: 'Inter', system-ui, sans-serif;\n}\n\n.dark {\n  /* Dark mode overrides */\n}`,
  componentDesignGuide: "# Component Design Guide\n\n## Buttons\n\nPrimary: `bg-primary text-white rounded-md px-4 py-2`\nSecondary: `bg-secondary text-white rounded-md px-4 py-2`\nGhost: `bg-transparent text-primary hover:bg-primary/10`",
};

const mockStream = {
  finalMessage: vi.fn(),
};

vi.mock("@anthropic-ai/sdk", () => ({
  default: class MockAnthropic {
    messages = {
      stream: vi.fn().mockReturnValue(mockStream),
    };
  },
}));

vi.mock("../../../lib/env.js", () => ({
  getAnthropicApiKey: () => "sk-test",
  getAnthropicBaseUrl: () => "https://api.anthropic.com",
}));

vi.mock("../../../lib/spec-parser/restructure-spec.js", () => ({
  extractJsonFromResponse: vi.fn().mockImplementation((text: string) => JSON.parse(text)),
}));

// Mock the library research Claude call — the second stream call in the agent
// The first mockResolvedValue handles research, subsequent ones handle design system
const mockLibraryResearchResponse = {
  animationLibrary: "framer-motion",
  componentLibrary: "shadcn/ui",
  premiumComponents: ["magicui"],
  rationale: "framer-motion pairs well with React for smooth animations. shadcn/ui provides accessible primitives. magicui adds premium polish.",
  installCommands: ["npm install framer-motion"],
};

// ─── Import under test ──────────────────────────────────────────────────────

import { runDesignSystemAgent } from "../../../lib/agents/design-system-agent.js";
import { ArtifactStore } from "../../../lib/agents/artifact-store.js";
import type { ProductInsights } from "../../../lib/agents/types.js";
import type { ProjectBrief } from "../../../lib/intake/types.js";

// ─── Helpers ────────────────────────────────────────────────────────────────

let tmpDir: string;
let store: ArtifactStore;

function makeBrief(): ProjectBrief {
  return {
    productName: "TestApp",
    productDescription: "A test application for developers",
    productVision: "The best developer tool",
    targetUsers: ["developers", "engineers"],
    jobsToBeDone: ["Build faster"],
    brandVoice: "Direct and bold.",
    designSystem: "",
    techStack: { frontend: "react", buildTool: "vite", styling: "tailwind", componentLib: "shadcn/ui", language: "typescript" },
    authProvider: "clerk",
    dbProvider: "neon",
    deployTarget: "vps",
    spec: { pages: [], sharedComponents: [], suggestedOrder: [] },
    isGreenfield: true,
    existingCodeScanned: false,
    sourceDocs: [],
  };
}

function makeInsights(): ProductInsights {
  return {
    productCategory: "developer-tools",
    targetUserProfile: "Full-stack developers building SaaS",
    competitiveIntel: null,
    designRecommendations: ["Use dark mode", "Bold accents"],
    copyRecommendations: ["Be concise"],
    architectureRecommendations: [],
    marketPositioning: "Premium developer platform",
  };
}

// ─── Setup / Teardown ───────────────────────────────────────────────────────

beforeEach(() => {
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "design-system-test-"));
  store = new ArtifactStore(tmpDir);
  vi.clearAllMocks();

  // First call: library research, second call: design system generation
  mockStream.finalMessage
    .mockResolvedValueOnce({
      content: [{ type: "text", text: JSON.stringify(mockLibraryResearchResponse) }],
    })
    .mockResolvedValue({
      content: [{ type: "text", text: JSON.stringify(mockDesignSystemResponse) }],
    });
});

afterEach(() => {
  fs.rmSync(tmpDir, { recursive: true, force: true });
});

// ─── Tests ──────────────────────────────────────────────────────────────────

describe("runDesignSystemAgent", () => {
  it("calls Claude and returns a DesignSystem artifact", async () => {
    const result = await runDesignSystemAgent(makeBrief(), makeInsights(), store);

    expect(result).toBeDefined();
    expect(result.aesthetic).toBe("Bold industrial with electric accents");
    expect(result.colorMode).toBe("dark");
    expect(result.tokens.colors.primary).toBe("#3b82f6");
    expect(result.tokens.typography.fontFamily).toBe("Inter");
    expect(result.tailwindConfigPath).toBe("tailwind.config.ts");
    expect(result.cssCustomPropertiesPath).toBe("client/src/styles/design-system.css");
    expect(result.componentDesignGuidePath).toBe(".planning/artifacts/COMPONENT_DESIGN_GUIDE.md");
  });

  it("writes DesignSystem to ArtifactStore", async () => {
    expect(store.getDesignSystem()).toBeNull();

    await runDesignSystemAgent(makeBrief(), makeInsights(), store);

    const stored = store.getDesignSystem();
    expect(stored).not.toBeNull();
    expect(stored!.aesthetic).toBe("Bold industrial with electric accents");
    expect(stored!.tokens.colors.primary).toBe("#3b82f6");
  });

  it("writes tailwind.config.ts to disk", async () => {
    await runDesignSystemAgent(makeBrief(), makeInsights(), store);

    const tailwindPath = path.join(tmpDir, "tailwind.config.ts");
    expect(fs.existsSync(tailwindPath)).toBe(true);

    const content = fs.readFileSync(tailwindPath, "utf-8");
    expect(content).toContain("tailwindcss");
    expect(content).toContain("extend");
  });

  it("writes CSS custom properties file to disk", async () => {
    await runDesignSystemAgent(makeBrief(), makeInsights(), store);

    const cssPath = path.join(tmpDir, "client", "src", "styles", "design-system.css");
    expect(fs.existsSync(cssPath)).toBe(true);

    const content = fs.readFileSync(cssPath, "utf-8");
    expect(content).toContain("--color-primary");
  });

  it("writes component design guide to disk", async () => {
    await runDesignSystemAgent(makeBrief(), makeInsights(), store);

    const guidePath = path.join(tmpDir, ".planning", "artifacts", "COMPONENT_DESIGN_GUIDE.md");
    expect(fs.existsSync(guidePath)).toBe(true);

    const content = fs.readFileSync(guidePath, "utf-8");
    expect(content).toContain("Component Design Guide");
    expect(content).toContain("Buttons");
  });

  it("appends to build log on completion", async () => {
    await runDesignSystemAgent(makeBrief(), makeInsights(), store);

    const logPath = path.join(tmpDir, ".planning", "artifacts", "build-log.jsonl");
    expect(fs.existsSync(logPath)).toBe(true);

    const lines = fs.readFileSync(logPath, "utf-8").trim().split("\n");
    const lastEntry = JSON.parse(lines[lines.length - 1]);
    expect(lastEntry.agent).toBe("design-system");
    expect(lastEntry.event).toBe("completed");
  });

  it("throws when response is missing required token fields", async () => {
    const { extractJsonFromResponse } = await import("../../../lib/spec-parser/restructure-spec.js");
    const mockExtract = extractJsonFromResponse as ReturnType<typeof vi.fn>;

    // First call: library research (succeeds), second call: design system (bad)
    mockExtract
      .mockReturnValueOnce(mockLibraryResearchResponse)
      .mockReturnValueOnce({
        aesthetic: "test",
        colorMode: "light",
        tokens: {},
        tailwindExtend: {},
        cssCustomProperties: ":root {}",
        componentDesignGuide: "# Guide",
      });

    await expect(
      runDesignSystemAgent(makeBrief(), makeInsights(), store),
    ).rejects.toThrow("missing required token fields");
  });

  it("throws when response is missing tailwindExtend", async () => {
    const { extractJsonFromResponse } = await import("../../../lib/spec-parser/restructure-spec.js");
    const mockExtract = extractJsonFromResponse as ReturnType<typeof vi.fn>;

    // First call: library research (succeeds), second call: design system (bad)
    mockExtract
      .mockReturnValueOnce(mockLibraryResearchResponse)
      .mockReturnValueOnce({
        ...mockDesignSystemResponse,
        tailwindExtend: null,
      });

    await expect(
      runDesignSystemAgent(makeBrief(), makeInsights(), store),
    ).rejects.toThrow("missing tailwindExtend");
  });

  it("writes DESIGN_COMPLIANCE_CHECKLIST.md with dynamic library choices", async () => {
    await runDesignSystemAgent(makeBrief(), makeInsights(), store);

    const checklistPath = path.join(tmpDir, ".planning", "artifacts", "DESIGN_COMPLIANCE_CHECKLIST.md");
    expect(fs.existsSync(checklistPath)).toBe(true);

    const content = fs.readFileSync(checklistPath, "utf-8");
    expect(content).toContain("Design Compliance Checklist");
    expect(content).toContain("#3b82f6");
    expect(content).toContain("Inter");
    // Dynamic library choices from research, not hardcoded
    expect(content).toContain("framer-motion");
    expect(content).toContain("shadcn/ui");
    expect(content).toContain("magicui");
    expect(content).toContain("ZERO TOLERANCE");
    // Should NOT contain hardcoded component names
    expect(content).not.toContain("MagicCard used for card components");
    expect(content).not.toContain("NumberTicker used for numeric stats");
  });

  it("stores component library recommendations in artifact store", async () => {
    expect(store.getComponentLibraryRecommendations()).toBeNull();

    await runDesignSystemAgent(makeBrief(), makeInsights(), store);

    const recs = store.getComponentLibraryRecommendations();
    expect(recs).not.toBeNull();
    expect(recs!.animationLibrary).toBe("framer-motion");
    expect(recs!.componentLibrary).toBe("shadcn/ui");
    expect(recs!.premiumComponents).toContain("magicui");
  });

  it("merges into existing tailwind.config.ts when one exists", async () => {
    const existingConfig = `import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./client/**/*.tsx"],
  theme: {
    extend: {
      spacing: { "128": "32rem" },
    },
  },
  plugins: [],
};

export default config;
`;
    store.writeProjectFile("tailwind.config.ts", existingConfig);

    await runDesignSystemAgent(makeBrief(), makeInsights(), store);

    const content = store.readProjectFile("tailwind.config.ts")!;
    // Should contain both old and new content
    expect(content).toContain("extend");
    expect(content).toContain("colors");
  });
});
