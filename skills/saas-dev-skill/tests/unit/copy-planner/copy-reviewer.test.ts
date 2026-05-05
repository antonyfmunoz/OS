import { describe, it, expect, vi, beforeEach } from "vitest";

// ─── Mock Anthropic SDK ───────────────────────────────────────────────────────

const mockStream = vi.fn();

vi.mock("@anthropic-ai/sdk", () => {
  return {
    default: vi.fn().mockImplementation(() => ({
      messages: {
        stream: mockStream,
      },
    })),
  };
});

// ─── Import under test ────────────────────────────────────────────────────────

import { reviewProjectCopy } from "../../../lib/copy-planner/copy-reviewer.js";
import type { ProjectCopy } from "../../../lib/copy-planner/types.js";

// ─── Helpers ──────────────────────────────────────────────────────────────────

const INPUT_COPY: ProjectCopy = {
  pages: [
    {
      pageName: "Dashboard",
      pageHeading: "Command Center",
      pageSubheading: "Your company at a glance",
      sections: [{ name: "kpis", heading: "Key Metrics" }],
      ctas: [{ id: "add-task", label: "Add Task", context: "Quick action" }],
      emptyState: "No data yet. Start by creating your first task.",
      errorMessages: { loadFailed: "Could not load dashboard." },
      placeholders: {},
      helperText: {},
      successMessages: {},
      navLabel: "Home",
    },
  ],
  generatedAt: new Date().toISOString(),
  brandVoiceHash: "abc123",
};

function makeReviewResponse(overallScore: number): object {
  return {
    overallScore,
    passed: overallScore >= 0.8,
    pageResults: [
      { pageName: "Dashboard", score: overallScore, issues: overallScore < 0.8 ? ["Heading too generic"] : [] },
    ],
    revisedCopy: {
      ...INPUT_COPY,
      pages: INPUT_COPY.pages.map((p) => ({
        ...p,
        pageHeading: overallScore >= 0.8 ? p.pageHeading : "Your Command Center",
      })),
    },
  };
}

function mockStreamResponse(json: object) {
  mockStream.mockReturnValueOnce({
    finalMessage: () => Promise.resolve({
      content: [{ type: "text", text: JSON.stringify(json) }],
    }),
  });
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("reviewProjectCopy", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns CopyReviewResult with correct shape", async () => {
    mockStreamResponse(makeReviewResponse(0.9));

    const result = await reviewProjectCopy(INPUT_COPY, "# Brand Voice");

    expect(result.overallScore).toBe(0.9);
    expect(result.passed).toBe(true);
    expect(result.pageResults).toHaveLength(1);
    expect(result.revisedCopy).toBeDefined();
    expect(result.revisedCopy.pages).toHaveLength(1);
  });

  it("passed is true when overallScore >= 0.8", async () => {
    mockStreamResponse(makeReviewResponse(0.85));

    const result = await reviewProjectCopy(INPUT_COPY, "# Brand");
    expect(result.passed).toBe(true);
  });

  it("passed is false when overallScore < 0.8", async () => {
    mockStreamResponse(makeReviewResponse(0.65));

    const result = await reviewProjectCopy(INPUT_COPY, "# Brand");
    expect(result.passed).toBe(false);
    expect(result.pageResults[0].issues.length).toBeGreaterThan(0);
  });

  it("revisedCopy is always present even when passed", async () => {
    mockStreamResponse(makeReviewResponse(0.95));

    const result = await reviewProjectCopy(INPUT_COPY, "# Brand");
    expect(result.revisedCopy).toBeDefined();
    expect(result.revisedCopy.pages.length).toBe(INPUT_COPY.pages.length);
  });

  it("revisedCopy preserves generatedAt and brandVoiceHash", async () => {
    mockStreamResponse(makeReviewResponse(0.9));

    const result = await reviewProjectCopy(INPUT_COPY, "# Brand");
    expect(result.revisedCopy.generatedAt).toBe(INPUT_COPY.generatedAt);
    expect(result.revisedCopy.brandVoiceHash).toBe(INPUT_COPY.brandVoiceHash);
  });
});
