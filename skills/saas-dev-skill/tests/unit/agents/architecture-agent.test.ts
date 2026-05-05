import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

// ─── Mock Anthropic SDK ─────────────────────────────────────────────────────

const mockArchitecture = {
  dataModel: {
    entities: [
      {
        tableName: "users",
        fields: [
          { name: "id", type: "serial", nullable: false },
          { name: "email", type: "text", nullable: false },
        ],
        indexes: ["unique on email"],
        timestamps: true,
      },
    ],
    relationships: [],
    enums: [],
  },
  apiContracts: [
    {
      method: "GET",
      path: "/api/users",
      description: "List all users",
      authRequired: true,
      responseShape: { users: "User[]" },
      validationRules: [],
      relatedEntity: "users",
    },
  ],
  pages: [
    {
      name: "Dashboard",
      route: "/dashboard",
      authLevel: "authenticated",
      purpose: "Main view",
      components: ["Sidebar"],
      dataNeeds: ["/api/users"],
      mutations: [],
    },
  ],
  componentHierarchy: [
    { name: "Sidebar", purpose: "Navigation", props: [], usedByPages: ["Dashboard"], dependsOn: [] },
  ],
  userFlows: [
    { name: "Login", steps: ["Enter credentials", "Submit"] },
  ],
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

// ─── Import under test ──────────────────────────────────────────────────────

import { runArchitectureAgent, preAudit } from "../../../lib/agents/architecture-agent.js";
import { ArtifactStore } from "../../../lib/agents/artifact-store.js";
import type { ProductInsights } from "../../../lib/agents/types.js";
import type { ProjectBrief } from "../../../lib/intake/types.js";

// ─── Helpers ────────────────────────────────────────────────────────────────

let tmpDir: string;
let store: ArtifactStore;

function makeBrief(): ProjectBrief {
  return {
    productName: "TestApp",
    productDescription: "A test application",
    productVision: "",
    targetUsers: ["developers"],
    jobsToBeDone: [],
    brandVoice: "",
    designSystem: "",
    techStack: { frontend: "react", buildTool: "vite", styling: "tailwind", componentLib: "shadcn/ui", language: "typescript" },
    authProvider: "clerk",
    dbProvider: "neon",
    deployTarget: "vps",
    spec: {
      pages: [
        { name: "Dashboard", route: "/dashboard", purpose: "Main view", components: ["Sidebar"], authLevel: "authenticated", priority: 1, dependsOn: [], specVersion: 1, source: "explicit" as const, dataRequirements: [], apiEndpoints: [], validationRules: [], events: [], featureFlagCandidates: [] },
      ],
      sharedComponents: [],
      suggestedOrder: ["/dashboard"],
    },
    isGreenfield: true,
    existingCodeScanned: false,
    sourceDocs: [],
  };
}

function makeInsights(): ProductInsights {
  return {
    productCategory: "saas",
    targetUserProfile: "developers",
    competitiveIntel: null,
    designRecommendations: ["Use dark mode"],
    copyRecommendations: [],
    architectureRecommendations: ["Use REST API"],
    marketPositioning: "Developer tools",
  };
}

// ─── Setup / Teardown ───────────────────────────────────────────────────────

beforeEach(() => {
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "arch-agent-test-"));
  store = new ArtifactStore(tmpDir);
  vi.clearAllMocks();

  // Default: return valid architecture JSON
  mockStream.finalMessage.mockResolvedValue({
    content: [{ type: "text", text: JSON.stringify(mockArchitecture) }],
  });
});

afterEach(() => {
  fs.rmSync(tmpDir, { recursive: true, force: true });
});

// ─── Tests ──────────────────────────────────────────────────────────────────

describe("runArchitectureAgent", () => {
  it("calls Claude with correct system prompt and returns SystemArchitecture", async () => {
    const result = await runArchitectureAgent(makeBrief(), makeInsights(), store);

    expect(result).toBeDefined();
    // Users entity from mock — inference validation keeps it (already exists)
    expect(result.dataModel.entities[0].tableName).toBe("users");
    // Mock has 1 explicit endpoint; inference validation adds standard
    // settings endpoints (GET /api/users/me, PATCH /api/users/me)
    expect(result.apiContracts.length).toBeGreaterThanOrEqual(1);
    expect(result.apiContracts[0].path).toBe("/api/users");
    // Mock has 1 explicit page (Dashboard, authenticated); inference
    // validation adds standard pages: login, signup, forgot-password,
    // reset-password, 404, settings
    expect(result.pages.length).toBeGreaterThanOrEqual(1);
    expect(result.pages[0].name).toBe("Dashboard");
    // Verify standard pages were added by inference validation
    const pageRoutes = result.pages.map((p) => p.route);
    expect(pageRoutes).toContain("/login");
    expect(pageRoutes).toContain("/signup");
    expect(pageRoutes).toContain("/404");
    expect(pageRoutes).toContain("/settings");
    // Standard pages should be tagged with source: "standard"
    const settingsPage = result.pages.find((p) => p.route === "/settings");
    expect(settingsPage?.source).toBe("standard");
    expect(result.componentHierarchy).toHaveLength(1);
    expect(result.userFlows).toHaveLength(1);
  });

  it("writes SystemArchitecture to ArtifactStore", async () => {
    expect(store.getArchitecture()).toBeNull();

    await runArchitectureAgent(makeBrief(), makeInsights(), store);

    const stored = store.getArchitecture();
    expect(stored).not.toBeNull();
    expect(stored!.dataModel.entities[0].tableName).toBe("users");
  });

  it("retries on JSON parse error and succeeds on second attempt", async () => {
    const { extractJsonFromResponse } = await import("../../../lib/spec-parser/restructure-spec.js");
    const mockExtract = extractJsonFromResponse as ReturnType<typeof vi.fn>;

    // First call: throw parse error
    mockExtract.mockImplementationOnce(() => {
      throw new SyntaxError("Unexpected token");
    });
    // Second call (retry): return valid data
    mockExtract.mockImplementationOnce(() => mockArchitecture);

    // Need two stream responses — first for initial attempt, second for retry
    mockStream.finalMessage
      .mockResolvedValueOnce({
        content: [{ type: "text", text: "invalid json" }],
      })
      .mockResolvedValueOnce({
        content: [{ type: "text", text: JSON.stringify(mockArchitecture) }],
      });

    const result = await runArchitectureAgent(makeBrief(), makeInsights(), store);

    expect(result.dataModel.entities[0].tableName).toBe("users");
    expect(store.getArchitecture()).not.toBeNull();
  });

  it("throws when both attempts fail to parse", async () => {
    const { extractJsonFromResponse } = await import("../../../lib/spec-parser/restructure-spec.js");
    const mockExtract = extractJsonFromResponse as ReturnType<typeof vi.fn>;

    // Both calls throw
    mockExtract.mockImplementation(() => {
      throw new SyntaxError("Unexpected token");
    });

    mockStream.finalMessage.mockResolvedValue({
      content: [{ type: "text", text: "not json at all" }],
    });

    await expect(
      runArchitectureAgent(makeBrief(), makeInsights(), store),
    ).rejects.toThrow();
  });

  it("throws when API returns non-text content", async () => {
    mockStream.finalMessage.mockResolvedValue({
      content: [{ type: "tool_use", id: "t1", name: "test", input: {} }],
    });

    await expect(
      runArchitectureAgent(makeBrief(), makeInsights(), store),
    ).rejects.toThrow("unexpected response type");
  });
});

describe("preAudit", () => {
  it("scans existing codebase and returns audit results", () => {
    // Create mock server/routes.ts with route patterns
    const routesDir = path.join(tmpDir, "server");
    fs.mkdirSync(routesDir, { recursive: true });
    fs.writeFileSync(
      path.join(routesDir, "routes.ts"),
      `app.get("/api/users", handler);\napp.post("/api/auth/login", handler);`,
      "utf-8",
    );

    // Create mock shared/schema.ts with table definitions
    const sharedDir = path.join(tmpDir, "shared");
    fs.mkdirSync(sharedDir, { recursive: true });
    fs.writeFileSync(
      path.join(sharedDir, "schema.ts"),
      `export const users = pgTable("users", { id: serial() });\nexport const sessions = pgTable("sessions", { id: serial() });`,
      "utf-8",
    );

    // Create mock pages directory
    const pagesDir = path.join(tmpDir, "client", "src", "pages");
    fs.mkdirSync(pagesDir, { recursive: true });
    fs.writeFileSync(path.join(pagesDir, "dashboard-page.tsx"), "export default function Dashboard() {}", "utf-8");

    // Create mock storage.ts
    fs.writeFileSync(
      path.join(routesDir, "storage.ts"),
      `async getUser(id: number): Promise<User> {\n  return db.query();\n}\nasync createUser(data: InsertUser): Promise<User> {\n  return db.insert();\n}`,
      "utf-8",
    );

    const audit = preAudit(tmpDir, store);

    expect(audit.existingRoutes).toContain("GET /api/users");
    expect(audit.existingRoutes).toContain("POST /api/auth/login");
    expect(audit.existingTables).toContain("users");
    expect(audit.existingTables).toContain("sessions");
    expect(audit.existingPages).toContain("dashboard-page.tsx");
    expect(audit.existingStorageMethods).toContain("getUser");
    expect(audit.existingStorageMethods).toContain("createUser");
    expect(audit.scannedAt).toBeDefined();
  });

  it("stores audit in artifact store", () => {
    const audit = preAudit(tmpDir, store);

    const stored = store.getExistingCodebaseAudit();
    expect(stored).not.toBeNull();
    expect(stored!.scannedAt).toBe(audit.scannedAt);
  });

  it("returns empty arrays when directories do not exist", () => {
    const audit = preAudit(tmpDir, store);

    expect(audit.existingRoutes).toEqual([]);
    expect(audit.existingTables).toEqual([]);
    expect(audit.existingPages).toEqual([]);
    expect(audit.existingStorageMethods).toEqual([]);
  });
});
