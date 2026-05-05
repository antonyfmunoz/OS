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

import { generateProjectCopy } from "../../../lib/copy-planner/copy-writer.js";
import { ProjectCopySchema } from "../../../lib/copy-planner/types.js";
import type { SpecOutput } from "@shared/spec-schema.js";
import type { ProjectBrief } from "../../../lib/intake/types.js";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeValidCopyResponse(pageNames: string[]): object {
  return {
    pages: pageNames.map((name) => ({
      pageName: name,
      pageHeading: `Welcome to ${name}`,
      pageSubheading: `Manage your ${name.toLowerCase()}`,
      sections: [{ name: "main", heading: "Overview", body: "Main content area." }],
      ctas: [{ id: "primary-action", label: "Get Started", context: "Main action button" }],
      emptyState: `No ${name.toLowerCase()} data yet. Create your first entry.`,
      errorMessages: { loadFailed: "Failed to load data. Try again." },
      placeholders: { search: `Search ${name.toLowerCase()}...` },
      helperText: { name: "Choose a descriptive name." },
      successMessages: { created: `${name} created successfully.` },
      navLabel: name,
    })),
    generatedAt: new Date().toISOString(),
    brandVoiceHash: "abc123def456",
  };
}

function mockStreamResponse(json: object) {
  mockStream.mockReturnValueOnce({
    finalMessage: () => Promise.resolve({
      content: [{ type: "text", text: JSON.stringify(json) }],
    }),
  });
}

const SPEC: SpecOutput = {
  pages: [
    { name: "Dashboard", route: "/dashboard", purpose: "Main view", components: ["sidebar"], authLevel: "authenticated", priority: 1, dependsOn: [], specVersion: 1, source: "explicit", dataRequirements: [], apiEndpoints: [], validationRules: [], events: [], featureFlagCandidates: [] },
    { name: "Login", route: "/login", purpose: "Auth", components: ["form"], authLevel: "public", priority: 1, dependsOn: [], specVersion: 1, source: "explicit", dataRequirements: [], apiEndpoints: [], validationRules: [], events: [], featureFlagCandidates: [] },
  ],
  sharedComponents: [],
  suggestedOrder: ["/login", "/dashboard"],
};

const BRIEF: ProjectBrief = {
  productName: "TestApp",
  productDescription: "A test application",
  productVision: "",
  targetUsers: ["developers"],
  jobsToBeDone: [],
  brandVoice: "# Brand Voice\nBe direct.",
  designSystem: "",
  techStack: { frontend: "react", buildTool: "vite", styling: "tailwind", componentLib: "shadcn/ui", language: "typescript" },
  authProvider: "clerk",
  dbProvider: "neon",
  deployTarget: "vps",
  spec: SPEC,
  isGreenfield: false,
  existingCodeScanned: false,
  sourceDocs: [],
};

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("generateProjectCopy", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("produces valid ProjectCopy from Claude response", async () => {
    const validResponse = makeValidCopyResponse(["Dashboard", "Login"]);
    mockStreamResponse(validResponse);

    const result = await generateProjectCopy(SPEC, "# Brand Voice\nBe direct.", BRIEF);

    expect(result.pages).toHaveLength(2);
    expect(result.pages[0].pageName).toBe("Dashboard");
    expect(result.pages[1].pageName).toBe("Login");
    expect(result.brandVoiceHash).toBeTruthy();
    expect(result.generatedAt).toBeTruthy();
  });

  it("all pages have required copy fields", async () => {
    const validResponse = makeValidCopyResponse(["Dashboard", "Login"]);
    mockStreamResponse(validResponse);

    const result = await generateProjectCopy(SPEC, "# Brand", BRIEF);

    for (const page of result.pages) {
      expect(page.pageHeading).toBeTruthy();
      expect(page.navLabel).toBeTruthy();
      expect(page.ctas.length).toBeGreaterThan(0);
      expect(page.emptyState).toBeTruthy();
    }
  });

  it("validates with Zod schema", async () => {
    const validResponse = makeValidCopyResponse(["Dashboard", "Login"]);
    mockStreamResponse(validResponse);

    const result = await generateProjectCopy(SPEC, "# Brand", BRIEF);
    const validation = ProjectCopySchema.safeParse(result);
    expect(validation.success).toBe(true);
  });

  it("retries once when first response fails validation", async () => {
    // First response: malformed (missing navLabel)
    mockStream.mockReturnValueOnce({
      finalMessage: () => Promise.resolve({
        content: [{ type: "text", text: JSON.stringify({ pages: [{ pageName: "X" }] }) }],
      }),
    });
    // Retry: valid
    const validResponse = makeValidCopyResponse(["Dashboard", "Login"]);
    mockStream.mockReturnValueOnce({
      finalMessage: () => Promise.resolve({
        content: [{ type: "text", text: JSON.stringify(validResponse) }],
      }),
    });

    const result = await generateProjectCopy(SPEC, "# Brand", BRIEF);
    expect(result.pages).toHaveLength(2);
    expect(mockStream).toHaveBeenCalledTimes(2);
  });
});
