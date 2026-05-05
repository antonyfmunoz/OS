import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { SpecOutputSchema } from "@shared/spec-schema";

// ─── Mock Anthropic SDK ───────────────────────────────────────────────────────

const mockSpecOutput = {
  pages: [
    {
      name: "Dashboard",
      route: "/dashboard",
      purpose: "Main analytics dashboard for authenticated users",
      components: ["StatsCard", "ActivityFeed", "ChartPanel"],
      authLevel: "authenticated",
      priority: 1,
      source: "explicit",
      dependsOn: [],
      specVersion: 1,
      layoutHint: "sidebar-main",
      emptyState: "No data yet. Start by adding your first record.",
      loadingState: "Loading your dashboard data...",
      errorState: "Failed to load data. Please refresh the page.",
      mobileConsiderations: "Stack cards vertically on mobile screens",
      dataRequirements: [
        {
          component: "StatsCard",
          fields: ["totalUsers", "revenue", "activeProjects"],
        },
      ],
      apiEndpoints: [{ endpoint: "/api/stats", source: "inferred" }],
      validationRules: [],
      events: [
        {
          name: "dashboard_viewed",
          trigger: "page load",
          properties: ["userId", "plan"],
          source: "inferred",
        },
      ],
      featureFlagCandidates: ["new-dashboard-layout"],
    },
    {
      name: "Login",
      route: "/login",
      purpose: "Authentication page for users to sign in",
      components: ["LoginForm", "SocialAuthButtons"],
      authLevel: "public",
      priority: 1,
      source: "inferred",
      dependsOn: [],
      specVersion: 1,
      emptyState: undefined,
      loadingState: "Authenticating...",
      errorState: "Invalid credentials. Please try again.",
      dataRequirements: [],
      apiEndpoints: [{ endpoint: "/api/auth/login", source: "inferred" }],
      validationRules: ["email must be valid", "password min 8 chars"],
      events: [
        {
          name: "login_attempted",
          trigger: "form submit",
          properties: ["method"],
          source: "inferred",
        },
      ],
      featureFlagCandidates: [],
    },
  ],
  sharedComponents: [
    {
      id: "shared-sidebar",
      name: "Sidebar",
      purpose: "Primary navigation sidebar",
      usedByPages: ["/dashboard"],
      props: ["currentRoute"],
      source: "inferred",
    },
  ],
  suggestedOrder: ["/login", "/dashboard"],
};

const mockCreate = vi.fn();

// Turn the create() mock's resolved value into a fake stream whose
// finalMessage() returns the same payload. This keeps existing tests
// that call mockCreate.mockResolvedValue({ content: [...] }) working
// after the streaming refactor.
const mockStream = vi.fn((...args: unknown[]) => {
  const resultPromise = mockCreate(...args);
  return {
    finalMessage: () => resultPromise,
  };
});

vi.mock("@anthropic-ai/sdk", () => ({
  default: vi.fn().mockImplementation(() => ({
    messages: {
      create: mockCreate,
      stream: mockStream,
    },
  })),
}));

vi.mock("p-retry", async (importOriginal) => {
  // Use actual p-retry behavior but allow mocking inside tests
  const actual = await importOriginal<typeof import("p-retry")>();
  return actual;
});

// ─── extractJsonFromResponse ──────────────────────────────────────────────────

describe("extractJsonFromResponse", () => {
  it("extracts JSON from plain text", async () => {
    const { extractJsonFromResponse } = await import(
      "../../../lib/spec-parser/restructure-spec.js"
    );
    const text = JSON.stringify({ hello: "world" });
    const result = extractJsonFromResponse(text);
    expect(result).toEqual({ hello: "world" });
  });

  it("extracts JSON from markdown fenced block (```json ... ```)", async () => {
    const { extractJsonFromResponse } = await import(
      "../../../lib/spec-parser/restructure-spec.js"
    );
    const text = "```json\n" + JSON.stringify({ hello: "world" }) + "\n```";
    const result = extractJsonFromResponse(text);
    expect(result).toEqual({ hello: "world" });
  });

  it("extracts JSON from markdown fenced block without language tag (``` ... ```)", async () => {
    const { extractJsonFromResponse } = await import(
      "../../../lib/spec-parser/restructure-spec.js"
    );
    const text = "```\n" + JSON.stringify({ hello: "world" }) + "\n```";
    const result = extractJsonFromResponse(text);
    expect(result).toEqual({ hello: "world" });
  });

  it("throws on invalid JSON", async () => {
    const { extractJsonFromResponse } = await import(
      "../../../lib/spec-parser/restructure-spec.js"
    );
    expect(() => extractJsonFromResponse("not valid json")).toThrow();
  });
});

// ─── restructureSpec ──────────────────────────────────────────────────────────

describe("restructureSpec", () => {
  beforeEach(() => {
    mockCreate.mockReset();
    mockCreate.mockResolvedValue({
      content: [{ type: "text", text: JSON.stringify(mockSpecOutput) }],
    });
  });

  it("returns a SpecOutput that passes SpecOutputSchema.parse()", async () => {
    const { restructureSpec } = await import(
      "../../../lib/spec-parser/restructure-spec.js"
    );
    const result = await restructureSpec(
      "Build a SaaS dashboard with analytics"
    );
    expect(() => SpecOutputSchema.parse(result)).not.toThrow();
  });

  it("output includes inferred authLevel for pages mentioning 'login'", async () => {
    const { restructureSpec } = await import(
      "../../../lib/spec-parser/restructure-spec.js"
    );
    const result = await restructureSpec("login page and dashboard");
    const loginPage = result.pages.find((p) => p.route === "/login");
    expect(loginPage).toBeDefined();
    expect(loginPage?.authLevel).toBe("public");
  });

  it("output includes emptyState, loadingState, errorState for data-driven pages", async () => {
    const { restructureSpec } = await import(
      "../../../lib/spec-parser/restructure-spec.js"
    );
    const result = await restructureSpec(
      "dashboard with analytics and user management"
    );
    const dashboard = result.pages.find((p) => p.route === "/dashboard");
    expect(dashboard?.emptyState).toBeDefined();
    expect(dashboard?.loadingState).toBeDefined();
    expect(dashboard?.errorState).toBeDefined();
  });

  it("marks AI-inferred items with source: 'inferred'", async () => {
    const { restructureSpec } = await import(
      "../../../lib/spec-parser/restructure-spec.js"
    );
    const result = await restructureSpec("build me a SaaS dashboard");
    const inferredPage = result.pages.find((p) => p.source === "inferred");
    // At least one page should be inferred (login page auto-added)
    expect(inferredPage).toBeDefined();
  });

  it("retries on transient failure then succeeds", async () => {
    mockCreate
      .mockRejectedValueOnce(new Error("transient network error"))
      .mockResolvedValue({
        content: [{ type: "text", text: JSON.stringify(mockSpecOutput) }],
      });

    const { restructureSpec } = await import(
      "../../../lib/spec-parser/restructure-spec.js"
    );
    const result = await restructureSpec("retry test input");
    expect(result.pages.length).toBeGreaterThan(0);
    expect(mockCreate).toHaveBeenCalledTimes(2);
  });
});

// ─── parseSpec ────────────────────────────────────────────────────────────────

describe("parseSpec", () => {
  beforeEach(() => {
    mockCreate.mockReset();
    mockCreate.mockResolvedValue({
      content: [{ type: "text", text: JSON.stringify(mockSpecOutput) }],
    });
  });

  it("accepts raw text and returns validated SpecOutput", async () => {
    const { parseSpec } = await import(
      "../../../lib/spec-parser/parse-spec.js"
    );
    const result = await parseSpec("My SaaS app with dashboard and analytics");
    expect(result.pages.length).toBeGreaterThan(0);
    expect(() => SpecOutputSchema.parse(result)).not.toThrow();
  });

  it("rejects input exceeding MAX_RAW_INPUT_SIZE with a clear error message", async () => {
    const { parseSpec, MAX_RAW_INPUT_SIZE } = await import(
      "../../../lib/spec-parser/parse-spec.js"
    );
    const oversized = "x".repeat(MAX_RAW_INPUT_SIZE + 1);
    await expect(parseSpec(oversized)).rejects.toThrow(
      /exceeds maximum size/i
    );
  });

  it("rejects empty string input", async () => {
    const { parseSpec } = await import(
      "../../../lib/spec-parser/parse-spec.js"
    );
    await expect(parseSpec("")).rejects.toThrow();
  });
});
