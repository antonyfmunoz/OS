import { describe, it, expect, vi, beforeEach, afterAll } from "vitest";

// ─── Mock Anthropic SDK ───────────────────────────────────────────────────────

const mockMessagesCreate = vi.fn();

vi.mock("@anthropic-ai/sdk", () => {
  return {
    default: vi.fn().mockImplementation(() => ({
      messages: {
        create: mockMessagesCreate,
      },
    })),
  };
});

// ─── Mock fetch ──────────────────────────────────────────────────────────────

const originalFetch = globalThis.fetch;

// ─── Import under test ────────────────────────────────────────────────────────

import {
  researchCompetitors,
  formatCompetitiveIntelReport,
  CompetitiveIntelSchema,
  CompetitorIntelSchema,
} from "../../../lib/intake/competitive-researcher.js";
import type { SpecOutput } from "@shared/spec-schema.js";

// ─── Helpers ──────────────────────────────────────────────────────────────────

const SPEC: SpecOutput = {
  pages: [
    { name: "Dashboard", route: "/dashboard", purpose: "Main view", components: [], authLevel: "authenticated", priority: 1, dependsOn: [], specVersion: 1, source: "explicit", dataRequirements: [], apiEndpoints: [], validationRules: [], events: [], featureFlagCandidates: [] },
  ],
  sharedComponents: [],
  suggestedOrder: ["/dashboard"],
};

function makeCompetitorResponse(name: string) {
  return {
    url: `https://${name.toLowerCase()}.com`,
    name,
    copyPatterns: ["Short imperative CTAs", "Benefit-led headings"],
    structurePatterns: ["Sidebar nav with collapsible sections"],
    uxPatterns: ["Progressive onboarding wizard"],
    whatToAdopt: ["CTA pattern: verb + outcome"],
    whatToAvoid: ["Dense feature comparison tables on landing"],
    rawNotes: `${name} has a clean SaaS dashboard approach.`,
  };
}

function makeSynthesisResponse() {
  return {
    synthesizedInsights: "Competitors favor clean dashboards with progressive disclosure.",
    copyInfluences: "Adopt short imperative CTAs. Avoid marketing jargon in app UI.",
    structureInfluences: "Consider sidebar nav with collapsible sections for deep pages.",
  };
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("researchCompetitors", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock fetch to return simple HTML
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      text: () => Promise.resolve("<html><body><h1>Competitor App</h1><p>Manage your business.</p></body></html>"),
    }) as unknown as typeof fetch;
  });

  afterAll(() => {
    globalThis.fetch = originalFetch;
  });

  it("produces CompetitiveIntel with correct shape for single competitor", async () => {
    // First call: analyze competitor
    mockMessagesCreate.mockResolvedValueOnce({
      content: [{ type: "text", text: JSON.stringify(makeCompetitorResponse("Competitor1")) }],
    });
    // Second call: synthesize
    mockMessagesCreate.mockResolvedValueOnce({
      content: [{ type: "text", text: JSON.stringify(makeSynthesisResponse()) }],
    });

    const result = await researchCompetitors(
      ["https://competitor1.com"],
      "# Brand Voice",
      SPEC,
    );

    expect(result.competitors).toHaveLength(1);
    expect(result.competitors[0].name).toBe("Competitor1");
    expect(result.competitors[0].copyPatterns.length).toBeGreaterThan(0);
    expect(result.synthesizedInsights).toBeTruthy();
    expect(result.copyInfluences).toBeTruthy();
    expect(result.structureInfluences).toBeTruthy();

    const validation = CompetitiveIntelSchema.safeParse(result);
    expect(validation.success).toBe(true);
  });

  it("synthesizes across multiple competitors", async () => {
    // Analyze competitor 1
    mockMessagesCreate.mockResolvedValueOnce({
      content: [{ type: "text", text: JSON.stringify(makeCompetitorResponse("AppA")) }],
    });
    // Analyze competitor 2
    mockMessagesCreate.mockResolvedValueOnce({
      content: [{ type: "text", text: JSON.stringify(makeCompetitorResponse("AppB")) }],
    });
    // Synthesize
    mockMessagesCreate.mockResolvedValueOnce({
      content: [{ type: "text", text: JSON.stringify(makeSynthesisResponse()) }],
    });

    const result = await researchCompetitors(
      ["https://appa.com", "https://appb.com"],
      "# Brand",
      SPEC,
    );

    expect(result.competitors).toHaveLength(2);
    expect(result.competitors[0].name).toBe("AppA");
    expect(result.competitors[1].name).toBe("AppB");
    expect(result.synthesizedInsights).toBeTruthy();
  });

  it("handles unreachable URLs gracefully", async () => {
    // Fetch fails
    globalThis.fetch = vi.fn().mockRejectedValue(new Error("ECONNREFUSED")) as unknown as typeof fetch;

    // Analysis still runs (from knowledge base)
    mockMessagesCreate.mockResolvedValueOnce({
      content: [{ type: "text", text: JSON.stringify(makeCompetitorResponse("Unreachable")) }],
    });
    // Synthesize
    mockMessagesCreate.mockResolvedValueOnce({
      content: [{ type: "text", text: JSON.stringify(makeSynthesisResponse()) }],
    });

    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const result = await researchCompetitors(
      ["https://unreachable.example.com"],
      "# Brand",
      SPEC,
    );

    expect(result.competitors).toHaveLength(1);
    expect(warnSpy).toHaveBeenCalledWith(
      expect.stringContaining("Could not fetch"),
    );
    warnSpy.mockRestore();
  });

  it("returns empty intel entries when Claude analysis fails", async () => {
    // Fetch succeeds
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      text: () => Promise.resolve("<html><body>Content</body></html>"),
    }) as unknown as typeof fetch;

    // Claude throws
    mockMessagesCreate.mockRejectedValueOnce(new Error("API error"));

    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const result = await researchCompetitors(
      ["https://failing.com"],
      "# Brand",
      SPEC,
    );

    expect(result.competitors).toHaveLength(1);
    expect(result.competitors[0].rawNotes).toContain("Analysis failed");
    // No synthesis since no valid patterns
    expect(result.synthesizedInsights).toBe("");
    warnSpy.mockRestore();
  });
});

describe("CompetitorIntelSchema", () => {
  it("validates a well-formed competitor intel object", () => {
    const result = CompetitorIntelSchema.safeParse(makeCompetitorResponse("Test"));
    expect(result.success).toBe(true);
  });

  it("applies defaults for missing arrays", () => {
    const result = CompetitorIntelSchema.safeParse({ url: "https://x.com", name: "X" });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.copyPatterns).toEqual([]);
      expect(result.data.structurePatterns).toEqual([]);
    }
  });
});

describe("formatCompetitiveIntelReport", () => {
  it("produces markdown with competitor sections", () => {
    const intel = {
      competitors: [makeCompetitorResponse("TestApp")],
      synthesizedInsights: "Key insight here.",
      copyInfluences: "Copy guide here.",
      structureInfluences: "Structure guide here.",
    };

    const md = formatCompetitiveIntelReport(intel);
    expect(md).toContain("# Competitive Intelligence Report");
    expect(md).toContain("## TestApp");
    expect(md).toContain("### Copy Patterns");
    expect(md).toContain("## Synthesized Insights");
    expect(md).toContain("## Copy Influences");
    expect(md).toContain("## Structure Influences");
  });
});

