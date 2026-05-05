import { describe, it, expect, vi, beforeEach } from "vitest";

// ─── Mock Anthropic SDK ───────────────────────────────────────────────────────

const mockSpecOutput = {
  pages: [
    {
      name: "Dashboard",
      route: "/dashboard",
      purpose: "Main dashboard for authenticated users",
      components: ["StatsCard", "ActivityFeed"],
      authLevel: "authenticated",
      priority: 2,
      source: "explicit",
      dependsOn: [],
      specVersion: 1,
      dataRequirements: [],
      apiEndpoints: [],
      validationRules: [],
      events: [],
      featureFlagCandidates: [],
    },
    {
      name: "Login",
      route: "/login",
      purpose: "Authentication page",
      components: ["LoginForm"],
      authLevel: "public",
      priority: 1,
      source: "inferred",
      dependsOn: [],
      specVersion: 1,
      dataRequirements: [],
      apiEndpoints: [],
      validationRules: [],
      events: [],
      featureFlagCandidates: [],
    },
  ],
  sharedComponents: [],
  suggestedOrder: ["/login", "/dashboard"],
};

const mockCreate = vi.fn();

vi.mock("@anthropic-ai/sdk", () => ({
  default: vi.fn().mockImplementation(() => ({
    messages: {
      create: mockCreate,
    },
  })),
}));

// ─── QUESTION_SEQUENCE ────────────────────────────────────────────────────────

describe("QUESTION_SEQUENCE", () => {
  it("has exactly 5 stages in the correct order", async () => {
    const { QUESTION_SEQUENCE } = await import(
      "../../../lib/spec-parser/collaborative-flow.js"
    );
    expect(QUESTION_SEQUENCE).toHaveLength(5);
    expect(QUESTION_SEQUENCE[0]).toBe("vision");
    expect(QUESTION_SEQUENCE[1]).toBe("user-flows");
    expect(QUESTION_SEQUENCE[2]).toBe("pages");
    expect(QUESTION_SEQUENCE[3]).toBe("page-detail");
    expect(QUESTION_SEQUENCE[4]).toBe("implied");
  });
});

// ─── createInitialState ───────────────────────────────────────────────────────

describe("createInitialState", () => {
  it("returns state with stage vision, stageIndex 0, empty messages, null partialSpec, complete false", async () => {
    const { createInitialState } = await import(
      "../../../lib/spec-parser/collaborative-flow.js"
    );
    const state = createInitialState();
    expect(state.stage).toBe("vision");
    expect(state.stageIndex).toBe(0);
    expect(state.messages).toEqual([]);
    expect(state.references).toEqual([]);
    expect(state.partialSpec).toBeNull();
    expect(state.complete).toBe(false);
  });
});

// ─── buildSystemPromptForStage ────────────────────────────────────────────────

describe("buildSystemPromptForStage", () => {
  it("returns prompt containing product, audience, and problem for vision stage", async () => {
    const { buildSystemPromptForStage } = await import(
      "../../../lib/spec-parser/collaborative-flow.js"
    );
    const prompt = buildSystemPromptForStage("vision", "");
    const lower = prompt.toLowerCase();
    expect(lower).toMatch(/product|audience|problem/);
  });

  it("returns prompt containing user journeys for user-flows stage", async () => {
    const { buildSystemPromptForStage } = await import(
      "../../../lib/spec-parser/collaborative-flow.js"
    );
    const prompt = buildSystemPromptForStage("user-flows", "context here");
    const lower = prompt.toLowerCase();
    expect(lower).toMatch(/user journeys|core things a user does|user does/);
  });

  it("includes priorContext in the returned prompt", async () => {
    const { buildSystemPromptForStage } = await import(
      "../../../lib/spec-parser/collaborative-flow.js"
    );
    const priorContext = "UNIQUE_CONTEXT_12345";
    const prompt = buildSystemPromptForStage("pages", priorContext);
    expect(prompt).toContain(priorContext);
  });

  it("returns prompt for page-detail stage mentioning components or auth", async () => {
    const { buildSystemPromptForStage } = await import(
      "../../../lib/spec-parser/collaborative-flow.js"
    );
    const prompt = buildSystemPromptForStage("page-detail", "some context");
    const lower = prompt.toLowerCase();
    expect(lower).toMatch(/components|auth|data/);
  });

  it("returns prompt for implied stage mentioning error states or auth gates", async () => {
    const { buildSystemPromptForStage } = await import(
      "../../../lib/spec-parser/collaborative-flow.js"
    );
    const prompt = buildSystemPromptForStage("implied", "some context");
    const lower = prompt.toLowerCase();
    expect(lower).toMatch(/error|auth|empty|loading|implied/);
  });

  it("returns a non-empty string for every stage in QUESTION_SEQUENCE", async () => {
    const { buildSystemPromptForStage, QUESTION_SEQUENCE } = await import(
      "../../../lib/spec-parser/collaborative-flow.js"
    );
    for (const stage of QUESTION_SEQUENCE) {
      const prompt = buildSystemPromptForStage(stage, "");
      expect(typeof prompt).toBe("string");
      expect(prompt.length).toBeGreaterThan(0);
      // Must not fall through to the exhaustiveness default branch
      expect(prompt.toLowerCase()).not.toContain("unknown stage");
    }
  });

  it("reflects priorContext in the prompt for every stage so prior answers aren't re-asked", async () => {
    const { buildSystemPromptForStage, QUESTION_SEQUENCE } = await import(
      "../../../lib/spec-parser/collaborative-flow.js"
    );
    const priorContext = "SENTINEL_PRIOR_CTX_abc987";
    for (const stage of QUESTION_SEQUENCE) {
      const withCtx = buildSystemPromptForStage(stage, priorContext);
      const withoutCtx = buildSystemPromptForStage(stage, "");
      expect(withCtx).toContain(priorContext);
      expect(withCtx.length).toBeGreaterThan(withoutCtx.length);
    }
  });
});

// ─── isFlowComplete ───────────────────────────────────────────────────────────

describe("isFlowComplete", () => {
  it("returns false when stageIndex < 5 with no partialSpec", async () => {
    const { isFlowComplete, createInitialState } = await import(
      "../../../lib/spec-parser/collaborative-flow.js"
    );
    const state = createInitialState();
    expect(isFlowComplete(state)).toBe(false);
  });

  it("returns false when stageIndex < 5 even with partialSpec", async () => {
    const { isFlowComplete, createInitialState } = await import(
      "../../../lib/spec-parser/collaborative-flow.js"
    );
    const state = {
      ...createInitialState(),
      stageIndex: 3,
      partialSpec: { pages: [] },
    };
    expect(isFlowComplete(state)).toBe(false);
  });

  it("returns true when stageIndex >= 5 and partialSpec is populated", async () => {
    const { isFlowComplete, createInitialState } = await import(
      "../../../lib/spec-parser/collaborative-flow.js"
    );
    const state = {
      ...createInitialState(),
      stage: "implied" as const,
      stageIndex: 5,
      partialSpec: { pages: [{ name: "Dashboard" }] },
    };
    expect(isFlowComplete(state)).toBe(true);
  });

  it("returns false when stageIndex >= 5 but partialSpec is null", async () => {
    const { isFlowComplete, createInitialState } = await import(
      "../../../lib/spec-parser/collaborative-flow.js"
    );
    const state = {
      ...createInitialState(),
      stageIndex: 5,
      partialSpec: null,
    };
    expect(isFlowComplete(state)).toBe(false);
  });
});

// ─── extractSpecFromConversation ──────────────────────────────────────────────

describe("extractSpecFromConversation", () => {
  beforeEach(() => {
    mockCreate.mockReset();
    mockCreate.mockResolvedValue({
      content: [{ type: "text", text: JSON.stringify(mockSpecOutput) }],
    });
  });

  it("returns validated SpecOutput from a conversation history", async () => {
    const { extractSpecFromConversation } = await import(
      "../../../lib/spec-parser/collaborative-flow.js"
    );
    const { SpecOutputSchema } = await import("@shared/spec-schema");
    const messages = [
      { role: "user" as const, content: "I want to build a dashboard app" },
      { role: "assistant" as const, content: "Great! What problem does it solve?" },
      { role: "user" as const, content: "It helps track business metrics" },
    ];
    const result = await extractSpecFromConversation(messages);
    expect(() => SpecOutputSchema.parse(result)).not.toThrow();
    expect(result.pages.length).toBeGreaterThan(0);
  });
});
